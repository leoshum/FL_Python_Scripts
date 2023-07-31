param(
    [string]$ExeFilePath,
    [string]$RunAsUser,
    [string]$ExeParams = "urls.json"
    [string]$TaskName1 = "MorningWakeup",
    [string]$TaskName2 = "DayilyBackup",
    [string]$Description1 = "Description",
    [string]$Description2 = "Description",
    [string]$StartTime1 = "05:00",
    [string]$StartTime2 = "14:00",
    [int]$RepeatInterval = 1
)

function New-DailyTrigger {
    param(
        [string]$StartTime,
        [int]$RepeatInterval
    )
    $trigger = New-ScheduledTaskTrigger -Daily -At $StartTime -DaysInterval $RepeatInterval
    return $trigger
}

function ConvertTo-Est {
    param(
        [datetime]$localTime
    )
    $estZone = [System.TimeZoneInfo]::FindSystemTimeZoneById("Eastern Standard Time")
    $estTime = [System.TimeZoneInfo]::ConvertTime($localTime, $estZone)
    return $estTime
}

$trigger1 = New-DailyTrigger -StartTime $StartTime1 -RepeatInterval $RepeatInterval
$trigger2 = New-DailyTrigger -StartTime $StartTime2 -RepeatInterval $RepeatInterval

$trigger1.StartBoundary = ConvertTo-Est $trigger1.StartBoundary
$trigger2.StartBoundary = ConvertTo-Est $trigger2.StartBoundary

$action = New-ScheduledTaskAction -Execute $ExeFilePath -Argument $ExeParams
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $RunAsUser -LogonType Password -RunLevel Highest

Register-ScheduledTask -TaskName $TaskName1 -Description $Description1 -Trigger $trigger1 -User $runAsUser -Action $action -Settings $settings -Principal $principal

Register-ScheduledTask -TaskName $TaskName2 -Description $Description2 -Trigger $trigger2 -User $runAsUser -Action $action -Settings $settings -Principal $principal