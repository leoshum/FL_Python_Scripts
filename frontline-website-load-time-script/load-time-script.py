import time
import numpy as np
import validators
import argparse
import speedtest  
from collections import namedtuple
from datetime import datetime
from urllib.parse import urlparse 
from openpyxl.workbook import Workbook
from openpyxl.styles import Alignment
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, colors, Font
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException

class unpresence_of_element(object):
	def __init__(self, locator):
		self.locator = locator

	def __call__(self, driver):
		try:
			driver.find_element(*self.locator)
			return False
		except:
			return True
		
def is_file_opened(filename):
	try:
		wb = load_workbook(filename)
		wb.save(filename)
		return False
	except:
		return True


def is_form_page(url):
	return "Forms" in url or ("ViewEvent" in url and urlparse(url).fragment)

def extract_base_url(url):
	url_parts = urlparse(url)
	return f"{url_parts.scheme}://{url_parts.netloc}"

def mark_form_as_invalid(row, color="FF0000"):
	row[0].font = Font(color=color)
	row[1].font = Font(color=color)

def measure_network_speed():
	st = speedtest.Speedtest()
	return st.download() / 1000000

def specify_sheet_layout(sheet):
	sheet.move_range("M1:M1", rows=0, cols=9)
	sheet.move_range("D1:D1", rows=0, cols=9)
	sheet.move_range("M2:M2", rows=0, cols=9)
	sheet.move_range("D2:D2", rows=0, cols=9)

def reset_styles(cells):
	for cell in cells:
		cell.style = "Normal"

def flag_high_load_time(cells, threshold):
	for cell in cells:
		if cell.value != None and float(cell.value) > threshold:
			cell.font = Font(color="FF0000")

def login_user(driver, url):
	driver.get(url)
	if "AcceliTrack" in driver.current_url:
		return
	username_field = driver.find_element("id", "UserName")
	password_field = driver.find_element("id", "Password")
	submit_btn = driver.find_element("id", "lnkLogin")
	username_field.send_keys("PMGMT")
	password_field.send_keys("8Huds(3d")
	submit_btn.click()

def measure_form_page_load(url, driver, timeout):
	start_time = time.time()
	driver.get(url)
	WebDriverWait(driver, timeout).until(
		EC.any_of(
			EC.presence_of_element_located((By.ID, "pnlForm")),
			EC.presence_of_element_located((By.ID, "pnlEventContent")),
			EC.presence_of_element_located((By.TAG_NAME, "accelify-forms-details")),
			EC.presence_of_element_located((By.TAG_NAME, "accelify-event-eligiblity-determination")),
			EC.presence_of_element_located((By.TAG_NAME, "accelify-progress-report")),
			EC.presence_of_element_located((By.TAG_NAME, "accelify-forms-details")),
            EC.presence_of_element_located((By.TAG_NAME, "accelify-event-exceptionalities-view"))
		)
	)
	return time.time() - start_time

def measure_standard_page_load(url, driver, timeout):
	start_time = time.time()
	driver.get(url)
	WebDriverWait(driver, timeout).until(
		EC.any_of(
			unpresence_of_element((By.CLASS_NAME, "loading-wrapper")),
			unpresence_of_element((By.CLASS_NAME, "blockUI")),
			unpresence_of_element((By.CLASS_NAME, "blockMsg")),
			unpresence_of_element((By.CLASS_NAME, "blockPage"))
		)
	)
	return time.time() - start_time

def measure_form_save(url, driver, timeout):
	measure_form_page_load(url, driver, timeout)
	loader_locator = unpresence_of_element((By.CSS_SELECTOR, ".blockUI .blockOverlay"))
	WebDriverWait(driver, timeout).until(loader_locator)
	WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#btnUpdateForm, accelify-forms-details button[type='submit']")))
	save_btns = driver.find_elements(By.CSS_SELECTOR, "#btnUpdateForm, accelify-forms-details button[type='submit']")
	start_time = None
	save_btn_elem = None
	for save_btn in save_btns:
		if save_btn.text == "Save Form":
			save_btn_elem = save_btn
			break
		
	if save_btn_elem != None:
		start_time = time.time()
		save_btn_elem.click()
		WebDriverWait(driver, timeout).until(loader_locator)
	else:
		raise NoSuchElementException()
	return time.time() - start_time

def measure_load_time(driver, url, timeout, loops, scenario):
	measure_result = namedtuple("MeasureResult", ["first_measure", "min", "max", "mean"])
	totals = np.zeros(loops)
	is_first_measure = True
	first_measure = 0
	for j in range(loops):
		measured_time = scenario(url, driver, timeout)
		totals[j] = measured_time
		if is_first_measure:
			is_first_measure = False
			first_measure = measured_time
	return measure_result(first_measure, np.min(totals), np.max(totals), np.mean(totals))

