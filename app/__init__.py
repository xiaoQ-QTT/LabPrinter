"""Flask应用工厂 - Windows版本"""
import os
from flask import Flask
import config

def create_app(*, start_worker: bool = True):
    app = Flask(__name__)
    app.config.from_object(config)

    # 确保上传目录存在
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

    # 注册路由
    from app.routes import bp
    app.register_blueprint(bp)

    # 启动后台任务处理器
    if start_worker:
        from app.task_queue import start_worker
        start_worker()

    return app
