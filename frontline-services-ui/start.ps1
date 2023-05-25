if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
	# Start a new PowerShell process with administrator privileges
	Start-Process powershell.exe "-File `"$PSCommandPath`"" -Verb RunAs
	# Exit the current PowerShell process
	Exit
}
#Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
$Path = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'services'
$StartAngular = { ng serve }

Start-Process powershell.exe -WorkingDirectory $Path -ArgumentList "-NoExit", $StartAngular

python "$(Split-Path -Parent $MyInvocation.MyCommand.Path)\server.py"
