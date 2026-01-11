"""打印工作线程"""
import os
import threading
import traceback
from app.task_queue import TaskQueue, TaskState
from app.converter import convert_to_pdf
from app.printer import print_file
from app.logger import log_print_result


class PrintWorker(threading.Thread):
    """后台打印工作线程"""

    def __init__(self, queue: TaskQueue, name: str = "PrintWorker"):
        super().__init__(name=name)
        self.queue = queue
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            task_id = self.queue.get_next(timeout=1.0)
            if task_id is None:
                continue

            task = self.queue.get_task(task_id)
            if task is None:
                continue

            self._process_task(task_id, task.filepath, task.options, task.original_filename)

    def _process_task(self, task_id: str, filepath: str, options: dict, original_filename: str):
        """处理单个打印任务"""
        temp_pdf = None

        try:
            # 更新状态: 开始处理
            self.queue.update_task(
                task_id,
                state=TaskState.PROGRESS,
                message="正在处理文件...",
                progress=10
            )

            ext = os.path.splitext(filepath)[1].lower()
            print_path = filepath

            # Word文档需要先转换为PDF
            if ext in ('.doc', '.docx'):
                self.queue.update_task(
                    task_id,
                    message="正在转换Word文档...",
                    progress=30
                )
                temp_pdf = convert_to_pdf(filepath)
                print_path = temp_pdf

            # 发送到打印机 (页面范围处理已内置在 print_file 中)
            self.queue.update_task(
                task_id,
                message="正在发送到打印机...",
                progress=70
            )
            job_id = print_file(print_path, options)

            # 清理临时文件
            self.queue.update_task(
                task_id,
                message="清理临时文件...",
                progress=90
            )
            self._cleanup_files(filepath, temp_pdf)

            # 完成
            self.queue.update_task(
                task_id,
                state=TaskState.SUCCESS,
                message="打印完成",
                progress=100,
                result={'job_id': job_id, 'status': 'completed'}
            )
            log_print_result(task_id, original_filename, True, f"任务ID: {job_id}", options=options)

        except Exception as e:
            self._cleanup_files(filepath, temp_pdf)
            error_msg = str(e)
            self.queue.update_task(
                task_id,
                state=TaskState.FAILURE,
                message=f"打印失败: {error_msg}",
                error=traceback.format_exc()
            )
            log_print_result(task_id, original_filename, False, error_msg, options=options)

    def _cleanup_files(self, *files):
        """清理文件"""
        for f in files:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass
