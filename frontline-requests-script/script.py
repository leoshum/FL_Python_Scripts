import os
import requests
import json
from bs4 import BeautifulSoup

def get_support_tool_session():
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json'
    })
    base_url = "https://support-tech.acceliplan.com"
    data = {
        "username": "SupportAdmin",
        "password": "GftOc244Qw^j"
    }
    token = json.loads(session.post(f"{base_url}/api/auth", json=data).text)["token"]
    session.headers.update({
        'Authorization': f"Bearer {token}"
    })
    return session

def get_magic_link(session, host, username):
    req = session.post("https://support-tech.acceliplan.com/api/Main/MagicLink", json={
        "hostname": host,
        "username": username
    })
    return json.loads(req.text)["magicLink"]

def get_accelify_session_using_support_tool(support_tool_session, base_url):
    link = get_magic_link(support_tool_session, base_url, "SFTDVTester")
    session = requests.Session()
    session.get(link)
    return session

def get_accelify_session(base_url):
    session = requests.Session()
    login_page = session.get(f"{base_url}/Login.aspx").text
    soup = BeautifulSoup(login_page, 'html.parser')
    fields = {
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": "",
        "__VIEWSTATEGENERATOR": "",
        "__EVENTVALIDATION": "",
    }

    for field in fields.keys():
        input = soup.find(id=field)
        if input:
            fields[field] = input.attrs["value"]
    fields["ctl00$plcContent$LoginControl$UserName"] = "SFTDVTester"
    fields["ctl00$plcContent$LoginControl$Password"] = "ht2jGMM2GnC3bwX7"
    fields["ctl00$plcContent$LoginControl$ctlCredentialsReminder$pnlCredentialsReminder$txtUserName"] = ""
    fields["ctl00$plcContent$LoginControl$ctlCredentialsReminder$pnlCredentialsReminder$txtEmail"] = ""
    fields["ctl00$plcContent$LoginControl$lnkLogin"] = "Log in"
    session.post(f"{base_url}/Login.aspx", data=fields)
    return session

def main():
    support_tool_session = get_support_tool_session()
    accelify_sessions = []
    urls = []
    with open(os.path.dirname(__file__) + "\\urls.txt", "r") as file:
        urls = file.readlines()

    for url in urls:
        url = url.strip()
        accelify_session = get_accelify_session_using_support_tool(support_tool_session, url)
        accelify_session.get(url)
        page = accelify_session.get(url + "user/GetDistricts").text
        print(page)
        accelify_sessions.append(accelify_session)

if __name__ == "__main__":
    main()