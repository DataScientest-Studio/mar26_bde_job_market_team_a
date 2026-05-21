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

# Parsing du fichier de référence region_codes.json
def parse_region_codes():
    with open(REGION_CODES_PATH, 'r') as file:
        regioncodes_lst = json.load(file)
    return regioncodes_lst

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
    # Max value = 7
    if days_result_nb >= 7:
        days_result_nb = 7

    return days_result_nb

def gather_data_from_api(target_regions_lst, access_token, update_bool=False, latest_ft=''):
    exported_files = 0

    # Parcours des régions
    for target_region in target_regions_lst:
        region_code = target_region['code']
        region_name = target_region['libelle']
        data_regionpages_lst = []

        for page in range(21):

            # parcours des pages par plages d'index (max index 3149)
            first_index = page*150
            last_index = first_index+150-1
            search_range = f"{first_index}-{last_index}"

            # API endpoint construction
            search_url = API_URL+f"?region={region_code}&range={search_range}"
            
            # Ajout de l'argument publieeDepuis en cas d'update (depuis 7j max)
            if update_bool==True:
                nb_days = get_publiee_depuis_arg_nb(latest_ft)
                publiee_depuis_arg = f"&publieeDepuis={nb_days}"
                search_url = search_url+publiee_depuis_arg

            # Lancement de la requête
            data = call_protected_api(search_url, access_token)

            # Check de la reponse et du contenu renvoyé par l'API
            if data == None:
                print(f"{region_name} (code {region_code}): No data found starting index {first_index}.")
                break

            # Appending of the region data to the dictionary for referencing
            data['region']=region_name
            data['region_code']=region_code

            # Regroupement des jobs dans une liste de pages
            data_regionpages_lst.append(data)
        if data_regionpages_lst:
            export_to_json(data_regionpages_lst, region_code)
            exported_files += 1

    return exported_files


def initialize(update_bool=False, latest_ft='' ):
    # access token
    access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, TOKEN_URL)
    print("[France Travail] Access token retrieved.")

    target_regions_lst = parse_region_codes()
    return gather_data_from_api(target_regions_lst, access_token, update_bool, latest_ft)

if __name__ == "__main__":
    initialize()



