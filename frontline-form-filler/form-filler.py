import validators
import time
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException


def login_user(driver, url, users):
    for user in users:
        driver.get(url)
        username_field = driver.find_element("id", "UserName")
        password_field = driver.find_element("id", "Password")
        submit_btn = driver.find_element("id", "lnkLogin")
        username_field.send_keys(user[0])
        password_field.send_keys(user[1])
        submit_btn.click()
        driver.get(f"{url}/plan")
        try:
            WebDriverWait(driver, 15).until(
                EC.any_of(EC.presence_of_element_located((By.CLASS_NAME, "validator")))
            )
            if not driver.find_element(By.CLASS_NAME, "validator").text.strip() == "Access denied!":
                break
            else:
                for cookie in driver.get_cookies():    
                    driver.delete_cookie(cookie["name"])
        except:
            pass


def main():
    users = [
        ("superlion", "CTAKAH613777"),
        ("PMGMT", "8Huds(3d")
    ]
    urls = [
        "https://texas-stg-acc.ss.frontlineeducation.com/plan/Events/ViewEvent?eventId=33682976-04ec-485c-880c-afbe013f2bdc#presentlevels&formId=603d3f01-2681-4942-b0cc-afbe013f2da5",
        "https://texas-stg-acc.ss.frontlineeducation.com/plan/Events/ViewEvent?eventId=33682976-04ec-485c-880c-afbe013f2bdc#stateassessment&formId=542fe1f9-678e-43a7-b09d-afbe013f2da5",
        "https://texas-stg-acc.ss.frontlineeducation.com/plan/Events/ViewEvent?eventId=33682976-04ec-485c-880c-afbe013f2bdc#transportationasarelatedservice&formId=4744649e-2153-4634-984a-afbe013f2daa"
    ]
    prev_base_url = ""
    options = Options()
    #options.headless = True
    driver = webdriver.Chrome(options=options)

    for url in urls:
        if not validators.url(url):
            continue
        url_parts = urlparse(url)
        base_url = f"{url_parts.scheme}://{url_parts.netloc}"
        if base_url != prev_base_url:
            driver.get(base_url)
            login_user(driver, base_url, users)
        print(url)
        driver.execute_script("window.open('" + url + "', '_blank');")
        current = driver.window_handles[1]
        driver.switch_to.window(driver.window_handles[0])
        driver.close()
        driver.switch_to.window(current)
        prev_base_url = base_url
        WebDriverWait(driver, 30).until(
            EC.any_of(
                EC.presence_of_element_located((By.CLASS_NAME, "form")),
                EC.presence_of_element_located((By.ID, "pnlForm")),
                EC.presence_of_element_located((By.ID, "pnlEventContent")),
                EC.presence_of_element_located((By.TAG_NAME, "accelify-forms-details")),
                EC.presence_of_element_located((By.TAG_NAME, "accelify-event-eligiblity-determination")),
                EC.presence_of_element_located((By.TAG_NAME, "accelify-progress-report")),
                EC.presence_of_element_located((By.TAG_NAME, "accelify-forms-details")),
                EC.presence_of_element_located((By.TAG_NAME, "accelify-event-exceptionalities-view"))
            )
        )
        time.sleep(5)
        # TODO: group and fill checkboxes by name
        driver.execute_script("$('.form textarea').each(function() { $(this).val('test'); })")
        driver.execute_script("$(\".k-editor[data-role='text-editor']\").each(function() { $(this).data('kendoEditor').value('test'); })")
        driver.execute_script("$(\"input[type='checkbox']\").each(function() { $(this).prop('checked', true)})")
        #radio button
        driver.execute_script("""
        var groups = {};
        $(".form input[type='radio']").map(function() {return $(this)}).get().forEach(item=> {
            var groupName = item.attr("name");
            if (!(groupName in groups)) {
                groups[groupName] = [];
            }
            groups[groupName].push(item);
        });
        var keys = Object.keys(groups);
        for (var i in keys) {
            console.log(groups[keys[i]][Math.floor(Math.random() * groups[keys[i]].length)]);
            groups[keys[i]][Math.floor(Math.random() * groups[keys[i]].length)].click();
        }
        """)
        #dropdown
        driver.execute_script("""
        $(".form select[data-role='dropDownList']").each(function() {
            var values = []
            $(this).find("option").each(function() {
                values.push($(this).val())
            })

            var dropDownList = $(this).data("kendoDropDownList");
            dropDownList.value(values[Math.floor(Math.random() * (values.length - 1)) + 1]);
            dropDownList.trigger("change");
        })
        """)
        #datetimepicker
        driver.execute_script("""
        $(".form input[data-role='datePicker']").each(function() {
            $(this).data("kendoDatePicker").value(new Date());
        })
        """)
        #multiple select
        driver.execute_script("""
        $(".form select[data-role='multiSelect']").each(function() { 
            var values = []
            $(this).find("option").each(function() {
                values.push($(this).val())
            });
            var randomIndex1 = Math.floor(Math.random() * values.length);
            var randomIndex2 = Math.floor(Math.random() * values.length);
            while (randomIndex2 === randomIndex1) {
                randomIndex2 = Math.floor(Math.random() * values.length);
            }
            $(this).data("kendoMultiSelect").value([values[randomIndex1], values[randomIndex2]]);
        });
        """)
        time.sleep(15)

if __name__ == "__main__":
    main()