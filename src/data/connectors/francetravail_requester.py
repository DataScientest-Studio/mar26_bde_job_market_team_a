import requests
import sys, os
from pprint import pprint
import json
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(".env")

CLIENT_ID = os.getenv("FRANCE_TRAVAIL_CLIENT_ID") 
CLIENT_SECRET = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")
TOKEN_URL = os.getenv("FRANCE_TRAVAIL_TOKEN_URL") # API's token endpoint
API_BASE_URL = os.getenv("FRANCE_TRAVAIL_BASE_URL")
SCOPES = os.getenv("FRANCE_TRAVAIL_SCOPE")

REGION_CODES_PATH = "references/data_extraction/francetravail/region_codes.json"
API_URL = f"{API_BASE_URL}/offres/search"

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
        print(f"API request failed: {e}", file=sys.stderr)
        sys.exit(1)

# Parsing du fichier de référence region_codes.json
def parse_region_codes():
    with open(REGION_CODES_PATH, 'r') as file:
        regioncodes_lst = json.load(file)
    return regioncodes_lst

def export_to_json(result_dict, region=''):
    
    connectors_dir = Path(__file__).parent
    src_data_dir = connectors_dir.parent
    src_dir = src_data_dir.parent
    project_root= src_dir.parent

    data_dump_folder = project_root.joinpath("data/raw/francetravail")
    data_dump_folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = data_dump_folder / f"francetravail_{region}{timestamp}.json"

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(result_dict, file, indent=4, ensure_ascii=False)

if __name__ == "__main__":

    # access token
    access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, TOKEN_URL)
    print(f"Access Token: {access_token}")

    target_regions_lst = parse_region_codes()

    for target_region in target_regions_lst:
        region_code = target_region['code']
        region_name = target_region['libelle']

        # API endpoint construction
        search_url = API_URL+f"?region={region_code}"
        data = call_protected_api(search_url, access_token)

        # appending of the region data
        data['region']=region_name
        data['region_code']=region_code

        export_to_json(data, region_name)


