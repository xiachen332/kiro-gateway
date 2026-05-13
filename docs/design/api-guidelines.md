# API 设计规范

## 核心原则

1. **兼容 OpenAI API**: 客户端应能无缝切换
2. **统一错误格式**: 所有错误返回标准 OpenAI 错误结构
3. **流式支持**: 所有文本生成接口支持 SSE 流式输出
4. **类型安全**: 所有接口使用 Pydantic 模型验证

## 请求/响应格式

### 标准请求

```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false,
  "temperature": 0.7
}
```

### 标准响应

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 10,
    "total_tokens": 20
  }
}
```

### 错误响应

```json
{
  "error": {
    "message": "Invalid API key",
    "type": "authentication_error",
    "code": "invalid_api_key"
  }
}
```

## 端点列表

| 方法 | 路径 | 描述 | 状态 |
|------|------|------|------|
| POST | `/v1/chat/completions` | 对话补全 | ✅ 已实现 |
| GET | `/v1/models` | 模型列表 | ✅ 已实现 |
| GET | `/health` | 健康检查 | ✅ 已实现 |
| POST | `/v1/completions` | 文本补全 | 🚧 待实现 |
| POST | `/v1/embeddings` | 文本嵌入 | 🚧 待实现 |
| POST | `/v1/images/generations` | 图像生成 | 🚧 待实现 |

## 头部规范

| 头部 | 必填 | 说明 |
|------|------|------|
| `Authorization` | 是 | `Bearer {api_key}` |
| `Content-Type` | 是 | `application/json` |
| `X-Request-ID` | 否 | 请求追踪 ID |

## 状态码

| 状态码 | 场景 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | API Key 无效 |
| 429 | 请求频率超限 |
| 500 | 内部错误 |
| 502 | 上游提供商错误 |
| 503 | 服务暂时不可用 |

## 新增端点流程

1. 在 `kiro/routes_*.py` 定义端点
2. 在 `kiro/models_*.py` 定义请求/响应模型
3. 添加对应的 converter 逻辑
4. 更新 `docs/design/api-guidelines.md`
5. 添加测试到 `tests/`
