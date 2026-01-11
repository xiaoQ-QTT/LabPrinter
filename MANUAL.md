# LabPrinter 完整使用手册

## 第一部分：系统安装

### 系统需求检查清单

在安装前，请确保您拥有：

```powershell
# 1. 检查Windows版本
winver
# 应为 Windows 10 或更新版本

# 2. 检查Python版本
python --version
# 应为 Python 3.10 或更新版本

# 3. 检查Microsoft Word
# 打开Word，验证应用能正常启动

# 4. 检查打印机
Get-Printer | Select-Object Name
# 应至少有一台可用的打印机
```

### 快速安装（3步）

**第1步：以管理员身份打开PowerShell**

按 `Win+X`，选择 "Windows PowerShell (管理员)"

**第2步：导航到项目目录**

```powershell
cd C:\path\to\LabPrinter
```

**第3步：运行安装脚本**

```powershell
.\deploy\install.ps1
```

脚本会自动：
- 创建Python虚拟环境
- 安装所有依赖包
- 配置Windows防火墙规则

等待完成（约2-5分钟）

---

## 第二部分：启动服务

### 方式1：使用启动脚本（推荐）

双击 `deploy\start.bat`

窗口会显示：
```
=== 实验室打印系统启动 ===
 * Running on http://0.0.0.0:5000
 * WARNING: This is a development server...
```

### 方式2：命令行启动

```powershell
# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 启动应用
python run.py
```

---

## 第三部分：访问服务

### 本机访问

打开浏览器输入：
```
http://localhost:5000
```

### 局域网访问

其他电脑访问：
```
http://<打印机所在电脑的IP>:5000
```

**查看本机IP**：
```powershell
ipconfig | findstr IPv4
```

输出示例：
```
IPv4 地址 . . . . . . . . . . . : 192.168.1.100
```

则其他用户访问：`http://192.168.1.100:5000`

---

## 第四部分：使用Web界面

### 打印文件步骤

1. **打开Web界面**
   - 浏览器访问 `http://localhost:5000`

2. **上传文件**
   - 方式A：拖拽文件到上传区
   - 方式B：点击上传区选择文件
   - 支持格式：PDF, Word (.doc, .docx)

3. **配置打印选项**
   - **打印机**：选择目标打印机（空白=默认）
   - **份数**：1-99份
   - **纸张大小**：A4/A3/Letter
   - **双面打印**：单面/双面(长边)/双面(短边)
   - **颜色模式**：彩色/黑白

4. **点击"开始打印"**
   - 显示上传进度
   - 进度条显示处理状态
   - 完成后自动清理临时文件

### 进度显示

```
正在处理文件...        [████░░░░░░░░░] 10%
正在转换Word文档...    [██████░░░░░░░] 30%
正在发送到打印机...    [████████████░░] 70%
清理临时文件...        [█████████████░] 90%
打印完成              [██████████████] 100%
```

---

## 第五部分：故障排查

### 问题1：无法访问Web界面

**症状**：浏览器显示 "无法连接"

**排查步骤**：

```powershell
# 1. 检查Python进程
Get-Process python | Where-Object ProcessName -eq python

# 2. 查看控制台输出
# 应看到: "Running on http://0.0.0.0:5000"

# 3. 尝试本地访问
curl http://localhost:5000

# 4. 检查防火墙规则
netsh advfirewall firewall show rule name="LabPrinter"
# 应显示: Direction: In  Action: Allow
```

**解决方案**：

```powershell
# 重新添加防火墙规则
netsh advfirewall firewall delete rule name="LabPrinter"
netsh advfirewall firewall add rule name="LabPrinter" dir=in action=allow protocol=tcp localport=5000
```

### 问题2：文件上传后没有反应

**症状**：上传完成但任务状态一直是"处理中"

**排查步骤**：

```powershell
# 1. 检查是否安装Word
# 打开 Word 应用程序，确认能正常启动

# 2. 检查临时文件夹
explorer %TEMP%\labprinter\uploads
# 应该能看到上传的文件

# 3. 检查Word进程
Get-Process winword
```

**解决方案**：

```powershell
# 重启应用
# 关闭当前窗口 (Ctrl+C)
# 重新启动 start.bat

# 清理临时文件
Remove-Item -Recurse -Force $env:TEMP\labprinter
mkdir $env:TEMP\labprinter\uploads
```

### 问题3：打印机列表为空

**症状**：Web界面中打印机列表没有任何选项

**排查步骤**：

