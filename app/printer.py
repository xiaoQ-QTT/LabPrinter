"""打印机操作封装 - Windows版本
主方案: SumatraPDF (命令行静默打印)
备用方案: PyMuPDF + GDI 原生打印
"""
import win32print
import win32api
import win32con
import win32gui
import pywintypes
import fitz  # PyMuPDF
import subprocess
import shutil
import os
import re
import time
from typing import List, Dict, Optional
import config


def _find_sumatra_pdf() -> Optional[str]:
    """
    查找 SumatraPDF 可执行文件路径

    Returns:
        SumatraPDF 路径，未找到返回 None
    """
    # 优先使用配置路径
    if hasattr(config, 'SUMATRA_PDF_PATH') and os.path.isfile(config.SUMATRA_PDF_PATH):
        return config.SUMATRA_PDF_PATH

    # 检查 PATH 环境变量
    sumatra_in_path = shutil.which('SumatraPDF.exe') or shutil.which('SumatraPDF')
    if sumatra_in_path:
        return sumatra_in_path

    # 常见安装路径
    common_paths = [
        r'C:\Program Files\SumatraPDF\SumatraPDF.exe',
        r'C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\SumatraPDF\SumatraPDF.exe'),
    ]
    for path in common_paths:
        if os.path.isfile(path):
            return path

    return None


# 缓存 SumatraPDF 路径
_SUMATRA_PATH: Optional[str] = None


def _get_sumatra_path() -> Optional[str]:
    """获取缓存的 SumatraPDF 路径"""
    global _SUMATRA_PATH
    if _SUMATRA_PATH is None:
        _SUMATRA_PATH = _find_sumatra_pdf() or ''
    return _SUMATRA_PATH if _SUMATRA_PATH else None


def get_printer_names() -> set[str]:
    """获取系统中可用的打印机名称集合。"""
    try:
        printer_enum = win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )
        return {name for _, _, name, _ in printer_enum}
    except Exception:
        return set()


def validate_printer_name(printer_name: str) -> bool:
    """
    校验用户提交的打印机名称是否为系统已安装的打印机。

    目的：避免接受任意字符串导致系统去连接未知远程打印队列（例如 UNC 路径），产生安全风险。
    """
    if not printer_name:
        return False
    printer_name = str(printer_name).strip()
    if not printer_name:
        return False

    names = get_printer_names()
    if names:
        return printer_name in names

    # 兜底：无法枚举时，仅允许非 UNC 名称，并尝试 OpenPrinter 校验
    if printer_name.startswith('\\\\'):
        return False
    try:
        handle = win32print.OpenPrinter(printer_name)
        win32print.ClosePrinter(handle)
        return True
    except Exception:
        return False


def parse_page_range(page_range: str, total_pages: int) -> List[int]:
    """
    解析页面范围字符串

    Args:
        page_range: 页面范围字符串，如 "1,3,5-7"
        total_pages: 文档总页数

    Returns:
        页码列表（0-based索引）

    Raises:
        ValueError: 页面范围格式错误或超出范围
    """
    if not page_range or not page_range.strip():
        return list(range(total_pages))

    pages = set()
    parts = page_range.replace(' ', '').split(',')

    for part in parts:
        if not part:
            continue
        if '-' in part:
            match = re.match(r'^(\d+)-(\d+)$', part)
            if not match:
                raise ValueError(f'无效的页面范围格式: {part}')
            start, end = int(match.group(1)), int(match.group(2))
            if start > end:
                raise ValueError(f'起始页不能大于结束页: {part}')
            if start < 1 or end > total_pages:
                raise ValueError(f'页码超出范围(1-{total_pages}): {part}')
            pages.update(range(start - 1, end))  # 转为0-based
        else:
            if not part.isdigit():
                raise ValueError(f'无效的页码: {part}')
            page = int(part)
            if page < 1 or page > total_pages:
                raise ValueError(f'页码超出范围(1-{total_pages}): {page}')
            pages.add(page - 1)  # 转为0-based

    return sorted(pages)


