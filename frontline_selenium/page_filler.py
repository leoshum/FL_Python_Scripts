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
    def is_css_interactable(driver: webdriver.Chrome, element: WebElement) -> bool:
        try:
            script = """
            var element = arguments[0];
            var style = window.getComputedStyle(element);
            return {
                pointerEvents: style.pointerEvents,
                opacity: style.opacity,
                visibility: style.visibility,
                display: style.display
            };
            """
            computed_styles = driver.execute_script(script, element)
            
            # checking css blocking 
            is_blocked = (
                computed_styles.get('pointerEvents') == 'none' or
                computed_styles.get('opacity') == '0.5' or 
                computed_styles.get('opacity') == '0' or
                computed_styles.get('visibility') == 'hidden' or
                computed_styles.get('display') == 'none'
            )
            
            return not is_blocked
            
        except Exception as ex:
            PageFormFiller.logger.warning(f"CSS interactability check failed: {ex}")
            return True

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
                    is_disabled = (
                        textbox.get_attribute("disabled") is not None
                        or textbox.get_attribute("readonly") is not None
                        or "k-disabled" in (textbox.get_attribute("class") or "")
                        or not textbox.is_enabled()
                        or not textbox.is_displayed()
                        # CSS checking. Developers not disabled elements, they just using opacity 0.5
                        or not PageFormFiller.is_css_interactable(driver, textbox)
                    )
                    if is_disabled:
                        continue
                    
                    # Scroll into view and wait briefly
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", textbox)
                    WebDriverWait(driver, 2).until(lambda d: textbox.is_enabled() and textbox.is_displayed())
                    
                    textbox.clear()
                    textbox.send_keys(text)
                except Exception as ex:
                    PageFormFiller.logger.error(f"Textbox fill failed. {type(ex).__name__}: {str(ex)}")

    @staticmethod
    def fill_form_textareas(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            # For plan pages, use JavaScript approach
            fake = Faker()
            text = fake.text(max_nb_chars=300).replace("\n", "\\n").replace('"', '\\"').replace("'", "\\'")
            script = PageFormFiller.create_script("textarea.js", {
                "{{isPlanPage}}": str(SeleniumHelper.is_plan_page_url(driver.current_url)).lower(),
                "{{text}}": f'"{text}"'
            })
            driver.execute_script(script)
        else:
            # For other pages, use direct Selenium approach
            textareas = driver.find_elements(By.CSS_SELECTOR, "textarea")
            fake = Faker()
            text = fake.text(max_nb_chars=300)
            for textarea in textareas:
                try:
                    # Enhanced disabled check
                    is_disabled = (
                        textarea.get_attribute("disabled") is not None
                        or textarea.get_attribute("readonly") is not None
                        or "k-disabled" in (textarea.get_attribute("class") or "")
                        or not textarea.is_enabled()
                        or not textarea.is_displayed()
                        # CSS checking. Developers not disabled elements, they just using opacity 0.5
                        or not PageFormFiller.is_css_interactable(driver, textarea)
                    )
                    if is_disabled:
                        continue
                    
                    # Scroll into view and wait briefly
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", textarea)
                    WebDriverWait(driver, 2).until(lambda d: textarea.is_enabled() and textarea.is_displayed())
                    
                    textarea.clear()
                    textarea.send_keys(text)
                except Exception as ex:
                    PageFormFiller.logger.error(f"Textarea fill failed. {type(ex).__name__}: {str(ex)}")

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
    def select_random_value_from_dropdown(driver: webdriver.Chrome, dropdown: WebElement) -> None:
        try:
            is_disabled = (
                dropdown.get_attribute("disabled") is not None
                or "k-disabled" in dropdown.get_attribute("class")
                or not dropdown.is_enabled()
                # CSS checking. Developers not disabled elements, they just using opacity 0.5
                or not PageFormFiller.is_css_interactable(driver, dropdown)
            )
            if is_disabled:
                return

            # Scroll element into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown)

            # Wait for element to be clickable
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(dropdown)
            )

            dropdown.click()
            popup = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "kendo-popup"))
            )
            options = popup.find_elements(By.CSS_SELECTOR, "ul>li")
            if options:
                selected_option = options[random.randint(0, len(options) - 1)]
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_option)
                WebDriverWait(driver, 1).until(EC.element_to_be_clickable(selected_option))
                selected_option.click()

            driver.find_element(By.TAG_NAME, "body").click() # Click on the body to close the dropdown
        except Exception as ex:
            PageFormFiller.logger.error(f"Multiselect click failed. {type(ex).__name__}: {str(ex)}")

    
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
                PageFormFiller.select_random_value_from_dropdown(driver, dropdownlist)


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
                PageFormFiller.select_random_value_from_dropdown(driver, multiselect)

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
       