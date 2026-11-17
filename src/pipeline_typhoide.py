"""
Prévision hebdomadaire des cas de fièvre typhoïde - Extrême-Nord du Cameroun
Pipeline reproductible : chargement -> imputation -> agrégation -> évaluation
par origine glissante (rolling origin) de 5 modèles sur les mêmes semaines test.

Auteur : Kazoune Bouba Israel
Usage  : python pipeline_typhoide.py --data df.xls --out resultats
"""
import argparse
import logging
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

# ----------------------------------------------------------------------------
# Paramètres de l'expérience (tous fixés à l'avance, rien n'est réglé sur le test)
# ----------------------------------------------------------------------------
SEED = 123
N_TEST = 52            # dernières semaines utilisées comme test (≈ 2023)
HORIZONS = [1, 4]      # prévision à 1 semaine et à 4 semaines
SEASON = 52            # saisonnalité annuelle en semaines
XGB_PARAMS = dict(n_estimators=300, max_depth=3, learning_rate=0.05,
                  subsample=0.8, colsample_bytree=0.8, random_state=SEED)


# ----------------------------------------------------------------------------
# 1. Données
# ----------------------------------------------------------------------------
def charger_donnees(chemin: str) -> pd.DataFrame:
    """Lit la base hebdomadaire (une colonne par district) et indexe par date."""
    df = pd.read_excel(chemin)
    df["date"] = pd.to_datetime(df["date"].astype(str).str.extract(r"(\d{4}-\d{2}-\d{2})")[0])
    df = df.set_index("date").sort_index()
    df.columns = [c.replace("District ", "").strip() for c in df.columns]
    return df.astype(float)


def imputer(df: pd.DataFrame) -> pd.DataFrame:
    """Interpolation linéaire par district (équivalent simple de l'interpolation
    de Stineman utilisée dans le mémoire), puis arrondi à l'entier."""
    return df.interpolate(method="linear", limit_direction="both").round()


def rapport_qualite(df: pd.DataFrame) -> pd.DataFrame:
    q = pd.DataFrame({
        "semaines_manquantes": df.isna().sum(),
        "pct_manquant": (df.isna().mean() * 100).round(1),
        "moyenne_cas": df.mean().round(1),
    })
    return q.sort_values("pct_manquant", ascending=False)


# ----------------------------------------------------------------------------
# 2. Modèles : chacun prend l'historique connu (jusqu'à l'origine incluse)
#    et renvoie les prévisions pour les horizons 1..H_MAX
# ----------------------------------------------------------------------------
H_MAX = max(HORIZONS)


def prevoir_naif(hist: pd.Series) -> np.ndarray:
    return np.repeat(hist.iloc[-1], H_MAX)


def prevoir_naif_saisonnier(hist: pd.Series) -> np.ndarray:
    return np.array([hist.iloc[-SEASON + h - 1] for h in range(1, H_MAX + 1)])


def choisir_ordre_arima(train: pd.Series):
    """Sélection automatique de l'ordre (p,d,q) sur la période d'entraînement
    initiale uniquement, puis ordre figé pour toutes les origines.
    d : test KPSS (comme auto.arima) ; p et q : AIC minimal sur une grille 0..3."""
    from statsmodels.tsa.stattools import kpss
    d = 1 if kpss(train.values, regression="c", nlags="auto")[1] < 0.05 else 0
    meilleur, ordre = np.inf, (0, d, 0)
    for p in range(4):
        for q in range(4):
            try:
                aic = ARIMA(train.values, order=(p, d, q)).fit().aic
            except Exception:
                continue
            if aic < meilleur:
                meilleur, ordre = aic, (p, d, q)
    return ordre


def prevoir_arima(hist: pd.Series, ordre) -> np.ndarray:
    fit = ARIMA(hist.values, order=ordre).fit()
    return np.asarray(fit.forecast(H_MAX))


def prevoir_prophet(hist: pd.Series) -> np.ndarray:
    from prophet import Prophet
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                daily_seasonality=False)
    m.fit(pd.DataFrame({"ds": hist.index, "y": hist.values}))
    futur = m.make_future_dataframe(periods=H_MAX, freq="W-MON", include_history=False)
    return m.predict(futur)["yhat"].values


def construire_features(y: pd.Series) -> pd.DataFrame:
    """Variables connues à la date t (aucune information future)."""
    X = pd.DataFrame(index=y.index)
    for k in range(0, 4):
        X[f"lag_{k}"] = y.shift(k)
    X["moy_4"] = y.rolling(4).mean()
    X["moy_13"] = y.rolling(13).mean()
    return X


