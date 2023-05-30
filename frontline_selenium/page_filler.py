import os
import random
import time
import logging
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from frontline_selenium.selenium_helper import SeleniumHelper
from frontline_selenium.random_html_generator import RandomHtmlGenerator
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
                        textbox.clear()
                        textbox.send_keys(text)
                    except Exception as ex:
                        PageFormFiller.logger.exception(ex)

    @staticmethod
    def fill_form_textareas(driver: webdriver.Chrome) -> None:
        fake = Faker()
        text = fake.text(max_nb_chars=600).replace("\n", "\\n")
        script = ""
        script = PageFormFiller.create_script("textarea.js", {
            "{{isPlanPage}}": str(SeleniumHelper.is_plan_page_url(driver.current_url)).lower(),
            "{{text}}": f"\"{text}\""
        })
        driver.execute_script(script)
    
    @staticmethod
    def fill_form_rich_text_editors(driver: webdriver.Chrome) -> None:
        text = RandomHtmlGenerator.generate_random_html()
        script = PageFormFiller.create_script("rich_text_editor.js", {
            "{{isPlanPage}}": str(SeleniumHelper.is_plan_page_url(driver.current_url)).lower(),
            "{{text}}": f"\"{text}\""
        })
        driver.execute_script(script)

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
    def fill_form_drop_down_lists(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            script = PageFormFiller.create_script("drop_down_list.js")
            driver.execute_script(script)
        else:
            comboboxes = driver.find_elements(By.CSS_SELECTOR, "kendo-combobox")
            for combobox in comboboxes:
                data_keys = combobox.get_attribute("datakeys").split(";")
                input = combobox.find_element(By.CSS_SELECTOR, "kendo-searchbar>input")
                try:
                    input.clear()
                    input.send_keys(data_keys[random.randint(0, len(data_keys) - 1)])
                except Exception as ex:
                    PageFormFiller.logger.exception(ex)

            driver.find_element(By.CSS_SELECTOR, "h1").click()
            dropdownlists = driver.find_elements(By.CSS_SELECTOR, "table kendo-dropdownlist")
            for dropdownlist in dropdownlists:
                try:
                    dropdownlist.click()
                    popup = driver.find_element(By.CSS_SELECTOR, "kendo-popup")
                    options = popup.find_elements(By.CSS_SELECTOR, "ul>li")
                    options[random.randint(0, len(options) - 1)].click()
                except Exception as ex:
                    PageFormFiller.logger.exception(ex)

    @staticmethod
    def fill_form_date_time_picker(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            script = PageFormFiller.create_script("date_time_picker.js")
            driver.execute_script(script)
        else:
            date_pickers = driver.find_elements(By.CSS_SELECTOR, "kendo-datepicker")
            for date_picker in date_pickers:
                try:
                    input = date_picker.find_element(By.CSS_SELECTOR, "kendo-dateinput>input")
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
                try:
                    multiselect.click()
                    popup = driver.find_element(By.CSS_SELECTOR, "kendo-popup")
                except Exception as ex:
                    PageFormFiller.logger.exception(ex)

       