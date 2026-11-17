# Données

## Origine et conditions d'utilisation

Les données de surveillance proviennent de DHIS-Minsante-CM (https://dhis-minsante-cm.org), système d'information sanitaire du ministère de la Santé publique du Cameroun, et ont été obtenues en collaboration avec la Délégation régionale de la santé publique de l'Extrême-Nord. Il s'agit de données agrégées (nombres de cas par formation sanitaire et par semaine), sans aucune information individuelle.

**Avant de rendre ce dépôt public**, vérifier que l'autorisation de la Délégation régionale et du ministère couvre la diffusion de ces données. À défaut, conserver le dépôt en privé, ou retirer `data/raw/` et ne publier que les séries agrégées par district (`data/processed/`) si celles-ci sont autorisées.

Les données climatiques proviennent de NASA POWER (https://power.larc.nasa.gov), en accès libre. Les limites des pays utilisées pour les cartes de situation proviennent de Natural Earth (domaine public).

## Fichiers

### data/raw
| Fichier | Contenu |
|---|---|
| `dhis2_dataValueSets_typhoide_2018_2025.csv.gz` (compressé, lu directement par pandas) | export brut : élément de données, période (semaine ISO), formation, catégorie d'âge et de sexe, valeur |
| `dhis2_districts_limites.json` | identifiants, noms et limites (polygones) des districts de santé |
| `dhis2_hierarchie_formations.json` | identifiant, nom, niveau et chemin hiérarchique de chaque formation |

Éléments de données : `n9co0eH116L` = MAPE16_H_10 Fièvres typhoïdes (cas, source principale) ; `WlAB6tVDT5k` = agrégat calculé par district (mai 2023 - mars 2025, utilisé pour contrôle).

### data/processed
| Fichier | Contenu |
|---|---|
| `df_2019_2025.xlsx` | cas hebdomadaires, 365 semaines × 32 districts (base d'analyse) ; cellule vide = semaine sans déclaration |
| `df_2018_2025.xlsx` | idem, à partir de 2018 (non utilisé : réseau de déclaration encore très incomplet) |
| `climat_hebdo_2018_2025.csv` | pluie (mm/semaine), température moyenne et maximale (°C), humidité (%), jours de pluie, par district et semaine |
| `districts_sante.geojson` | limites des 32 districts (DHIS2) |
| `districts_coordonnees.csv` | point représentatif de chaque district (utilisé pour NASA POWER) |
| `formations_par_district.csv` | nombre de formations sanitaires déclarantes par district (2019-2025) |
| `formations_declarantes_par_semaine.csv` | nombre de formations déclarantes chaque semaine |

Les semaines sont des semaines épidémiologiques ISO (du lundi au dimanche), identifiées par la date du lundi. Les districts créés après 2023 ont été ramenés à leur district d'origine (Waza dans Mora).
