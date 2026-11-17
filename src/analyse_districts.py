"""
Analyse district par district :
  1. lien entre la pluie (cumul 4 semaines) et les cas, selon le décalage ;
  2. prévisions hors échantillon (52 dernières semaines, origine glissante)
     pour chaque district, évaluées uniquement sur les semaines réellement
     observées (les semaines imputées ne servent pas de « vérité »).

Modèles : naïf, naïf saisonnier, ARIMA (par district), XGBoost local
(un modèle par district) et XGBoost global (un seul modèle entraîné sur
tous les districts à la fois, en échelle logarithmique).

Usage : python analyse_districts.py --data df.xls --climat climat_hebdo.csv \
            --geojson districts_sante.geojson --out districts
"""
import argparse
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

from pipeline_typhoide import (SEASON, XGB_PARAMS, charger_donnees, choisir_ordre_arima,
                               construire_features, imputer, prevoir_arima)

warnings.filterwarnings("ignore")
N_TEST = 52
HORIZONS = [1, 4]


# ----------------------------------------------------------------------------
# 1. Pluie et cas, par district
# ----------------------------------------------------------------------------
def correlations_district(y: pd.Series, pluie: pd.Series, max_lag=12):
    """Cas sans tendance (ratio à la moyenne mobile 52 sem.) vs pluie 4 sem."""
    tend = y.rolling(52, center=True, min_periods=26).mean()
    yd = y / tend.replace(0, np.nan)
    p4 = pluie.rolling(4).sum()
    sem = p4.index.isocalendar().week.values
    anom = p4 - p4.groupby(sem).transform("mean")
    c = [yd.corr(p4.shift(k).reindex(y.index)) for k in range(max_lag + 1)]
    a = [yd.corr(anom.shift(k).reindex(y.index)) for k in range(max_lag + 1)]
    k = int(np.nanargmax(c))
    return dict(corr_max=c[k], decalage_max=k, corr_lag8=c[8], corr_anomalie_lag8=a[8])


# ----------------------------------------------------------------------------
# 2. Modèles
# ----------------------------------------------------------------------------
def xgb_local(hist: pd.Series, h: int) -> float:
    X = construire_features(hist)
    sem = hist.index.isocalendar().week.astype(int).values
    sem_c = (sem + h - 1) % 52 + 1
    X["sin_sem"], X["cos_sem"] = np.sin(2 * np.pi * sem_c / 52), np.cos(2 * np.pi * sem_c / 52)
    X["meme_sem_an_passe"] = hist.shift(SEASON - h)
    cible = hist.shift(-h) - hist
    ok = X.notna().all(axis=1) & cible.notna()
    m = xgb.XGBRegressor(**XGB_PARAMS).fit(X[ok], cible[ok])
    return hist.iloc[-1] + m.predict(X.iloc[[-1]])[0]


def table_globale(Y: pd.DataFrame, h: int) -> pd.DataFrame:
    """Une ligne par (semaine, district), en log(1 + cas)."""
    L = np.log1p(Y)
    blocs = []
    for d in Y.columns:
        y = L[d]
        X = construire_features(y)
        sem = y.index.isocalendar().week.astype(int).values
        sem_c = (sem + h - 1) % 52 + 1
        X["sin_sem"], X["cos_sem"] = np.sin(2 * np.pi * sem_c / 52), np.cos(2 * np.pi * sem_c / 52)
        X["meme_sem_an_passe"] = y.shift(SEASON - h)
        X["niveau_district"] = y.expanding().mean()      # passé uniquement
        X["cible"] = y.shift(-h) - y
        X["district"] = d
        blocs.append(X)
    return pd.concat(blocs)


def xgb_global(T: pd.DataFrame, origine) -> pd.Series:
    """Entraîne sur toutes les lignes dont la cible est connue à l'origine,
    puis prédit la ligne 'origine' de chaque district."""
    feats = [c for c in T.columns if c not in ("cible", "district")]
    h_ok = T.index <= origine
    train = T[h_ok & T["cible"].notna()]
    # la cible y(t+h) doit être connue à l'origine : t + h <= origine
    train = train[train.index <= origine - pd.Timedelta(weeks=T.attrs["h"])]
    train = train.dropna(subset=feats)
    m = xgb.XGBRegressor(**XGB_PARAMS).fit(train[feats], train["cible"])
    ligne = T[T.index == origine]
    pred_log = ligne[feats[0]].values + m.predict(ligne[feats])   # lag_0 + variation
    return pd.Series(np.expm1(pred_log), index=ligne["district"].values)


