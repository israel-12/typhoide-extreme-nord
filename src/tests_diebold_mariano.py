"""
Tests de Diebold-Mariano (avec la correction pour petits échantillons de
Harvey, Leybourne et Newbold, 1997) : les écarts d'erreur entre deux modèles
sont-ils statistiquement significatifs ?

H0 : les deux modèles ont la même précision.
Statistique négative : le premier modèle a une erreur plus faible.

Usage : python tests_diebold_mariano.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chemins import ROOT, RAW, DATA, RES, FIG
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def diebold_mariano(e1, e2, h=1, perte="abs"):
    """e1, e2 : erreurs de prévision alignées. Renvoie (stat HLN, p-valeur bilatérale)."""
    e1, e2 = np.asarray(e1, float), np.asarray(e2, float)
    d = np.abs(e1) - np.abs(e2) if perte == "abs" else e1 ** 2 - e2 ** 2
    return dm_differentiel(d, h)


def dm_differentiel(d, h=1):
    """Test DM directement sur une série d'écarts de perte d (H0 : moyenne nulle)."""
    d = np.asarray(d, float)
    n = len(d)
    dbar = d.mean()
    # variance de long terme : autocovariances jusqu'à h-1 (erreurs h-pas corrélées)
    gamma = [np.mean((d[k:] - dbar) * (d[:n - k] - dbar)) for k in range(h)]
    var = (gamma[0] + 2 * sum(gamma[1:])) / n
    if var <= 0:
        var = gamma[0] / n
    dm = dbar / np.sqrt(var)
    hln = dm * np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    p = 2 * stats.t.sf(np.abs(hln), df=n - 1)
    return hln, p


def regional(fichier, sortie):
    P = pd.read_csv(fichier, parse_dates=["date_cible"])
    P["err"] = P.reel - P.prevu
    lignes = []
    for h in sorted(P.horizon.unique()):
        E = P[P.horizon == h].pivot(index="date_cible", columns="modele", values="err").dropna()
        mods = list(E.columns)
        for a in mods:
            for b in mods:
                if a < b:
                    for perte in ["abs", "carre"]:
                        s, p = diebold_mariano(E[a], E[b], h, perte)
                        lignes.append(dict(horizon=h, modele_A=a, modele_B=b, perte=perte,
                                           n=len(E), stat_DM=round(s, 3), p_valeur=round(p, 4)))
    R = pd.DataFrame(lignes)
    R.to_csv(sortie, index=False)
    return R


def districts(fichier, sortie, ref="XGBoost global"):
    P = pd.read_csv(fichier, parse_dates=["date_cible"])
    P = P[P.observe]
    P["err"] = P.reel - P.prevu
    lignes, panel = [], []
    for h in sorted(P.horizon.unique()):
        Ph = P[P.horizon == h]
        for autre in ["Naïf", "ARIMA", "XGBoost local", "Naïf saisonnier"]:
            for d, g in Ph.groupby("district"):
                E = g.pivot(index="date_cible", columns="modele", values="err")[[ref, autre]].dropna()
                if len(E) < 20:
                    continue
                s, p = diebold_mariano(E[ref], E[autre], h)
                lignes.append(dict(horizon=h, district=d, comparaison=f"{ref} vs {autre}",
                                   n=len(E), stat_DM=round(s, 3), p_valeur=round(p, 4)))
            # test « panel » : écart d'erreur absolue normalisé par district
            # (divisé par la MAE du naïf), moyenné sur les districts chaque semaine
            W = Ph.pivot_table(index=["date_cible", "district"], columns="modele", values="err").dropna()
            echelle = W["Naïf"].abs().groupby(level="district").transform("mean").replace(0, np.nan)
            dd = ((W[ref].abs() - W[autre].abs()) / echelle).groupby(level="date_cible").mean().dropna()
            s, p = dm_differentiel(dd.values, h)   # teste moyenne(dd) = 0
            panel.append(dict(horizon=h, comparaison=f"{ref} vs {autre}", semaines=len(dd),
                              ecart_moyen_normalise=round(dd.mean(), 3),
                              stat_DM=round(s, 3), p_valeur=round(p, 4)))
    D = pd.DataFrame(lignes)
    D.to_csv(sortie, index=False)
    return D, pd.DataFrame(panel)


if __name__ == "__main__":
    out = RES / "tests_dm"; out.mkdir(exist_ok=True)
    R = regional(RES / "regional_climat" / "previsions_test.csv", out / "dm_regional.csv")
    D, Pn = districts(RES / "districts" / "previsions_districts.csv", out / "dm_districts.csv")
    Pn.to_csv(out / "dm_panel_districts.csv", index=False)

    print("=== Régional, perte absolue ===")
    print(R[R.perte == "abs"].to_string(index=False))
    print("\n=== Districts : nombre de districts où XGBoost global est significativement "
          "meilleur / pire (p < 0,05) ===")
    D["sig_mieux"] = (D.p_valeur < 0.05) & (D.stat_DM < 0)
    D["sig_pire"] = (D.p_valeur < 0.05) & (D.stat_DM > 0)
    print(D.groupby(["horizon", "comparaison"])[["sig_mieux", "sig_pire"]].sum().to_string())
    print("\n=== Test panel (tous districts) ===")
    print(Pn.to_string(index=False))
