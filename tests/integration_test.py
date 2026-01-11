"""集成测试脚本"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def test_imports():
    """测试所有模块可正常导入"""
    print("\n[1/5] 测试模块导入...")
    
    try:
        import config
        print("  ✓ config")
        
        from app import create_app
        print("  ✓ app")
        
        from app.task_queue import TaskQueue, task_queue
        print("  ✓ task_queue")
        
        from app.routes import allowed_file
        print("  ✓ routes")
        
        from app.printer import get_printers
        print("  ✓ printer")
        
        print("  所有导入成功 ✓")
        return True
    except Exception as e:
        print(f"  导入失败: {e}")
        return False


def test_config():
    """测试配置"""
    print("\n[2/5] 测试配置...")
    
    import config
    
    assert hasattr(config, 'HOST'), "缺少HOST配置"
    assert hasattr(config, 'PORT'), "缺少PORT配置"
    assert hasattr(config, 'UPLOAD_FOLDER'), "缺少UPLOAD_FOLDER配置"
    assert hasattr(config, 'DEFAULT_PRINTER'), "缺少DEFAULT_PRINTER配置"
    assert hasattr(config, 'MAX_CONCURRENT_JOBS'), "缺少MAX_CONCURRENT_JOBS配置"
    
    assert config.PORT > 0, "PORT必须大于0"
    assert config.MAX_CONCURRENT_JOBS > 0, "MAX_CONCURRENT_JOBS必须大于0"
    
    print(f"  HOST: {config.HOST}")
    print(f"  PORT: {config.PORT}")
    print(f"  UPLOAD_FOLDER: {config.UPLOAD_FOLDER}")
    print(f"  MAX_CONCURRENT_JOBS: {config.MAX_CONCURRENT_JOBS}")
    print("  配置检查通过 ✓")
    
    return True


def test_app_creation():
    """测试应用创建"""
    print("\n[3/5] 测试应用创建...")
    
    from app import create_app
    
    app = create_app(start_worker=False)
    assert app is not None, "应用创建失败"
    print("  Flask应用已创建 ✓")
    
    # 测试路由
    assert app.url_map is not None, "URL map不存在"
    routes = [str(rule) for rule in app.url_map.iter_rules()]
    print(f"  已注册的路由: {len(routes)}个")
    for route in routes:
        print(f"    - {route}")
    
    return True


def test_file_validation():
    """测试文件验证"""
    print("\n[4/5] 测试文件验证...")
    
    from app.routes import allowed_file
    
    test_cases = [
        ('test.pdf', True),
        ('test.doc', True),
        ('test.docx', True),
        ('test.txt', False),
        ('test.exe', False),
        ('test.pdf.exe', False),
        ('test', False),
    ]
    
    for filename, expected in test_cases:
        result = allowed_file(filename)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {filename}: {result} (预期: {expected})")
        assert result == expected, f"文件验证失败: {filename}"
    
    print("  文件验证测试通过 ✓")
    return True


def test_task_queue():
    """测试任务队列"""
    print("\n[5/5] 测试任务队列...")
    
    from app.task_queue import TaskQueue, TaskState
    
    queue = TaskQueue()
    
    # 测试提交任务
    task_id = queue.submit('/fake/path.pdf', {'copies': 1})
    print(f"  提交任务: {task_id[:8]}...")
    assert task_id is not None, "任务ID为空"
    
    # 测试获取任务
    task = queue.get_task(task_id)
    print(f"  获取任务: {task.id[:8]}...")
    assert task is not None, "任务不存在"
    assert task.state == TaskState.PENDING, "初始状态应为PENDING"
    
    # 测试更新任务
    queue.update_task(task_id, state=TaskState.PROGRESS, message='处理中')
    task = queue.get_task(task_id)
    print(f"  更新任务状态: {task.state.value}")
    assert task.state == TaskState.PROGRESS, "状态更新失败"
    assert task.message == '处理中', "消息更新失败"
    
    print("  任务队列测试通过 ✓")
    return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  LabPrinter Windows 集成测试")
    print("="*60)
    
    tests = [
        ("模块导入", test_imports),
        ("配置检查", test_config),
        ("应用创建", test_app_creation),
        ("文件验证", test_file_validation),
        ("任务队列", test_task_queue),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ 测试异常: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    # 总结
    print("\n" + "="*60)
    print(f"  测试结果: {passed}个通过, {failed}个失败")
    print("="*60)
    
    if failed == 0:
        print("  ✓ 所有测试通过！系统可以启动")
        return 0
    else:
        print("  ✗ 有测试失败，请检查配置")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
