# 部署工作流

## 部署前检查清单

- [ ] 代码通过所有测试（make check）
- [ ] 本地验证通过（make health）
- [ ] 配置文件已更新（.env.example）
- [ ] 变更已提交到 git
- [ ] 备份当前运行状态（pm2 save）

## 部署流程

### 1. 保存当前状态

```bash
pm2 save
pm2 list  # 记录当前 PID
```

### 2. 拉取最新代码

```bash
git pull fork main
# 或如果是本地修改
git add . && git commit -m "deploy: xxx"
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 重启服务

```bash
# 方式 1: PM2 平滑重启（推荐）
pm2 restart ecosystem.config.js

# 方式 2: 直接重启
pm2 restart kiro-gateway
```

### 5. 验证部署

```bash
# 健康检查
make health

# 或手动
curl -s http://localhost:8000/health

# 验证 API
curl -s http://localhost:8000/v1/models \
  -H "Authorization: Bearer $API_KEY"
```

### 6. 监控

```bash
# 查看日志
pm2 logs kiro-gateway --lines 50

# 查看资源使用
pm2 monit
```

## 回滚流程

如果部署失败：

```bash
# 1. 查看上一个可用版本
git log --oneline -5

# 2. 回退到上一个版本
git reset --hard HEAD~1

# 3. 重新部署
pm2 restart ecosystem.config.js

# 4. 验证
make health
```

## 环境配置

### 开发环境
- 本地运行
- 使用 .env 配置
- 启用热重载

### 生产环境
- PM2 管理进程
- 配置环境变量
- 日志收集
- 监控告警

### 配置优先级

```
1. 环境变量（最高优先级）
2. .env 文件
3. 默认值（最低优先级）
```

## 故障处理

| 场景 | 处理 |
|------|------|
| 启动失败 | 检查日志：`pm2 logs` |
| 端口占用 | 检查进程：`lsof -i :8000` |
| 配置错误 | 验证 .env 文件 |
| 上游不可用 | 检查提供商状态页 |
| 内存溢出 | 调整 PM2 max_memory_restart |