def compare_measures(curr_cell, prev_cell, diff_cell):
	if curr_cell.value == None or prev_cell.value == None:
		reset_styles([curr_cell, prev_cell, diff_cell])
		return

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
		diff_cell.fill = PatternFill(start_color="00FF00", fill_type = "solid")
	elif growth <= 10 and growth >= -10:
		diff_cell.fill = PatternFill(start_color="FFFF00", fill_type = "solid")
	else:
		diff_cell.fill = PatternFill(start_color="FF0000", fill_type = "solid")

def main():
	timestamp = datetime.now().strftime("%m-%d-%y_%H-%M")
	start_time = time.time()
	parser = argparse.ArgumentParser()
	parser.add_argument("input_file", type=str)
	parser.add_argument("--loops", type=int, default=3)
	parser.add_argument("--disable_save", action="store_true")
	my_namespace = parser.parse_args()

	#network_speed = measure_network_speed()
	input_file = my_namespace.input_file
	loops = my_namespace.loops
	disable_save = my_namespace.disable_save
	threshold = 6
	timeout = 30

	if is_file_opened(input_file):
		print(f"Close opened {input_file} file!")
		return
	
	wb = load_workbook(input_file, data_only=True)
	wb_sheet = wb.active
	specify_sheet_layout(wb_sheet)
	driver = webdriver.Chrome()
	#driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled":True})
	options = Options()
	options.headless = True

	driver = webdriver.Chrome(options=options)
	head_cell_top = wb_sheet["D1"]
	head_cell_top.alignment = Alignment(horizontal='center')
	head_cell_bottom = wb_sheet["D2"]
	head_cell_bottom.alignment = Alignment(horizontal='center')

	build_version = ""
	prev_base_url = ""

	base_url = ""
	is_first_row = True
	for row in wb_sheet.iter_rows(min_row=5):
		url = row[1].value
		if url != None and validators.url(url):
			print(url)
			base_url = extract_base_url(url)
			if prev_base_url != base_url or is_first_row:
				login_user(driver, base_url)
				build_version = driver.find_element(By.CSS_SELECTOR, "span.version").text.replace("Version ", "")
				is_first_row = False
			row[21].value = row[12].value
			row[22].value = row[13].value
			row[23].value = row[14].value
			row[24].value = row[15].value

			row[25].value = row[17].value
			row[26].value = row[18].value
			row[27].value = row[19].value

			reset_styles([row[12], row[13], row[14], 
		 				  row[15], row[21], row[22], 
						  row[23], row[24], row[25],
						  row[17], row[18], row[19],
						  row[7], row[11], row[16],
						  row[26], row[27], row[20]])

			row[12].value = row[3].value
			row[13].value = row[4].value
			row[14].value = row[5].value
			row[15].value = row[6].value

			row[17].value = row[8].value
			row[18].value = row[9].value
			row[19].value = row[10].value

			flag_high_load_time([row[12], row[13], row[14], 
		 				  		 row[15], row[21], row[22], 
						  		 row[23], row[24], row[25],
						  		 row[17], row[18], row[19],
						  		 row[26], row[27]], threshold)

			scenario = measure_form_page_load
			is_form_page_url = is_form_page(url)
			if not is_form_page_url:
					scenario = measure_standard_page_load

			try:
				(first_load_time, min_time, max_time, mean_time) = measure_load_time(driver, url, timeout, loops, scenario)
				reset_styles([row[0], row[1]])
			except TimeoutException:
				(first_load_time, min_time, max_time, mean_time) = (timeout, timeout, timeout, timeout)
				mark_form_as_invalid(row)

			if is_form_page_url and not disable_save:
				try:
					(first_save_time, min_save_time, max_save_time, mean_save_time) = measure_load_time(driver, url, timeout, loops, measure_form_save)
				except TimeoutException:
					(first_save_time, min_save_time, max_save_time, mean_save_time) = (timeout, timeout, timeout, timeout)
					mark_form_as_invalid(row)
				except ElementClickInterceptedException:
					(first_save_time, min_save_time, max_save_time, mean_save_time) = (timeout, timeout, timeout, timeout)
					mark_form_as_invalid(row, color="9933FF")

			row[3].value = f"{first_load_time:.2f}"
			row[4].value = f"{min_time:.2f}"
			row[5].value = f"{max_time:.2f}"
			row[6].value = f"{mean_time:.2f}"
			compare_measures(row[15], row[24], row[16])
			compare_measures(row[6], row[15], row[7])

			if is_form_page_url and not disable_save:
				row[8].value = f"{min_save_time:.2f}"
				row[9].value = f"{max_save_time:.2f}"
				row[10].value = f"{mean_save_time:.2f}"
				compare_measures(row[19], row[28], row[20])
				compare_measures(row[10], row[19], row[11])

			reset_styles([row[3], row[4], row[5], row[6], row[8], row[9], row[10]])
			flag_high_load_time([row[3], row[4], row[5], row[6], row[8], row[9], row[10]], threshold)
			prev_base_url = base_url
	head_cell_top.value = f"{build_version} {timestamp}"
	head_cell_bottom.value = f"{((time.time() - start_time) / 60):.2f}m, {network_speed:.2f}mb/s, loops: {loops}"
	wb.save(input_file)

if __name__ == "__main__":
	main()