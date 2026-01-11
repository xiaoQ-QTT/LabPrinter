"""全局配置 - Linux (Ubuntu 22.04 / CUPS)"""
import os
import tempfile

# Flask配置
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', '5000'))
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY', 'lab-printer-secret-key-change-in-production')

# 文件上传配置
UPLOAD_FOLDER = os.environ.get(
    'UPLOAD_FOLDER',
    os.path.join(tempfile.gettempdir(), 'labprinter', 'uploads')
)
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

# 打印配置
DEFAULT_PRINTER = os.environ.get('DEFAULT_PRINTER', None)  # None 使用 CUPS 默认
ALLOWED_PRINTERS = [p.strip() for p in os.environ.get('ALLOWED_PRINTERS', '').split(',') if p.strip()] or None

# 安全/稳定性配置
MAX_QUEUE_SIZE = int(os.environ.get('MAX_QUEUE_SIZE', '50'))  # 0=不限制
TASK_RETENTION_SECONDS = int(os.environ.get('TASK_RETENTION_SECONDS', '3600'))
TASK_CLEANUP_INTERVAL_SECONDS = int(os.environ.get('TASK_CLEANUP_INTERVAL_SECONDS', '300'))

# CUPS 命令
LP_COMMAND = os.environ.get('LP_COMMAND', 'lp')
LPSTAT_COMMAND = os.environ.get('LPSTAT_COMMAND', 'lpstat')
LP_TIMEOUT = int(os.environ.get('LP_TIMEOUT', '60'))

# LibreOffice 转换
SOFFICE_PATH = os.environ.get('SOFFICE_PATH', '')
CONVERT_TIMEOUT = int(os.environ.get('CONVERT_TIMEOUT', '120'))

# PDF 预处理（用于兼容复杂字体/文档，必要时可开启）
# - none: 不处理（默认）
# - gs-pdfwrite: 使用 Ghostscript 重写 PDF（尽量嵌入字体，保持矢量）
# - gs-rasterize: 使用 Ghostscript 将每页栅格化后再生成 PDF（最兼容，但更慢/更大）
PDF_PREPROCESS = os.environ.get('PDF_PREPROCESS', 'Ghostscript').strip().lower()
GS_COMMAND = os.environ.get('GS_COMMAND', 'gs')
PDF_PREPROCESS_TIMEOUT = int(os.environ.get('PDF_PREPROCESS_TIMEOUT', '180'))
PDF_RASTER_DPI = int(os.environ.get('PDF_RASTER_DPI', '200'))

# 任务配置
MAX_CONCURRENT_JOBS = int(os.environ.get('MAX_CONCURRENT_JOBS', '3'))