def _driver_validate_devmode(hprinter, printer_name: str, devmode):
    """
    调用驱动校验/补全 DEVMODE。

    说明：pywin32 的 win32print.DocumentProperties 在不同版本/构建下可能返回 int 或 PyDEVMODEW；
    返回 int 时通常会原地修改传入的 devmode。
    """
    try:
        dp_result = win32print.DocumentProperties(
            0,
            hprinter,
            printer_name,
            devmode,
            devmode,
            win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER,
        )
        if isinstance(dp_result, pywintypes.DEVMODEType):
            return dp_result
    except Exception:
        pass
    return devmode


# 打印机状态码映射
PRINTER_STATUS_MAP = {
    0: ('ready', '就绪'),
    win32print.PRINTER_STATUS_PAUSED: ('paused', '已暂停'),
    win32print.PRINTER_STATUS_ERROR: ('error', '错误'),
    win32print.PRINTER_STATUS_PENDING_DELETION: ('error', '待删除'),
    win32print.PRINTER_STATUS_PAPER_JAM: ('error', '卡纸'),
    win32print.PRINTER_STATUS_PAPER_OUT: ('error', '缺纸'),
    win32print.PRINTER_STATUS_MANUAL_FEED: ('warning', '手动进纸'),
    win32print.PRINTER_STATUS_PAPER_PROBLEM: ('error', '纸张问题'),
    win32print.PRINTER_STATUS_OFFLINE: ('offline', '离线'),
    win32print.PRINTER_STATUS_IO_ACTIVE: ('busy', '传输中'),
    win32print.PRINTER_STATUS_BUSY: ('busy', '忙碌'),
    win32print.PRINTER_STATUS_PRINTING: ('busy', '打印中'),
    win32print.PRINTER_STATUS_OUTPUT_BIN_FULL: ('warning', '出纸盒已满'),
    win32print.PRINTER_STATUS_NOT_AVAILABLE: ('offline', '不可用'),
    win32print.PRINTER_STATUS_WAITING: ('busy', '等待中'),
    win32print.PRINTER_STATUS_PROCESSING: ('busy', '处理中'),
    win32print.PRINTER_STATUS_INITIALIZING: ('busy', '初始化中'),
    win32print.PRINTER_STATUS_WARMING_UP: ('busy', '预热中'),
    win32print.PRINTER_STATUS_TONER_LOW: ('warning', '墨粉不足'),
    win32print.PRINTER_STATUS_NO_TONER: ('error', '无墨粉'),
    win32print.PRINTER_STATUS_PAGE_PUNT: ('warning', '页面错误'),
    win32print.PRINTER_STATUS_USER_INTERVENTION: ('warning', '需要干预'),
    win32print.PRINTER_STATUS_OUT_OF_MEMORY: ('error', '内存不足'),
    win32print.PRINTER_STATUS_DOOR_OPEN: ('warning', '门已打开'),
    win32print.PRINTER_STATUS_SERVER_UNKNOWN: ('offline', '服务器未知'),
    win32print.PRINTER_STATUS_POWER_SAVE: ('ready', '省电模式'),
}


def get_printer_status(printer_name: str) -> Dict:
    """
    获取打印机详细状态

    Args:
        printer_name: 打印机名称

    Returns:
        状态信息字典 {status: str, status_text: str, jobs: int}
    """
    try:
        handle = win32print.OpenPrinter(printer_name)
        try:
            info = win32print.GetPrinter(handle, 2)
            status_code = info.get('Status', 0)
            jobs_count = info.get('cJobs', 0)

            # 解析状态
            status, status_text = 'ready', '就绪'
            for code, (s, t) in PRINTER_STATUS_MAP.items():
                if status_code & code:
                    status, status_text = s, t
                    break

            return {
                'status': status,
                'status_text': status_text,
                'jobs': jobs_count
            }
        finally:
            win32print.ClosePrinter(handle)
    except Exception as e:
        return {
            'status': 'offline',
            'status_text': f'无法连接: {str(e)}',
            'jobs': 0
        }


