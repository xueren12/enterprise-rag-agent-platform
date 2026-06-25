# AGENTS.md

## 项目名称

企业知识库与业务 Agent 平台

## 项目定位

本项目是一个面向企业内部业务场景的 RAG + Tool Calling Agent 平台。

系统支持企业内部文档知识库问答，并能根据用户问题调用业务工具完成数据库查询、HTTP 接口调用、脚本任务触发等操作。

本项目不是普通聊天机器人，也不是简单 RAG Demo，而是一个具备知识库检索、上下文拼接、来源引用、工具调用、参数校验、缓存限流和链路追踪能力的企业级 Agent 原型。

------

## 项目背景

企业内部存在大量业务文档、接口说明、操作手册、故障处理手册和 FAQ。普通员工或研发人员经常需要查询：

- 某个业务流程怎么操作；
- 某个接口如何调用；
- 某个错误码是什么意思；
- 某个后台任务如何触发；
- 某类数据如何查询；
- 某个系统异常应该如何排查。

本项目目标是构建一个企业内部智能助手，使用户可以通过自然语言完成：

1. 知识库问答；
2. 文档引用溯源；
3. 业务工具调用；
4. 参数校验；
5. 操作结果返回；
6. 调用链路追踪；
7. 异常兜底处理。

------

## 技术栈

优先使用以下技术栈：

- Python
- FastAPI
- LangChain
- LangGraph
- Chroma 或 FAISS
- Sentence Transformers 或 OpenAI-Compatible Embedding
- DeepSeek API
- Pydantic
- SQLAlchemy
- SQLite / PostgreSQL
- Redis
- Docker
- Pytest

第一版优先使用 Python 技术栈实现完整 MVP，不要一开始引入 Java / Spring Boot，避免项目过重。

------

## 核心能力

本项目最终需要支持以下能力：

- 文档上传 / 本地文档加载；
- 文档切片；
- Embedding 向量化；
- 向量检索；
- TopK 召回；
- RAG 上下文拼接；
- 引用来源返回；
- 无答案拒答；
- 业务 Tool Calling；
- Tool 参数 Schema；
- Tool 参数校验；
- Tool 调用失败兜底；
- Redis 缓存；
- 简单接口限流；
- TraceID 链路日志；
- FastAPI 接口服务；
- README 和演示样例。

------

## MVP 目标

第一版 MVP 要跑通以下场景：

用户输入：

```text
查询知识库中“订单退款流程”的操作步骤，并告诉我可以调用哪些相关业务工具。
```

系统完成：

1. 接收用户问题；
2. 解析问题意图；
3. 从知识库中检索相关文档片段；
4. 拼接上下文；
5. 调用大模型生成回答；
6. 返回引用来源；
7. 判断是否需要业务工具；
8. 如果需要，生成工具调用计划；
9. 校验工具参数；
10. 调用 Mock 业务工具；
11. 返回最终结果；
12. 写入 TraceID 日志。

------

## 项目目录结构

请尽量按照以下结构开发：

```text
enterprise-rag-agent-platform/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── state.py
│   ├── graph.py
│   ├── nodes/
│   │   ├── intent_node.py
│   │   ├── retrieve_node.py
│   │   ├── answer_node.py
│   │   ├── tool_plan_node.py
│   │   ├── tool_validate_node.py
│   │   ├── tool_execute_node.py
│   │   └── fallback_node.py
│   ├── rag/
│   │   ├── document_loader.py
│   │   ├── text_splitter.py
│   │   ├── embedding_service.py
│   │   ├── vector_store.py
│   │   ├── retriever.py
│   │   └── prompt_builder.py
│   ├── tools/
│   │   ├── tool_registry.py
│   │   ├── sql_query_tool.py
│   │   ├── http_api_tool.py
│   │   ├── script_task_tool.py
│   │   └── mock_tools.py
│   ├── services/
│   │   ├── llm_service.py
│   │   ├── cache_service.py
│   │   ├── rate_limit_service.py
│   │   ├── log_service.py
│   │   └── trace_service.py
│   ├── schemas/
│   │   ├── request.py
│   │   ├── response.py
│   │   ├── tool_schema.py
│   │   └── trace_schema.py
│   └── prompts/
│       ├── rag_answer_prompt.txt
│       ├── intent_prompt.txt
│       └── tool_plan_prompt.txt
├── data/
│   ├── docs/
│   │   ├── order_refund_guide.md
│   │   ├── api_manual.md
│   │   ├── error_code_manual.md
│   │   └── operation_faq.md
│   └── mock_business.db
├── vector_store/
├── logs/
├── tests/
├── requirements.txt
├── README.md
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

------

## LangGraph 状态设计

请在 `app/state.py` 中定义 AgentState。

State 至少包含：

```python
trace_id: str
user_question: str

