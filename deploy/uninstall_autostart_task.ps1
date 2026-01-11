[CmdletBinding()]
param(
    [string]$TaskName = 'LabPrinter'
)

$ErrorActionPreference = 'Stop'

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "计划任务不存在: $TaskName" -ForegroundColor Yellow
    exit 0
}

try {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Out-Null
} catch {
    # ignore
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
Write-Host "已删除计划任务: $TaskName" -ForegroundColor Green

