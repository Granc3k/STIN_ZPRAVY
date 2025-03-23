import requests
import time
import json

def print_pretty_json(title, data):
    print(title)
    print(json.dumps(data, indent=4, ensure_ascii=False))

URL = "https://stin-zpravy.azurewebsites.net"

if(__name__) == "__main__":
    test_data = [
        {
            "name": "Nvidia",
            "from": "2025-03-04",
            "to": "2025-03-10"
        },
        {
            "name": "Microsoft",
            "from": "2025-03-04",
            "to": "2025-03-10"
        },
        {
            "name": "Apple",
            "from": "2025-03-04",
            "to": "2025-03-10"
        },
        {
            "name": "Google",
            "from": "2025-03-04",
            "to": "2025-03-10"
        },
        {
            "name": "Amazon",
            "from": "2025-03-04",
            "to": "2025-03-10"
        }
    ]

    print_pretty_json(f"zasílám na toto URL: {URL} \ntyto testovací data: ",test_data)
    
    response = requests.post(f"{URL}/submit",json=test_data)
    request_id = response.json().get("request_id")
    status = requests.get(f"{URL}/output/{request_id}/status").json()    
               
    print(f"čekám na status done u id: {request_id}, momentálně status = {status.get("status")}\n status může nabývat techto hodnot: \"processing\", \"done\"")                                                        
    timeout = 60
    while (status.get("status") == "processing" and timeout > 0):
        status = requests.get(f"{URL}/output/{request_id}/status").json()
        print(f"čekám na status done u id: {request_id}, momentálně status = {status.get('status')}")
        time.sleep(2)
        timeout = timeout - 2
    if timeout <= 0:
        print("reached timeout")
    articles = requests.get(f"{URL}/output/{status.get("request_id")}").json()
    if articles == None:
        print("Pozor: nebyly načteny žádné články")
    else:
        print_pretty_json("zprávy získané o firmách:",articles)