def get_printers() -> List[Dict]:
    """
    获取系统中可用的打印机列表（含状态）

    Returns:
        打印机信息列表
    """
    try:
        printers = []
        default_printer = win32print.GetDefaultPrinter()

        # 枚举所有打印机
        printer_enum = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)

        for _, description, name, _ in printer_enum:
            status_info = get_printer_status(name)
            printers.append({
                'name': name,
                'description': description,
                'is_default': (name == default_printer),
                **status_info
            })

        return printers
    except Exception as e:
        print(f"获取打印机列表失败: {e}")
        return []


def print_file(filepath: str, options: dict) -> str:
    """
    发送文件到打印机
    主方案: SumatraPDF (PDF文件)
    备用方案: PyMuPDF + GDI (PDF文件)
    其他文件: ShellExecute

    Args:
        filepath: 要打印的文件路径
        options: 打印选项 {printer, copies, page_range}

    Returns:
        打印任务ID

    Raises:
        RuntimeError: 打印失败时抛出
    """
    try:
        printer_name = options.get('printer') or config.DEFAULT_PRINTER or win32print.GetDefaultPrinter()
        abs_path = os.path.abspath(filepath)

        if not os.path.exists(abs_path):
            raise RuntimeError(f'文件不存在: {abs_path}')

        try:
            copies = int(options.get('copies', 1))
        except (TypeError, ValueError):
            raise RuntimeError('份数格式错误')
        if copies < 1 or copies > 99:
            raise RuntimeError('份数超出范围(1-99)')

        page_range = options.get('page_range', '')
        duplex = options.get('duplex', 'one-sided')
        paper_size = (options.get('paper_size') or 'A4').strip() or 'A4'
        color = (options.get('color') or 'color').strip() or 'color'
        ext = os.path.splitext(abs_path)[1].lower()

        # PDF文件: 优先使用 SumatraPDF
        if ext == '.pdf':
            sumatra_path = _get_sumatra_path()
            if sumatra_path:
                try:
                    _print_pdf_sumatra(abs_path, printer_name, copies, page_range, duplex, paper_size, color, sumatra_path)
                    return f"print-job-{os.path.basename(filepath)}"
                except Exception as e:
                    print(f"SumatraPDF 打印失败，切换到备用方案: {e}")

            # 备用方案: PyMuPDF + GDI
            _print_pdf_pymupdf(abs_path, printer_name, copies, page_range, duplex, paper_size, color)
        else:
            # 其他文件使用 ShellExecute
            for _ in range(copies):
                result = win32api.ShellExecute(0, "print", abs_path, None, os.path.dirname(abs_path), 0)
                if result <= 32:
                    raise RuntimeError(f'ShellExecute失败(代码:{result})')
                if copies > 1:
                    time.sleep(0.5)

        return f"print-job-{os.path.basename(filepath)}"

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f'打印失败: {str(e)}')