```powershell
# 检查系统打印机
Get-Printer | Select-Object Name, PrinterStatus

# 添加打印机
# 设置 → 设备 → 打印机和扫描仪 → 添加打印机或扫描仪
```

### 问题4：Word文档转换失败

**症状**：上传Word文件后显示 "打印失败: Word应用程序未找到"

**排查步骤**：

```powershell
# 检查Word安装
Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Office\16.0\Word\InstallRoot"

# 手动启动Word进程
$word = New-Object -ComObject Word.Application
$word.Quit()
```

**解决方案**：

- 重新安装或修复 Microsoft Office
- 确保 Office 已激活

### 问题5：打印机显示繁忙

**症状**：虽然成功提交打印任务，但打印机一直不动

**排查步骤**：

```powershell
# 1. 检查打印队列
Get-PrintJob -PrinterName "HP LaserJet" | Select-Object ID, DocumentName, JobStatus

# 2. 清空打印队列
Get-PrintJob -PrinterName "HP LaserJet" | Stop-PrintJob

# 3. 重启打印机
Restart-Printer -Name "HP LaserJet"
```

---

## 第六部分：性能优化

### 并发任务调整

编辑 `config.py`：

```python
MAX_CONCURRENT_JOBS = 5  # 从3改为5
```

**建议值**：
- 低端电脑 (2核4GB): 2
- 中端电脑 (4核8GB): 3
- 高端电脑 (8核16GB): 5

### 端口修改

编辑 `config.py`：

```python
PORT = 8080  # 从5000改为8080
```

重启应用后访问 `http://localhost:8080`

### 默认打印机设置

编辑 `config.py`：

```python
DEFAULT_PRINTER = "HP LaserJet Pro M404n"  # 设置为打印机名称
```

查看打印机名称：
```powershell
Get-Printer | Select-Object Name
```

---

## 第七部分：高级功能

### 通过API集成到其他系统

**Python 脚本示例**：

```python
import requests
import time

BASE_URL = "http://localhost:5000"

# 上传文件
with open('report.pdf', 'rb') as f:
    files = {'file': f}
    data = {'copies': 2}
    response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
    task_id = response.json()['task_id']

# 查询状态
while True:
    response = requests.get(f"{BASE_URL}/status/{task_id}")
    status = response.json()
    print(f"状态: {status['state']}")
    
    if status['state'] == 'SUCCESS':
        break
    time.sleep(1)
```

### 开机自启动

**使用任务计划程序**：

1. 按 `Win+R`，输入 `taskschd.msc`
2. 右键"任务计划程序库" → 创建基本任务
3. 设置：
   - 名称：LabPrinter
   - 触发器：登录时
   - 操作：启动程序
   - 程序：`C:\workspace\LabPrinter\deploy\start.bat`
   - 起始于：`C:\workspace\LabPrinter`

---

## 第八部分：日常维护

### 检查系统状态

```powershell
# 查看Python进程
Get-Process python

# 检查网络连接
Test-NetConnection localhost -Port 5000

# 查看防火墙状态
netsh advfirewall firewall show rule name="LabPrinter"
```

### 清理临时文件

```powershell
# 删除超过1小时的上传文件
$cutoff = (Get-Date).AddHours(-1)
Get-ChildItem $env:TEMP\labprinter\uploads | 
    Where-Object {$_.CreationTime -lt $cutoff} | 
    Remove-Item
```

### 更新依赖包

```powershell
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install --upgrade -r requirements.txt
```

---

## 常见问题Q&A

**Q: 支持多少用户同时使用?**
A: 理论无限制，但最多3个任务并发处理。其他请求会排队。

**Q: 单个文件最大多少MB?**
A: 配置中限制为50MB，可修改 `config.py` 的 `MAX_CONTENT_LENGTH`。

**Q: 能否在Mac/Linux上运行?**
A: 不能，本版本专为Windows优化，使用了Windows API。

**Q: 如何关闭服务?**
A: 在命令窗口按 `Ctrl+C`，或直接关闭窗口。

**Q: 任务数据会保存吗?**
A: 不会，任务数据存储在内存中，重启应用后丢失。

**Q: 如何重置到默认配置?**
A: 编辑 `config.py`，恢复默认值，重启应用。

---

## 支持和反馈

如遇到问题，请检查：
1. 本手册的故障排查部分
2. 应用控制台输出的错误信息
3. Windows事件查看器（eventvwr.msc）

---

**版本**: 1.0
**最后更新**: 2024
**维护**: 实验室IT团队

