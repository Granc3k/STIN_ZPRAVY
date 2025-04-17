import requests
from sim_output import print_pretty_json

URL = "https://stin-zpravy.azurewebsites.net/UI"

def check_changes(old_data, new_data, test_data):
    """Porovná stav akcií před a po a ověří správnost změn."""
    changes = {item["name"]: "prodáno" if item["status"] == 0 else "nakoupeno" for item in test_data}
    old_status = {stock["company"]: stock["status"] for stock in old_data["stocks"]}

    for stock in new_data["stocks"]:
        company = stock["company"]
        expected_status = changes.get(company, old_status.get(company, "žádné změny"))

        if stock["status"] != expected_status:
            print(f"Chyba: {company} mělo být '{expected_status}', ale je '{stock['status']}'")
        else:
            print(f"OK: {company} správně '{stock['status']}'")


if(__name__) == "__main__":
    print("============================ TESTOVÁNÍ PORTFOLIA ============================")
    print("Zasílám na toto URL: ",URL)
    test_data = [
    {"name": "Nvidia", "status": 0},
    {"name": "Apple", "status": 1},
    {"name": "Meta", "status": 1}
    ]
    request_headers = {"Accept": "application/json"}

    old_portfolio = requests.get(URL,headers=request_headers).json() 
    print_pretty_json("stav akcií před nákupem/prodejem:",old_portfolio) 
    print_pretty_json("odeslané data: ", test_data)
    requests.post(f"{URL}",json=test_data)

    new_portfolio = requests.get(URL,headers=request_headers).json() 
    print_pretty_json("stav akcií po nákupu/prodeji:", new_portfolio) 

    print("Kontrola změn:")
    check_changes(old_portfolio,new_portfolio,test_data)
    
    print("============================ TESTOVÁNÍ PROVOZU UKONČENO ============================\n\n\n")