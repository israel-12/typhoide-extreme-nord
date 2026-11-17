# Pluie et fièvre typhoïde au Sahel camerounais

Code, données agrégées, résultats et article de l'étude :

> **Influence de la pluviométrie sur la dynamique et la prévision de la fièvre typhoïde au Sahel camerounais — De la modélisation mathématique à l'apprentissage automatique, à partir des données de surveillance de l'Extrême-Nord (2019-2025)**
> Kazoune Bouba Israel, Maïrousgou Céline, Kolaye Guilsou Gabriel

*English version of the article:* `article/pdf/Article_rainfall_typhoid_EN.pdf`

## Résumé

L'étude analyse 417 910 cas de fièvre typhoïde déclarés dans le DHIS2 par 522 formations sanitaires des 32 districts de santé de l'Extrême-Nord du Cameroun (2019-2025), combinés aux précipitations satellitaires (NASA POWER). Un modèle de transmission à réservoir environnemental sert à formuler les hypothèses ; plusieurs méthodes de prévision (naïve, ARIMA, Prophet, XGBoost local, global et avec climat) sont évaluées par origine glissante sur 2023-2025 et comparées par le test de Diebold-Mariano.

Principaux résultats : le pic des cas survient en octobre, environ 8 semaines après le pic des pluies ; une saison plus pluvieuse que la normale n'entraîne pas davantage de cas, et la pluie n'améliore pas la prévision ; un modèle XGBoost unique commun aux 32 districts réduit l'erreur de prévision à 4 semaines de 15 % par rapport à la méthode naïve (p < 0,001).

## Organisation du dépôt

```
data/
  raw/          exports bruts du DHIS2 (cas par formation, limites, hiérarchie)
  processed/    séries hebdomadaires par district, climat, limites, coordonnées
src/            code Python (prétraitement, analyses, modèles, figures)
results/
  exploration/        stationnarité, décomposition STL, indices saisonniers, ACF/PACF
  regional/           prévisions régionales sans climat (2023-2025)
  regional_climat/    prévisions régionales avec climat, corrélations pluie-cas
  districts/          prévisions par district, tableau par district
  sensibilite/        exclusion des districts à données incomplètes
  tests_dm/           tests de Diebold-Mariano
figures/        toutes les figures (préfixes fr_ et en_)
article/
  pdf/          article (FR, EN), matériel supplémentaire S1, guide des formules
  word/         article au format Word (FR, EN)
  latex/        projet LaTeX prêt pour Overleaf (compilateur XeLaTeX)
notebooks/      carnet Google Colab
```

## Reproduire les analyses

```bash
pip install -r requirements.txt

# 1. Construire les séries par district à partir de l'export DHIS2
python src/construire_base.py

# 2. (facultatif) Télécharger le climat NASA POWER — nécessite Internet
python src/telecharger_climat.py --coords data/processed/districts_coordonnees.csv \
       --debut 20180101 --fin 20251231 --out data/processed/climat_hebdo_2018_2025.csv

# 3. Analyse exploratoire (stationnarité, STL, ACF, Hampel, loi de Taylor)
python src/prepro.py

# 4. Prévisions régionales, sans puis avec climat (période test 2023-2025)
python src/pipeline_typhoide.py --data data/processed/df_2019_2025.xlsx --n_test 156 --out results/regional
python src/pipeline_typhoide.py --data data/processed/df_2019_2025.xlsx --n_test 156 \
       --climat data/processed/climat_hebdo_2018_2025.csv --out results/regional_climat

# 5. Analyses de sensibilité (exclusion des districts à plus de 20 %, 5 % ou 0 % de semaines manquantes)
python src/pipeline_typhoide.py --data data/processed/df_2019_2025.xlsx --n_test 156 \
       --climat data/processed/climat_hebdo_2018_2025.csv --max_manquant 20 --out results/sensibilite/max_manquant_20

# 6. Prévisions par district (modèles local et global) — environ 15 minutes
python src/analyse_districts.py --data data/processed/df_2019_2025.xlsx --n_test 156 \
       --climat data/processed/climat_hebdo_2018_2025.csv \
       --geojson data/processed/districts_sante.geojson --out results/districts

# 7. Tests de Diebold-Mariano
python src/tests_diebold_mariano.py

# 8. Figures (fr ou en)
python src/figures.py fr
python src/cartes.py fr
python src/carte_zone.py fr
python src/etapes.py fr
python src/schema.py fr
```

Le carnet `notebooks/Typhoide_Colab.ipynb` permet d'exécuter le téléchargement du climat et les analyses régionales sur Google Colab.

## Méthode en bref

| Étape | Méthode |
|---|---|
| Données manquantes | interpolation linéaire par district (5,5 % des semaines-districts) |
| Valeurs aberrantes | filtre de Hampel (fenêtre de 9 semaines, 3 écarts) |
| Stationnarité | tests ADF et KPSS ; différenciation d'ordre 1 |
| Décomposition | STL (période 52 semaines) |
| Modèles | naïf, naïf saisonnier, ARIMA, Prophet, XGBoost (local, global, avec climat) |
| Évaluation | origine glissante, 2023-2025, horizons 1 et 4 semaines ; MAE, RMSE, MAPE |
| Comparaison | test de Diebold-Mariano avec correction de Harvey-Leybourne-Newbold |

Les formules complètes figurent dans `article/pdf/Materiel_supplementaire_S1_FR.pdf`.

## Données

Voir `data/LISEZMOI_DONNEES.md` pour la description des fichiers et leurs conditions d'utilisation.

## Citation

Voir `CITATION.cff`. Merci de citer l'article lorsqu'il sera publié.

## Licence

Code : licence MIT (voir `LICENSE`). Données : conditions propres, voir `data/LISEZMOI_DONNEES.md`.
