"""打印日志模块 - Linux版本"""
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

print_logger = logging.getLogger('print_log_linux')
print_logger.setLevel(logging.INFO)
print_logger.propagate = False

log_file = os.path.join(LOG_DIR, 'print.log')
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,
    backupCount=30,
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
print_logger.addHandler(file_handler)


def log_print_request(task_id: str, client_ip: str, filename: str, options: dict):
    page_range = (options.get('page_range') or '').strip() or '全部'
    print_logger.info(
        f"REQUEST | 任务: {task_id} | IP: {client_ip} | 文件: {filename} | "
        f"打印机: {options.get('printer') or '默认'} | "
        f"份数: {options.get('copies', 1)} | "
        f"纸张: {options.get('paper_size', 'A4')} | "
        f"页面: {page_range} | "
        f"双面: {options.get('duplex', 'one-sided')} | "
        f"颜色: {options.get('color', 'color')}"
    )


def log_print_result(task_id: str, filename: str, success: bool, message: str = '', options: dict = None):
    status = "SUCCESS" if success else "FAILED"
    if options:
        page_range = (options.get('page_range') or '').strip() or '全部'
        print_logger.info(
            f"RESULT | 任务: {task_id} | 文件: {filename} | 状态: {status} | "
            f"打印机: {options.get('printer') or '默认'} | "
            f"份数: {options.get('copies', 1)} | "
            f"纸张: {options.get('paper_size', 'A4')} | "
            f"页面: {page_range} | "
            f"双面: {options.get('duplex', 'one-sided')} | "
            f"颜色: {options.get('color', 'color')} | "
            f"{message}"
        )
    else:
        print_logger.info(f"RESULT | 任务: {task_id} | 文件: {filename} | 状态: {status} | {message}")

