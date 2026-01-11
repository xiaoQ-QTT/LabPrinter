"""单元测试 - Windows版本"""
import os
import sys
import pytest
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
import config


@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app(start_worker=False)
    app.config['TESTING'] = True
    yield app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


class TestRoutes:
    """路由测试"""

    def test_index(self, client):
        """测试主页"""
        response = client.get('/')
        assert response.status_code == 200
        assert '实验室打印服务' in response.data.decode('utf-8')

    def test_favicon(self, client):
        """测试 favicon 不返回404"""
        response = client.get('/favicon.ico')
        assert response.status_code == 204

    def test_list_printers(self, client):
        """测试获取打印机列表"""
        response = client.get('/printers')
        assert response.status_code == 200
        data = response.get_json()
        assert 'printers' in data
        assert isinstance(data['printers'], list)

    def test_upload_no_file(self, client):
        """测试上传空文件"""
        response = client.post('/upload', data={})
        assert response.status_code == 400
        assert '未选择文件' in response.get_json()['error']

    def test_upload_invalid_type(self, client):
        """测试上传不支持的文件类型"""
        data = {'file': (BytesIO(b'test'), 'test.txt')}
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert '不支持的文件类型' in response.get_json()['error']

    def test_upload_invalid_copies(self, client):
        """测试上传非法份数"""
        data = {
            'file': (BytesIO(b'%PDF-1.4 test'), 'test.pdf'),
            'copies': 'abc',
        }
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert '份数格式错误' in response.get_json()['error']

    def test_upload_invalid_page_range_format(self, client):
        """测试上传非法页面范围格式"""
        data = {
            'file': (BytesIO(b'%PDF-1.4 test'), 'test.pdf'),
            'page_range_type': 'custom',
            'page_range': '1--2',
        }
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert '页面范围格式错误' in response.get_json()['error']


class TestFileValidation:
    """文件验证测试"""

    def test_allowed_extensions(self):
        """测试允许的扩展名"""
        from app.routes import allowed_file

        assert allowed_file('test.pdf') is True
        assert allowed_file('test.doc') is True
        assert allowed_file('test.docx') is True
        assert allowed_file('test.txt') is False
        assert allowed_file('test.exe') is False


class TestTaskQueue:
    """任务队列测试"""

    def test_submit_task(self):
        """测试提交任务"""
        from app.task_queue import TaskQueue, TaskState

        queue = TaskQueue()
        task_id = queue.submit('/fake/path.pdf', {'copies': 1})

        assert task_id is not None
        task = queue.get_task(task_id)
        assert task is not None
        assert task.state == TaskState.PENDING

    def test_update_task(self):
        """测试更新任务状态"""
        from app.task_queue import TaskQueue, TaskState

        queue = TaskQueue()
        task_id = queue.submit('/fake/path.pdf', {'copies': 1})

        queue.update_task(task_id, state=TaskState.PROGRESS, message='处理中')
        task = queue.get_task(task_id)

        assert task.state == TaskState.PROGRESS
        assert task.message == '处理中'


class TestConfig:
    """配置测试"""

    def test_config_exists(self):
        """测试配置文件存在"""
        assert hasattr(config, 'HOST')
        assert hasattr(config, 'PORT')
        assert hasattr(config, 'UPLOAD_FOLDER')
        assert hasattr(config, 'MAX_CONTENT_LENGTH')
        assert hasattr(config, 'ALLOWED_EXTENSIONS')

    def test_config_values(self):
        """测试配置值合理"""
        assert config.PORT > 0
        assert config.MAX_CONTENT_LENGTH > 0
        assert len(config.ALLOWED_EXTENSIONS) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
