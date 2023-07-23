$scriptName = 'wakeup'

Write-Host "Running PyInstaller..."
pyinstaller --hidden-import=requests --hidden-import=argparse "$scriptName.py"

Write-Host "Removing temporary files and folders..."
Remove-Item -Path ".\build" -Force -Recurse
Remove-Item -Path ".\$scriptName.spec"

Copy-Item -Path ".\config.json" -Destination ".\dist\$scriptName\config.json"
Copy-Item -Path ".\planng-mappings.json" -Destination ".\dist\$scriptName\planng-mappings.json"
#Copy-Item -Path ".\certs" -Destination "$newFolderName\certs" -Recurse

Write-Host "Creating a zip archive with the application..."
$zipFileName = "$scriptName.zip"
Compress-Archive -Path ".\dist\$scriptName" -DestinationPath $zipFileName -Force

Remove-Item -Path ".\dist" -Recurse

Write-Host "Process completed!"