"""Flask应用工厂 - Linux版本"""
import os
from flask import Flask
try:
    from labprinter_linux import config
except ImportError:
    import config


def create_app(*, start_worker: bool = True):
    app = Flask(__name__)
    app.config.from_object(config)

    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

    from .routes import bp
    app.register_blueprint(bp)

    if start_worker:
        from .task_queue import start_worker
        start_worker()

    return app
