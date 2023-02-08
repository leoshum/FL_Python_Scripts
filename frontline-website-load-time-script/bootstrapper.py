import os
import subprocess
import argparse

def get_excel_files_in_dir(base_path):
	result_files = []
	for (root,dirs,files) in os.walk(base_path, topdown=True):
		for file in files:
			if "xlsx" in file:
				result_files.append(f"{root}\{file}")
	return result_files

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--loops", type=int, default=3)
	parser.add_argument("--disable_save", action="store_true")
	my_namespace = parser.parse_args()
	files = get_excel_files_in_dir(".")
	for file in files:
		command = f"start cmd /k python load-time-script.py {file} --loops {my_namespace.loops}"
		if my_namespace.disable_save:
			command += " --disable_save"
		subprocess.call(command, shell=True)

if __name__ == "__main__":
	main()