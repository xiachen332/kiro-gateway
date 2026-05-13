# Skill: Feature Development（功能开发）

## 触发条件
- 收到新功能需求
- 新增 API 端点
- 新增上游提供商支持

## 执行流程

### Step 1: 需求分析
1. 阅读需求描述
2. 查看相关文档
3. 确认是否需要设计文档
4. 评估影响范围

### Step 2: 设计（复杂功能）
1. 编写执行计划（docs/plans/active/）
2. 确定接口设计
3. 确定数据模型
4. 确认依赖关系

### Step 3: 实现
1. 按分层架构实现：
   - Models（数据模型）
   - Config（配置）
   - Converters（协议转换）
   - Resolvers（解析逻辑）
   - Routes（API 路由）
2. 遵循黄金原则
3. 使用共享工具

### Step 4: 测试
1. 单元测试
2. 集成测试
3. 手动验证
4. 边界情况测试

### Step 5: 文档
1. 更新 API 文档
2. 更新架构文档（如需要）
3. 更新变更日志

### Step 6: 提交
1. git add .
2. git commit -m "feat(module): description"
3. git push fork main
4. 部署并验证

## 新增上游提供商模板

1. 创建 `kiro/converters_{provider}.py`
   - 请求转换函数
   - 响应转换函数
   - 流式响应处理

2. 创建/更新 `kiro/routes_{provider}.py`
   - 注册新路由
   - 调用 converter

3. 更新 `kiro/model_resolver.py`
   - 添加模型映射

4. 更新配置
   - .env.example
   - kiro/config.py

5. 添加测试
   - tests/test_converters_{provider}.py
   - tests/test_routes_{provider}.py

6. 更新文档
   - docs/design/api-guidelines.md
   - README.md