def features_climat(clim: pd.DataFrame) -> pd.DataFrame:
    """Variables climatiques connues à la date t (passé uniquement).
    Les décalages couvrent l'effet retardé de la pluie (2 à 8 semaines)."""
    X = pd.DataFrame(index=clim.index)
    pluie4 = clim["pluie_mm"].rolling(4).sum()
    X["pluie_4sem"] = pluie4                 # pluie des 4 dernières semaines
    X["pluie_4sem_lag4"] = pluie4.shift(4)   # pluie d'il y a 5 à 8 semaines
    X["temp_4sem"] = clim["temp_moy"].rolling(4).mean()
    X["humid_4sem"] = clim["humidite"].rolling(4).mean()
    return X


def prevoir_xgboost(hist: pd.Series, clim: pd.DataFrame = None) -> np.ndarray:
    """Stratégie directe : un modèle par horizon. La cible est la variation
    y(t+h) - y(t), car les arbres ne savent pas extrapoler une tendance."""
    X = construire_features(hist)
    if clim is not None:
        X = X.join(features_climat(clim).reindex(hist.index))
    sem = hist.index.isocalendar().week.astype(int).values
    preds = []
    for h in range(1, H_MAX + 1):
        Xh = X.copy()
        sem_cible = (sem + h - 1) % 52 + 1
        Xh["sin_sem"] = np.sin(2 * np.pi * sem_cible / 52)
        Xh["cos_sem"] = np.cos(2 * np.pi * sem_cible / 52)
        Xh["meme_sem_an_passe"] = hist.shift(SEASON - h)  # y(t+h-52)
        cible = hist.shift(-h) - hist
        ok = Xh.notna().all(axis=1) & cible.notna()
        modele = xgb.XGBRegressor(**XGB_PARAMS)
        modele.fit(Xh[ok], cible[ok])
        delta = modele.predict(Xh.iloc[[-1]])[0]
        preds.append(hist.iloc[-1] + delta)
    return np.array(preds)


# ----------------------------------------------------------------------------
# 3. Évaluation par origine glissante (fenêtre d'entraînement croissante)
# ----------------------------------------------------------------------------
def evaluation_glissante(y: pd.Series, clim: pd.DataFrame = None) -> pd.DataFrame:
    n = len(y)
    debut_test = n - N_TEST
    ordre = choisir_ordre_arima(y.iloc[:debut_test])
    print(f"Ordre ARIMA retenu (sur l'entraînement initial) : {ordre}")

    modeles = {
        "Naïf": prevoir_naif,
        "Naïf saisonnier": prevoir_naif_saisonnier,
        "ARIMA": lambda h: prevoir_arima(h, ordre),
        "Prophet": prevoir_prophet,
        "XGBoost": prevoir_xgboost,
    }
    if clim is not None:
        # le climat est coupé à la date d'origine : aucune météo future
        modeles["XGBoost + climat"] = lambda h: prevoir_xgboost(
            h, clim.loc[: h.index[-1]])
    lignes = []
    origines = range(debut_test - 1, n - 1)
    for i, t in enumerate(origines):
        hist = y.iloc[: t + 1]
        for nom, f in modeles.items():
            p = f(hist)
            for h in HORIZONS:
                if t + h < n:
                    lignes.append(dict(modele=nom, horizon=h, origine=y.index[t],
                                       date_cible=y.index[t + h],
                                       reel=y.iloc[t + h], prevu=max(p[h - 1], 0)))
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(origines)} origines traitées")
    return pd.DataFrame(lignes)


def metriques(prev: pd.DataFrame) -> pd.DataFrame:
    def calc(g):
        e = g["reel"] - g["prevu"]
        return pd.Series({
            "MAE": np.abs(e).mean(),
            "RMSE": np.sqrt((e ** 2).mean()),
            "MAPE_%": (np.abs(e) / g["reel"]).mean() * 100,
            "n": len(g),
        })
    m = prev.groupby(["horizon", "modele"]).apply(calc).round(2).reset_index()
    # Skill score : gain relatif de MAE par rapport au naïf (positif = mieux)
    ref = m[m.modele == "Naïf"].set_index("horizon")["MAE"]
    m["gain_vs_naif_%"] = ((1 - m["MAE"] / m["horizon"].map(ref)) * 100).round(1)
    return m.sort_values(["horizon", "MAE"])


def charger_climat(chemin: str, districts) -> pd.DataFrame:
    """Moyenne régionale hebdomadaire des variables climatiques."""
    c = pd.read_csv(chemin, parse_dates=["date"])
    c = c[c.district.isin(districts)]
    return c.groupby("date")[["pluie_mm", "temp_moy", "temp_max", "humidite"]].mean()


