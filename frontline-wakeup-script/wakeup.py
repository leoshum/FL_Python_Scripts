import os
import re
import json
import logging
import requests
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def extract_base_url(url):
	url_parts = urlparse(url)
	return f"{url_parts.scheme}://{url_parts.netloc}"


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


def get_accelify_session_using_support_tool(support_tool_session, base_url, username):
    link = get_magic_link(support_tool_session, base_url, username)
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


def get_endpoints_for_planng(url, planng_mappings):
    base_url = extract_base_url(url)
    endpoints = []
    for url_regex in planng_mappings.keys():
        if re.compile(url_regex).search(url):
            mapping = planng_mappings[url_regex]
            data = []
            for data_regex in mapping["regexes"]:
                data.append(re.compile(data_regex).search(url).group(0))
                
            for endpoint in mapping["endpoints"]:
                endpoints.append(endpoint.format(base_url, *data))
            return endpoints
    raise ValueError("there is no regex matches url")


def filter_urls(urls, sites):
    if sites:
        for site in sites:
            if not urls.get(site): raise ValueError(f"Given site name '{site}' doesn't exist in the urls file!")
        urls = dict(filter(lambda pair: pair[0] in sites, urls.items()))
    return urls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", type=str)
    parser.add_argument('--sites', nargs='+')
    args = parser.parse_args()
    urls_file_name = args.urls
    sites = args.sites
    
    with open(urls_file_name) as file:
        urls = json.load(file)

    with open(os.path.dirname(__file__) + "/planng-mappings.json") as file:
        planng_mappings = json.load(file)

    urls = filter_urls(urls, sites) # make logging

    support_tool_session = get_support_tool_session()
    for site_name in urls.keys():
        accelify_session = get_accelify_session_using_support_tool(support_tool_session, extract_base_url(urls[site_name][0]), "pmgmt")
        for url in urls[site_name]:
            url = url.strip()
            if "planng" in url:
                endpoints = get_endpoints_for_planng(url, planng_mappings) # make logging
                for endpoint in endpoints:
                    accelify_session.get(endpoint)
                    # make logging
                    print(endpoint)
            else:
                accelify_session.get(url)
                # make logging
                print(url)

if __name__ == "__main__":
    main()