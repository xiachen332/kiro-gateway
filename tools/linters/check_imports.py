#!/usr/bin/env python3
"""
依赖方向检查 Linter
确保模块间依赖方向正确

运行: python tools/linters/check_imports.py
"""

import os
import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

# 依赖方向规则
# key: 模块, value: 允许导入的模块
DEPENDENCY_RULES = {
    'kiro/config.py': [],  # 最底层，无依赖
    'kiro/auth.py': ['kiro/config.py'],
    'kiro/rate_limit.py': ['kiro/config.py'],
    'kiro/model_resolver.py': ['kiro/config.py'],
    'kiro/converters_openai.py': ['kiro/config.py', 'kiro/models_openai.py'],
    'kiro/models_openai.py': [],  # 纯数据模型
    'kiro/routes_openai.py': [
        'kiro/config.py',
        'kiro/auth.py',
        'kiro/converters_openai.py',
        'kiro/model_resolver.py',
        'kiro/models_openai.py',
    ],
}

def extract_imports(file_path):
    """提取 Python 文件中的导入"""
    content = file_path.read_text(encoding='utf-8')
    imports = []
    
    # 匹配 import xxx
    for match in re.finditer(r'^import\s+(\S+)', content, re.MULTILINE):
        imports.append(match.group(1))
    
    # 匹配 from xxx import yyy
    for match in re.finditer(r'^from\s+(\S+)\s+import', content, re.MULTILINE):
        imports.append(match.group(1))
    
    return imports

def check_file(file_path):
    """检查单个文件"""
    relative_path = str(file_path.relative_to(ROOT)).replace('\\', '/')
    
    # 只检查 kiro/ 下的文件
    if not relative_path.startswith('kiro/'):
        return []
    
    # 获取该文件的规则
    allowed = DEPENDENCY_RULES.get(relative_path)
    if allowed is None:
        # 未定义规则的，允许所有
        return []
    
    imports = extract_imports(file_path)
    errors = []
    
    for imp in imports:
        # 只检查项目内部导入
        if not imp.startswith('kiro.'):
            continue
        
        # 转换为文件路径
        import_path = imp.replace('.', '/') + '.py'
        
        # 检查是否在允许列表中
        if import_path not in allowed:
            errors.append({
                'file': relative_path,
                'import': imp,
                'allowed': allowed,
            })
    
    return errors

def main():
    print("[INFO] 依赖方向检查")
    print("=" * 50)
    
    all_errors = []
    
    for py_file in (ROOT / 'kiro').rglob('*.py'):
        errors = check_file(py_file)
        all_errors.extend(errors)
    
    if all_errors:
        print(f"[FAIL] 发现 {len(all_errors)} 个依赖方向错误:")
        for e in all_errors:
            print(f"  - {e['file']} 导入了 {e['import']}")
            print(f"    允许导入: {', '.join(e['allowed']) or '无'}")
        return 1
    else:
        print("[PASS] 依赖方向检查通过")
        return 0

if __name__ == '__main__':
    sys.exit(main())
