"""安全加固相关测试 - Linux版本"""
import os
import sys
from io import BytesIO

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from labprinter_linux.app import create_app
from labprinter_linux import config


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr(config, "DEBUG", False)
    app = create_app(start_worker=False)
    app.config["TESTING"] = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def _upload_folder():
    return config.UPLOAD_FOLDER


def test_invalid_copies_does_not_save_file(client):
    os.makedirs(_upload_folder(), exist_ok=True)
    before = set(os.listdir(_upload_folder()))

    data = {
        "file": (BytesIO(b"%PDF-1.4 test"), "test.pdf"),
        "copies": "abc",
    }
    res = client.post("/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 400

    after = set(os.listdir(_upload_folder()))
    assert after == before


def test_invalid_printer_does_not_save_file(client, monkeypatch):
    os.makedirs(_upload_folder(), exist_ok=True)
    before = set(os.listdir(_upload_folder()))

    import labprinter_linux.app.printer as printer_mod

    monkeypatch.setattr(printer_mod, "validate_printer_name", lambda name: False)

    data = {
        "file": (BytesIO(b"%PDF-1.4 test"), "test.pdf"),
        "copies": "1",
        "printer": "FakePrinter",
    }
    res = client.post("/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 400

    after = set(os.listdir(_upload_folder()))
    assert after == before


def test_queue_full_removes_saved_file(client, monkeypatch):
    os.makedirs(_upload_folder(), exist_ok=True)
    before = set(os.listdir(_upload_folder()))

    import labprinter_linux.app.routes as routes_mod

    def fake_submit(filepath, options, filename=""):
        raise RuntimeError("任务队列已满，请稍后再试")

    monkeypatch.setattr(routes_mod.task_queue, "submit", fake_submit)

    data = {
        "file": (BytesIO(b"%PDF-1.4 test"), "test.pdf"),
        "copies": "1",
    }
    res = client.post("/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 429

    after = set(os.listdir(_upload_folder()))
    assert after == before


def test_status_does_not_expose_traceback_by_default(client):
    from labprinter_linux.app.task_queue import task_queue, TaskState

    task_id = task_queue.submit("/fake/path.pdf", {"copies": 1}, "test.pdf")
    task_queue.update_task(
        task_id,
        state=TaskState.FAILURE,
        message="打印失败: xxx",
        error="Traceback (most recent call last): ...",
    )

    res = client.get(f"/status/{task_id}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["state"] == "FAILURE"
    assert "error" not in data


def test_favicon_does_not_404(client):
    res = client.get("/favicon.ico")
    assert res.status_code == 204
