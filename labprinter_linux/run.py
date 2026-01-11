"""应用入口 - Linux版本"""
try:
    from labprinter_linux.app import create_app
    from labprinter_linux import config
except ImportError:  # 兼容：在 labprinter_linux 目录内直接运行 `python run.py`
    from app import create_app
    import config

app = create_app()

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
