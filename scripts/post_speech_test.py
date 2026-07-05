import json
import urllib.request

import requests

# D10 (MASTER_PLAN): mutating HTTP requests require the session token header
with urllib.request.urlopen('http://127.0.0.1:8000/auth/session-secret') as _resp:
    _token = json.loads(_resp.read().decode())['session_secret']

resp = requests.post(
    'http://127.0.0.1:8000/speech',
    data={'text': 'how are you'},
    headers={'X-Amandla-Token': _token},
)
print(resp.status_code)
print(resp.text)
