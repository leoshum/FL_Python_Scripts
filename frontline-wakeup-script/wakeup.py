import os
import re
import sys
import json
import logging
import requests
import argparse
from urllib.parse import urlparse
from urllib.error import HTTPError
from datetime import datetime


def log_uncaught_exceptions(exctype, value, traceback):
    logging.exception("Uncaught exception occurred: ", exc_info=(exctype, value, traceback))


def get_script_directory():
    if getattr(sys, 'frozen', False):
        file_location = sys.argv[0]
    else:
        file_location = __file__
    return os.path.dirname(os.path.abspath(file_location))


def extract_base_url(url):
    url_parts = urlparse(url)
    return f"{url_parts.scheme}://{url_parts.netloc}"


def get_support_tool_session(username, password):
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json'
    })
    base_url = "https://support-tech.acceliplan.com"
    data = {
        "username": username,
        "password": password
    }
    response = session.post(f"{base_url}/api/auth", json=data)
    response.raise_for_status()
    token = json.loads(response.text)["token"]
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
    response = session.get(link)
    response.raise_for_status()
    return session


def get_endpoints_for_planng(url, planng_mappings):
    base_url = extract_base_url(url)
    endpoints = []
    for url_regex in planng_mappings.keys():
        if re.compile(url_regex).search(url):
            mapping = planng_mappings[url_regex]
            data = {}
            for pair in mapping["regexes"].items():
                key, value = pair
                data[key] = re.compile(value).search(url).group(0)
                
            for endpoint in mapping["endpoints"]:
                temp_endpoint = "" + endpoint
                for pair in data.items():
                    key, value = pair
                    temp_endpoint = temp_endpoint.replace("{" + key + "}", value)
                endpoints.append(base_url + temp_endpoint)
            return endpoints
    raise ValueError(f"there is no regex in mapping matches {url}")


def filter_urls(urls, sites):
    if sites:
        for site in sites:
            if not urls.get(site): raise ValueError(f"Parameter '{site}' doesn't exist in the urls file!")
        urls = dict(filter(lambda pair: pair[0] in sites, urls.items()))
    return urls


def main():
    formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M")
    logging.basicConfig(
        filename=f"wakeup__{formatted_datetime}.log",
        level=logging.DEBUG,
        format='%(asctime)s - %(message)s',
    )
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    sys.excepthook = log_uncaught_exceptions

    parser = argparse.ArgumentParser()
    parser.add_argument("urls", type=str)
    parser.add_argument('--sites', nargs='+')
    args = parser.parse_args()
    urls_file_name = args.urls
    sites = args.sites
    
    with open(urls_file_name) as file:
        urls = json.load(file)

    script_dir = get_script_directory()
    with open(os.path.join(script_dir, "planng-mappings.json")) as file:
        planng_mappings = json.load(file)

    with open(os.path.join(script_dir, "config.json")) as file:
        config = json.load(file)

    urls = filter_urls(urls, sites)
        
    support_tool_session = get_support_tool_session(config["support_tool"]["username"]
                                                  , config["support_tool"]["password"])
    for site_name in urls.keys():
        try:
            base_url = extract_base_url(urls[site_name][0])
            accelify_session = get_accelify_session_using_support_tool(support_tool_session
                                                                     , base_url
                                                                     , config["fl_credentials"]["username"])
        except HTTPError as ex:
            logging.error(f"Error occured while authenticating in {base_url}")
            logging.exception(ex)
            continue

        for url in urls[site_name]:
            url = url.strip()
            if "planng" in url:
                try:
                    endpoints = get_endpoints_for_planng(url, planng_mappings)
                except ValueError as ex:
                    logging.error(ex.args[0])
                    continue

                logging.info(f"{url}")
                for endpoint in endpoints:
                    response = accelify_session.get(endpoint)
                    logging.info(f"    {response.status_code} - {endpoint}")
            else:
                response = accelify_session.get(url)
                logging.info(f"{response.status_code} - {url}")

if __name__ == "__main__":
    main()