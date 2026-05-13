# 开发工作流

## 开发流程

```
1. 认领任务
   └── 从 Issue / Linear / 用户需求中获取

2. 理解上下文
   └── 阅读 AGENTS.md
   └── 查看相关文档 (docs/architecture/ docs/design/)
   └── 检查活跃计划 (docs/plans/active/)

3. 设计实现
   └── 如需复杂变更，先写执行计划
   └── 简单变更直接开始

4. 编码实现
   └── 遵循分层规则
   └── 遵循黄金原则
   └── 使用 make lint 检查

5. 本地测试
   └── make test
   └── make verify
   └── 手动验证 (curl / 浏览器)

6. 自审
   └── 对照 Self-Review Checklist
   └── 确保文档同步更新

7. 提交
   └── git add .
   └── git commit -m "type: description"
   └── git push fork main

8. 部署（如需要）
   └── make deploy MSG="description"
   └── make health 验证
```

## 提交信息规范

```
type(scope): description

[optional body]

[optional footer]
```

### Type 列表

| Type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能）|
| `refactor` | 重构 |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖更新 |
| `deploy` | 部署相关 |

### 示例

```
feat(routes): add streaming support for chat completions

fix(auth): handle expired API keys correctly

docs(api): update error code documentation

deploy: update model mapping for minimax
```

## Self-Review Checklist

### 代码质量
- [ ] 是否符合架构分层？（Models → Config → Converters → Resolvers → Services → Routes）
- [ ] 是否使用了共享工具？（kiro/utils/）
- [ ] 是否有重复代码？
- [ ] 错误处理是否完整？（try/except、边界情况）
- [ ] 日志是否结构化？（使用 logger，禁止 print）

### 测试
- [ ] 新功能是否有测试覆盖？
- [ ] 测试是否通过？（pytest tests/）
- [ ] 边界情况是否测试？

### 文档
- [ ] API 变更是否更新 docs/design/api-guidelines.md？
- [ ] 架构变更是否更新 docs/architecture/overview.md？
- [ ] 复杂逻辑是否有注释？

### 部署
- [ ] 配置变更是否更新 .env.example？
- [ ] 是否需要数据库迁移？
- [ ] 部署后是否需要验证？

## 常见问题

### Q: 新增一个上游提供商怎么做？

1. 创建 `kiro/converters_{provider}.py`（协议转换）
2. 创建/修改 `kiro/routes_{provider}.py`（路由处理）
3. 在 `kiro/model_resolver.py` 添加模型映射
4. 更新配置（.env.example + 实际配置）
5. 添加测试
6. 更新文档

### Q: 如何调试？

```bash
# 本地启动（热重载）
make dev

# 查看日志
pm2 logs kiro-gateway

# 测试 API
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"hi"}]}'

# 运行诊断
make diagnose
```

### Q: 测试失败怎么办？

1. 查看具体失败信息：`pytest tests/ -v -k "test_name"`
2. 检查环境变量是否正确加载
3. 检查上游提供商是否可用
4. 查看 `docs/troubleshooting/` 相关章节
