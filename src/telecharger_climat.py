"""
Télécharge la pluie, la température et l'humidité quotidiennes (NASA POWER)
pour chaque district, puis les agrège en semaines alignées sur le DHIS2
(semaine du lundi au dimanche, étiquetée par le lundi).

Usage : python telecharger_climat.py --coords districts_coordonnees.csv \
            --debut 20180101 --fin 20231231 --out climat_hebdo.csv
À lancer sur ton ordinateur (accès Internet nécessaire).
"""
import argparse
import time

import pandas as pd
import requests

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = {
    "PRECTOTCORR": "pluie_mm",     # précipitations corrigées (mm/jour)
    "T2M": "temp_moy",             # température moyenne à 2 m (°C)
    "T2M_MAX": "temp_max",         # température maximale (°C)
    "RH2M": "humidite",            # humidité relative à 2 m (%)
}


def telecharger_point(lat, lon, debut, fin, essais=3):
    q = dict(parameters=",".join(PARAMS), community="AG", latitude=lat,
             longitude=lon, start=debut, end=fin, format="JSON")
    for i in range(essais):
        try:
            r = requests.get(URL, params=q, timeout=120)
            r.raise_for_status()
            data = r.json()["properties"]["parameter"]
            df = pd.DataFrame(data).rename(columns=PARAMS)
            df.index = pd.to_datetime(df.index, format="%Y%m%d")
            return df.replace(-999, pd.NA).astype(float)
        except Exception as e:
            print(f"   essai {i + 1} échoué : {e}")
            time.sleep(5)
    raise RuntimeError(f"Échec pour ({lat}, {lon})")


def vers_hebdo(jour: pd.DataFrame) -> pd.DataFrame:
    """Semaines lundi-dimanche étiquetées par le lundi, comme dans le DHIS2."""
    r = jour.resample("W-MON", closed="left", label="left")
    return pd.DataFrame({
        "pluie_mm": r["pluie_mm"].sum(min_count=5),   # cumul de la semaine
        "temp_moy": r["temp_moy"].mean(),
        "temp_max": r["temp_max"].mean(),
        "humidite": r["humidite"].mean(),
        "jours_pluie": r["pluie_mm"].apply(lambda s: (s >= 1).sum()),
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coords", default="districts_coordonnees.csv")
    ap.add_argument("--debut", default="20180101")
    ap.add_argument("--fin", default="20231231")
    ap.add_argument("--out", default="climat_hebdo.csv")
    a = ap.parse_args()

    coords = pd.read_csv(a.coords)
    if (coords["verifie"] != "oui").any():
        print("ATTENTION : certaines coordonnées ne sont pas marquées comme vérifiées.")

    cache, sorties = {}, []
    for _, row in coords.iterrows():
        cle = (round(row.latitude, 2), round(row.longitude, 2))
        print(f"{row.district} {cle}")
        if cle not in cache:              # Maroua 1, 2, 3 partagent un point
            cache[cle] = vers_hebdo(telecharger_point(*cle, a.debut, a.fin))
            time.sleep(1)                 # politesse envers l'API
        h = cache[cle].copy()
        h.insert(0, "district", row.district)
        sorties.append(h)

    res = pd.concat(sorties).rename_axis("date").reset_index()
    res.to_csv(a.out, index=False)
    print(f"\n{len(res)} lignes enregistrées dans {a.out}")
    print(res.groupby(res.date.dt.year)[["pluie_mm", "temp_moy"]].mean().round(1))


if __name__ == "__main__":
    main()
