# 企业知识库与业务 Agent 平台

面向秋招展示的企业级 RAG + Tool Calling 项目。当前已完成四阶段能力：RAG MVP、Tool Calling MVP、LangGraph 编排、FastAPI 服务化。项目重点展示企业知识库问答、引用来源、无答案拒答、工具注册、参数校验、高风险确认、trace 日志、状态图编排和 API 服务化。

## 当前能力

- 加载 `data/docs` 下的 `.md` / `.txt` 示例企业文档。
- 按 `chunk_size=500`、`chunk_overlap=80` 切片，并保留 `source`、`title`、`chunk_id`、`start_index`、`end_index`。
- 使用可替换的本地 Hash Embedding 构建持久化向量索引。
- 支持 TopK 检索并返回 score 与引用来源。
- 基于检索上下文生成离线可运行的抽取式回答。
- 检索内容不足时返回统一拒答文案。
- 支持 Tool Registry、Pydantic 参数校验和统一工具执行入口。
- 支持 3 个 mock 业务工具：订单退款查询、用户账号状态查询、后台任务触发。
- 高风险工具 `script_task_tool` 必须带 `confirm=true` 才能执行。
- 使用 LangGraph `StateGraph` 编排 RAG + Tool 流程。
- 提供 FastAPI 接口：知识库索引、Agent 对话、trace 查询。
- 提供 `/health` 健康检查接口。
- 接口异常统一返回 `code/message/trace_id`。
- 提供 GitHub Actions CI 和 Docker 启动方式。
- 每个图节点写入 trace 日志到 `logs/agent_trace.jsonl`。

## RAG MVP

企业文档通常较长，直接整体向量化会稀释局部语义，也会让上下文过长。切片可以把检索粒度控制在更接近问题答案的位置。

- chunk 太大：召回内容噪声多，模型上下文成本高，引用不够精确。
- chunk 太小：语义不完整，容易丢失步骤之间的上下文。
- overlap：让相邻片段保留部分重叠，降低答案被切断在边界处的概率。

## Tool Calling MVP

工具注册中心位于 `app/tools/tool_registry.py`，每个工具都包含：

```python
{
    "name": "...",
    "description": "...",
    "args_schema": ...,
    "handler": ...,
    "risk_level": "low" | "medium" | "high",
}
```

当前注册的工具：

- `sql_query_tool`：查询 mock 订单退款状态，风险等级 `low`。
- `http_api_tool`：查询 mock 用户账号状态，风险等级 `medium`。
- `script_task_tool`：触发 mock 后台任务，风险等级 `high`，必须 `confirm=true`。

工具规划暂时使用轻量规则实现，位于 `app/tools/tool_plan.py`。它会识别订单号、用户编号、任务名称，并生成结构化 `ToolCallPlan`。工具执行必须先通过 Pydantic Schema 校验，不允许直接执行未校验的 handler。

## LangGraph 编排

`AgentService.chat()` 内部使用 LangGraph 状态图编排，对外调用方式保持不变：

```python
AgentService().chat(question, top_k=5, confirm=False)
```

图编排位于 `app/graph.py`：

```text
START
  ↓
init_node
  ↓
retrieve_node
  ↓
tool_plan_node
  ├── need_tool=false → final_node → END
  └── need_tool=true  → tool_execute_node
                         ├── error → fallback_node → END
                         └── ok    → final_node → END
```

异常兜底规则：

- `init_node`、`retrieve_node`、`tool_plan_node`、`tool_execute_node` 任一节点产生 `error`，进入 `fallback_node`。
- 高风险任务未确认时，`tool_execute_node` 返回工具失败结果，并进入 `fallback_node` 组装最终响应。
- 工具调用失败不会导致整个 RAG 问答崩溃。

## FastAPI 服务化

API 入口位于 `app/main.py`，请求/响应模型位于 `app/schemas/`。

启动服务：

```bash
py -m uvicorn app.main:app --reload
```

接口列表：

- `GET /health`：健康检查。
- `POST /knowledge/index`：构建或重建知识库索引。
- `POST /agent/chat`：提交自然语言问题，返回 RAG 答案和可选工具结果。
- `GET /trace/{trace_id}`：按 trace_id 查询 `logs/agent_trace.jsonl` 中的链路日志。

