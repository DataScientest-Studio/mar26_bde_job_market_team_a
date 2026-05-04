import requests
import sys
from pprint import pprint
import json

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

#TODO Remplacer par les creds du compte jobmarket plutôt que les miens
CLIENT_ID = "PAR_exercicededata_bfed8ea9c00ca1f95f6e15ac044ac08830738f286682371c8db593d6fc6769a8"
CLIENT_SECRET = "f9f4ac35c0f48453b01974d4682aaeee3b0650cdde8d7d985225f61b45b77a1b"
TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"  # API's token endpoint
SCOPES = "o2dsoffre api_offresdemploiv2"
JSON_PATH = "src/data/json_export/francetravail.json"


def get_access_token(client_id, client_secret, token_url):
    """
    Obtain an OAuth2 access token using the Client Credentials flow.
    """
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

if __name__ == "__main__":
    # access token
    access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, TOKEN_URL)
    print(f"Access Token: {access_token}")

    # API endpoint
    API_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
    data = call_protected_api(API_URL, access_token)
    # json_obj = json.loads(str(data))
    # formatted_data = json.dumps(json_obj)

    ## load dans un fichier json ?
    # with open("france_travail.json","w") as fichier:
        # donnees = json.dump(data, fichier, indent=4)

#Parcours des résultats de l'API
for job_info in data["resultats"]:
    job_id = job_info["id"]
    
    pprint(job_info)
with open(JSON_PATH, "w", encoding="utf-8") as file:
    json.dump(data, file, indent=4, ensure_ascii=False)