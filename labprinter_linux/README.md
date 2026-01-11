# LabPrinter Linux (Ubuntu 22.04)

该目录是 **Linux 版实现**，与当前 Windows 代码完全隔离；在 Ubuntu 22.04 上通过：

- **LibreOffice headless**：将 `.doc/.docx` 转成 PDF
- **CUPS (lp/lpstat)**：提交打印任务、列出打印机
- **pypdf**：用于校验 PDF 总页数（页面范围越界直接报错，行为对齐 Windows）

## 依赖 (Ubuntu 22.04)

```bash
sudo apt update
sudo apt install -y python3 python3-venv cups cups-client cups-filters libreoffice-writer ghostscript poppler-utils fontconfig \
  fonts-noto-cjk fonts-noto-cjk-extra \
  fonts-wqy-zenhei fonts-wqy-microhei \
  fonts-arphic-ukai fonts-arphic-uming \
  fonts-droid-fallback fonts-liberation \
  fonts-crosextra-carlito fonts-crosextra-caladea
```

说明：
- `cups`/`cups-client` 提供 `lp`/`lpstat`
- `libreoffice-writer` 提供 `soffice` 用于转换
- `cups-filters`/`poppler-utils` 用于 PDF/渲染链路（缺失时可能出现“缺字/乱码/过滤器失败”）
- 字体包用于中文/兼容性（可按需替换；遇到“部分文字无法显示/打印失败”优先补字体）

## 一键安装 (推荐)

```bash
cd labprinter_linux
chmod +x deploy/*.sh
./deploy/install_ubuntu22.sh
```

## 开机自启动（systemd）

安装并设置开机启动：

```bash
cd labprinter_linux
chmod +x deploy/*.sh
./deploy/install_systemd_service.sh
```

查看状态与日志：

```bash
sudo systemctl status labprinter.service --no-pager
sudo journalctl -u labprinter.service -f
```

停止并取消开机启动：

```bash
sudo systemctl disable --now labprinter.service
```

卸载服务文件（可选）：

```bash
./deploy/uninstall_systemd_service.sh
```

## 字体（缺字/乱码）排查

Linux 上打印 Word 最常见的问题是：文档里指定了 **Windows 专有字体名**（如 `SimSun/宋体`、`SimHei/黑体`、`Microsoft YaHei/微软雅黑`、`Calibri` 等），
LibreOffice headless 转 PDF 或 CUPS 渲染时找不到同名字体，导致 **缺字/乱码/打印失败**。

1) 安装字体包 + 写入 fontconfig 别名映射（本项目已提供脚本）：

```bash
cd labprinter_linux
./deploy/install_fonts.sh
```

2) 如果文档必须使用真实 Windows 字体（更接近 Windows 排版），把字体文件放到 `labprinter_linux/deploy/fonts/`（支持 `.ttf/.otf/.ttc`），再运行上面的脚本。

可选：
- 安装 Microsoft Core Fonts（需要联网下载且包含许可/EULA）：`INSTALL_MS_FONTS=1 ./deploy/install_fonts.sh`

3) 验证字体匹配（看 `fc-match` 结果是否能匹配到可用字体）：

```bash
fc-match "SimSun"
fc-match "宋体"
fc-match "Microsoft YaHei"
fc-match "Calibri"
```

4) 判断问题发生在哪一步：
- **转换阶段**：手动把 Word 转成 PDF，打开 PDF 看是否缺字：

```bash
python -c 'from app.converter import convert_to_pdf; print(convert_to_pdf("你的文件.docx"))'
```

- **打印阶段**：如果 PDF 本身正常，但 CUPS 打印缺字/失败，建议开启 PDF 预处理兜底：
  - `PDF_PREPROCESS=gs-pdfwrite`（尽量嵌入字体，速度/体积较均衡）
  - `PDF_PREPROCESS=gs-rasterize`（最兼容，但更慢/更大）

## 安装与启动

```bash
cd labprinter_linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

浏览器访问：`http://localhost:5000`

## 环境变量 (可选)

- `DEFAULT_PRINTER`：默认打印机名（不设则使用 CUPS 默认）
- `ALLOWED_PRINTERS`：允许的打印机白名单（逗号分隔），不设则允许全部
- `SOFFICE_PATH`：`soffice` 路径（不设则自动 `which`）
- `CONVERT_TIMEOUT`：转换超时秒数（默认 120）
- `LP_TIMEOUT`：提交打印超时秒数（默认 60）
- `PDF_PREPROCESS`：PDF 预处理模式（`none`/`gs-pdfwrite`/`gs-rasterize`，默认 `none`）
- `GS_COMMAND`：Ghostscript 命令（默认 `gs`）
- `PDF_PREPROCESS_TIMEOUT`：PDF 预处理超时秒数（默认 180）
- `PDF_RASTER_DPI`：`gs-rasterize` 分辨率（默认 200）
- `MAX_CONCURRENT_JOBS`：后台并发任务数（默认 3）
