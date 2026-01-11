"""文档格式转换 - Linux版本 (LibreOffice headless)"""
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path

try:
    from labprinter_linux import config
except ImportError:
    import config

_CONVERT_LOCK = threading.Lock()


def _find_soffice() -> str:
    if config.SOFFICE_PATH and os.path.isfile(config.SOFFICE_PATH):
        return config.SOFFICE_PATH
    return shutil.which('soffice') or shutil.which('libreoffice') or ''


def convert_to_pdf(input_path: str) -> str:
    abs_input = os.path.abspath(input_path)
    if not os.path.exists(abs_input):
        raise RuntimeError(f'文件不存在: {abs_input}')

    soffice = _find_soffice()
    if not soffice:
        raise RuntimeError('未找到 LibreOffice (soffice)，请安装 libreoffice-writer 或设置 SOFFICE_PATH')

    out_dir = os.path.join(tempfile.gettempdir(), 'labprinter')
    os.makedirs(out_dir, exist_ok=True)

    stem = Path(abs_input).stem
    abs_output = os.path.abspath(os.path.join(out_dir, f'{stem}.pdf'))

    profile_dir = os.path.join(tempfile.gettempdir(), 'labprinter', 'lo_profile', uuid.uuid4().hex)
    os.makedirs(profile_dir, exist_ok=True)
    user_install = Path(profile_dir).as_uri()

    cmd = [
        soffice,
        '--headless',
        '--nologo',
        '--nofirststartwizard',
        '--norestore',
        f'-env:UserInstallation={user_install}',
        '--convert-to', 'pdf',
        '--outdir', out_dir,
        abs_input
    ]

    try:
        with _CONVERT_LOCK:
            # 某些环境（例如 SSH 开启 X11 转发但本机无 X Server）会因 DISPLAY 存在而触发 X11 相关提示。
            # 强制清理 DISPLAY / WAYLAND_DISPLAY，确保 LibreOffice 真正以 headless 运行。
            env = os.environ.copy()
            env.pop('DISPLAY', None)
            env.pop('WAYLAND_DISPLAY', None)
            env.pop('XAUTHORITY', None)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=config.CONVERT_TIMEOUT
            )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or '').strip() or f'LibreOffice 转换失败，返回码 {result.returncode}')
        if not os.path.exists(abs_output):
            raise RuntimeError('转换后的PDF文件未找到')
        return abs_output
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)