intent: str
need_rag: bool
need_tool: bool

retrieved_chunks: list[dict]
context: str
answer: str
citations: list[dict]

tool_name: str
tool_args: dict
tool_validation_error: str | None
tool_result: dict

cache_hit: bool
error: str | None
retry_count: int
```

字段含义：

- trace_id：一次 Agent 调用的唯一追踪 ID；
- user_question：用户原始问题；
- intent：问题意图；
- need_rag：是否需要知识库检索；
- need_tool：是否需要调用业务工具；
- retrieved_chunks：召回的文档片段；
- context：拼接后的上下文；
- answer：知识库问答结果；
- citations：引用来源；
- tool_name：计划调用的工具名称；
- tool_args：工具入参；
- tool_validation_error：参数校验错误；
- tool_result：工具调用结果；
- cache_hit：是否命中缓存；
- error：错误信息；
- retry_count：重试次数。

------

## LangGraph 流程设计

主流程建议如下：

```text
START
  ↓
intent_node
  ↓
cache_check_node
  ↓
retrieve_node
  ↓
answer_node
  ↓
route_need_tool
      ├── no_tool → final_response → END
      └── need_tool → tool_plan_node
                      ↓
                    tool_validate_node
                      ↓
                    route_tool_valid
                      ├── valid → tool_execute_node → final_response → END
                      └── invalid → fallback_node → END
```

第一版可以简化为：

```text
intent_node
→ retrieve_node
→ answer_node
→ tool_plan_node
→ tool_validate_node
→ tool_execute_node
→ final_response
```

要求：

- 每个节点职责单一；
- 不要把所有逻辑堆在一个函数里；
- 每个节点都要记录 trace 日志；
- 失败时进入 fallback；
- 不要让 LLM 直接执行工具，必须先经过参数校验。

------

## RAG 模块要求

### 文档加载

支持加载以下格式：

- `.md`
- `.txt`
- `.pdf` 可后续支持，第一版可先不做。

第一版请准备示例文档：

```text
data/docs/order_refund_guide.md
data/docs/api_manual.md
data/docs/error_code_manual.md
data/docs/operation_faq.md
```

文档内容需要模拟企业内部资料，包括：

- 订单退款流程；
- 用户信息查询接口说明；
- 常见错误码；
- 后台任务操作 FAQ；
- 业务系统操作说明。

不要使用真实公司敏感信息。

------

### 文档切片

实现文本切片能力。

要求：

- chunk_size 默认 500；
- chunk_overlap 默认 80；
- 每个 chunk 保留 metadata；
- metadata 至少包含：
  - source；
  - title；
  - chunk_id；
  - start_index；
  - end_index。

需要能解释：

- 为什么要切片；
- chunk 太大有什么问题；
- chunk 太小有什么问题；
- overlap 的作用是什么。

------

### Embedding 与向量库

第一版可以优先使用：

- Chroma；
- 或 FAISS；
- 或本地 Sentence Transformers。

如果环境复杂，可以先实现一个简单的可替换接口：

```python
class VectorStoreService:
    def build_index(self, docs: list[Document]) -> None:
        ...

    def similarity_search(self, query: str, top_k: int = 5) -> list[dict]:
        ...
