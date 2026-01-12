[CmdletBinding()]
param(
    [string]$TaskName = 'LabPrinter',
    [string]$UserName = $env:USERNAME
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$runner = Join-Path $PSScriptRoot 'run_waitress.py'
$pythonw = Join-Path $repoRoot 'venv\Scripts\pythonw.exe'

if (-not (Test-Path $runner)) {
    throw "未找到启动脚本: $runner"
}
if (-not (Test-Path $pythonw)) {
    throw "未找到 venv Python: $pythonw （请先运行 .\\deploy\\install.ps1）"
}

$action = New-ScheduledTaskAction `
    -Execute $pythonw `
    -Argument "`"$runner`"" `
    -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $UserName
# 不同 Windows/PowerShell 版本支持的 LogonType 枚举不同：
# - 有的版本是 InteractiveToken
# - 有的版本只有 Interactive/InteractiveOrPassword
$principal = $null
try {
    $principal = New-ScheduledTaskPrincipal -UserId $UserName -LogonType Interactive -RunLevel LeastPrivilege
} catch {
    try {
        $principal = New-ScheduledTaskPrincipal -UserId $UserName -RunLevel LeastPrivilege
    } catch {
        $principal = New-ScheduledTaskPrincipal -UserId $UserName
    }
}
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -Hidden `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$task = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'LabPrinter Web 服务（登录后自启动）。注意：Word COM/打印通常需要用户会话。'

try {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        try {
            Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Out-Null
        } catch {
            # ignore
        }
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
    }
} catch {
    # ignore
}

Register-ScheduledTask -TaskName $TaskName -InputObject $task | Out-Null

Write-Host "已创建计划任务: $TaskName" -ForegroundColor Green
Write-Host "触发器: 用户 $UserName 登录后自动启动" -ForegroundColor Green
Write-Host ""
Write-Host "现在启动一次（可选）：" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName `"$TaskName`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "查看状态：" -ForegroundColor Yellow
Write-Host "  Get-ScheduledTask -TaskName `"$TaskName`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "卸载：" -ForegroundColor Yellow
Write-Host "  .\\deploy\\uninstall_autostart_task.ps1 -TaskName `"$TaskName`"" -ForegroundColor Yellow
