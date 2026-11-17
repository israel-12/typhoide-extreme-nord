"""
Construit les séries hebdomadaires par district à partir de l'export brut du DHIS2.

Entrées (data/raw) :
  - dhis2_dataValueSets_typhoide_2018_2025.csv.gz : valeurs brutes par formation,
    semaine et catégorie d'âge et de sexe (éléments n9co0eH116L et WlAB6tVDT5k)
  - dhis2_districts_limites.json   : districts de santé (id, nom, limites)
  - dhis2_hierarchie_formations.json : hiérarchie (chemin) de chaque formation
Sorties (data/processed) :
  - df_2018_2025.xlsx, df_2019_2025.xlsx : cas hebdomadaires, 32 districts
  - formations_declarantes_par_semaine.csv, formations_par_district.csv

Usage : python src/construire_base.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chemins import RAW, DATA
import numpy as np
import pandas as pd

ELEMENT = "n9co0eH116L"          # MAPE16_H_10.Fievres typhoides
NOUVEAUX = {"Waza": "Mora"}      # districts créés après 2023, ramenés à leur district d'origine


def semaine_vers_date(p):
    an, sem = p.split("W")
    return pd.Timestamp.fromisocalendar(int(an), int(sem), 1)


def main():
    d = pd.read_csv(RAW / "dhis2_dataValueSets_typhoide_2018_2025.csv.gz", low_memory=False,
                    usecols=["dataelement", "period", "orgunit", "value"])
    d = d[d.dataelement == ELEMENT]
    dist = {x["id"]: x["name"].replace("District ", "")
            for x in json.load(open(RAW / "dhis2_districts_limites.json", encoding="utf-8"))["organisationUnits"]}
    h = pd.DataFrame(json.load(open(RAW / "dhis2_hierarchie_formations.json", encoding="utf-8"))["organisationUnits"])
    h["district"] = h.path.map(lambda p: next((dist[i] for i in p.split("/") if i in dist), None)).replace(NOUVEAUX)
    d = d.merge(h[["id", "district"]], left_on="orgunit", right_on="id")

    # 1. agrégation : somme des catégories et des formations, par district et semaine
    s = d.groupby(["period", "district"]).value.sum().unstack()
    s.index = [semaine_vers_date(p) for p in s.index]
    s = s.sort_index().reindex(pd.date_range(s.index.min(), s.index.max(), freq="W-MON"))
    out = s.copy(); out.columns = ["District " + c for c in out.columns]; out = out[sorted(out.columns)]
    out.insert(0, "date", [f"Week {t.isocalendar().week} {t.date()} - {(t + pd.Timedelta(days=6)).date()}" for t in out.index])
    out.to_excel(DATA / "df_2018_2025.xlsx", index=False)
    out[out.index >= "2018-12-31"].to_excel(DATA / "df_2019_2025.xlsx", index=False)

    # 2. réseau de surveillance : formations déclarantes par semaine et par district
    f = d.groupby("period").orgunit.nunique(); f.index = [semaine_vers_date(p) for p in f.index]
    f.sort_index()[lambda x: x.index >= "2018-12-31"].rename("formations").to_csv(DATA / "formations_declarantes_par_semaine.csv")
    d[d.period >= "2019"].groupby("district").orgunit.nunique().sort_values(ascending=False) \
        .rename("formations").to_csv(DATA / "formations_par_district.csv")
    print(f"{out.shape[0]} semaines, {out.shape[1]-1} districts ; {d.orgunit.nunique()} formations")


if __name__ == "__main__":
    main()
