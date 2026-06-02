# Job Market

Job Market est un projet data autour des offres d'emploi.

Nous partons de plusieurs sources d'offres, nous conservons le brut pour la traçabilité, puis nous construisons avec dbt une base analytique dédoublonnée et exploitable pour la suite produit.

Les sources ciblées sont :

- France Travail
- Welcome to the Jungle

La base finale doit servir à :

- analyser le marché de l'emploi
- alimenter un dashboard Streamlit
- alimenter une API de recommandation d'offres
- alimenter une API de prédiction de salaire
- exposer des tables propres dans Supabase

## Pipeline

Le pipeline suit ce flux :

1. collecte des offres en Python
2. stockage du brut en local
3. chargement des JSON dans PostgreSQL
4. transformations SQL avec dbt
5. production de tables analytics propres

## Stack

- collecte : Python
- sources : API France Travail, Welcome to the Jungle
- base de développement : PostgreSQL
- transformations : dbt SQL
- base cible : Supabase PostgreSQL
- visualisation : Streamlit
- couche produit : API FastAPI

## Collecte
La collecte s'effectue à partir d'un script principal qui va appeler deux autres scripts chacun utilisant une méthode d'extraction de données différente.

La première va aller effectuer des requêtes à l'API de France Travail pour pouvoir obtenir des données brutes par batch de 150 éléments. On va se baser sur des fichiers de référence comme les codes de départements pour affiner la recherche, ou encore les codes de régions pour regrouper les éléments requêtés par régions dans le .json généré.

