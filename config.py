"""全局配置 - Windows版本"""
import os
import tempfile

# Flask配置
HOST = '0.0.0.0'
PORT = 5000
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY', 'lab-printer-secret-key-change-in-production')

# 文件上传配置
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'labprinter', 'uploads')
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

# 打印配置
DEFAULT_PRINTER = os.environ.get('DEFAULT_PRINTER', None)  # None使用系统默认

# 安全/稳定性配置
# - MAX_QUEUE_SIZE: 限制排队中的任务数量，避免被刷任务导致磁盘/内存耗尽（0=不限制）
MAX_QUEUE_SIZE = int(os.environ.get('MAX_QUEUE_SIZE', '50'))
# - TASK_RETENTION_SECONDS: 成功/失败任务的保留时长（用于状态查询与排障）
TASK_RETENTION_SECONDS = int(os.environ.get('TASK_RETENTION_SECONDS', '3600'))
# - TASK_CLEANUP_INTERVAL_SECONDS: 后台清理线程间隔
TASK_CLEANUP_INTERVAL_SECONDS = int(os.environ.get('TASK_CLEANUP_INTERVAL_SECONDS', '300'))

# SumatraPDF 配置 - 主打印方案
SUMATRA_PDF_PATH = os.environ.get('SUMATRA_PDF_PATH', r'C:\Program Files\SumatraPDF\SumatraPDF.exe')
# SumatraPDF 打印命令超时（秒）。大文件/网络打印机在启动时可能较慢。
SUMATRA_TIMEOUT = int(os.environ.get('SUMATRA_TIMEOUT', '120'))

# 任务配置
MAX_CONCURRENT_JOBS = 3  # 最大并发打印任务数
