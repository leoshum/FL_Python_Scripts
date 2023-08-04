param(
    [string]$ExeFilePath,
    [string]$RunAsUser,
    [string]$ExeParams,
    [string]$TaskName1 = "MorningWakeup",
    [string]$TaskName2 = "DailyWakeup",
    [string]$Description1 = "Description",
    [string]$Description2 = "Description",
    [string]$StartTime1 = "05:00",
    [string]$StartTime2 = "14:00"
)

function New-DailyTrigger {
    param(
        [string]$StartTime
    )
    $startTimeISO8601 = Get-Date -Hour ([int]($StartTime -split ':')[0]) -Minute ([int]($StartTime -split ':')[1]) -Second 0 -Format "yyyy-MM-ddTHH:mm:ss"
    $trigger = New-ScheduledTaskTrigger -Daily -At $startTimeISO8601 -DaysInterval 1
    return $trigger
}

if ([string]::IsNullOrEmpty($ExeParams)) {
    $ExeParams = Join-Path (Get-Item $ExeFilePath).Directory.FullName "urls.json"
}

$trigger1 = New-DailyTrigger -StartTime $StartTime1
$trigger2 = New-DailyTrigger -StartTime $StartTime2

$action = New-ScheduledTaskAction -Execute $ExeFilePath -Argument $ExeParams
$principal = New-ScheduledTaskPrincipal -UserId $RunAsUser -LogonType Password -RunLevel Highest

Register-ScheduledTask -TaskName $TaskName1 -Trigger $trigger1 -User $RunAsUser -Action $action -Description $Description1 -Force -AsJob
Register-ScheduledTask -TaskName $TaskName2 -Trigger $trigger2 -User $RunAsUser -Action $action -Description $Description2 -Force -AsJob