$scriptName = 'wakeup'

Write-Host "Running PyInstaller..."
pyinstaller --hidden-import=requests --hidden-import=argparse "$scriptName.py"

Write-Host "Removing temporary files and folders..."
Remove-Item -Path ".\build" -Force -Recurse
Remove-Item -Path ".\$scriptName.spec"

Copy-Item -Path ".\config.json" -Destination ".\dist\$scriptName\config.json"
Copy-Item -Path ".\urls.json" -Destination ".\dist\$scriptName\urls.json"
Copy-Item -Path ".\setup_scheduler.ps1" -Destination ".\dist\$scriptName\setup_scheduler.ps1"
Copy-Item -Path ".\planng-mappings.json" -Destination ".\dist\$scriptName\planng-mappings.json"

Write-Host "Creating a zip archive with the application..."
$zipFileName = "$scriptName.zip"
Compress-Archive -Path ".\dist\$scriptName" -DestinationPath $zipFileName -Force

Remove-Item -Path ".\dist" -Recurse

Write-Host "Process completed!"