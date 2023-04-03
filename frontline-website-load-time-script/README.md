### python load-time-script.py loading_test.xlsx --loops 3
### python load-time-script.py loading_test.xlsx --loops 3 --disable_save
## To run all files simultaneously:
### flags
#### --path - A path or a list of paths
#### --recurse - Allows to get files and nested files from a directory
#### --disable_save
#### --idm_auth
#### --loops
### python bootstrapper.py --path . --disable_save
### python bootstrapper.py --path . --disable_save --recurse
### python bootstrapper.py --path TX-DEV TX-STG --disable_save --recurse
### python bootstrapper.py --path TX-DEV TX-STG loading-test.xlsx --disable_save --recurse
### python bootstrapper.py --disable_save --loops 3
## Libraries to install
### pip install numpy
### pip install openpyxl
### pip install selenium
### pip install speedtest-cli
### pip install argparse
### pip install validators