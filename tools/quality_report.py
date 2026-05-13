#!/usr/bin/env python3
"""
质量评分报告生成器
自动计算并更新质量评分

运行: python tools/quality_report.py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent

def calculate_test_coverage():
    """计算测试覆盖率（简化版）"""
    tests_dir = ROOT / 'tests'
    kiro_dir = ROOT / 'kiro'
    
    if not tests_dir.exists():
        return 0
    
    test_files = list(tests_dir.glob('test_*.py'))
    kiro_files = list(kiro_dir.glob('*.py'))
    
    if not kiro_files:
        return 0
    
    # 简化计算：测试文件数 / 模块文件数
    coverage = min(100, int(len(test_files) / len(kiro_files) * 100))
    return coverage

def calculate_doc_coverage():
    """计算文档覆盖率"""
    docs_dir = ROOT / 'docs'
    kiro_dir = ROOT / 'kiro'
    
    if not docs_dir.exists():
        return 0
    
    # 检查是否有对应文档
    kiro_modules = [f.stem for f in kiro_dir.glob('*.py') if not f.name.startswith('_')]
    
    doc_files = []
    for subdir in ['architecture', 'design', 'workflows', 'troubleshooting']:
        doc_dir = docs_dir / subdir
        if doc_dir.exists():
            doc_files.extend([f.stem for f in doc_dir.glob('*.md')])
    
    # 简化计算
    return min(100, int(len(doc_files) / max(1, len(kiro_modules)) * 100))

def check_type_annotations():
    """检查类型注解覆盖率"""
    kiro_dir = ROOT / 'kiro'
    
    total_files = 0
    typed_files = 0
    
    for py_file in kiro_dir.rglob('*.py'):
        if py_file.name.startswith('_'):
            continue
        
        total_files += 1
        content = py_file.read_text(encoding='utf-8')
        
        # 简单检查：是否包含类型注解特征
        if '-> ' in content or ': ' in content:
            typed_files += 1
    
    if total_files == 0:
        return 0
    
    return int(typed_files / total_files * 100)

def check_print_statements():
    """检查是否有 print 语句"""
    kiro_dir = ROOT / 'kiro'
    
    print_count = 0
    for py_file in kiro_dir.rglob('*.py'):
        content = py_file.read_text(encoding='utf-8')
        # 简单计数（排除注释中的 print）
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('print(') and not stripped.startswith('#'):
                print_count += 1
    
    return print_count

def generate_report():
    """生成质量报告"""
    
    # 计算各项指标
    test_coverage = calculate_test_coverage()
    doc_coverage = calculate_doc_coverage()
    type_coverage = check_type_annotations()
    print_count = check_print_statements()
    
    # 计算总分（简化算法）
    test_score = min(100, test_coverage * 1.2)  # 测试权重 30%
    doc_score = min(100, doc_coverage * 1.2)    # 文档权重 20%
    type_score = type_coverage                     # 类型权重 25%
    
    # print 语句扣分
    print_penalty = min(20, print_count * 2)
    
    total_score = int(
        test_score * 0.30 +
        doc_score * 0.20 +
        type_score * 0.25 +
        (100 - print_penalty) * 0.25
    )
    
    # 生成报告内容
    report = f"""# 质量评分报告

## 总体评分: {get_grade(total_score)} ({total_score}/100)

更新日期: {datetime.now().strftime('%Y-%m-%d')}

---

## 详细指标

| 指标 | 分数 | 权重 | 说明 |
|------|------|------|------|
| 测试覆盖 | {test_coverage}% | 30% | {'[PASS]' if test_coverage > 60 else '[WARN]'} |
| 文档覆盖 | {doc_coverage}% | 20% | {'[PASS]' if doc_coverage > 60 else '[WARN]'} |
| 类型注解 | {type_coverage}% | 25% | {'[PASS]' if type_coverage > 70 else '[WARN]'} |
| 代码规范 | {100 - print_penalty}% | 25% | {'[PASS]' if print_count == 0 else '[WARN]'} {f'({print_count} 个 print 语句)' if print_count > 0 else ''} |

## 评分标准

| 等级 | 分数 | 说明 |
|------|------|------|
| A | 90-100 | 优秀 |
| B+ | 85-89 | 良好 |
| B | 80-84 | 合格 |
| C+ | 75-79 | 及格 |
| C | 70-74 | 差 |
| D | <70 | 不可用 |

## 改进建议

"""
    
    # 添加改进建议
    suggestions = []
    if test_coverage < 60:
        suggestions.append("- 增加测试覆盖，当前不足 60%")
    if doc_coverage < 60:
        suggestions.append("- 补充模块文档")
    if type_coverage < 70:
        suggestions.append("- 增加类型注解")
    if print_count > 0:
        suggestions.append(f"- 移除 {print_count} 个 print 语句，改用 logging")
    
    if suggestions:
        report += "\n".join(suggestions)
    else:
        report += "- 代码质量良好，继续保持"
    
    report += """

## 更新方式

```bash
python tools/quality_report.py
```

---

*自动生成的质量报告*
"""
    
    return report

def get_grade(score):
    """根据分数返回等级"""
    if score >= 90:
        return 'A'
    elif score >= 85:
        return 'B+'
    elif score >= 80:
        return 'B'
    elif score >= 75:
        return 'C+'
    elif score >= 70:
        return 'C'
    else:
        return 'D'

def main():
    print("[INFO] 生成质量报告...")
    
    report = generate_report()
    
    # 保存到文件
    report_file = ROOT / 'docs' / 'quality' / 'report.md'
    report_file.write_text(report, encoding='utf-8')
    
    print(f"[DONE] 报告已保存: {report_file}")
    
    # 同时输出摘要
    print("\n" + "=" * 50)
    print(report.split('---')[0])  # 输出前半部分
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