健康检查示例：

```bash
curl http://127.0.0.1:8000/health
```

响应：

```json
{
  "status": "ok"
}
```

构建索引示例：

```bash
curl -X POST http://127.0.0.1:8000/knowledge/index ^
  -H "Content-Type: application/json" ^
  -d "{\"docs_dir\":\"data/docs\"}"
```

响应：

```json
{
  "status": "success",
  "indexed_chunks": 6
}
```

Agent 对话示例：

```bash
curl -X POST http://127.0.0.1:8000/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"查询订单 10001 的退款状态。\",\"top_k\":5}"
```

响应：

```json
{
  "trace_id": "e4f1...",
  "status": "success",
  "answer": "1. ...",
  "citations": [
    {
      "source": "order_refund_guide.md",
      "title": "订单退款流程",
      "chunk_id": "order_refund_guide_001",
      "score": 0.46
    }
  ],
  "need_tool": true,
  "tool_name": "sql_query_tool",
  "tool_args": {
    "order_id": "10001"
  },
  "tool_result": {
    "order_id": "10001",
    "refund_status": "processing",
    "updated_at": "2026-06-01 10:20:00",
    "payment_channel": "mock_pay"
  },
  "error": null
}
```

高风险任务确认示例：

```bash
curl -X POST http://127.0.0.1:8000/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"触发订单退款状态同步任务。\",\"confirm\":true}"
```

Trace 查询示例：

```bash
curl http://127.0.0.1:8000/trace/{trace_id}
```

响应：

```json
{
  "trace_id": "e4f1...",
  "events": [
    {
      "time": "2026-06-25T08:00:00+00:00",
      "trace_id": "e4f1...",
      "node_name": "retrieve_node",
      "question": "查询订单 10001 的退款状态。",
      "tool_name": null,
      "tool_args": {},
      "success": true,
      "error": null
    }
  ]
}
```

统一错误响应：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数校验失败",
  "trace_id": "6d35..."
}
```

## Docker 启动

构建并启动：

```bash
docker compose up --build
```

服务启动后访问：

```bash
curl http://127.0.0.1:8000/health
```

容器会挂载：

- `./logs:/app/logs`
- `./vector_store:/app/vector_store`

## CI

项目包含 GitHub Actions 工作流 `.github/workflows/ci.yml`。在 `push` 和 `pull_request` 时自动执行：

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

## 命令行演示

`run_demo.py` 原有用法保持不变：

```bash
py -X utf8 run_demo.py --build-index
py -X utf8 run_demo.py --question "订单退款流程是什么？"
py -X utf8 run_demo.py --question "查询订单 10001 的退款状态。"
py -X utf8 run_demo.py --question "查询用户 U1001 的账号状态。"
py -X utf8 run_demo.py --question "触发订单退款状态同步任务。"
py -X utf8 run_demo.py --question "触发订单退款状态同步任务。" --confirm
```

## 测试

安装依赖：

```bash
py -m pip install -r requirements.txt
```

运行测试：

```bash
py -X utf8 -m pytest -q
```

当前测试覆盖：

- RAG + Tool 基础流程。
- Tool Registry、Tool Planner、Tool Validation、Tool Execution。
- LangGraph 节点路由、fallback 和高风险确认。
- FastAPI `/knowledge/index`、`/agent/chat`、`/trace/{trace_id}`。
- FastAPI `/health`。
- FastAPI 统一错误响应。

## 目录说明

```text
app/
  main.py
  config.py
  state.py
  graph.py
  schemas/
    request.py
    response.py
  rag/
  services/
  tools/
  prompts/
data/
  docs/
  mock/
tests/
vector_store/
run_demo.py
Dockerfile
docker-compose.yml
.github/workflows/ci.yml
```

## 本轮没有做的内容

- 没有引入 Redis。
- 没有引入真实数据库。
- 没有引入真实 LLM。
- 没有引入 Chroma 或 FAISS。
- 没有重构已有 RAG、Tool、LangGraph 逻辑。

## 下一阶段计划

下一阶段建议补充工程化能力：简单限流、内存缓存、统一错误码、更多接口测试，以及 Docker/Docker Compose 部署说明。
