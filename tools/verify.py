#!/usr/bin/env python3
"""
Agent Environment Self-Verification
Usage: python tools/verify.py
"""

import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent

def check_agents_md():
    """Check AGENTS.md exists and readable"""
    agents_file = ROOT / "AGENTS.md"
    if not agents_file.exists():
        print("[FAIL] AGENTS.md not found")
        return False
    
    content = agents_file.read_text(encoding='utf-8')
    if len(content) < 100:
        print("[FAIL] AGENTS.md too short (<100 chars)")
        return False
    
    required_sections = ['Quick Start', 'Directory', 'Commands']
    for section in required_sections:
        if section not in content:
            print(f"[WARN] AGENTS.md missing section: {section}")
    
    print("[PASS] AGENTS.md check passed")
    return True

def check_directory_structure():
    """Check directory structure"""
    required_dirs = ['kiro', 'tests', 'docs']
    for dir_name in required_dirs:
        if not (ROOT / dir_name).exists():
            print(f"[FAIL] Missing directory: {dir_name}/")
            return False
    
    print("[PASS] Directory structure check passed")
    return True

def check_import_rules():
    """Check import directions"""
    violations = []
    
    for py_file in (ROOT / 'kiro').rglob('*.py'):
        content = py_file.read_text(encoding='utf-8')
        if 'import tests' in content or 'from tests' in content:
            violations.append(f"[FAIL] {py_file.name} imports tests")
    
    if violations:
        for v in violations:
            print(v)
        return False
    
    print("[PASS] Import rules check passed")
    return True

def check_tests():
    """Check tests exist"""
    tests_dir = ROOT / 'tests'
    if not tests_dir.exists():
        print("[WARN] tests/ directory not found")
        return True
    
    test_files = list(tests_dir.glob('test_*.py'))
    if not test_files:
        print("[WARN] No test files found")
        return True
    
    print(f"[PASS] Found {len(test_files)} test files")
    return True

def check_health_endpoint():
    """Check health endpoint exists"""
    main_file = ROOT / 'main.py'
    if not main_file.exists():
        print("[FAIL] main.py not found")
        return False
    
    content = main_file.read_text(encoding='utf-8')
    if 'health' not in content.lower():
        print("[WARN] main.py may lack health endpoint")
        return True
    
    print("[PASS] Health endpoint found")
    return True

def run_linters():
    """Run code linters"""
    print("\n[INFO] Running linters...")
    
    try:
        result = subprocess.run(
            ['ruff', 'check', '.'], 
            cwd=ROOT, 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            print("[PASS] Ruff check passed")
        else:
            print("[WARN] Ruff found issues:")
            if result.stdout:
                print(result.stdout[:500])
            elif result.stderr:
                print(result.stderr[:500])
    except FileNotFoundError:
        print("[WARN] ruff not installed, skipping")
    except Exception as e:
        print(f"[WARN] Ruff failed: {e}")
    
    return True

def main():
    print("[AGENT] Agent Environment Self-Verification\n")
    print("=" * 50)
    
    checks = [
        ("AGENTS.md", check_agents_md),
        ("Directory Structure", check_directory_structure),
        ("Import Rules", check_import_rules),
        ("Tests", check_tests),
        ("Health Endpoint", check_health_endpoint),
    ]
    
    results = []
    for name, check_fn in checks:
        print(f"\n[INFO] Checking: {name}")
        results.append(check_fn())
    
    run_linters()
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"[PASS] All checks passed ({passed}/{total})")
        print("\n[DONE] Agent environment is ready!")
        return 0
    else:
        print(f"[WARN] Some checks failed ({passed}/{total})")
        print("\n[INFO] Recommendations:")
        print("1. Fix the issues above")
        print("2. Run `python tools/verify.py` again")
        return 1

if __name__ == '__main__':
    sys.exit(main())
