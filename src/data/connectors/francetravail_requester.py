import requests
import sys, os
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(".env")

CLIENT_ID = os.getenv("FRANCE_TRAVAIL_CLIENT_ID") 
CLIENT_SECRET = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")
TOKEN_URL = os.getenv("FRANCE_TRAVAIL_TOKEN_URL") # API's token endpoint
API_BASE_URL = os.getenv("FRANCE_TRAVAIL_BASE_URL")
SCOPES = os.getenv("FRANCE_TRAVAIL_SCOPE")

REGION_CODES_PATH = "references/data_extraction/france_travail/region_codes.json"
DEPARTEMENT_CODES_PATH = "references/data_extraction/france_travail/departements_codes.json"
API_URL = f"{API_BASE_URL}/offres/search"

request_datetime = datetime.now().strftime("%Y-%m-%d_%H%M%S")

def get_access_token(client_id, client_secret, token_url):
    # OAuth token access
    try:    
        data = {
            "grant_type": "client_credentials",
            "scope": SCOPES
        }

        response = requests.post(
            token_url,
            data=data,
            auth=(client_id, client_secret),
            timeout=10
        )
        print(f"RESPONSE: {response}")

        response.raise_for_status()

        token_info = response.json()

        if "access_token" not in token_info:
            raise ValueError("No access_token found in response.")

        return token_info["access_token"]

    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Invalid token response: {e}", file=sys.stderr)
        sys.exit(1)


def call_protected_api(api_url, token):
    """
    Call a protected API endpoint using the access token.
    """
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return None

# Parsing de fichiers de référence
def parse_json(path):
    with open(path, 'r') as file:
        content = json.load(file)
    return content

def export_to_json(result_lst, region=''):
    
    connectors_dir = Path(__file__).parent
    src_data_dir = connectors_dir.parent
    src_dir = src_data_dir.parent
    project_root= src_dir.parent

    data_dump_folder = project_root.joinpath("data/raw/france_travail")
    data_dump_folder.mkdir(parents=True, exist_ok=True)

    json_path = data_dump_folder / f"france_travail_{region}_{request_datetime}.json"
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(result_lst, file, indent=4, ensure_ascii=False)

def get_publiee_depuis_arg_nb(latest_ft):

    format = "%Y-%m-%dT%H:%M:%SZ"
    now_utc = datetime.now(timezone(timedelta(hours=2))).strftime(format)
    
    # Formattage du delta entre now et la dernière requete en une valeur absolue
    days_result_nb = abs((datetime.strptime(now_utc,format) - datetime.strptime(latest_ft,format)).days)
    
    day_milestones_lst = [1,3,7,14,31]

    if days_result_nb not in day_milestones_lst:
        if days_result_nb == 0:
            days_result_nb = 1
        elif days_result_nb > day_milestones_lst[-1]:
            days_result_nb = day_milestones_lst[-1]

        else:
            for day_milestone in day_milestones_lst:
                if days_result_nb < day_milestone:
                    days_result_nb = day_milestones_lst[day_milestones_lst.index(day_milestone)-1]
                    break
                else:
                    continue

    return days_result_nb

def gather_data_from_api(target_regions_lst, target_departements_lst, access_token, update_bool=False, latest_ft=''):

    # Parcours des régions
    for target_region in target_regions_lst:

        region_code = target_region['code']
        region_name = target_region['libelle']
        data_regionpages_lst = []

        for target_departement in target_departements_lst:

            departement_code = target_departement['code']
            departement_name = target_departement['libelle']

            if target_departement['region']['code'] == region_code:

                for page in range(21):

                    # parcours des pages par plages d'index (max index 3149)
                    first_index = page*150
                    last_index = first_index+150-1
                    search_range = f"{first_index}-{last_index}"

                    # API endpoint construction
                    search_url = API_URL+f"?departement={departement_code}&range={search_range}"
                    
                    # Ajout de l'argument publieeDepuis en cas d'update (depuis 7j max)
                    if update_bool==True:
                        nb_days = get_publiee_depuis_arg_nb(latest_ft)
                        publiee_depuis_arg = f"&publieeDepuis={nb_days}"
                        search_url = search_url+publiee_depuis_arg
                        print(f"Publiées depuis {publiee_depuis_arg}")
                    # Lancement de la requête
                    data = call_protected_api(search_url, access_token)

                    # Check de la reponse et du contenu renvoyé par l'API
                    if data == None:
                        print(f"{region_code}:{region_name} - {departement_name} : No data found after {first_index}.")
                        break

                    # Appending of the region data to the dictionary for referencing
                    data['region']=region_name
                    data['region_code']=region_code

                    # Regroupement des jobs dans une liste de pages
                    data_regionpages_lst.append(data)
                export_to_json(data_regionpages_lst, region_code)


def initialize(update_bool=False, latest_ft='' ):
    # access token
    access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, TOKEN_URL)
    print(f"Access Token: {access_token}")

    target_regions_lst = parse_json(REGION_CODES_PATH)
    target_departements_lst = parse_json(DEPARTEMENT_CODES_PATH)
    gather_data_from_api(target_regions_lst, target_departements_lst, access_token, update_bool, latest_ft)

if __name__ == "__main__":
    initialize()



