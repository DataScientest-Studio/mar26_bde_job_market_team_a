# Airflow

Ce dossier contient le microservice Airflow du projet Job Market.

## Contenu

- `Dockerfile` : image Airflow custom avec le client Docker
- `requirements.txt` : dépendances propres à Airflow
- `dags/` : DAGs Airflow
- `.env.example` : configuration du service Airflow

Airflow est volontairement séparé des dépendances applicatives du projet. Le DAG
ne lance pas les scripts Python directement dans le conteneur Airflow : il
appelle le service Docker `job_market_pipeline`, qui possède déjà les
dépendances applicatives et le `.env` du projet.

## Configuration locale

Depuis la racine du projet :

```bash
cp airflow/.env.example airflow/.env
```

Changer aussi le mot de passe admin et la clé webserver avant un déploiement :

```env
AIRFLOW_ADMIN_PASSWORD=<mot_de_passe_solide>
AIRFLOW__WEBSERVER__SECRET_KEY=<chaine_longue_aleatoire>
```

Pour générer une clé :

```bash
openssl rand -hex 32
```

## Lancement Docker

Depuis la racine du projet :

```bash
make airflow
```

Interface Airflow :

```text
http://localhost:8080
```

Le DAG principal est `job_market_batch_pipeline`.
