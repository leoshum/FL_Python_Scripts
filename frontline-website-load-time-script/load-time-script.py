import os
import sys
import time
import numpy as np
import validators
import argparse
import speedtest
import logging
from collections import namedtuple
from datetime import datetime
from urllib.parse import urlparse 
from openpyxl.styles import Alignment
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

package_path = os.path.abspath('..')
sys.path.append(package_path)
from frontline_selenium.selenium_helper import SeleniumHelper
from frontline_selenium.page_filler import PageFormFiller
from frontline_selenium.support_tech_helper import SupportTech

class HideBacktraceFormatter(logging.Formatter):
    def formatException(self, exc_info):
        tb = super().formatException(exc_info)
        return HideBacktraceFormatter.removeBackTrace(tb)
    
    def format(self, record: logging.LogRecord):
        record.msg = HideBacktraceFormatter.removeBackTrace(record.msg)
        return super().format(record)
    
    @staticmethod
    def removeBackTrace(record):
        tb_lines = str(record).splitlines()
        filtered_tb_lines = []
        skip_slce = False
        for line in tb_lines:
            if "Backtrace:" in line:
                skip_slce = True
            if "Traceback (most recent call last):" in line:
                skip_slce = False
            if not skip_slce:
                filtered_tb_lines.append(line)
        return "\n".join(filtered_tb_lines)
    
    
def split_path(path):
    folders = []
    head, tail = os.path.split(path)
    
    while tail:
        folders.insert(0, tail)
        head, tail = os.path.split(head)
    return folders


def is_excel_file_opened(filename):
    try:
        wb = load_workbook(filename)
        wb.save(filename)
        return False
    except:
        return True


def extract_base_url(url):
    url_parts = urlparse(url)
    return f"{url_parts.scheme}://{url_parts.netloc}"


def mark_form_as_invalid(row, color="FF0000"):
    row[0].font = Font(color=color)
    row[1].font = Font(color=color)


def measure_network_speed():
    try:
        st = speedtest.Speedtest()
        return round(st.download() / 1000000, 2)
    except:
        return -1


def specify_sheet_layout(sheet):
    sheet.move_range("N1:N1", rows=0, cols=9)
    sheet.move_range("E1:E1", rows=0, cols=9)
    sheet.move_range("N2:N2", rows=0, cols=9)
    sheet.move_range("E2:E2", rows=0, cols=9)


def reset_styles(cells):
    for cell in cells:
        cell.style = "Normal"


def flag_high_load_time(cells, threshold):
    for cell in cells:
        if cell.value != None and cell.value != "" and float(cell.value) > threshold:
            cell.font = Font(color="FF0000")


def measure_load_time(driver, url, loops, scenario):
    measure_result = namedtuple("MeasureResult", ["first_measure", "min", "max", "mean"])
    totals = np.zeros(loops)
    is_first_measure = True
    first_measure = 0
    
    # Extract form name from URL for better logging
    form_name = "Page"
    
    if "/Forms/" in url:
        # Standard form URL: .../Forms/FormName/id
        form_name = url.split("/Forms/")[1].split("/")[0]
    elif "/ViewEvent/" in url:
        # Event URL: .../ViewEvent/id/PageName or just .../ViewEvent/id
        parts = url.split("/ViewEvent/")[1].split("/")
        if len(parts) >= 2:
            form_name = parts[1]  # Get the page name after event ID
        else:
            form_name = "ViewEvent"
    elif "ViewEvent?" in url:
        # Handle ViewEvent with query parameters like ViewEvent?eventId=...#formname&formId=...
        if "#" in url:
            # Extract the form name from the hash fragment
            hash_part = url.split("#")[1]
            if "&" in hash_part:
                form_name = hash_part.split("&")[0]
            else:
                form_name = hash_part
            # Clean up the form name
            form_name = form_name.replace("(", "").replace(")", "").title()
        else:
            form_name = "ViewEvent"
    else:
        # Generic page - extract last meaningful part
        path_parts = url.split("/")
        for part in reversed(path_parts):
            if part and len(part) > 2 and part.strip() and not part.replace("-", "").isdigit():
                form_name = part
                break
    
    operation_type = "LOAD"
    if "save" in scenario.__name__.lower():
        operation_type = "SAVE"
    
    print(f"\n🔄 Starting {operation_type} measurements for: {form_name}")
    
    for j in range(loops):
        print(f"\n📏 Measurement {j+1}/{loops} ({operation_type}): {form_name}")
        # Let measurement functions handle their own navigation
        
        # Check if scenario returns tuple (new format) or just time (old format)
        if hasattr(scenario, '__name__') and 'form_page_load' in scenario.__name__:
            # New format returns (load_time, network_state)
            measured_time, network_state = scenario(driver, url)
            
            # Extract API requests from network_state
            if isinstance(network_state, dict):
                api_requests = network_state.get('allApiRequests', [])
            else:
                api_requests = []
            
            # Log API requests for debugging on first measurement
            if j == 0 and api_requests:
                slow_requests = [req for req in api_requests if isinstance(req, dict) and req.get('duration', 0) > 3000]
                if slow_requests:
                    print(f"🐌 Slow API requests detected:")
                    for req in slow_requests:
                        print(f"   {req.get('url', 'Unknown')} - {req.get('duration', 0):.0f}ms ({req.get('status', 'Unknown')})")
        else:
            # Fixed: measure_form_save_time only takes driver argument
            if hasattr(scenario, '__name__') and 'save' in scenario.__name__:
                measured_time = scenario(driver)  # Only driver for save functions
            elif hasattr(scenario, '__name__') and 'standard_page_load' in scenario.__name__:
                measured_time = scenario(driver)  # Only driver for standard page load
            else:
                measured_time = scenario(driver, url)  # driver + url for other functions
            api_requests = []
        
        totals[j] = measured_time
        print(f"✅ Completed in {measured_time:.3f}s")
        
        if is_first_measure:
            is_first_measure = False
            first_measure = measured_time
    
    print(f"\n📈 {operation_type} Results for {form_name}:")
    print(f"   First: {first_measure:.3f}s | Min: {np.min(totals):.3f}s | Max: {np.max(totals):.3f}s | Mean: {np.mean(totals):.3f}s")
    
    return measure_result(first_measure, np.min(totals), np.max(totals), np.mean(totals))