```

要求：

- 向量库可持久化；
- 支持重新构建索引；
- 支持 TopK 检索；
- 返回 score；
- 返回 source metadata。

------

### 检索结果

检索结果格式：

```json
{
  "content": "文档片段内容",
  "source": "order_refund_guide.md",
  "title": "订单退款流程",
  "chunk_id": "order_refund_guide_001",
  "score": 0.82
}
```

------

### RAG 回答要求

回答必须满足：

1. 只基于检索到的上下文回答；
2. 不知道就拒答；
3. 必须给出引用来源；
4. 不要编造文档中不存在的信息；
5. 如果召回内容不足，需要提示用户补充信息。

无答案时回答：

```text
当前知识库中没有找到足够的信息支持该问题。建议补充相关业务文档后再查询。
```

------

## Tool Calling 模块要求

本项目需要模拟企业业务工具调用。

第一版至少实现 3 个工具：

### 1. sql_query_tool

用途：

查询模拟业务数据库。

示例问题：

```text
查询订单 10001 的退款状态。
```

入参：

```json
{
  "order_id": "10001"
}
```

返回：

```json
{
  "order_id": "10001",
  "refund_status": "processing",
  "updated_at": "2026-06-01 10:20:00"
}
```

要求：

- 只能查询白名单表；
- 不允许执行危险 SQL；
- 第一版可以使用 SQLite mock 数据库；
- 后续可切 PostgreSQL。

------

### 2. http_api_tool

用途：

模拟调用企业内部 HTTP 接口。

示例问题：

```text
查询用户 U1001 的账号状态。
```

入参：

```json
{
  "user_id": "U1001"
}
```

返回：

```json
{
  "user_id": "U1001",
  "status": "normal",
  "risk_level": "low"
}
```

第一版可以不用真的请求外部接口，使用 Mock 函数模拟。

------

### 3. script_task_tool

用途：

模拟触发后台脚本任务。

示例问题：

```text
触发订单退款状态同步任务。
```

入参：

```json
{
  "task_name": "refund_status_sync",
  "confirm": true
}
```

返回：

```json
{
  "task_name": "refund_status_sync",
  "status": "submitted",
  "task_id": "task_xxx"
}
```

要求：

- 高风险任务必须要求 `confirm=true`；
- 如果缺少确认参数，不能执行；
- 必须记录 trace 日志。

------

## Tool Registry 要求

实现工具注册中心：

```python
TOOL_REGISTRY = {
    "sql_query_tool": {
        "name": "sql_query_tool",
        "description": "查询订单、退款、用户等业务数据",
        "args_schema": SqlQueryInput,
        "handler": sql_query_tool,
        "risk_level": "low"
    },
    "http_api_tool": {
        "name": "http_api_tool",
        "description": "调用企业内部 HTTP API 查询用户或业务状态",
        "args_schema": HttpApiInput,
        "handler": http_api_tool,
        "risk_level": "medium"
    },
    "script_task_tool": {
        "name": "script_task_tool",
        "description": "触发后台脚本任务",
        "args_schema": ScriptTaskInput,
        "handler": script_task_tool,
        "risk_level": "high"
    }
}
```

要求：

- 每个工具必须有 name；
- 每个工具必须有 description；
- 每个工具必须有 Pydantic args_schema；
- 每个工具必须有 risk_level；
- 每次工具调用前必须根据 args_schema 校验参数；
- 高风险工具必须要求 confirm=true；
- 不允许 LLM 直接执行 handler。

------

## Tool Plan 要求

LLM 可以生成工具调用计划，但必须结构化。

定义：

```python
class ToolCallPlan(BaseModel):
    need_tool: bool
    tool_name: str | None
    tool_args: dict
    reason: str
