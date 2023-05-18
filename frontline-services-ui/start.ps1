$Path = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'services'
$StartAngular = { ng serve }

Start-Process powershell.exe -WorkingDirectory $Path -ArgumentList "-NoExit", $StartAngular

python server.py