def correlations_decalees(y: pd.Series, clim: pd.DataFrame, out: Path):
    """Corrélation entre les cas et la pluie cumulée sur 4 semaines,
    pour des décalages de 0 à 12 semaines (exploration, pas prévision)."""
    pluie4 = clim["pluie_mm"].rolling(4).sum().reindex(y.index)
    res = pd.DataFrame({
        "decalage_sem": range(13),
        "corr_pluie_4sem": [y.corr(pluie4.shift(k)) for k in range(13)],
        "corr_temp": [y.corr(clim["temp_moy"].reindex(y.index).shift(k)) for k in range(13)],
    }).round(3)
    res.to_csv(out / "correlations_climat.csv", index=False)
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(res.decalage_sem, res.corr_pluie_4sem, color="#4a7ab5")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Décalage (semaines)"); ax.set_ylabel("Corrélation")
    ax.set_title("Cas de typhoïde vs pluie cumulée sur 4 semaines")
    fig.tight_layout(); fig.savefig(out / "fig4_correlation_pluie.png", dpi=200)
    plt.close(fig)
    return res


# ----------------------------------------------------------------------------
# 4. Figures
# ----------------------------------------------------------------------------
def figures(y: pd.Series, prev: pd.DataFrame, met: pd.DataFrame, out: Path):
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(y.index, y.values, color="#333")
    ax.axvspan(y.index[-N_TEST], y.index[-1], color="#f2b880", alpha=0.3,
               label="Période test")
    ax.set_title(f"Cas hebdomadaires de fièvre typhoïde, Extrême-Nord ({y.index[0].year + 1}-{y.index[-1].year})")
    ax.set_ylabel("Cas"); ax.legend()
    fig.tight_layout(); fig.savefig(out / "fig1_serie.png", dpi=200); plt.close(fig)

    for h in HORIZONS:
        fig, ax = plt.subplots(figsize=(11, 4))
        sub = prev[prev.horizon == h]
        reel = sub.drop_duplicates("date_cible").set_index("date_cible")["reel"]
        ax.plot(reel.index, reel.values, color="black", lw=2, label="Réel")
        for nom in ["Naïf saisonnier", "ARIMA", "Prophet", "XGBoost", "XGBoost + climat"]:
            if nom not in set(sub.modele):
                continue
            s = sub[sub.modele == nom].set_index("date_cible")["prevu"]
            ax.plot(s.index, s.values, lw=1.2, label=nom)
        ax.set_title(f"Prévisions hors échantillon à {h} semaine(s)")
        ax.set_ylabel("Cas"); ax.legend(ncol=5, fontsize=8)
        fig.tight_layout(); fig.savefig(out / f"fig2_previsions_h{h}.png", dpi=200)
        plt.close(fig)

    fig, axes = plt.subplots(1, len(HORIZONS), figsize=(11, 4), sharey=True)
    for ax, h in zip(axes, HORIZONS):
        s = met[met.horizon == h].sort_values("MAE")
        ax.barh(s.modele, s.MAE, color="#4a7ab5")
        ax.set_title(f"MAE, horizon {h} sem."); ax.invert_yaxis()
    fig.tight_layout(); fig.savefig(out / "fig3_mae.png", dpi=200); plt.close(fig)


# ----------------------------------------------------------------------------
def main():
    global N_TEST
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="df.xls")
    ap.add_argument("--out", default="resultats")
    ap.add_argument("--climat", default=None,
                    help="climat_hebdo.csv produit par telecharger_climat.py")
    ap.add_argument("--n_test", type=int, default=N_TEST,
                    help="nombre de semaines de la période test (156 = 2023-2025)")
    ap.add_argument("--max_manquant", type=float, default=100,
                    help="exclure les districts avec plus de X %% de semaines manquantes")
    args = ap.parse_args()
    N_TEST = args.n_test
    out = Path(args.out); out.mkdir(exist_ok=True)
    np.random.seed(SEED)

    brut = charger_donnees(args.data)
    print(f"{brut.shape[0]} semaines x {brut.shape[1]} districts, "
          f"{brut.index.min().date()} -> {brut.index.max().date()}")
    rapport_qualite(brut).to_csv(out / "qualite_donnees.csv")
    pct = brut.isna().mean() * 100
    exclus = list(pct[pct > args.max_manquant].index)
    if exclus:
        print(f"Districts exclus (> {args.max_manquant} % manquant) : {', '.join(exclus)}")
        brut = brut.drop(columns=exclus)
    print(f"Districts analysés : {brut.shape[1]}")

    imp = imputer(brut)
    y = imp.sum(axis=1).rename("Extreme_Nord")
    y.to_csv(out / "serie_regionale.csv")

    adf = adfuller(y.values)
    print(f"ADF : statistique = {adf[0]:.3f}, p-valeur = {adf[1]:.4f}")

    clim = None
    if args.climat:
        clim = charger_climat(args.climat, brut.columns)
        manque = y.index.difference(clim.index)
        if len(manque):
            raise ValueError(f"{len(manque)} semaines sans données climatiques")
        print(correlations_decalees(y, clim, out).to_string(index=False))

    prev = evaluation_glissante(y, clim)
    prev.to_csv(out / "previsions_test.csv", index=False)
    met = metriques(prev)
    met.to_csv(out / "metriques.csv", index=False)
    print("\n", met.to_string(index=False))
    figures(y, prev, met, out)


if __name__ == "__main__":
    main()
