#!/usr/bin/env python3
"""
诊断工具
自动诊断常见问题

运行: python tools/diagnose.py
"""

import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"[PASS] Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"[FAIL] Python {version.major}.{version.minor}，需要 >= 3.11")
        return False

def check_dependencies():
    """检查依赖安装"""
    try:
        import fastapi
        import hypercorn
        import pydantic
        print("[PASS] 核心依赖已安装")
        return True
    except ImportError as e:
        print(f"[FAIL] 缺少依赖: {e}")
        print("[INFO] 运行: pip install -r requirements.txt")
        return False

def check_env_file():
    """检查环境变量文件"""
    env_file = ROOT / '.env'
    env_example = ROOT / '.env.example'
    
    if not env_file.exists():
        if env_example.exists():
            print("[WARN] .env 不存在，但 .env.example 存在")
            print("[INFO] 运行: cp .env.example .env")
        else:
            print("[FAIL] .env 和 .env.example 都不存在")
        return False
    
    # 检查关键变量
    content = env_file.read_text(encoding='utf-8')
    required_vars = ['API_KEY', 'PORT']
    missing = [v for v in required_vars if v not in content]
    
    if missing:
        print(f"[WARN] .env 可能缺少变量: {', '.join(missing)}")
        return False
    
    print("[PASS] 环境变量配置正常")
    return True

def check_port_available():
    """检查端口是否可用"""
    import socket
    port = 8000
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            print(f"[INFO] 端口 {port} 已被占用（服务可能正在运行）")
            return True
        else:
            print(f"[PASS] 端口 {port} 可用")
            return True
    except Exception as e:
        print(f"[WARN] 无法检查端口: {e}")
        return True

def check_git_status():
    """检查 git 状态"""
    try:
        result = subprocess.run(
            ['git', 'status', '--short'],
            cwd=ROOT,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print("[WARN] 有未提交的变更:")
            print(result.stdout[:200])
        else:
            print("[PASS] Git 工作区干净")
        
        return True
    except Exception:
        print("[WARN] 无法检查 git 状态")
        return True

def check_disk_space():
    """检查磁盘空间"""
    import shutil
    
    try:
        stat = shutil.disk_usage(str(ROOT))
        free_gb = stat.free / (1024**3)
        
        if free_gb < 1:
            print(f"[FAIL] 磁盘空间不足: {free_gb:.1f} GB")
            return False
        else:
            print(f"[PASS] 磁盘空间充足: {free_gb:.1f} GB")
            return True
    except Exception:
        print("[WARN] 无法检查磁盘空间")
        return True

def main():
    print("[INFO] 诊断工具")
    print("=" * 50)
    
    checks = [
        ("Python 版本", check_python_version),
        ("依赖安装", check_dependencies),
        ("环境变量", check_env_file),
        ("端口可用性", check_port_available),
        ("Git 状态", check_git_status),
        ("磁盘空间", check_disk_space),
    ]
    
    results = []
    for name, check_fn in checks:
        print(f"\n[INFO] 检查: {name}")
        try:
            results.append(check_fn())
        except Exception as e:
            print(f"[FAIL] 检查失败: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    print(f"[INFO] 结果: {passed}/{total} 项通过")
    
    if passed == total:
        print("[DONE] 环境正常，可以开始开发")
        return 0
    else:
        print("[WARN] 部分检查未通过，请根据提示修复")
        return 1

if __name__ == '__main__':
    sys.exit(main())