# ----------------------------------------------------------------------------
def main():
    global N_TEST
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="df.xls")
    ap.add_argument("--climat", default="climat_hebdo.csv")
    ap.add_argument("--geojson", default="districts_sante.geojson")
    ap.add_argument("--out", default="districts")
    ap.add_argument("--n_test", type=int, default=N_TEST)
    a = ap.parse_args()
    N_TEST = a.n_test
    out = Path(a.out); out.mkdir(exist_ok=True)

    brut = charger_donnees(a.data)
    Y = imputer(brut)
    observe = brut.notna()
    clim = pd.read_csv(a.climat, parse_dates=["date"])
    n = len(Y); debut = n - N_TEST
    origines = Y.index[debut - 1: n - 1]

    # --- 1. corrélations
    lignes = []
    for d in Y.columns:
        pl = clim[clim.district == d].set_index("date")["pluie_mm"]
        r = correlations_district(Y[d], pl)
        r.update(district=d, pct_manquant=round(brut[d].isna().mean() * 100, 1),
                 cas_moyens=round(brut[d].mean(), 1))
        lignes.append(r)
    corr = pd.DataFrame(lignes).set_index("district")
    print("Corrélations calculées.")

    # --- 2. prévisions
    prev = []
    tables = {h: table_globale(Y, h) for h in HORIZONS}
    for h, T in tables.items():
        T.attrs["h"] = h
    for i, t in enumerate(origines):
        for h in HORIZONS:
            g = xgb_global(tables[h], t)
            for d in Y.columns:
                prev.append(dict(district=d, modele="XGBoost global", horizon=h,
                                 origine=t, prevu=g[d]))
    print("XGBoost global terminé.")

    for j, d in enumerate(Y.columns):
        y = Y[d]
        ordre = choisir_ordre_arima(y.iloc[:debut])
        for t in origines:
            hist = y.loc[:t]
            try:
                ar = prevoir_arima(hist, ordre)
            except Exception:
                ar = np.repeat(hist.iloc[-1], max(HORIZONS))
            for h in HORIZONS:
                prev += [
                    dict(district=d, modele="Naïf", horizon=h, origine=t, prevu=hist.iloc[-1]),
                    dict(district=d, modele="Naïf saisonnier", horizon=h, origine=t,
                         prevu=hist.iloc[-SEASON + h - 1]),
                    dict(district=d, modele="ARIMA", horizon=h, origine=t, prevu=ar[h - 1]),
                    dict(district=d, modele="XGBoost local", horizon=h, origine=t,
                         prevu=xgb_local(hist, h)),
                ]
        print(f"  {j + 1}/{Y.shape[1]} {d} (ARIMA {ordre})", flush=True)

    P = pd.DataFrame(prev)
    P["prevu"] = P["prevu"].clip(lower=0)
    idx = {t: k for k, t in enumerate(Y.index)}
    P["date_cible"] = [Y.index[idx[o] + h] if idx[o] + h < n else pd.NaT
                       for o, h in zip(P.origine, P.horizon)]
    P = P.dropna(subset=["date_cible"])
    P["reel"] = [Y.at[t, d] for t, d in zip(P.date_cible, P.district)]
    P["observe"] = [observe.at[t, d] for t, d in zip(P.date_cible, P.district)]
    P.to_csv(out / "previsions_districts.csv", index=False)

    # --- 3. métriques, sur les semaines réellement observées
    E = P[P.observe].assign(ae=lambda x: (x.reel - x.prevu).abs())
    mae = E.groupby(["horizon", "district", "modele"])["ae"].mean().unstack("modele")
    rel = mae.div(mae["Naïf"], axis=0)             # < 1 : meilleur que le naïf
    resume = pd.DataFrame({
        "MAE_rel_mediane": rel.groupby("horizon").median().stack(),
        "districts_meilleurs_que_naif": (rel < 1).groupby("horizon").sum().stack(),
    }).round(3)
    resume.to_csv(out / "resume_modeles.csv")
    print("\n", resume.to_string())

    for h in HORIZONS:
        corr[f"MAE_rel_xgbglobal_h{h}"] = rel.loc[h, "XGBoost global"].round(3)
        corr[f"meilleur_modele_h{h}"] = rel.loc[h].drop(columns="Naïf saisonnier").idxmin(axis=1)
    corr = corr.round(3)
    corr.to_csv(out / "tableau_districts.csv")

    s = spearmanr(corr.pct_manquant, corr.MAE_rel_xgbglobal_h4, nan_policy="omit")
    s2 = spearmanr(corr.cas_moyens, corr.MAE_rel_xgbglobal_h4, nan_policy="omit")
    print(f"\nSpearman % manquant vs erreur relative (h=4) : rho={s.statistic:.2f}, p={s.pvalue:.3f}")
    print(f"Spearman cas moyens vs erreur relative (h=4) : rho={s2.statistic:.2f}, p={s2.pvalue:.3f}")

    # --- 4. cartes
    geo = json.load(open(a.geojson, encoding="utf-8"))["features"]
    cartes = [("corr_lag8", "Corrélation cas / pluie (décalage 8 sem.)", "RdBu_r", -0.8, 0.8),
              ("MAE_rel_xgbglobal_h4", "Erreur XGBoost global / naïf (h = 4)\n< 1 : meilleur que le naïf",
               "RdYlGn_r", 0.5, 1.5),
              ("pct_manquant", "Semaines manquantes (%)", "Oranges", 0, 55)]
    fig, axes = plt.subplots(1, 3, figsize=(15, 7))
    for ax, (col, titre, cmap, vmin, vmax) in zip(axes, cartes):
        norm = plt.Normalize(vmin, vmax); cm = plt.get_cmap(cmap)
        for f in geo:
            d = f["properties"]["district"]; g = f["geometry"]
            polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            for p in polys:
                xs, ys = zip(*p[0])
                v = corr.at[d, col]
                ax.fill(xs, ys, color=cm(norm(v)) if pd.notna(v) else "#ddd", ec="#555", lw=0.4)
        ax.set_aspect("equal"); ax.axis("off"); ax.set_title(titre, fontsize=10)
        plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cm), ax=ax, shrink=0.6)
    fig.tight_layout(); fig.savefig(out / "cartes_districts.png", dpi=200); plt.close(fig)
    print("Terminé.")


if __name__ == "__main__":
    main()
