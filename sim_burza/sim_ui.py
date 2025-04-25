import requests
from sim_output import print_pretty_json
from sim_all import URL

UI_URL = URL+"UI"

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
    print("Zasílám na toto URL: ",UI_URL)
    test_data = [
    {"name": "NVDA", "status": 0},
    {"name": "AAPL", "status": 1},
    {"name": "META", "status": 1}
    ]
    request_headers = {"Accept": "application/json"}

    old_portfolio = requests.get(UI_URL,headers=request_headers).json() 
    print_pretty_json("stav akcií před nákupem/prodejem:",old_portfolio) 
    print_pretty_json("odeslané data: ", test_data)
    requests.post(f"{UI_URL}",json=test_data)

    new_portfolio = requests.get(UI_URL,headers=request_headers).json() 
    print_pretty_json("stav akcií po nákupu/prodeji:", new_portfolio) 

    print("Kontrola změn:")
    check_changes(old_portfolio,new_portfolio,test_data)
    
    print("============================ TESTOVÁNÍ PROVOZU UKONČENO ============================\n\n\n")