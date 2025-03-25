import requests

response = requests.get("http://localhost:8000/find_path_by_name/Mitzva Bar/Powerhouse Moscow")
print(response.json())