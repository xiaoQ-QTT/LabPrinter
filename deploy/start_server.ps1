[CmdletBinding()]
param(
    [string]$ListenHost,
    [int]$Port,
    [string]$PythonExe
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repoRoot

function Resolve-PythonExe {
    param([string]$ExplicitPath)

    if ($ExplicitPath) {
        if (Test-Path $ExplicitPath) {
            return (Resolve-Path $ExplicitPath).Path
        }
        throw "PythonExe not found: $ExplicitPath"
    }

    $candidates = @(
        (Join-Path $repoRoot 'venv\Scripts\python.exe'),
        (Join-Path $repoRoot '.venv\Scripts\python.exe')
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }

    throw 'Python not found. Please run .\\deploy\\install.ps1 to create a venv and install dependencies.'
}

$pythonExeResolved = Resolve-PythonExe -ExplicitPath $PythonExe

if (-not $ListenHost -or -not $Port) {
    try {
        $out = & $pythonExeResolved -c "import config; print(getattr(config,'HOST','0.0.0.0')); print(getattr(config,'PORT',5000))"
        $lines = @($out | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
        if (-not $ListenHost -and $lines.Count -ge 1) { $ListenHost = $lines[0] }
        if (-not $Port -and $lines.Count -ge 2) { $Port = [int]$lines[1] }
    } catch {
        if (-not $ListenHost) { $ListenHost = '0.0.0.0' }
        if (-not $Port) { $Port = 5000 }
    }
}

if (-not $ListenHost) { $ListenHost = '0.0.0.0' }
if (-not $Port) { $Port = 5000 }

$logsDir = Join-Path $repoRoot 'logs'
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$serverLog = Join-Path $logsDir "server_$timestamp.log"
$serverOutLog = Join-Path $logsDir "server_$timestamp.out.log"

Write-Host "=== LabPrinter Server ==="
Write-Host "Repo:   $repoRoot"
Write-Host "Python: $pythonExeResolved"
Write-Host "Listen: $ListenHost`:$Port"
Write-Host "Log:    $serverLog"
Write-Host "Stdout: $serverOutLog"
Write-Host ""

$useWaitress = $true
try {
    & $pythonExeResolved -c "import waitress" | Out-Null
} catch {
    $useWaitress = $false
}

if ($useWaitress) {
    $args = @(
        '-m', 'waitress',
        "--host=$ListenHost",
        "--port=$Port",
        'run:app'
    )
} else {
    Write-Warning "waitress is not installed; falling back to Flask development server (not recommended). Install with: pip install -r requirements.txt"
    $args = @('run.py')
}

$proc = Start-Process `
    -FilePath $pythonExeResolved `
    -ArgumentList $args `
    -WorkingDirectory $repoRoot `
    -RedirectStandardOutput $serverOutLog `
    -RedirectStandardError $serverLog `
    -WindowStyle Hidden `
    -PassThru

Write-Host "PID:    $($proc.Id)"
Write-Host ""
Write-Host "To stop: Stop-Process -Id $($proc.Id)  (or Stop-ScheduledTask -TaskName LabPrinter)" -ForegroundColor Yellow

$proc.WaitForExit()
exit $proc.ExitCode
