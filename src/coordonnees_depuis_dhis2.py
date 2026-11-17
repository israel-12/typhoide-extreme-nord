"""
Convertit l'export JSON des unités d'organisation DHIS2 (districts de santé)
en :
  - districts_coordonnees.csv : un point par district (centre du polygone)
  - districts_sante.geojson   : les limites des districts (pour CHIRPS/ERA5)

Usage : python coordonnees_depuis_dhis2.py --json districts_dhis2.json --data df.xls
"""
import argparse
import difflib
import json
import re
import unicodedata

import pandas as pd
from shapely.geometry import mapping, shape
from shapely.validation import make_valid


def normaliser(nom: str) -> str:
    """Minuscules, sans accents ni préfixes ('DS', 'District de santé de')."""
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(district|de|sante|ds|du|d)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    romains = {"i": "1", "ii": "2", "iii": "3", "iv": "4"}   # Maroua I -> maroua 1
    return " ".join(romains.get(m, m) for m in s.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="districts_dhis2.json")
    ap.add_argument("--data", default="df.xls")
    ap.add_argument("--out_csv", default="districts_coordonnees.csv")
    ap.add_argument("--out_geojson", default="districts_sante.geojson")
    a = ap.parse_args()

    unites = json.load(open(a.json, encoding="utf-8"))["organisationUnits"]
    noms_base = [c.replace("District ", "").strip()
                 for c in pd.read_excel(a.data).columns[1:]]

    index = {normaliser(u["name"]): u for u in unites if u.get("geometry")}
    lignes, features, absents = [], [], []
    for nom in noms_base:
        cle = normaliser(nom)
        trouve = index.get(cle) or next(
            iter(index[k] for k in difflib.get_close_matches(cle, index, n=1, cutoff=0.75)),
            None)
        if trouve is None:
            absents.append(nom)
            continue
        geom = shape(trouve["geometry"])
        if not geom.is_valid:            # auto-intersections fréquentes dans le DHIS2
            geom = make_valid(geom)
            if geom.geom_type == "GeometryCollection":
                geom = geom.buffer(0)
        pt = geom.representative_point() if geom.geom_type != "Point" else geom
        lignes.append(dict(district=nom, nom_dhis2=trouve["name"],
                           latitude=round(pt.y, 4), longitude=round(pt.x, 4),
                           type_geometrie=geom.geom_type, verifie="oui"))
        if geom.geom_type != "Point":
            features.append({"type": "Feature",
                             "properties": {"district": nom, "nom_dhis2": trouve["name"],
                                            "uid": trouve["id"]},
                             "geometry": mapping(geom)})

    res = pd.DataFrame(lignes)
    res.to_csv(a.out_csv, index=False)
    json.dump({"type": "FeatureCollection", "features": features},
              open(a.out_geojson, "w", encoding="utf-8"))

    print(res[["district", "nom_dhis2", "latitude", "longitude"]].to_string(index=False))
    print(f"\n{len(res)}/{len(noms_base)} districts trouvés, {len(features)} polygones.")
    if absents:
        print("Introuvables (à compléter à la main) :", ", ".join(absents))
    diff = res[res.district.map(normaliser) != res.nom_dhis2.map(normaliser)]
    if len(diff):
        print("Correspondances approximatives à vérifier :")
        print(diff[["district", "nom_dhis2"]].to_string(index=False))


if __name__ == "__main__":
    main()
