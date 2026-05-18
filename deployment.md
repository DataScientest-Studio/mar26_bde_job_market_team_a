# Déploiement sur une VM distante

Ce guide décrit le déploiement du projet Job Market sur une VM avec Docker Compose.

## Architecture déployée

Les services lancés sur la VM sont :

- `postgres` : base projet pour les tables `landing` et `analytics`
- `api` : API FastAPI
- `dashboard` : interface Streamlit
- `pgadmin` : administration PostgreSQL
- `airflow-postgres` : base metadata Airflow
- `airflow-webserver` : interface Airflow
- `airflow-scheduler` : exécution planifiée des DAGs

Le DAG principal est `job_market_batch_pipeline`. Il exécute :

1. collecte France Travail
2. collecte Welcome to the Jungle
3. chargement raw vers PostgreSQL
4. transformations dbt
5. tests dbt
6. entraînement des modèles ML

## Prérequis VM

Sur une VM Ubuntu/Debian :

```bash
sudo apt update
sudo apt install -y git ca-certificates curl
```

Installer Docker :

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Se reconnecter à la VM pour appliquer le groupe Docker, puis vérifier :

```bash
docker --version
docker compose version
```

## Récupérer le projet

```bash
git clone <URL_DU_REPO>
cd mar26_bde_job_market_team_a
```

Créer les fichiers d'environnement :

```bash
cp .env.example .env
cp airflow/.env.example airflow/.env
nano .env
nano airflow/.env
```

Renseigner au minimum :

```env
FRANCE_TRAVAIL_CLIENT_ID=...
FRANCE_TRAVAIL_CLIENT_SECRET=...
FRANCE_TRAVAIL_SCOPE=...
FRANCE_TRAVAIL_TOKEN_URL=...
FRANCE_TRAVAIL_BASE_URL=...

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=job_market
POSTGRES_USER=job_market
POSTGRES_PASSWORD=<mot_de_passe_solide>

DBT_TARGET=dev
DBT_DEV_SCHEMA=analytics

API_PORT=8000
DASHBOARD_PORT=8501
PGADMIN_PORT=5050

JOB_MARKET_API_URL=http://api:8000
SELENIUM_HEADLESS=true
```

Configurer ensuite Airflow dans `airflow/.env` :

```env
AIRFLOW_ADMIN_USERNAME=admin
AIRFLOW_ADMIN_PASSWORD=<mot_de_passe_solide>
AIRFLOW_ADMIN_EMAIL=marbdejobmarketa@gmail.com
AIRFLOW__WEBSERVER__SECRET_KEY=<chaine_longue_aleatoire>
ML_NEIGHBORS=50
```

Pour générer une clé Airflow simple :

```bash
openssl rand -hex 32
```

## Lancer les conteneurs

Construire et démarrer tous les services :

```bash
docker compose up -d --build
```

Vérifier l'état :

```bash
docker compose ps
```

Les interfaces seront disponibles sur :

- API FastAPI : `http://<IP_VM>:8000/docs`
- Streamlit : `http://<IP_VM>:8501`
- Airflow : `http://<IP_VM>:8080`
- pgAdmin : `http://<IP_VM>:5050`

Si la VM a un firewall, ouvrir les ports utiles :

```bash
sudo ufw allow 8000/tcp
sudo ufw allow 8501/tcp
sudo ufw allow 8080/tcp
sudo ufw allow 5050/tcp
```

## Exécuter le pipeline Airflow

1. Ouvrir `http://<IP_VM>:8080`
2. Se connecter avec `AIRFLOW_ADMIN_USERNAME` et `AIRFLOW_ADMIN_PASSWORD`
3. Activer le DAG `job_market_batch_pipeline`
4. Lancer un run manuel avec le bouton de déclenchement

Le pipeline est aussi planifié en quotidien (`@daily`).

Au premier run, la tâche `install_project_dependencies` crée un environnement
virtuel `.airflow_venv` dans le projet et y installe `requirements.txt`. Cela
permet de garder Airflow séparé des dépendances applicatives comme SQLAlchemy 2.

Pour suivre les logs :

```bash
docker compose logs -f airflow-scheduler
docker compose logs -f airflow-webserver
```

## Commandes utiles

Relancer l'API après une modification :

```bash
docker compose restart api
```

Relancer le dashboard :

```bash
docker compose restart dashboard
```

Voir les logs API :

```bash
docker compose logs -f api
```

Voir les logs Streamlit :

```bash
docker compose logs -f dashboard
```

Exécuter dbt manuellement dans le conteneur Airflow :

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && .airflow_venv/bin/python scripts/run_dbt.py run"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && .airflow_venv/bin/python scripts/run_dbt.py test"
```

Exécuter l'entraînement ML manuellement :

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && .airflow_venv/bin/python -m src.models.train_models --model-dir models --n-neighbors 50"
```

## Mise à jour du déploiement

Pour déployer une nouvelle version :

```bash
git pull
docker compose up -d --build
docker compose ps
```

Si les dépendances Python ou les Dockerfiles changent, le `--build` est important.

## Données persistantes

Les données PostgreSQL sont conservées dans des volumes Docker :

- `postgres_data`
- `airflow_postgres_data`
- `pgadmin_data`
- `airflow_logs`

Les fichiers raw et les artefacts ML restent dans le dossier du projet :

- `data/raw`
- `models`

Ne pas supprimer ces dossiers ou volumes si l'objectif est de conserver l'historique.

## Arrêt propre

Arrêter les services sans supprimer les données :

```bash
docker compose down
```

Arrêter et supprimer aussi les volumes persistants :

```bash
docker compose down -v
```

La deuxième commande remet les bases à zéro.
