#!/usr/bin/env python3
"""
结构检查 Linter
检查目录结构和文件命名是否符合规范

运行: python tools/linters/check_structure.py
"""

import os
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent.parent.parent

def check_required_dirs():
    """检查必需目录"""
    required = [
        'kiro',
        'tests',
        'docs',
        'tools',
    ]
    
    errors = []
    for dir_name in required:
        if not (ROOT / dir_name).exists():
            errors.append(f"[FAIL] 缺少目录: {dir_name}/")
    
    return errors

def check_kiro_modules():
    """检查 kiro 核心模块"""
    kiro_dir = ROOT / 'kiro'
    if not kiro_dir.exists():
        return ["[FAIL] kiro/ 目录不存在"]
    
    # 检查核心文件
    required_files = [
        'config.py',
        'auth.py',
    ]
    
    warnings = []
    for f in required_files:
        if not (kiro_dir / f).exists():
            warnings.append(f"[WARN] 缺少核心文件: kiro/{f}")
    
    return warnings

def check_file_size():
    """检查文件大小"""
    max_lines = 300
    errors = []
    
    for py_file in (ROOT / 'kiro').rglob('*.py'):
        line_count = len(py_file.read_text(encoding='utf-8').splitlines())
        if line_count > max_lines:
            errors.append(
                f"[FAIL] {py_file.name} 超过 {max_lines} 行 ({line_count} 行)"
            )
    
    return errors

def check_naming_convention():
    """检查命名规范"""
    errors = []
    
    # Python 文件应该使用 snake_case
    for py_file in (ROOT / 'kiro').rglob('*.py'):
        name = py_file.stem
        if '-' in name:
            errors.append(f"[FAIL] {py_file.name} 使用 '-'，应使用 '_'")
    
    return errors

def main():
    print("[INFO] 结构检查")
    print("=" * 50)
    
    all_issues = []
    
    # 检查目录
    issues = check_required_dirs()
    all_issues.extend(issues)
    if issues:
        for i in issues:
            print(i)
    else:
        print("[PASS] 目录结构检查通过")
    
    # 检查模块
    issues = check_kiro_modules()
    all_issues.extend(issues)
    if issues:
        for i in issues:
            print(i)
    else:
        print("[PASS] 核心模块检查通过")
    
    # 检查文件大小
    issues = check_file_size()
    all_issues.extend(issues)
    if issues:
        for i in issues:
            print(i)
    else:
        print("[PASS] 文件大小检查通过")
    
    # 检查命名
    issues = check_naming_convention()
    all_issues.extend(issues)
    if issues:
        for i in issues:
            print(i)
    else:
        print("[PASS] 命名规范检查通过")
    
    print("=" * 50)
    
    # 统计
    failures = [i for i in all_issues if i.startswith('[FAIL]')]
    warnings = [i for i in all_issues if i.startswith('[WARN]')]
    
    if failures:
        print(f"[FAIL] 发现 {len(failures)} 个错误")
        return 1
    elif warnings:
        print(f"[PASS] 检查通过，{len(warnings)} 个警告")
        return 0
    else:
        print("[PASS] 全部通过")
        return 0

if __name__ == '__main__':
    sys.exit(main())
