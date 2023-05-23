import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from frontline_selenium.selenium_helper import SeleniumHelper
from frontline_selenium.random_html_generator import RandomHtmlGenerator
from faker import Faker

class PageFormFiller:
    scripts_directory: str = os.path.dirname(os.path.abspath(__file__)) + "\\filling_scripts\\"
    
    @staticmethod
    def fill_form(driver: webdriver.Chrome) -> None:
        PageFormFiller.fill_form_radio_buttons(driver)
        PageFormFiller.fill_form_checkboxes(driver)
        PageFormFiller.fill_form_drop_down_lists(driver)
        PageFormFiller.fill_form_multiple_selects(driver)
        PageFormFiller.fill_form_textboxes(driver)
        PageFormFiller.fill_form_textareas(driver)
        PageFormFiller.fill_form_rich_text_editors(driver)
        PageFormFiller.fill_form_date_time_pickes(driver)
    
    def create_script(file_name: str, params: dict) -> str:
        with open(PageFormFiller.scripts_directory + file_name, "r") as script_file:
            script = script_file.read()
            for key in params.keys():
                script = script.replace(key, params[key])
            return script
    
    @staticmethod
    def fill_form_textboxes(driver: webdriver.Chrome) -> None:
        Faker.seed(0)
        fake = Faker()
        text = fake.sentence()
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            script = PageFormFiller.create_script("textbox.js", {
                "{{isPlanPage}}": str(SeleniumHelper.is_plan_page_url(driver.current_url)).lower(),
                "{{text}}": f"\"{text}\""
            })
            driver.execute_script(script)
        else:
            textboxes = driver.find_elements(By.CSS_SELECTOR, ".k-textbox")
            for textbox in textboxes:
                textbox.clear()
                textbox.send_keys(text)

    @staticmethod
    def fill_form_textareas(driver: webdriver.Chrome) -> None:
        Faker.seed(0)
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
        script = PageFormFiller.create_script("drop_down_list.js", {
            "{{isPlanPage}}": str(SeleniumHelper.is_plan_page_url(driver.current_url)).lower()
        })
        driver.execute_script(script)

    @staticmethod
    def fill_form_date_time_pickes(driver: webdriver.Chrome) -> None:
        script = PageFormFiller.create_script("date_time_picker.js", {
            "{{isPlanPage}}": str(SeleniumHelper.is_plan_page_url(driver.current_url)).lower()
        })
        driver.execute_script(script)
    
    @staticmethod
    def fill_form_multiple_selects(driver: webdriver.Chrome) -> None:
        script = PageFormFiller.create_script("multiple_select.js", {
            "{{isPlanPage}}": str(SeleniumHelper.is_plan_page_url(driver.current_url)).lower()
        })
        driver.execute_script(script)
       