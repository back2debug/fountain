import requests
import os

FOUNTAIN_URL = os.environ['FOUNTAIN_URL']
FOUNTAIN_TRUST_KEY = os.environ['FOUNTAIN_TRUST_KEY']
FOUNTAIN_API_KEY = os.environ['FOUNTAIN_API_KEY']

headers = {
    "accept": "application/json",
    "content-type": "application/son"
    "X-ACCESS-TOKEN": f" { FOUNTAIN_TRUST_KEY }"
}