def _print_pdf_sumatra(
    pdf_path: str,
    printer_name: str,
    copies: int,
    page_range: str,
    duplex: str,
    paper_size: str,
    color: str,
    sumatra_path: str,
):
    """
    使用 SumatraPDF 命令行打印 PDF

    Args:
        pdf_path: PDF文件路径
        printer_name: 打印机名称
        copies: 打印份数
        page_range: 页面范围 (如 "1,3,5-7")
        paper_size: 纸张大小 (A4/A3/Letter)
        color: 颜色模式 (color/grayscale)
        sumatra_path: SumatraPDF 可执行文件路径
    """
    cmd = [sumatra_path, '-print-to', printer_name]

    # 构建打印设置参数
    settings = []
    if copies > 1:
        settings.append(f'{copies}x')
    if page_range and page_range.strip():
        settings.append(page_range.strip())

    # 双面设置（SumatraPDF 的 print-settings 支持 duplex/duplexlong/duplexshort）
    duplex = (duplex or '').strip()
    if duplex == 'one-sided':
        settings.append('simplex')
    elif duplex == 'two-sided-long-edge':
        settings.append('duplexlong')
    elif duplex == 'two-sided-short-edge':
        settings.append('duplexshort')

    # 纸张（SumatraPDF 支持 paper=...，优先走此路径以避免 PyMuPDF 渲染变慢）
    paper_size = (paper_size or '').strip() or 'A4'
    if paper_size in {'A4', 'A3', 'Letter'} and paper_size != 'A4':
        settings.append(f'paper={paper_size}')

    # 颜色（SumatraPDF 支持 monochrome）
    color = (color or '').strip() or 'color'
    if color == 'grayscale':
        settings.append('monochrome')

    if settings:
        cmd.extend(['-print-settings', ','.join(settings)])

    cmd.append(pdf_path)

    # 执行命令 (静默模式)
    result = subprocess.run(cmd, capture_output=True, timeout=getattr(config, 'SUMATRA_TIMEOUT', 120))
    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', errors='ignore')
        raise RuntimeError(f'SumatraPDF 返回错误码 {result.returncode}: {stderr}')


