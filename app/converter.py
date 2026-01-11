"""文档格式转换 - Windows版本"""
import os
import tempfile
import time
import threading
import win32com.client
import pywintypes
import pythoncom

# Word导出PDF常量
WD_EXPORT_FORMAT_PDF = 17
WD_EXPORT_OPTIMIZE_FOR_PRINT = 0

_CONVERT_LOCK = threading.Lock()
_RETRYABLE_HRESULTS = {
    -2147418111,  # RPC_E_CALL_REJECTED
    -2147417845,  # RPC_E_SERVERCALL_REJECTED
    -2147417846,  # RPC_E_SERVERCALL_RETRYLATER
}


def _is_retryable_com_error(exc: Exception) -> bool:
    return isinstance(exc, pywintypes.com_error) and getattr(exc, "hresult", None) in _RETRYABLE_HRESULTS


def _with_retry(func, retries: int = 20, delay: float = 0.25):
    last_exc = None
    for _ in range(retries):
        try:
            return func()
        except Exception as e:
            last_exc = e
            if _is_retryable_com_error(e):
                time.sleep(delay)
                continue
            raise
    if last_exc is not None:
        raise last_exc


def _convert_with_progid(
    progid: str,
    abs_input: str,
    abs_output: str,
    *,
    open_retries: int = 40,
    export_retries: int = 60,
    retry_delay: float = 0.5,
):
    """
    使用指定的 COM ProgID 打开 Word 文档并导出 PDF。

    说明：Word/WPS 在后台自动化时可能出现 RPC_E_CALL_REJECTED，需做重试。
    """
    app = None
    doc = None

    try:
        app = win32com.client.DispatchEx(progid)

        # 尽量关闭交互提示（不同实现可能不支持这些属性）
        try:
            app.Visible = False
        except Exception:
            pass
        try:
            app.DisplayAlerts = 0
        except Exception:
            pass
        try:
            app.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
        except Exception:
            pass
        try:
            app.Options.UpdateLinksAtOpen = False
        except Exception:
            pass
        try:
            app.Options.SaveNormalPrompt = False
        except Exception:
            pass

        def _open():
            return app.Documents.Open(
                abs_input,
                ConfirmConversions=False,
                ReadOnly=True,
                AddToRecentFiles=False,
                NoEncodingDialog=True,
                Visible=False,
            )

        doc = _with_retry(_open, retries=open_retries, delay=retry_delay)

        def _export():
            return doc.ExportAsFixedFormat(
                abs_output,
                WD_EXPORT_FORMAT_PDF,
                OpenAfterExport=False,
                OptimizeFor=WD_EXPORT_OPTIMIZE_FOR_PRINT,
            )

        _with_retry(_export, retries=export_retries, delay=retry_delay)

    finally:
        if doc is not None:
            try:
                _with_retry(lambda: doc.Close(SaveChanges=False), retries=10, delay=retry_delay)
            except Exception:
                pass
        if app is not None:
            try:
                _with_retry(app.Quit, retries=10, delay=retry_delay)
            except Exception:
                pass


def convert_to_pdf(input_path: str) -> str:
    """
    将Word文档转换为PDF (使用Word COM自动化)

    Args:
        input_path: 输入文件路径

    Returns:
        转换后的PDF文件路径

    Raises:
        RuntimeError: 转换失败时抛出
    """
    pythoncom.CoInitialize()

    try:
        output_path = os.path.join(
            tempfile.gettempdir(),
            'labprinter',
            f"{os.path.splitext(os.path.basename(input_path))[0]}.pdf"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        abs_input = os.path.abspath(input_path)
        abs_output = os.path.abspath(output_path)

        with _CONVERT_LOCK:
            conversion_errors = []

            # 优先使用 Microsoft Word；若遇到 RPC_E_CALL_REJECTED 等问题，再尝试 WPS (KWPS.Application)
            engines = [
                ("Word.Application", "Word", dict(open_retries=20, export_retries=10, retry_delay=0.5)),
                ("KWPS.Application", "WPS", dict(open_retries=40, export_retries=20, retry_delay=0.5)),
            ]

            for progid, label, kwargs in engines:
                try:
                    _convert_with_progid(progid, abs_input, abs_output, **kwargs)
                    break
                except Exception as e:
                    conversion_errors.append(f"{label}转换失败: {e}")
            else:
                raise RuntimeError(" | ".join(conversion_errors) if conversion_errors else "未知错误")

        if not os.path.exists(output_path):
            raise RuntimeError('转换后的PDF文件未找到')

        return output_path

    except Exception as e:
        raise RuntimeError(f'Word文档转换失败: {str(e)}')

    finally:
        pythoncom.CoUninitialize()
