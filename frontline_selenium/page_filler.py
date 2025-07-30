import os
import random
import time
import logging
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from frontline_selenium.selenium_helper import SeleniumHelper
from frontline_selenium.random_html_generator import RandomHtmlGenerator
from selenium.webdriver.remote.webelement import WebElement
from faker import Faker

class PageFormFiller:
    scripts_directory: str = os.path.dirname(os.path.abspath(__file__)) + "\\filling_scripts\\"
    logger: logging.Logger = None

    @staticmethod
    def setup_logger(logger: logging.Logger):
        PageFormFiller.logger = logger

    @staticmethod
    def fill_form(driver: webdriver.Chrome) -> None:        
        PageFormFiller.fill_form_radio_buttons(driver)
        PageFormFiller.fill_form_checkboxes(driver)
        #PageFormFiller.fill_form_drop_down_lists(driver)
        PageFormFiller.fill_form_multiple_selects(driver)
        PageFormFiller.fill_form_textboxes(driver)
        PageFormFiller.fill_form_textareas(driver)
        PageFormFiller.fill_form_rich_text_editors(driver)
        PageFormFiller.fill_form_date_time_picker(driver)
        PageFormFiller.fill_form_phones(driver)
        PageFormFiller.fill_form_emails(driver)
        PageFormFiller.fill_form_zipcodes(driver)
    
    def create_script(file_name: str, params: dict={}) -> str:
        with open(PageFormFiller.scripts_directory + file_name, "r") as script_file:
            script = script_file.read()
            for key in params.keys():
                script = script.replace(key, params[key])
            return script
    
    @staticmethod
    def fill_form_textboxes(driver: webdriver.Chrome) -> None:
        fake = Faker()
        text = fake.sentence()
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            script = PageFormFiller.create_script("textbox.js", {
                "{{text}}": f"\"{text}\""
            })
            driver.execute_script(script)
        else:
                textboxes = driver.find_elements(By.CSS_SELECTOR, ".k-textbox")
                for textbox in textboxes:
                    try:
                        # Skip disabled elements
                        if textbox.get_attribute("disabled") is not None:
                            continue
                        # Skip elements that are not interactable
                        if not textbox.is_enabled():
                            continue
                        textbox.clear()
                        textbox.send_keys(text)
                    except Exception as ex:
                        PageFormFiller.logger.exception(ex)

    @staticmethod
    def fill_form_textareas(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            # For plan pages, use JavaScript approach
            fake = Faker()
            text = fake.text(max_nb_chars=600).replace("\n", "\\n").replace('"', '\\"').replace("'", "\\'")
            script = PageFormFiller.create_script("textarea.js", {
                "{{isPlanPage}}": str(SeleniumHelper.is_plan_page_url(driver.current_url)).lower(),
                "{{text}}": f'"{text}"'
            })
            driver.execute_script(script)
        else:
            # For other pages, use direct Selenium approach
            textareas = driver.find_elements(By.CSS_SELECTOR, "textarea")
            fake = Faker()
            text = fake.text(max_nb_chars=600)
            for textarea in textareas:
                try:
                    # Skip disabled elements
                    if textarea.get_attribute("disabled") is not None:
                        continue
                    # Skip elements that are not interactable
                    if not textarea.is_enabled():
                        continue
                    textarea.clear()
                    textarea.send_keys(text)
                except Exception as ex:
                    PageFormFiller.logger.exception(ex)

    @staticmethod
    def fill_form_rich_text_editors(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            text = RandomHtmlGenerator.generate_random_html().replace('"', '\\"').replace("'", "\\'")
            script = PageFormFiller.create_script("rich_text_editor.js", {
                "{{isPlanPage}}": str(SeleniumHelper.is_plan_page_url(driver.current_url)).lower(),
                "{{text}}": f'"{text}"'
            })
            driver.execute_script(script)
        else:
            rich_editors_count = driver.execute_script("return $('accelify-rich-editor').length;")
            for i in range(rich_editors_count):
                if driver.execute_script(f"return $('accelify-rich-editor:eq({i}) kendo-editor').attr('ariadisabled') == 'false';"):
                    driver.execute_script(f"$(\"accelify-rich-editor:eq({i}) kendo-editor div[contenteditable='true']\").empty();")
                    driver.execute_script(f"$('accelify-rich-editor:eq({i}) kendo-toolbar .k-i-image').click()")
                    image_inputs = driver.execute_script("return $('kendo-dialog input')")
                    img, width, height = RandomHtmlGenerator.get_random_bull_image_link()
                    image_inputs[0].send_keys(img)
                    image_inputs[1].send_keys("img")
                    image_inputs[2].send_keys(width)
                    image_inputs[3].send_keys(height)
                    driver.execute_script("$('kendo-dialog kendo-dialog-actions button:eq(1)').click()")

    @staticmethod
    def fill_form_checkboxes(driver: webdriver.Chrome) -> None:
        script = PageFormFiller.create_script("checkbox.js", {
            "{{isPlanPage}}": str(SeleniumHelper.is_plan_page_url(driver.current_url)).lower()
        })
        driver.execute_script(script)

    
    @staticmethod
    def fill_form_radio_buttons(driver: webdriver.Chrome) -> None:
        script = PageFormFiller.create_script("radio_button.js", {
            "{{isPlanPage}}": str(SeleniumHelper.is_plan_page_url(driver.current_url)).lower()
        })
        driver.execute_script(script)

    @staticmethod
    def select_random_value_from_dropdownlist(driver: webdriver.Chrome, dropdownlist: WebElement) -> None:
        try:
            is_disabled = (
                dropdownlist.get_attribute("disabled") is not None
                or "k-disabled" in dropdownlist.get_attribute("class")
                    or not dropdownlist.is_enabled()
            )
            if is_disabled:
                return

            # Scroll element into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdownlist)

            # Wait for element to be clickable
            WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable(dropdownlist)
            )

            dropdownlist.click()
            popup = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "kendo-popup"))
            )
            options = popup.find_elements(By.CSS_SELECTOR, "ul>li")
            if options:
                selected_option = options[random.randint(0, len(options) - 1)]
                # Scroll option into view and wait for clickability
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_option)
                WebDriverWait(driver, 1).until(EC.element_to_be_clickable(selected_option))
                selected_option.click()
        except Exception as ex:
            PageFormFiller.logger.error(f"Multiselect click failed: {type(ex).__name__}: {str(ex)}")

    
    @staticmethod
    def fill_form_drop_down_lists(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            script = PageFormFiller.create_script("drop_down_list.js")
            driver.execute_script(script)
        else:
            comboboxes = driver.find_elements(By.CSS_SELECTOR, "kendo-combobox")
            for combobox in comboboxes:
                try:
                    # Skip disabled elements
                    if combobox.get_attribute("disabled") is not None:
                        continue
                    # Skip elements that are not interactable
                    if not combobox.is_enabled():
                        continue
                        
                    data_keys = combobox.get_attribute("datakeys")
                    if not data_keys:
                        continue
                        
                    data_keys = data_keys.split(";")
                    input = combobox.find_element(By.CSS_SELECTOR, "kendo-searchbar>input")
                    
                    # Check if input is also enabled
                    if not input.is_enabled():
                        continue
                        
                    input.clear()
                    input.send_keys(data_keys[random.randint(0, len(data_keys) - 1)])
                except Exception as ex:
                    PageFormFiller.logger.exception(ex)

            try:
                driver.find_element(By.CSS_SELECTOR, "h1").click()
            except:
                pass  # Ignore if h1 not found
                
            dropdownlists = driver.find_elements(By.CSS_SELECTOR, "table kendo-dropdownlist")
            for dropdownlist in dropdownlists:
                PageFormFiller.select_random_value_from_dropdownlist(driver, dropdownlist)


    @staticmethod
    def fill_form_date_time_picker(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            script = PageFormFiller.create_script("date_time_picker.js")
            driver.execute_script(script)
        else:
            date_pickers = driver.find_elements(By.CSS_SELECTOR, "kendo-datepicker")
            for date_picker in date_pickers:
                try:
                    # Skip disabled elements - check multiple conditions
                    if date_picker.get_attribute("disabled") is not None:
                        continue
                    # Skip elements that are not interactable
                    if not date_picker.is_enabled():
                        continue
                    # Skip elements with disabled CSS class
                    if "k-disabled" in date_picker.get_attribute("class"):
                        continue
                        
                    input = date_picker.find_element(By.CSS_SELECTOR, "kendo-dateinput>input")
                    
                    # Check if input is also enabled and not disabled
                    if not input.is_enabled() or input.get_attribute("disabled") is not None:
                        continue
                        
                    next_day_date = datetime.datetime.today() + datetime.timedelta(days=1)
                    input.send_keys(str(next_day_date.year), Keys.ARROW_LEFT, str(next_day_date.day), Keys.ARROW_LEFT, Keys.ARROW_LEFT, str(next_day_date.month))
                except Exception as ex:
                    PageFormFiller.logger.exception(ex)
                  
    @staticmethod
    def fill_form_multiple_selects(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            script = PageFormFiller.create_script("multiple_select.js")
            driver.execute_script(script)
        else:
            multiselects = driver.find_elements(By.CSS_SELECTOR, "kendo-multiselect")
            for multiselect in multiselects:
                PageFormFiller.select_random_value_from_dropdownlist(driver, multiselect)

    @staticmethod
    def fill_form_phones(driver: webdriver.Chrome) -> None:
        try:
            script = PageFormFiller.create_script("phone.js")
            result = driver.execute_script(script)            
        except Exception as ex:
            PageFormFiller.logger.exception(ex)

    @staticmethod
    def fill_form_emails(driver: webdriver.Chrome) -> None:
        try:
            script = PageFormFiller.create_script("email.js")
            result = driver.execute_script(script)                
        except Exception as ex:
            PageFormFiller.logger.exception(ex)

    @staticmethod
    def fill_form_zipcodes(driver: webdriver.Chrome) -> None:
        try:
            script = PageFormFiller.create_script("zipcode.js")
            result = driver.execute_script(script)         
        except Exception as ex:
            PageFormFiller.logger.exception(ex)
       