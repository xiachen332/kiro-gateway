# Kiro Gateway - Agent 友好 Makefile
# 统一命令入口，Agent 和人类都使用这些命令

.PHONY: setup dev test lint format verify check deploy clean

# 初始化环境
setup:
	pip install -r requirements.txt
	cp .env.example .env
	@echo "[DONE] 环境初始化完成"

# 本地开发（热重载）
dev:
	python start.py

# 生产启动
start:
	pm2 start ecosystem.config.js

# 运行测试
test:
	pytest tests/ -v

# 运行特定测试
test-one:
	pytest tests/ -v -k $(TEST)

# 代码检查
lint:
	ruff check .
	python tools/linters/check_structure.py
	python tools/linters/check_imports.py

# 代码格式化
format:
	ruff format .

# 类型检查
type-check:
	mypy kiro/ --ignore-missing-imports

# Agent 环境自检
verify:
	python tools/verify.py

# 全面检查（CI 用）
check: lint type-check test verify
	@echo "[DONE] 全部检查通过"

# 部署到生产
deploy:
	git add .
	git commit -m "deploy: $(MSG)" || true
	git push fork main
	pm2 restart ecosystem.config.js
	@echo "[DONE] 部署完成"

# 健康检查
health:
	curl -s http://localhost:8000/health | python -m json.tool

# 诊断问题
diagnose:
	python tools/diagnose.py

# 质量评分更新
quality-update:
	python tools/quality_report.py

# 清理缓存
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "[DONE] 缓存清理完成"
