import requests
import re
import json

def parse_event_seats(pid, pyr, pmo, pda):
    base_url = "https://sc.telecharge.com/rest/Performance3Djs.ashx"
    payload = {
        "pid": pid,
        "prf": 0,
        "pyr": pyr,
        "pmo": pmo,
        "pda": pda,
        "ptp": "E",
        "pcs": "ZA,Z ,R,,,",
        "rta": 1,
        "mcs": "MIDPREM,PREMIUM",
        "oid": 0,
        "sid": 2
    }

    response_text = requests.get(base_url, params=payload).text
    response_text = response_text.replace("function GetPerfSeats(){", "").strip()
    response_text = response_text.replace("return ", "").strip()
    response_text = response_text[:len(response_text) - 8]
    return json.loads(response_text)


def main():
    print(parse_event_seats()["Seats"])

if __name__ == "__main__":
    main()