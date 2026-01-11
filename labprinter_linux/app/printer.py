"""打印机操作封装 - Linux版本 (CUPS lp/lpstat)"""
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from typing import Dict, List, Optional

try:
    from labprinter_linux import config
except ImportError:
    import config

_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 5.0
_DEFAULT_PRINTER_CACHE = None  # (ts_monotonic, value)
_PRINTER_NAMES_CACHE = None  # (ts_monotonic, frozenset[str])
_JOBS_COUNT_CACHE = None  # (ts_monotonic, dict[str, int])


def _run_cmd(cmd: List[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _find_gs() -> Optional[str]:
    gs = getattr(config, 'GS_COMMAND', 'gs') or 'gs'
    if os.path.isfile(gs):
        return gs
    return shutil.which(gs)


def _preprocess_pdf_for_print(pdf_path: str) -> str:
    mode = (getattr(config, 'PDF_PREPROCESS', 'none') or 'none').strip().lower()
    if mode in {'', '0', 'false', 'none'}:
        return pdf_path

    gs = _find_gs()
    if not gs:
        raise RuntimeError('未找到 Ghostscript(gs)，请安装 ghostscript 或设置 GS_COMMAND')

    out_dir = os.path.join(tempfile.gettempdir(), 'labprinter', 'preprocessed')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'{uuid.uuid4().hex}.pdf')

    if mode == 'gs-pdfwrite':
        cmd = [
            gs,
            '-dSAFER',
            '-dBATCH',
            '-dNOPAUSE',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/prepress',
            '-dEmbedAllFonts=true',
            '-dSubsetFonts=true',
            '-dAutoRotatePages=/None',
            f'-sOutputFile={out_path}',
            pdf_path,
        ]
    elif mode == 'gs-rasterize':
        dpi = int(getattr(config, 'PDF_RASTER_DPI', 200) or 200)
        if dpi < 72 or dpi > 600:
            raise RuntimeError('PDF_RASTER_DPI 超出范围(72-600)')
        cmd = [
            gs,
            '-dSAFER',
            '-dBATCH',
            '-dNOPAUSE',
            '-sDEVICE=pdfimage24',
            f'-r{dpi}',
            f'-sOutputFile={out_path}',
            pdf_path,
        ]
    else:
        return pdf_path

    result = _run_cmd(cmd, timeout=int(getattr(config, 'PDF_PREPROCESS_TIMEOUT', 180) or 180))
    if result.returncode != 0 or not os.path.exists(out_path):
        msg = (result.stderr or result.stdout or '').strip() or f'PDF 预处理失败，返回码 {result.returncode}'
        try:
            os.remove(out_path)
        except OSError:
            pass
        raise RuntimeError(msg)

    return out_path


def _parse_default_printer(lpstat_output: str) -> Optional[str]:
    m = re.search(r'system default destination:\s*(.+)\s*$', (lpstat_output or '').strip())
    return m.group(1).strip() if m else None


def get_default_printer() -> Optional[str]:
    global _DEFAULT_PRINTER_CACHE
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _DEFAULT_PRINTER_CACHE
        if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
            return cached[1]

    value: Optional[str] = None
    try:
        result = _run_cmd([config.LPSTAT_COMMAND, '-d'], timeout=10)
        if result.returncode != 0:
            value = None
        else:
            value = _parse_default_printer(result.stdout)
    except Exception:
        value = None

    with _CACHE_LOCK:
        _DEFAULT_PRINTER_CACHE = (now, value)
    return value


def _get_jobs_count_map() -> Dict[str, int]:
    global _JOBS_COUNT_CACHE
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _JOBS_COUNT_CACHE
        if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
            return dict(cached[1])

    counts: Dict[str, int] = {}
    try:
        # 一次性取回所有队列作业，避免每台打印机都 fork/subprocess
        result = _run_cmd([config.LPSTAT_COMMAND, '-o'], timeout=10)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                first = line.split(None, 1)[0]  # e.g. "HP-123"
                if '-' not in first:
                    continue
                dest, jobid = first.rsplit('-', 1)
                if not jobid.isdigit():
                    continue
                counts[dest] = counts.get(dest, 0) + 1
    except Exception:
        counts = {}

    with _CACHE_LOCK:
        _JOBS_COUNT_CACHE = (now, dict(counts))
    return counts


def get_printers() -> List[Dict]:
    default_printer = config.DEFAULT_PRINTER or get_default_printer()
    try:
        result = _run_cmd([config.LPSTAT_COMMAND, '-p'], timeout=10)
        if result.returncode != 0:
            return []

        jobs_map = _get_jobs_count_map()
        printers: List[Dict] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line.startswith('printer '):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            name = parts[1]
            if config.ALLOWED_PRINTERS is not None and name not in config.ALLOWED_PRINTERS:
                continue
            status = 'ready'
            status_text = '就绪'
            if 'disabled' in line:
                status = 'offline'
                status_text = '已禁用/离线'
            elif 'printing' in line:
                status = 'busy'
                status_text = '打印中'

            printers.append({
                'name': name,
                'description': '',
                'is_default': (name == default_printer),
                'status': status,
                'status_text': status_text,
                'jobs': jobs_map.get(name, 0)
            })

        return printers
    except Exception:
        return []


def get_printer_names() -> set[str]:
    global _PRINTER_NAMES_CACHE
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _PRINTER_NAMES_CACHE
        if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
            return set(cached[1])

    names: set[str] = set()
    try:
        result = _run_cmd([config.LPSTAT_COMMAND, '-p'], timeout=10)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line.startswith('printer '):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    names.add(parts[1])
    except Exception:
        names = set()

    if config.ALLOWED_PRINTERS is not None:
        names = {n for n in names if n in config.ALLOWED_PRINTERS}

    with _CACHE_LOCK:
        _PRINTER_NAMES_CACHE = (now, frozenset(names))
    return names


def validate_printer_name(printer_name: str) -> bool:
    if not printer_name:
        return False
    printer_name = str(printer_name).strip()
    if not printer_name:
        return False
    if printer_name.startswith('-'):
        return False

    if config.ALLOWED_PRINTERS is not None:
        return printer_name in config.ALLOWED_PRINTERS

    names = get_printer_names()
    if names:
        return printer_name in names

    return True


def _normalize_page_range(page_range: str) -> str:
    page_range = (page_range or '').strip()
    if not page_range:
        return ''
    page_range = page_range.replace(' ', '')
    if len(page_range) > 200:
        raise RuntimeError('页面范围过长')
    if not re.fullmatch(r'\d+(-\d+)?(,\d+(-\d+)?)*', page_range):
        raise RuntimeError('页面范围格式错误')

    for part in page_range.split(','):
        if not part:
            continue
        if '-' in part:
            start_s, end_s = part.split('-', 1)
            start, end = int(start_s), int(end_s)
            if start < 1 or end < 1:
                raise RuntimeError('页码必须大于等于1')
            if start > end:
                raise RuntimeError('起始页不能大于结束页')
        else:
            page = int(part)
            if page < 1:
                raise RuntimeError('页码必须大于等于1')
    return page_range


def _get_pdf_total_pages(pdf_path: str) -> int:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as e:
        raise RuntimeError('缺少依赖 pypdf，请在 Linux 端安装 requirements.txt') from e

    try:
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception as e:
        raise RuntimeError(f'无法读取PDF页数: {e}')


def _parse_page_range_to_pages(page_range: str, total_pages: int) -> List[int]:
    if total_pages < 1:
        raise RuntimeError('PDF页数无效')
    page_range = _normalize_page_range(page_range)
    if not page_range:
        return list(range(1, total_pages + 1))

    pages = set()
    parts = page_range.split(',')
    for part in parts:
        if not part:
            continue
        if '-' in part:
            start_s, end_s = part.split('-', 1)
            start, end = int(start_s), int(end_s)
            if start > end:
                raise RuntimeError('起始页不能大于结束页')
            if start < 1 or end > total_pages:
                raise RuntimeError(f'页码超出范围(1-{total_pages}): {part}')
            pages.update(range(start, end + 1))
        else:
            page = int(part)
            if page < 1 or page > total_pages:
                raise RuntimeError(f'页码超出范围(1-{total_pages}): {page}')
            pages.add(page)

    return sorted(pages)


def _pages_to_range_string(pages: List[int]) -> str:
    pages = sorted(set(pages))
    if not pages:
        return ''

    ranges = []
    start = prev = pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
            continue
        ranges.append(f'{start}-{prev}' if start != prev else f'{start}')
        start = prev = p
    ranges.append(f'{start}-{prev}' if start != prev else f'{start}')
    return ','.join(ranges)


def build_lp_command(filepath: str, options: dict, *, printer_name: Optional[str]) -> List[str]:
    cmd: List[str] = [config.LP_COMMAND]

    if printer_name:
        if printer_name.startswith('-'):
            raise RuntimeError('打印机名称无效')
        cmd.extend(['-d', printer_name])

    copies = int(options.get('copies', 1))
    if copies < 1 or copies > 99:
        raise RuntimeError('份数超出范围(1-99)')
    if copies > 1:
        cmd.extend(['-n', str(copies)])

    page_range = _normalize_page_range(options.get('page_range', ''))
    if page_range:
        cmd.extend(['-o', f'page-ranges={page_range}'])

    duplex = (options.get('duplex') or 'one-sided').strip()
    sides_map = {
        'one-sided': 'one-sided',
        'two-sided-long-edge': 'two-sided-long-edge',
        'two-sided-short-edge': 'two-sided-short-edge',
    }
    if duplex in sides_map:
        cmd.extend(['-o', f'sides={sides_map[duplex]}'])

    paper_size = (options.get('paper_size') or 'A4').strip() or 'A4'
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,32}', paper_size):
        raise RuntimeError('纸张格式错误')
    cmd.extend(['-o', f'media={paper_size}'])

    color = (options.get('color') or 'color').strip()
    if color == 'grayscale':
        cmd.extend(['-o', 'print-color-mode=monochrome'])
    else:
        cmd.extend(['-o', 'print-color-mode=color'])

    cmd.append(filepath)
    return cmd


