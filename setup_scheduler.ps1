# Get the current directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$botPath = Join-Path $scriptPath "run_bot_daily.bat"

# Create the scheduled task
$action = New-ScheduledTaskAction -Execute $botPath
$trigger = New-ScheduledTaskTrigger -Daily -At 9AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries

# Create the task
Register-ScheduledTask -TaskName "RedditVideoMakerBot" -Action $action -Trigger $trigger -Settings $settings -Force

Write-Host "Task has been scheduled to run daily at 9:00 AM"
Write-Host "You can modify the schedule in Windows Task Scheduler"
Write-Host "Press any key to open Task Scheduler..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Start-Process "taskschd.msc" 