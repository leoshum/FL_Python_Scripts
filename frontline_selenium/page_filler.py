from selenium import webdriver
from frontline_selenium.selenium_helper import SeleniumHelper

class PageFormFiller:
    @staticmethod
    def fill_form(driver: webdriver.Chrome) -> None:
        PageFormFiller.fill_form_radio_buttons(driver)
        PageFormFiller.fill_form_checkboxes(driver)
        PageFormFiller.fill_form_textareas(driver)
        PageFormFiller.fill_form_rich_text_editors(driver)
        PageFormFiller.fill_form_drop_down_lists(driver)
        PageFormFiller.fill_form_multiple_selects(driver)
        PageFormFiller.fill_form_date_time_pickes(driver)
        
    @staticmethod
    def fill_form_textareas(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            driver.execute_script("$('.form textarea').each(function() { $(this).val('test'); })")
        else:
            pass
    
    @staticmethod
    def fill_form_rich_text_editors(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            driver.execute_script("$(\".k-editor[data-role='text-editor']\").each(function() { $(this).data('kendoEditor').value('test'); })")
        else:
            pass

    @staticmethod
    def fill_form_checkboxes(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            driver.execute_script("$(\"input[type='checkbox']\").each(function() { $(this).prop('checked', true)})")
        else:
            driver.execute_script("""
                for (var i = 0; i < $("input[type='checkbox']").length; ++i) {
                    $("input[type='checkbox']")[i].click()
                }
            """)
    
    @staticmethod
    def fill_form_radio_buttons(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
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
        else:
            pass
    
    @staticmethod
    def fill_form_drop_down_lists(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
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
        else:
            pass
            #driver.execute_script("")
            #var comboBoxes = $("accelify-form-details-content kendo-combobox");
            #var comboBox = $("accelify-form-details-content kendo-combobox")[0];
            #comboBox.value = "a7a29640-2eeb-44d0-a864-3c4a5a4e8aca";
            #comboBox.dispatchEvent(new Event('change'));
            #var values = []
            #comboBoxes.each(function (index, comboBox) {
            #    console.log($(comboBox));
            #    console.log(comboBox.getElementsByTagName("option"));
            #    //var values = $(comboBox).data("kendoComboBox").dataItems().map(function (item) {
            #    //    return item.text;
            #    //});
            #    //var randomIndex = Math.floor(Math.random() * values.length);
            #    //var randomValue = values[randomIndex];
            #    //$(comboBox).data("kendoComboBox").value(randomValue);
            #});

    @staticmethod
    def fill_form_date_time_pickes(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
            driver.execute_script("""
            $(".form input[data-role='datePicker']").each(function() {
                $(this).data("kendoDatePicker").value(new Date());
            })
            """)
        else:
            pass
    
    @staticmethod
    def fill_form_multiple_selects(driver: webdriver.Chrome) -> None:
        if SeleniumHelper.is_plan_page_url(driver.current_url):
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
        else:
            pass