def _parse_lp_job_id(output: str) -> Optional[str]:
    m = re.search(r'request id is\\s+(\\S+)\\s', output or '')
    return m.group(1) if m else None


def print_file(filepath: str, options: dict) -> str:
    abs_path = os.path.abspath(filepath)
    if not os.path.exists(abs_path):
        raise RuntimeError(f'文件不存在: {abs_path}')

    printer_name = options.get('printer') or config.DEFAULT_PRINTER or get_default_printer()
    if not printer_name:
        names = get_printer_names()
        if len(names) == 1:
            printer_name = next(iter(names))
        else:
            raise RuntimeError('未设置默认打印机，请在页面选择打印机或在CUPS中设置默认打印机')
    if config.ALLOWED_PRINTERS is not None:
        if not printer_name or printer_name not in config.ALLOWED_PRINTERS:
            raise RuntimeError('打印机不在允许列表中')

    processed_pdf: Optional[str] = None
    print_path = abs_path
    try:
        # 预处理 PDF（可选）：用于处理复杂字体/排版导致的打印失败或缺字问题
        if os.path.splitext(abs_path)[1].lower() == '.pdf':
            processed = _preprocess_pdf_for_print(abs_path)
            if processed != abs_path:
                processed_pdf = processed
                print_path = processed_pdf

        # 校验/规范化页面范围（对齐 Windows 的行为：非法或越界会直接报错）
        page_range = (options.get('page_range') or '').strip()
        if page_range:
            if os.path.splitext(print_path)[1].lower() != '.pdf':
                # 非 PDF 无法可靠获取总页数，这里仅做格式校验
                normalized = _normalize_page_range(page_range)
            else:
                total_pages = _get_pdf_total_pages(print_path)
                pages = _parse_page_range_to_pages(page_range, total_pages)
                normalized = _pages_to_range_string(pages)
            options = dict(options)
            options['page_range'] = normalized

        cmd = build_lp_command(print_path, options, printer_name=printer_name)
        result = _run_cmd(cmd, timeout=config.LP_TIMEOUT)
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or '').strip() or f'lp 失败，返回码 {result.returncode}')

        job_id = _parse_lp_job_id(result.stdout)
        return job_id or f"lp-job-{os.path.basename(print_path)}"
    finally:
        if processed_pdf and os.path.exists(processed_pdf):
            try:
                os.remove(processed_pdf)
            except OSError:
                pass
