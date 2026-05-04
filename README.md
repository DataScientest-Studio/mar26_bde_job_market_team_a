# Job Market

Job Market est un projet data autour des offres d'emploi.

Nous partons de plusieurs sources d'offres, nous conservons le brut pour la tracabilite, puis nous construisons avec dbt une base analytique dedoublonnee et exploitable pour la suite produit.

Les sources ciblees sont :

- France Travail
- Welcome to the Jungle

La base finale doit servir a :

- analyser le marche de l'emploi
- alimenter un dashboard Streamlit
- preparer une API de recommandation d'offres
- preparer une API de prediction de salaire
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
- base de developpement : PostgreSQL
- transformations : dbt SQL
- base cible : Supabase PostgreSQL
- visualisation : Streamlit
- couche produit a venir : API metier

## Collecte

Le script principal de collecte est :

- [src/data/make_dataset.py](src/data/make_dataset.py)

Les connecteurs sont ici :

- [src/data/connectors/france_travail.py](src/data/connectors/france_travail.py)
- `src/data/connectors/welcome_to_the_jungle.py`

Le referentiel de collecte est ici :

- [references/collection_targets.yml](references/collection_targets.yml)


## Stockage

Le brut est garde dans :

- `data/raw/france_travail`
- `data/raw/welcome_to_the_jungle`

Le chargement vers PostgreSQL est gere ici :

- [src/data/normalizers/load_raw_to_postgres.py](src/data/normalizers/load_raw_to_postgres.py)

Le raw reste volontairement non dedoublonne. Une ligne raw represente une offre source telle qu'elle a ete collectee.

## dbt

Le projet dbt est ici :

- [job_market_dbt](job_market_dbt)

Les couches `staging` et `intermediate` sont materialisees en `ephemeral`. Elles structurent le SQL dans dbt, mais ne creent pas de tables techniques en base.

Seules les tables finales `marts` sont materialisees dans le schema `analytics`.

Tables finales principales :

- `analytics.fact_job_offers` : offres canoniques dedoublonnees
- `analytics.bridge_job_source` : tracabilite entre offres finales et offres source
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

## Deduplication

La deduplication se fait apres normalisation, avec un fingerprint de matching construit a partir de :

- titre normalise
- entreprise normalisee
- ville normalisee
- annee/mois de publication

Si la date de publication est absente, nous utilisons la date d'ingestion comme date de reference de matching.

Deux offres issues de sources differentes peuvent etre rapprochees seulement si leurs dates de reference sont dans une fenetre de 30 jours glissants.

Quand deux sources matchent, France Travail reste prioritaire comme source primaire.

## API Predict

L'API expose des endpoints de prediction encore prets a brancher aux modeles ML :

- `POST /predict`
- `POST /predict/salary`
- `POST /predict/recommendation`

Les anciens formats `GET` restent disponibles pour tester rapidement avec des query params.

Exemple `POST /predict/recommendation` :

```json
{
  "skills": ["python", "sql", "airflow"],
  "experience_years": 3,
  "expected_salary": 45000,
  "job_title": "data engineer",
  "location": "Paris",
  "contract_type": "CDI",
  "remote": "teletravail",
  "education_level": "Bac +5",
  "industry": "IT / Digital",
  "limit": 10
}
```

Exemple `POST /predict/salary` :

```json
{
  "job_title": "data engineer",
  "experience_years": 3,
  "skills": ["python", "sql", "dbt"],
  "location": "Paris",
  "contract_type": "CDI",
  "remote": "teletravail",
  "education_level": "Bac +5",
  "industry": "IT / Digital"
}
```

## Lancer le projet en local

Installer les dependances :

```
python -m pip install -r requirements.txt
```

Lancer PostgreSQL et pgAdmin :

```
docker compose up -d postgres pgadmin
```

Collecter le brut :

```
python src\data\make_dataset.py --source france_travail
python src\data\make_dataset.py --source welcome_to_the_jungle
```

Charger le raw dans PostgreSQL :

```
python src\data\normalizers\load_raw_to_postgres.py --source all
```

Lancer dbt :

```
python scripts\run_dbt.py run
python scripts\run_dbt.py test
```

Le script `scripts/run_dbt.py` charge automatiquement le fichier `.env` avant d'executer dbt.

## Configuration

Exemple de configuration :

- [.env.example](.env.example)

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
- `PGADMIN_PORT`
- `SELENIUM_HEADLESS`

`DBT_TARGET=dev` pointe vers PostgreSQL local.

`DBT_TARGET=prod` pointe vers Supabase
