"""Web路由"""
import os
import uuid
import re
from flask import Blueprint, request, jsonify, render_template, Response
from werkzeug.utils import secure_filename
import config
from app.task_queue import task_queue, TaskState
from app.logger import log_print_request

bp = Blueprint('main', __name__)


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


@bp.route('/')
def index():
    """主页"""
    return render_template('index.html')


@bp.route('/favicon.ico')
def favicon():
    # 避免浏览器自动请求 /favicon.ico 导致日志出现 404
    return Response(status=204)


@bp.route('/upload', methods=['POST'])
def upload():
    """上传文件并创建打印任务"""
    if 'file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'不支持的文件类型，仅支持: {", ".join(config.ALLOWED_EXTENSIONS)}'}), 400

    # 获取打印选项
    try:
        copies = int(request.form.get('copies', 1))
    except (TypeError, ValueError):
        return jsonify({'error': '份数格式错误'}), 400
    if copies < 1 or copies > 99:
        return jsonify({'error': '份数超出范围(1-99)'}), 400

    duplex = (request.form.get('duplex') or 'one-sided').strip() or 'one-sided'
    if duplex not in {'one-sided', 'two-sided-long-edge', 'two-sided-short-edge'}:
        duplex = 'one-sided'

    color = (request.form.get('color') or 'color').strip() or 'color'
    if color not in {'color', 'grayscale'}:
        color = 'color'

    paper_size = (request.form.get('paper_size') or 'A4').strip() or 'A4'
    if paper_size not in {'A4', 'A3', 'Letter'}:
        paper_size = 'A4'

    # 打印机：仅允许系统已安装的打印机名称，避免接受任意字符串触发未知远程连接
    raw_printer = (request.form.get('printer') or '').strip()
    if raw_printer:
        from app.printer import validate_printer_name
        if not validate_printer_name(raw_printer):
            return jsonify({'error': '无效的打印机'}), 400
    printer = raw_printer or config.DEFAULT_PRINTER

    page_range = ''
    if request.form.get('page_range_type') == 'custom':
        page_range = (request.form.get('page_range') or '').strip()
        if page_range:
            if not re.fullmatch(r'\d+(-\d+)?(,\d+(-\d+)?)*', page_range.replace(' ', '')):
                return jsonify({'error': '页面范围格式错误'}), 400

    options = {
        'copies': copies,
        'duplex': duplex,
        'color': color,
        'paper_size': paper_size,
        'printer': printer,
        'page_range': page_range,
    }

    # 生成唯一文件名并落盘（放到最后，避免参数校验失败时留下垃圾文件）
    name_root, ext = os.path.splitext(file.filename)
    ext = ext.lower()
    safe_root = secure_filename(name_root) or 'file'
    filename = f"{safe_root}{ext}"
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(config.UPLOAD_FOLDER, unique_name)
    file.save(filepath)

    # 创建打印任务
    try:
        task_id = task_queue.submit(filepath, options, filename)
    except RuntimeError as e:
        try:
            os.remove(filepath)
        except OSError:
            pass
        return jsonify({'error': str(e)}), 429

    # 记录日志
    client_ip = request.remote_addr
    log_print_request(task_id, client_ip, filename, options)

    return jsonify({
        'task_id': task_id,
        'filename': filename,
        'message': '打印任务已提交'
    })


@bp.route('/status/<task_id>')
def task_status(task_id: str):
    """查询任务状态"""
    task = task_queue.get_task(task_id)

    if task is None:
        return jsonify({'error': '任务不存在'}), 404

    response = {
        'task_id': task_id,
        'state': task.state.value,
        'message': task.message,
        'progress': task.progress
    }

    if task.state == TaskState.SUCCESS:
        response['result'] = task.result
    elif task.state == TaskState.FAILURE and config.DEBUG:
        response['error'] = task.error

    return jsonify(response)


@bp.route('/printers')
def list_printers():
    """获取可用打印机列表"""
    from app.printer import get_printers
    printers = get_printers()
    return jsonify({'printers': printers})
