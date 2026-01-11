# LabPrinter Windows 部署脚本
# 以管理员身份运行 PowerShell

Write-Host "=== 实验室打印系统 Windows 部署 ===" -ForegroundColor Cyan

# 检查Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "错误: 未找到Python，请先安装Python 3.10+" -ForegroundColor Red
    exit 1
}

# 检查Python版本
$version = python --version 2>&1
Write-Host "检测到: $version" -ForegroundColor Green

# 创建虚拟环境
Write-Host "`n[1/3] 创建Python虚拟环境..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
}

# 激活虚拟环境并安装依赖
Write-Host "[2/3] 安装依赖包..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# 配置防火墙
Write-Host "[3/3] 配置防火墙规则..." -ForegroundColor Yellow
$rule = Get-NetFirewallRule -DisplayName "LabPrinter" -ErrorAction SilentlyContinue
if (-not $rule) {
    New-NetFirewallRule -DisplayName "LabPrinter" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
    Write-Host "防火墙规则已添加" -ForegroundColor Green
} else {
    Write-Host "防火墙规则已存在" -ForegroundColor Green
}

# 获取本机IP
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.*" } | Select-Object -First 1).IPAddress

Write-Host "`n=== 部署完成 ===" -ForegroundColor Cyan
Write-Host "启动命令: python run.py" -ForegroundColor White
Write-Host "本机访问: http://localhost:5000" -ForegroundColor White
Write-Host "局域网访问: http://${ip}:5000" -ForegroundColor White

