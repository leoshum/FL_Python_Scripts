$scriptName = 'wakeup'

Write-Host "Running PyInstaller..."
pyinstaller  --hidden-import=requests --hidden-import=argparse "$scriptName.py" --onefile

Write-Host "Removing temporary files and folders..."
Remove-Item -Path ".\build" -Force -Recurse
Remove-Item -Path ".\$scriptName.spec"

$oldFolderName = ".\dist"
$newFolderName = ".\wakeup-script"
Rename-Item -Path $oldFolderName -NewName $newFolderName

Copy-Item -Path ".\config.json" -Destination "$newFolderName\config.json"
Copy-Item -Path ".\planng-mappings.json" -Destination "$newFolderName\planng-mappings.json"

Write-Host "Creating a zip archive with the application..."
$zipFileName = "$scriptName.zip"
Compress-Archive -Path $newFolderName -DestinationPath $zipFileName -Force

Remove-Item -Path $newFolderName -Recurse

Write-Host "Process completed!"