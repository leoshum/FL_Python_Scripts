import time
from selenium import webdriver
from selenium.webdriver.common.by import By

class SupportTech:
    @staticmethod
    def login(driver: webdriver.Chrome) -> None:
        driver.get("https://support-tech.acceliplan.com/login")
        username_field = driver.find_element(By.CSS_SELECTOR, "kendo-textbox[formcontrolname='username'] input")
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        submit_btn = driver.find_element(By.CSS_SELECTOR, "form button")
        username_field.send_keys("SupportAdmin")
        password_field.send_keys("GftOc244Qw^j")
        submit_btn.click()
	
    @staticmethod
    def open_website(driver: webdriver.Chrome, url: str, username: str) -> None:
        username_field = driver.find_element(By.CSS_SELECTOR, "kendo-textbox[formcontrolname='username'] input")
        host_field = driver.find_element(By.CSS_SELECTOR, "kendo-textbox[formcontrolname='host'] input")
        navigate_button = driver.find_element(By.CSS_SELECTOR, ".k-buttons-end button")
        host_field.clear()
        username_field.clear()
        username_field.send_keys(username)
        host_field.send_keys(url)
        navigate_button.click()
        time.sleep(2)
        child = driver.window_handles[1]
        driver.switch_to.window(driver.window_handles[0])
        driver.close()
        driver.switch_to.window(child)

    #def get_accelify_session(base_url):
    #    session = requests.Session()
    #    login_page = session.get(f"{base_url}/Login.aspx").text
    #    soup = BeautifulSoup(login_page, 'html.parser')
    #    fields = {
    #        "__EVENTTARGET": "",
    #        "__EVENTARGUMENT": "",
    #        "__VIEWSTATE": "",
    #        "__VIEWSTATEGENERATOR": "",
    #        "__EVENTVALIDATION": "",
    #    }

    #    for field in fields.keys():
    #        input = soup.find(id=field)
    #        if input:
    #            fields[field] = input.attrs["value"]
    #    fields["ctl00$plcContent$LoginControl$UserName"] = "SFTDVTester"
    #    fields["ctl00$plcContent$LoginControl$Password"] = "ht2jGMM2GnC3bwX7"
    #    fields["ctl00$plcContent$LoginControl$ctlCredentialsReminder$pnlCredentialsReminder$txtUserName"] = ""
    #    fields["ctl00$plcContent$LoginControl$ctlCredentialsReminder$pnlCredentialsReminder$txtEmail"] = ""
    #    fields["ctl00$plcContent$LoginControl$lnkLogin"] = "Log in"
    #    session.post(f"{base_url}/Login.aspx", data=fields)
    #    return session