def _print_pdf_pymupdf(
    pdf_path: str,
    printer_name: str,
    copies: int,
    page_range: str,
    duplex: str,
    paper_size: str,
    color: str,
):
    """
    使用 PyMuPDF 渲染 + win32print 原生打印 PDF (备用方案)

    Args:
        pdf_path: PDF文件路径
        printer_name: 打印机名称
        copies: 打印份数
        page_range: 页面范围 (如 "1,3,5-7")
        paper_size: 纸张大小 (A4/A3/Letter)
        color: 颜色模式 (color/grayscale)
    """
    import ctypes
    from ctypes import wintypes

    # GDI 常量
    SRCCOPY = 0x00CC0020
    DIB_RGB_COLORS = 0
    BI_RGB = 0

    gdi32 = ctypes.windll.gdi32
    doc = fitz.open(pdf_path)

    try:
        try:
            copies = int(copies)
        except (TypeError, ValueError):
            copies = 1
        if copies < 1:
            copies = 1
        if copies > 99:
            copies = 99

        # 解析页面范围
        if page_range and page_range.strip():
            pages_to_print = parse_page_range(page_range, len(doc))
        else:
            pages_to_print = list(range(len(doc)))

        hprinter = win32print.OpenPrinter(printer_name)
        try:
            devmode = None
            use_driver_copies = False
            try:
                info = win32print.GetPrinter(hprinter, 2)
                devmode = info.get('pDevMode')
            except Exception:
                devmode = None

            # 应用打印设置（通过 DEVMODE → ResetDC）
            duplex = (duplex or '').strip() or 'one-sided'
            if devmode is not None:
                duplex_map = {
                    'one-sided': win32con.DMDUP_SIMPLEX,
                    'two-sided-long-edge': win32con.DMDUP_VERTICAL,
                    'two-sided-short-edge': win32con.DMDUP_HORIZONTAL,
                }
                try:
                    # 份数（尽量交给驱动/打印机处理，避免重复渲染与重复传输导致变慢）
                    try:
                        devmode.Fields |= win32con.DM_COPIES
                        devmode.Copies = copies
                        use_driver_copies = True
                        if copies > 1:
                            try:
                                devmode.Fields |= win32con.DM_COLLATE
                                devmode.Collate = win32con.DMCOLLATE_TRUE
                            except Exception:
                                pass
                    except Exception:
                        use_driver_copies = False

                    # 双面
                    if duplex in duplex_map:
                        devmode.Fields |= win32con.DM_DUPLEX
                        devmode.Duplex = duplex_map[duplex]

                    # 纸张
                    paper_size = (paper_size or '').strip() or 'A4'
                    paper_map = {
                        'A4': win32con.DMPAPER_A4,
                        'A3': win32con.DMPAPER_A3,
                        'Letter': win32con.DMPAPER_LETTER,
                    }
                    if paper_size in paper_map:
                        devmode.Fields |= win32con.DM_PAPERSIZE
                        devmode.PaperSize = paper_map[paper_size]

                    # 颜色（同时在渲染阶段做灰度，确保输出一致）
                    color = (color or '').strip() or 'color'
                    color_map = {
                        'color': win32con.DMCOLOR_COLOR,
                        'grayscale': win32con.DMCOLOR_MONOCHROME,
                    }
                    if color in color_map:
                        devmode.Fields |= win32con.DM_COLOR
                        devmode.Color = color_map[color]

                    # 让驱动校验/补全 DEVMODE（失败则继续用当前值）
                    devmode = _driver_validate_devmode(hprinter, printer_name, devmode)

                    # 驱动校验后再设置一次份数（有些驱动可能会覆盖 Copies）
                    if use_driver_copies:
                        try:
                            devmode.Fields |= win32con.DM_COPIES
                            devmode.Copies = copies
                            if copies > 1:
                                try:
                                    devmode.Fields |= win32con.DM_COLLATE
                                    devmode.Collate = win32con.DMCOLLATE_TRUE
                                except Exception:
                                    pass
                        except Exception:
                            use_driver_copies = False
                except Exception as e:
                    if duplex != 'one-sided':
                        raise RuntimeError(f"无法应用双面设置({duplex}): {e}")

            render_copies = 1 if use_driver_copies else copies

            hdc = gdi32.CreateDCA(None, printer_name.encode(), None, None)
            if not hdc:
                raise RuntimeError("无法创建打印机DC")

            try:
                if devmode is not None:
                    try:
                        win32gui.ResetDC(hdc, devmode)
                    except Exception as e:
                        if duplex != 'one-sided':
                            raise RuntimeError(f"无法应用双面设置({duplex}): {e}")

                # 获取打印机参数
                printable_width = gdi32.GetDeviceCaps(hdc, 8)   # HORZRES
                printable_height = gdi32.GetDeviceCaps(hdc, 10) # VERTRES
                dpi_x = gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                dpi_y = gdi32.GetDeviceCaps(hdc, 90)  # LOGPIXELSY

                # 开始文档
                doc_name = os.path.basename(pdf_path).encode()

                class DOCINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", wintypes.INT),
                        ("lpszDocName", wintypes.LPCSTR),
                        ("lpszOutput", wintypes.LPCSTR),
                        ("lpszDatatype", wintypes.LPCSTR),
                        ("fwType", wintypes.DWORD),
                    ]

                di = DOCINFO()
                di.cbSize = ctypes.sizeof(DOCINFO)
                di.lpszDocName = doc_name
                di.lpszOutput = None
                di.lpszDatatype = None
                di.fwType = 0

                gdi32.StartDocA(hdc, ctypes.byref(di))

                for _ in range(render_copies):
                    for page_num in pages_to_print:
                        page = doc[page_num]

                        # 计算渲染DPI
                        page_rect = page.rect
                        scale = min(
                            printable_width / (page_rect.width * dpi_x / 72),
                            printable_height / (page_rect.height * dpi_y / 72),
                            1.0
                        ) * (dpi_x / 72)

                        mat = fitz.Matrix(scale, scale)
                        if (color or '').strip() == 'grayscale':
                            pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=fitz.csGRAY)
                        else:
                            pix = page.get_pixmap(matrix=mat, alpha=False)

                        img_width, img_height = pix.width, pix.height

                        # 居中
                        x = (printable_width - img_width) // 2
                        y = (printable_height - img_height) // 2

                        gdi32.StartPage(hdc)

                        # 创建 DIB
                        class BITMAPINFOHEADER(ctypes.Structure):
                            _fields_ = [
                                ("biSize", wintypes.DWORD),
                                ("biWidth", wintypes.LONG),
                                ("biHeight", wintypes.LONG),
                                ("biPlanes", wintypes.WORD),
                                ("biBitCount", wintypes.WORD),
                                ("biCompression", wintypes.DWORD),
                                ("biSizeImage", wintypes.DWORD),
                                ("biXPelsPerMeter", wintypes.LONG),
                                ("biYPelsPerMeter", wintypes.LONG),
                                ("biClrUsed", wintypes.DWORD),
                                ("biClrImportant", wintypes.DWORD),
                            ]

                        bmi = BITMAPINFOHEADER()
                        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                        bmi.biWidth = img_width
                        bmi.biHeight = -img_height  # 负值表示自上而下
                        bmi.biPlanes = 1
                        bmi.biBitCount = 24
                        bmi.biCompression = BI_RGB

                        # RGB -> BGR 转换并对齐到4字节
                        # 说明：原先逐像素 Python 循环非常慢；改为 Pillow/批量拷贝提升性能（尤其是大文档）。
                        stride = ((img_width * 3 + 3) // 4) * 4
                        samples = pix.samples
                        row_len = img_width * 3

                        # 可直接传 bytes/bytearray 给 ctypes（避免不必要的拷贝）
                        bgr_buf = None
                        try:
                            from PIL import Image  # type: ignore

                            if pix.n >= 3:
                                img = Image.frombuffer('RGB', (img_width, img_height), samples, 'raw', 'RGB', 0, 1)
                            else:
                                img = Image.frombuffer('L', (img_width, img_height), samples, 'raw', 'L', 0, 1).convert('RGB')

                            bgr = img.tobytes('raw', 'BGR')
                            if stride == row_len:
                                bgr_buf = bgr
                            else:
                                padded = bytearray(stride * img_height)
                                mv_padded = memoryview(padded)
                                mv_bgr = memoryview(bgr)
                                for row in range(img_height):
                                    src_start = row * row_len
                                    dst_start = row * stride
                                    mv_padded[dst_start:dst_start + row_len] = mv_bgr[src_start:src_start + row_len]
                                bgr_buf = padded
                        except Exception:
                            # 无 Pillow 或转换失败时，退回慢路径（保持功能可用）
                            bgr_data = bytearray(stride * img_height)
                            if pix.n >= 3:
                                for row in range(img_height):
                                    for col in range(img_width):
                                        src_idx = (row * img_width + col) * 3
                                        dst_idx = row * stride + col * 3
                                        bgr_data[dst_idx] = samples[src_idx + 2]      # B
                                        bgr_data[dst_idx + 1] = samples[src_idx + 1]  # G
                                        bgr_data[dst_idx + 2] = samples[src_idx]      # R
                            else:
                                for row in range(img_height):
                                    for col in range(img_width):
                                        src_idx = row * img_width + col
                                        dst_idx = row * stride + col * 3
                                        gray = samples[src_idx]
                                        bgr_data[dst_idx] = gray
                                        bgr_data[dst_idx + 1] = gray
                                        bgr_data[dst_idx + 2] = gray
                            bgr_buf = bgr_data

                        # 绘制到打印机
                        gdi32.StretchDIBits(
                            hdc, x, y, img_width, img_height,
                            0, 0, img_width, img_height,
                            bgr_buf, ctypes.byref(bmi),
                            DIB_RGB_COLORS, SRCCOPY
                        )

                        gdi32.EndPage(hdc)

                gdi32.EndDoc(hdc)

            finally:
                gdi32.DeleteDC(hdc)
        finally:
            win32print.ClosePrinter(hprinter)

    finally:
        doc.close()
