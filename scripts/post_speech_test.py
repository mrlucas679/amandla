import requests

resp = requests.post('http://127.0.0.1:8000/speech', data={'text':'how are you'})
print(resp.status_code)
print(resp.text)