La seconde va aller effectuer un scraping du site Welcome To The Jungle à partir d'un lien d'entrée (pas la page d'accueil, car suite à une màj de leur site fin avril, une authentification est nécessaire pour effectuer des recherches personnalisées). En passant par ce lien, qui liste des pages de recherches prédéfinies, rangées par régions, on effectue un scraping récursif de chaque offre contenue dans chaque page de recherche au travers d'un driver Selenium transversal.

Ces deux étapes génèrent à des fichiers .json de données brutes qui vont transiter vers les étapes de stockage et de traitement des données.

Le script principal de collecte est :

- [src/data/make_dataset.py](src/data/make_dataset.py)

Les connecteurs sont ici :

- [src/data/connectors/francetravail_requester.py](src/data/connectors/francetravail_requester.py)
- [src/data/connectors/welcometothejungle_scraper.py](src/data/connectors/welcometothejungle_scraper.py)

Les référentiels et fichiers de suivi de collecte sont ici :

- [references/data_extraction/history.yml](references/data_extraction/history.yml)
- [references/data_extraction/france_travail/departements_codes.json](references/data_extraction/france_travail/departements_codes.json)
- [references/data_extraction/france_travail/region_codes.json](references/data_extraction/france_travail/region_codes.json)
- [references/data_extraction/welcome_to_the_jungle/webscraping_metadata.yml](references/data_extraction/welcome_to_the_jungle/webscraping_metadata.yml)

Le lien d'entrée Welcome To the Jungle se trouve ici :
[https://www.welcometothejungle.com/fr/pages/offres-emploi-par-metiers-villes]

## Stockage

Le brut est gardé dans :

- `data/raw/france_travail`
- `data/raw/welcome_to_the_jungle`

Le chargement vers PostgreSQL est géré ici :

- [src/data/normalizers/load_raw_to_postgres.py](src/data/normalizers/load_raw_to_postgres.py)

Le raw reste volontairement non dédoublonné. Une ligne raw représente une offre source telle qu'elle a été collectée.

## dbt

Le projet dbt est ici :

- [job_market_dbt](job_market_dbt)

Les couches `staging` et `intermediate` sont matérialisées en `ephemeral`. Elles structurent le SQL dans dbt, mais ne créent pas de tables techniques en base.

Seules les tables finales `marts` sont matérialisées dans le schéma `analytics`.

Tables finales principales :

- `analytics.fact_job_offers` : offres canoniques dédoublonnées
- `analytics.bridge_job_source` : traçabilité entre offres finales et offres source
- `analytics.dim_company`
- `analytics.dim_location`
- `analytics.dim_contract`
- `analytics.dim_job_type`
- `analytics.dim_industry`
- `analytics.dim_salary`
- `analytics.dim_education`
- `analytics.dim_skill`
- `analytics.dim_advantage`
- `analytics.bridge_job_skill`
- `analytics.bridge_job_advantage`

## Déduplication

La déduplication se fait après normalisation, avec un fingerprint de matching construit à partir de :

- titre normalisé
- entreprise normalisée
- ville normalisée
- année/mois de publication

Si la date de publication est absente, nous utilisons la date d'ingestion comme date de référence de matching.

Deux offres issues de sources différentes peuvent être rapprochées seulement si leurs dates de référence sont dans une fenêtre de 30 jours glissants.

Le `match_score` permet de distinguer le niveau de confiance du rapprochement :

- `1.00` pour un match inter-source exact sur titre, entreprise, ville et fenêtre de dates ;
- entre `0.70` et `0.95` pour un match fuzzy, quand l'entreprise, la ville et les dates sont compatibles mais que le titre est rapproché par recouvrement de tokens ;
- `0.50` pour une offre isolée, présente dans une seule source.

Quand deux sources matchent, France Travail reste prioritaire comme source primaire.

## API Predict

L'API expose des endpoints de prédiction branchés aux modèles ML :

- `POST /predict/salary`
- `POST /predict/recommendation`

## API Lookups

Pour tester les routes `POST` dans la documentation Swagger et alimenter les
filtres du dashboard, l'API expose des endpoints de listes de valeurs
directement issus de PostgreSQL :

- `GET /lookups/skills` : compétences disponibles ;
- `GET /lookups/contracts` : types de contrat ;
- `GET /lookups/remote` : modalités de télétravail ;
- `GET /lookups/education` : niveaux de formation ;
- `GET /lookups/industries` : secteurs ;
- `GET /lookups/locations` : localisations ;
- `GET /lookups/job-titles` : intitulés de poste.

Chaque valeur retournée contient :

```json
{
  "value": "valeur à envoyer dans le POST",
  "label": "libellé affiché",
  "count": 42
}
```

## Machine Learning

Les modèles ML sont entraînés à partir des tables PostgreSQL du schéma
`analytics`. Le code principal est dans :

- [src/models/features_preparation.py](src/models/features_preparation.py)
- [src/models/train_models.py](src/models/train_models.py)
- [src/models/predict_models.py](src/models/predict_models.py)

Le projet contient deux modèles métier :

- un modèle de recommandation d'offres ;
- un modèle de prédiction de salaire.

Un modèle `KMeans` est aussi utilisé comme préfiltre technique pour regrouper
les offres similaires et limiter le nombre d'offres à scorer.

### Données utilisées

Les variables explicatives sont construites depuis les tables marts :

- `analytics.fact_job_offers`
- `analytics.dim_salary`
- `analytics.dim_company`
- `analytics.dim_location`
- `analytics.dim_contract`
- `analytics.dim_skill`
- `analytics.bridge_job_skill`

Les principales variables utilisées sont :

- compétences de l'offre ;
- années d'expérience ;
- salaire annuel moyen ;
- localisation ;
- type de contrat.

### Préparation des données

La préparation suit les étapes classiques d'un pipeline ML :

1. Récupération des données depuis PostgreSQL avec SQLAlchemy/SQLModel.
2. Nettoyage des valeurs nulles.
3. Suppression des lignes sans salaire exploitable pour le modèle de salaire.
4. Encodage des compétences avec `MultiLabelBinarizer`.
5. Transformation de l'expérience en niveau ordinal.
6. Transformation du salaire en tranche pour la recommandation.
7. Standardisation des variables numériques avec `StandardScaler`.
8. Séparation train/test pour évaluer les modèles.
9. Entraînement des modèles avec `.fit(...)`.
10. Évaluation avec des métriques adaptées.
11. Réentraînement final sur toutes les données disponibles pour l'API.
12. Prédiction avec `.predict(...)` ou `.predict_proba(...)`.

### Modèle de salaire

La prédiction de salaire est un problème de régression supervisée.

La variable cible est :

- `salary` : salaire annuel estimé de l'offre.

Les variables explicatives sont principalement :

- compétences ;
- expérience ;
- contrat.

Le modèle utilisé est `KNeighborsRegressor`. Il apprend à estimer un salaire à
partir des offres déjà présentes en base. L'endpoint `POST /predict/salary`
encode le profil fourni, standardise les variables, puis appelle
`salary_model.predict(...)`.

L'évaluation utilise un `train_test_split` :

- entraînement sur 80% des offres ;
- test sur 20% des offres ;
- métriques affichées : MAE, RMSE et R2.

### Modèle de recommandation

La recommandation est plus délicate, car le projet ne dispose pas de vraie
variable cible utilisateur. Il n'y a pas encore d'historique de clics,
candidatures, favoris ou offres ignorées.

Pour construire une première démonstration ML, des labels synthétiques sont
générés depuis les offres PostgreSQL :

- un profil candidat est dérivé d'une offre existante ;
- le couple profil/offre d'origine reçoit `label = 1` ;
- le même profil est associé à quelques offres aléatoires ;
- ces couples reçoivent `label = 0`.

Le modèle de recommandation est une `LogisticRegression`. Il apprend à prédire
la probabilité qu'un couple profil candidat / offre corresponde à un bon match.
L'endpoint `POST /predict/recommendation` utilise ensuite
`ranking_model.predict_proba(...)` pour scorer les offres candidates.

L'évaluation utilise aussi un `train_test_split` avec stratification sur le
label :

- entraînement sur 80% des couples profil/offre ;
- test sur 20% des couples profil/offre ;
- métriques affichées : accuracy, precision, recall et F1-score.

Ces métriques sont à interpréter avec prudence, car les labels de recommandation
sont synthétiques. Elles valident surtout que la chaîne ML fonctionne de bout en
bout. Une évaluation production devrait utiliser des interactions réelles.

Les paramètres envoyés à l'API ne servent pas à entraîner le modèle. Ils servent
à créer le profil candidat au moment de la prédiction :

- `skills`
- `experience_years`
- `expected_salary`
- `location`
- `contract_type`

Ces valeurs sont comparées aux offres en base pour calculer des features de
matching : recouvrement des compétences, écart d'expérience, écart de salaire,
localisation et contrat.

### Artefacts ML

Entraîner les modèles ML depuis PostgreSQL :

```
make ml-train
make ml-check
```

`make ml-train` écrit les artefacts dans `models/`, dont
`models/job_market_model_artifacts.pkl`. L'API charge cet artefact au premier
appel predict et le garde en cache mémoire. Si l'artefact n'existe pas encore,
l'API peut le recréer depuis PostgreSQL en fallback de développement.

La commande affiche aussi les métriques de test, par exemple :

```text
ranking accuracy
ranking precision
ranking recall
ranking f1
salary MAE
salary RMSE
salary R2
```

### Limites

Le modèle de salaire est supervisé, car la cible `salary` est disponible dans
les données.

Le modèle de recommandation repose sur des labels synthétiques. Il permet de
montrer une chaîne ML complète, mais il ne remplace pas un vrai modèle entraîné
sur des interactions utilisateurs réelles. Pour une version production, il
faudrait collecter des événements comme :

- clic sur une offre ;
- candidature ;
- sauvegarde en favori ;
- offre ignorée ;
- retour utilisateur positif ou négatif.

## API Dashboard

L'API expose aussi les données consommées par le dashboard Streamlit :

- `GET /stats`
- `GET /stats/ml`
- `GET /stats/summary`
- `GET /stats/breakdown`
- `GET /stats/salary_breakdown`

Le dashboard Streamlit est organisé dans :

- [src/dashboard/streamlit_app.py](src/dashboard/streamlit_app.py) : point
  d'entrée et navigation ;
- [src/dashboard/config.py](src/dashboard/config.py) : configuration lue depuis les variables d'environnement ;
- [src/dashboard/call_api.py](src/dashboard/call_api.py) : appels HTTP vers l'API FastAPI ;
- [src/dashboard/dataframes.py](src/dashboard/dataframes.py) : préparation légère des DataFrames pour l'affichage ;
- [src/dashboard/charts.py](src/dashboard/charts.py) : graphiques Altair ;
- [src/dashboard/ui.py](src/dashboard/ui.py) : styles, formatage et helpers UI ;
- [src/dashboard/app_pages/analytics.py](src/dashboard/app_pages/analytics.py) : page
  d'analyse marché ;
- [src/dashboard/app_pages/machine_learning.py](src/dashboard/app_pages/machine_learning.py) :
  page ML.

Il contient deux vues :

- `Analyse du marché` : filtre principal par métier, analyse secondaire par
  région, source ou secteur, KPI, graphique du nombre d'offres et graphique du
  salaire moyen selon la sélection, puis signaux métier
- `Prédictions` : pipeline ML, métriques train/test, formulaire dynamique
  alimenté par les endpoints `/lookups/skills`, `/lookups/contracts` et
  `/lookups/locations`, prédiction de salaire et recommandations d'offres

Exemple `POST /predict/recommendation` :

```json
{
  "skills": ["python", "sql", "airflow"],
  "experience_years": 3,
  "expected_salary": 45000,
  "location": "Paris",
  "contract_type": "CDI",
  "limit": 10
}
```

Exemple `POST /predict/salary` :

```json
{
  "experience_years": 3,
  "skills": ["python", "sql", "dbt"],
  "location": "Paris",
  "contract_type": "CDI"
}
```

## Lancer le projet en local

Installer les dépendances :

```
python -m pip install -r requirements.txt
```

Lancer PostgreSQL et pgAdmin :

```
docker compose up -d postgres pgadmin
```

Lancer l'API et le dashboard avec Docker :

```
docker compose up -d api dashboard
```

Lancer Airflow avec Docker :

```
make airflow
```

Airflow est disponible par défaut sur :

```
http://localhost:8080
```

Le DAG principal est `job_market_batch_pipeline`. Il orchestre la collecte, le
chargement raw, dbt, les tests dbt et l'entraînement ML.
Les commandes métier sont exécutées dans le service Docker `pipeline`, pas dans
le conteneur Airflow.

Le dashboard est disponible par défaut sur :

```
http://localhost:8501
```

Lancer le dashboard en local sans Docker, avec l'API déjà démarrée :

```
python -m streamlit run src/dashboard/streamlit_app.py
```

Collecter le brut :

```
python src\data\make_dataset.py --source francetravail
python src\data\make_dataset.py --source welcometothejungle
```

Charger le raw dans PostgreSQL :

```
python src\data\normalizers\load_raw_to_postgres.py --source all
```

Par défaut, le loader charge uniquement les fichiers JSON suffixés par la date du jour
au format `YYYY-MM-DD`
et ignore les offres déjà présentes avec le même couple `(source_system, source_offer_id)`.
Le `raw_hash` est conservé pour tracer le contenu brut collecté.

Pour charger une date précise ou tout l'historique :

```
python src\data\normalizers\load_raw_to_postgres.py --source all --date 2026-05-06
python src\data\normalizers\load_raw_to_postgres.py --source all --all-files
```

Lancer dbt :

```
python scripts\run_dbt.py run
python scripts\run_dbt.py test
```

Le script `scripts/run_dbt.py` charge automatiquement le fichier `.env` avant d'exécuter dbt.

## Configuration

Exemple de configuration :

- [.env.example](.env.example)
- [airflow/.env.example](airflow/.env.example)

Variables principales :

- `FRANCE_TRAVAIL_CLIENT_ID`
- `FRANCE_TRAVAIL_CLIENT_SECRET`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DBT_TARGET`
- `DBT_DEV_SCHEMA`
- `SUPABASE_DB_HOST`
- `SUPABASE_DB_PORT`
- `SUPABASE_DB_NAME`
- `SUPABASE_DB_USER`
- `SUPABASE_DB_PASSWORD`
- `SUPABASE_DB_SCHEMA`
- `PGADMIN_DEFAULT_EMAIL`
- `PGADMIN_DEFAULT_PASSWORD`
- `API_PORT`
- `DASHBOARD_PORT`
- `JOB_MARKET_API_URL`
- `PGADMIN_PORT`
- `SELENIUM_HEADLESS`

Les variables Airflow sont documentées dans [airflow/README.md](airflow/README.md).

`DBT_TARGET=dev` pointe vers PostgreSQL local.

`DBT_TARGET=prod` pointe vers Supabase
