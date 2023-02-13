import os
import subprocess
import argparse

def get_excel_files_in_dir(base_path, recurse=False):
	result_files = []
	for (root,dirs,files) in os.walk(base_path, topdown=True):
		for file in files:
			if "xlsx" in file:
				result_files.append(f"{root}\{file}")
		if not recurse:
			break
	return result_files

def get_new_unique_files(new_files, existing_files):
	unique_files = []
	for new_file in new_files:
		is_file_exists = False
		for existing_file in existing_files:
			if os.path.samefile(new_file, existing_file):
				is_file_exists = True
				break
		if not is_file_exists:
			unique_files.append(new_file)
	return unique_files

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--loops", type=int, default=3)
	parser.add_argument("--disable_save", action="store_true")
	parser.add_argument("--recurse", action="store_true")
	parser.add_argument('-p', '--path', default=get_excel_files_in_dir("."), nargs='+')
	my_namespace = parser.parse_args()

	files = []
	for file in my_namespace.path:
		new_files = []
		if os.path.isfile(file) and "~" not in file:
			new_files.append(file)

		if os.path.isdir(file):
			new_files += get_excel_files_in_dir(file, my_namespace.recurse)
		files += get_new_unique_files(new_files, files)

	for file in files:
		command = f"start cmd /k python load-time-script.py {file} --loops {my_namespace.loops}"
		if my_namespace.disable_save:
			command += " --disable_save"
		subprocess.call(command, shell=True)
	print(files)
if __name__ == "__main__":
	main()