def compare_measures(curr_cell, prev_cell, diff_cell):
    if curr_cell.value == None or prev_cell.value == None:
        reset_styles([curr_cell, prev_cell, diff_cell])
        return
    
    GREEN_COLOR = "00FF00"
    YELLOW_COLOR = "FFFF00"
    RED_COLOR = "FF0000"

    prev_row_float = 0.0
    try:
        prev_row_float = float(prev_cell.value[:prev_cell.value.index("(")])
    except:
        prev_row_float = float(prev_cell.value)

    try:
        diff = float(curr_cell.value) / prev_row_float
    except:
        diff = 0
    growth = (diff * 100) - 100
    diff_cell.value = f"{abs(growth):.2f}%"
    if growth < -10:
        diff_cell.fill = PatternFill(start_color=GREEN_COLOR, fill_type = "solid")
    elif growth <= 10 and growth >= -10:
        diff_cell.fill = PatternFill(start_color=YELLOW_COLOR, fill_type = "solid")
    else:
        diff_cell.fill = PatternFill(start_color=RED_COLOR, fill_type = "solid")


def configure_logger(file_name: str, processing_filename: str) -> logging.Logger:
    logger = logging.getLogger("main")
    logger.setLevel(logging.INFO)

    formatter = HideBacktraceFormatter("%(asctime)s - %(message)s", datefmt="%m-%d-%y_%H:%M")
    timestamp = datetime.now().strftime("%m-%d-%y_%H-%M")
    parts = split_path(processing_filename)
    folders = parts[0:len(parts)-1]
    filename = parts[-1]
    fh = logging.FileHandler(f"{file_name}_{'_'.join(folders)}_{filename.split('.')[0]}_{timestamp}.log")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    SeleniumHelper.setup_logger(logger)
    PageFormFiller.setup_logger(logger)
    return logger