```

校验规则：

- tool_name 必须在 TOOL_REGISTRY 中；
- tool_args 必须通过对应 args_schema 校验；
- high risk 工具必须 confirm=true；
- 工具不存在时进入 fallback；
- 参数错误时返回友好提示。

------

## 缓存要求

实现简单 Redis 缓存。

缓存对象：

- RAG 问答结果；
- 检索结果；
- Tool 调用结果。

缓存 key 设计：

```text
rag:answer:{md5(question)}
rag:retrieve:{md5(question)}:{top_k}
tool:{tool_name}:{md5(tool_args)}
```

要求：

- TTL 可配置；
- 缓存命中时记录 cache_hit=true；
- Redis 不可用时不影响主流程，降级为无缓存；
- 不缓存高风险工具调用结果。

如果 Redis 环境复杂，第一版可以先实现内存缓存，并保留 Redis 接口。

------

## 限流要求

实现简单限流能力。

第一版可以基于内存实现：

```text
每个 client_ip 每分钟最多 30 次请求
```

后续可替换为 Redis 令牌桶。

要求：

- 超过限制返回 429；
- 记录限流日志；
- 限流逻辑不要写死在业务节点里，放到 service 层。

------

## TraceID 与日志要求

每次请求必须生成 trace_id。

日志保存路径：

```text
logs/agent_trace.jsonl
```

每个节点都要记录日志。

日志字段：

```json
{
  "time": "...",
  "trace_id": "...",
  "node_name": "...",
  "user_question": "...",
  "intent": "...",
  "retrieved_chunks": "...",
  "tool_name": "...",
  "tool_args": "...",
  "tool_result_summary": "...",
  "cache_hit": false,
  "error": null,
  "latency_ms": 123
}
```

要求：

- 不记录 API Key；
- 不记录数据库密码；
- 不记录大段原始文档全文；
- tool_args 需要做摘要；
- 失败时必须记录 error。

------

## FastAPI 接口要求

至少实现以下接口：

### POST /knowledge/index

构建或重建知识库索引。

请求：

```json
{
  "docs_dir": "data/docs"
}
```

响应：

```json
{
  "status": "success",
  "indexed_chunks": 32
}
```

------

### POST /agent/chat

提交自然语言问题。

请求：

```json
{
  "question": "订单退款流程是什么？",
  "top_k": 5
}
```

响应：

```json
{
  "trace_id": "...",
  "status": "success",
  "answer": "...",
  "citations": [
    {
      "source": "order_refund_guide.md",
      "chunk_id": "order_refund_guide_001"
    }
  ],
  "need_tool": false,
  "tool_name": null,
  "tool_result": null,
  "error": null
}
```

------

### GET /trace/{trace_id}

查看一次请求的链路日志。

响应：

```json
{
  "trace_id": "...",
  "events": [...]
}
```

------

## 示例问题

项目需要支持以下问题：

### RAG 问答类

```text
订单退款流程是什么？
退款失败应该怎么处理？
错误码 E1001 是什么意思？
用户账号被冻结时应该如何排查？
后台任务触发失败怎么办？
```

### Tool Calling 类

```text
查询订单 10001 的退款状态。
查询用户 U1001 的账号状态。
触发订单退款状态同步任务。
帮我查看订单 10001 为什么还没有退款完成。
```

### RAG + Tool 混合类

```text
根据知识库说明，查询订单 10001 的退款状态，并告诉我下一步应该怎么处理。
根据错误码 E1001 的说明，查询用户 U1001 的账号状态。
```

------

## 测试要求

至少补充以下测试：

- 文档加载测试；
- 文本切片测试；
- 向量检索测试；
- RAG 无答案拒答测试；
- 引用来源返回测试；
- Tool Registry 测试；
- Tool 参数校验测试；
- 高风险工具 confirm 校验测试；
- 缓存命中测试；
- 限流测试；
- TraceID 日志测试；
- FastAPI 接口测试；
- 完整 RAG + Tool 流程测试。

运行命令：

```bash
python -m pytest -q
```

------

## README 要求

README 必须包含：

1. 项目简介；
2. 技术栈；
3. 系统架构；
4. RAG 流程图；
5. Tool Calling 流程图；
6. 快速启动；
7. 环境变量；
8. 示例文档；
9. 示例问题；
10. 示例响应；
11. 测试方式；
12. 项目亮点；
13. 后续优化方向。

项目亮点需要突出：

- 文档切片与向量检索；
- TopK 召回；
- 引用来源；
- 无答案拒答；
- Tool Registry；
- Pydantic 参数校验；
- 高风险工具确认机制；
- Redis 缓存；
- 简单限流；
- TraceID 链路日志。

------

## 开发顺序

不要一次性生成全部功能。

请按以下顺序逐步开发：

### 第一阶段：RAG MVP

1. 创建项目目录；
2. 准备示例文档；
3. 实现文档加载；
4. 实现文本切片；
5. 实现向量索引；
6. 实现 TopK 检索；
7. 实现 RAG Prompt；
8. 实现带引用的回答；
9. 实现无答案拒答。

### 第二阶段：Tool Calling MVP

1. 实现 Tool Registry；
2. 实现 3 个 Mock Tool；
3. 实现 ToolCallPlan；
4. 实现参数校验；
5. 实现高风险工具 confirm 机制；
6. 实现工具调用日志。

### 第三阶段：LangGraph 编排

1. 定义 AgentState；
2. 实现 intent_node；
3. 实现 retrieve_node；
4. 实现 answer_node；
5. 实现 tool_plan_node；
6. 实现 tool_validate_node；
7. 实现 tool_execute_node；
8. 实现 fallback_node；
9. 跑通完整 RAG + Tool 流程。

### 第四阶段：FastAPI 服务化

1. POST /knowledge/index；
2. POST /agent/chat；
3. GET /trace/{trace_id}；
4. 统一响应格式；
5. 友好错误返回。

### 第五阶段：工程化补强

1. 缓存；
2. 限流；
3. TraceID；
4. 测试；
5. README；
6. Docker；
7. docker-compose。

------

## 禁止事项

不要做以下事情：

- 不要使用真实公司文档；
- 不要写入真实业务数据；
- 不要把 API Key 写死在代码里；
- 不要让 LLM 直接执行工具；
- 不要跳过参数校验；
- 不要在 Tool 中执行危险操作；
- 不要在日志里记录敏感信息；
- 不要把所有逻辑写在 main.py；
- 不要一开始做复杂前端；
- 不要编造知识库没有的答案；
- 不要为了炫技引入过多框架。

------

## 验收标准

项目达到以下标准才算第一版完成：

1. 可以构建知识库索引；
2. 可以对企业文档进行切片和向量检索；
3. RAG 回答带引用来源；
4. 无相关内容时可以拒答；
5. 至少实现 3 个业务工具；
6. 工具调用前经过 Pydantic 参数校验；
7. 高风险工具必须 confirm=true；
8. LangGraph 主流程可以跑通；
9. FastAPI 接口可用；
10. 每次调用都有 trace_id；
11. 日志可以按 trace_id 查询；
12. 有基础缓存和限流；
13. pytest 可以通过；
14. README 可以指导别人启动和演示。

------

## 面试导向说明

本项目最终服务于 Agent 应用开发 / 大模型应用开发 / AI 后端开发岗位。

实现时优先突出：

- RAG 文档问答；
- 文档切片；
- Embedding；
- 向量检索；
- TopK 召回；
- 上下文拼接；
- 引用来源；
- 无答案拒答；
- Tool Calling；
- Tool Registry；
- Pydantic Schema；
- 参数校验；
- TraceID；
- 缓存限流；
- 企业场景落地。

最终项目要做到：

```text
能运行
能演示
能讲清楚
能被面试追问
```