def main():
    timestamp = datetime.now().strftime("%m-%d-%y_%H-%M")
    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str)
    parser.add_argument("--loops", type=int, default=3)
    parser.add_argument("--disable_save", action="store_true")
    parser.add_argument("--disable_filler", action="store_true", default=False)
    parser.add_argument("--idm_auth", action="store_true", default=False)
    my_namespace = parser.parse_args()

    input_file = my_namespace.input_file
    loops = my_namespace.loops
    disable_save = my_namespace.disable_save
    disable_filler = my_namespace.disable_filler
    idm_auth = my_namespace.idm_auth
    threshold = 6
    timeout = 30

    logger = configure_logger("script-log", input_file)
    SeleniumHelper.set_options({
        "disable_filler": disable_filler
    })
    print(f"Input file: {input_file}")
    if not os.path.isfile(input_file):
        print("Input file doesn't exist.")
        return
    if is_excel_file_opened(input_file):
        print(f"Close opened {input_file} file!")
        return
    
    network_speed = measure_network_speed()

    wb = load_workbook(input_file, data_only=True)
    wb_sheet = wb.active
    wb_sheet.cell(row=1, column=31).value = "."
    wb_sheet.cell(row=1, column=31).value = ""
    specify_sheet_layout(wb_sheet)

    options = Options()
    #options.headless = True
    driver = webdriver.Chrome(options=options)
    head_cell_top = wb_sheet["F1"]
    head_cell_top.alignment = Alignment(horizontal='center')
    head_cell_bottom = wb_sheet["F2"]
    head_cell_bottom.alignment = Alignment(horizontal='center')

    for row in wb_sheet.iter_rows(min_row=5):
        for i in range(14, 18):
            row[i + 9].value = row[i].value

        for i in range(19, 22):
            row[i + 8].value = row[i].value

        reset_styles([row[14], row[15], row[16], 
                      row[17], row[23], row[24], 
                      row[25], row[26], row[27],
                      row[19], row[20], row[21],
                      row[9], row[13], row[18],
                      row[28], row[29], row[22]])

        for i in range(5, 9):
            row[i + 9].value = row[i].value

        for i in range(10, 13):
            row[i + 9].value = row[i].value

        flag_high_load_time([row[14], row[15], row[16], 
                             row[17], row[24], row[24], 
                             row[25], row[26], row[27],
                             row[19], row[20], row[21],
                             row[28], row[29]], threshold)
        for i in range(3, 13):
            row[i].value = ""
        reset_styles([row[3], row[4], row[5], row[6], row[7], row[8], row[10], row[11], row[12]])

    build_version = ""
    prev_base_url = ""
    processed_records = 0

    base_url = ""
    is_first_row = True
    for row in wb_sheet.iter_rows(min_row=5):
        url = row[1].value
        if url == None or not validators.url(url):
            continue
        
        processed_records += 1
        
        row[4].value = datetime.now().strftime('%y-%m-%d %H:%M:%S')
        print(f"\n{url}")
        logger.debug(f"Processing: {url}")
        
        try:
            base_url = extract_base_url(url)
            if prev_base_url != base_url or is_first_row:
                if idm_auth:
                    SupportTech.login(driver)
                    time.sleep(3)
                    SupportTech.open_website(driver, base_url, "SFTDVTester")
                    # Initial navigation to establish session - this doesn't count as measurement
                    driver.get(url)
                else:
                    SeleniumHelper.login_user(base_url, driver, "SFTDVTester", "ht2jGMM2GnC3bwX7")
                build_version = SeleniumHelper.get_build_version(driver)
                is_first_row = False

            driver.get(url)

            scenario = SeleniumHelper.measure_form_page_load_time
            is_form_page_url = SeleniumHelper.is_form_page_url(url)
            if not is_form_page_url:
                    scenario = SeleniumHelper.measure_standard_page_load_time

            error_in_page_loading = False
            
            if not is_form_page_url:
                driver.get(url)

            if not error_in_page_loading:
                try:
                    (first_load_time, min_time, max_time, mean_time) = measure_load_time(driver, url, loops, scenario)
                    reset_styles([row[0], row[1]])
                except TimeoutException as ex:
                    # Form load timeout - record error in column D
                    (first_load_time, min_time, max_time, mean_time) = (timeout, timeout, timeout, timeout)
                    row[3].value = f"Timeout waiting for form to load: {timeout}s"
                    mark_form_as_invalid(row)
                    error_in_page_loading = True
                    logger.error(f"Timeout waiting for form to load: {url}")
                except Exception as e:
                    (first_load_time, min_time, max_time, mean_time) = (timeout, timeout, timeout, timeout)
                    row[3].value = f"Page speed measurement error: {str(e)[:50]}"
                    mark_form_as_invalid(row)
                    error_in_page_loading = True
                    logger.error(f"Page speed measurement error for {url}: {str(e)}")

            # SAVE MEASUREMENT SECTION
            error_in_save = False
            if is_form_page_url and not disable_save and not error_in_page_loading:
                try:
                    # Check if this is a likely readonly form before attempting save
                    if SeleniumHelper.is_likely_readonly_form(url):
                        if logger:
                            logger.info(f"Skipping save measurement for likely readonly form: {url}")
                        row[3].value = "Likely read-only form (no Save button expected)"
                        row[10].value = ""
                        row[11].value = ""
                        row[12].value = ""
                    else:
                        (first_save_time, min_save_time, max_save_time, mean_save_time) = measure_load_time(driver, url, loops, SeleniumHelper.measure_form_save_time)
                        
                except ValueError as ex:
                    error_in_save = True
                    error_msg = str(ex)
                    
                    if "likely read-only" in error_msg.lower() or "no save button" in error_msg.lower():
                        logger.info(f"Form appears to be read-only: {url} - {error_msg}")
                        row[3].value = "Likely read-only form (no Save button expected)"
                        error_in_save = False  # This is not an error
                    elif "non-functional" in error_msg.lower():
                        mark_form_as_invalid(row, color="FF9900")  # Orange for non-functional buttons
                        logger.error(f"Form save button non-functional: {url} - {error_msg}")
                        row[3].value = "Save button found but non-functional"
                    elif "network error" in error_msg.lower():
                        mark_form_as_invalid(row)
                        logger.error(f"Form save network error: {url} - {error_msg}")
                        row[3].value = f"Save failed: Network error ({error_msg.split(':')[1].strip() if ':' in error_msg else 'Status code error'})"
                    else:
                        mark_form_as_invalid(row)
                        logger.error(f"Form save exception: {url} - {error_msg}")
                        row[3].value = "Exception occurred while saving the form!"
                        
                except TimeoutException as ex:
                    mark_form_as_invalid(row)
                    error_in_save = True
                    logger.error(f"Form save timeout: {url} - No success confirmation after 30s")
                    row[3].value = "Save timeout: No confirmation received"
                    
                except ElementClickInterceptedException as ex:
                    mark_form_as_invalid(row, color="9933FF")
                    error_in_save = True
                    logger.error(f"Form save click intercepted: {url} - Save button not clickable")
                    row[3].value = "Save button click intercepted"
                    
                except NoSuchElementException as ex:
                    error_in_save = True
                    error_msg = str(ex)
                    
                    # Simle handling - we can't always distinguish between readonly and errors
                    if SeleniumHelper.is_likely_readonly_form(url):
                        # If URL suggests readonly, treat as expected behavior
                        logger.info(f"No Save button found on likely readonly form: {url}")
                        row[3].value = "Likely read-only form (no Save button expected)"
                        error_in_save = False  # This is not an error
                    else:
                        # Otherwise, treat as an error that needs investigation
                        mark_form_as_invalid(row, color="FF6600")  # Orange for investigation needed
                        logger.error(f"Save button not found: {url} - Needs investigation")
                        row[3].value = "Save button not found "
                    
                except StaleElementReferenceException as ex:
                    mark_form_as_invalid(row, color="550000")
                    error_in_save = True
                    logger.error(f"Form save stale element: {url} - DOM changed during save")
                    row[3].value = "DOM changed during save"
                    
                except TypeError as ex:
                    mark_form_as_invalid(row, color="FF6600")
                    error_in_save = True
                    logger.error(f"Form save TypeError: {url} - Function call error: {str(ex)}")
                    row[3].value = "Function call error (TypeError)"
                    
                except Exception as ex:
                    mark_form_as_invalid(row, color="800080")
                    error_in_save = True
                    logger.error(f"Form save unexpected error: {url} - {str(ex)}")
                    row[3].value = f"Unexpected error: {str(ex)[:30]}"

            row[5].value = f"{first_load_time:.2f}"
            row[6].value = f"{min_time:.2f}"
            row[7].value = f"{max_time:.2f}"
            row[8].value = f"{mean_time:.2f}"

            compare_measures(row[17], row[26], row[18])
            compare_measures(row[8], row[17], row[9])

            if is_form_page_url and not disable_save and not error_in_page_loading:
                if not error_in_save:
                    row[10].value = f"{min_save_time:.2f}"
                    row[11].value = f"{max_save_time:.2f}"
                    row[12].value = f"{mean_save_time:.2f}"
                    compare_measures(row[21], row[29], row[22])
                    compare_measures(row[12], row[21], row[13])
                else:
                    row[10].value = ""
                    row[11].value = ""
                    row[12].value = ""

            if disable_save or error_in_page_loading:
                row[10].value = ""
                row[11].value = ""
                row[12].value = ""

            flag_high_load_time([row[5], row[6], row[7], row[8], row[10], row[11], row[12]], threshold)
            
        except Exception as critical_ex:
            logger.error(f"Critical error processing {url}: {str(critical_ex)}")
            row[3].value = f"Critical error: {str(critical_ex)[:40]}"
            mark_form_as_invalid(row, color="000000")  # Black for critical errors
            
            # Set default values to prevent crashes
            row[5].value = f"{timeout:.2f}"
            row[6].value = f"{timeout:.2f}"
            row[7].value = f"{timeout:.2f}"
            row[8].value = f"{timeout:.2f}"
            row[10].value = ""
            row[11].value = ""
            row[12].value = ""
        
        prev_base_url = base_url
        head_cell_top.value = f"{build_version} {timestamp}"
        head_cell_bottom.value = f"{((time.time() - start_time) / 60):.2f}m, {network_speed}mb/s, loops: {loops}"
        wb.save(input_file)
    
    driver.quit()

    total_seconds = time.time() - start_time
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    
    print(f"\n" + "="*60)
    print(f"🎉 PROCESSING COMPLETED!\n")
    print(f"🔄 Loops per record: {loops}")
    print(f"📊 Total records processed: {processed_records}")
    print(f"⏱️ Total time: {hours:02d}h {minutes:02d}m {seconds:02d}s")
    if processed_records > 0:
        print(f"📈 Average time per record: {(total_seconds/(processed_records * loops)):.1f}s")
    print(f"="*60)

if __name__ == "__main__":
    main()