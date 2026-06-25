# 企业知识库与业务 Agent 平台

面向秋招展示的企业级 RAG + Tool Calling 项目。当前已完成三阶段能力：RAG MVP、Tool Calling MVP、LangGraph 编排。项目重点展示企业知识库问答、引用来源、无答案拒答、工具注册、参数校验、高风险确认、trace 日志和状态图编排。

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

第三阶段将原来 `AgentService.chat()` 内部的线性流程改为 LangGraph 状态图。对外调用方式保持不变，`run_demo.py` 仍然调用：

```python
AgentService().chat(question, top_k=5, confirm=False)
```

状态定义位于 `app/state.py`，核心字段包括：

- `trace_id`
- `question`
- `top_k`
- `confirm`
- `rag_result`
- `answer`
- `citations`
- `tool_plan`
- `tool_result`
- `need_tool`
- `error`
- `status`

图编排位于 `app/graph.py`，节点如下：

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

每个节点都会继续使用 `LogService` 记录 trace 日志。

## 快速演示

```bash
py -X utf8 run_demo.py --build-index
py -X utf8 run_demo.py --question "订单退款流程是什么？"
py -X utf8 run_demo.py --question "查询订单 10001 的退款状态。"
py -X utf8 run_demo.py --question "查询用户 U1001 的账号状态。"
py -X utf8 run_demo.py --question "触发订单退款状态同步任务。"
py -X utf8 run_demo.py --question "触发订单退款状态同步任务。" --confirm
```

高风险任务不加 `--confirm` 时会返回友好错误，不会执行 mock task；加上 `--confirm` 后会返回 `task_id`。

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

- Tool Registry 中 3 个工具都存在。
- 订单号识别并生成 `sql_query_tool`。
- 用户号识别并生成 `http_api_tool`。
- 后台任务识别并生成 `script_task_tool`。
- 高风险工具缺少 confirm 时禁止执行。
- 高风险工具 `confirm=true` 时允许执行。
- 不存在的工具名返回友好错误。
- 参数缺失返回友好错误。
- 普通 RAG 问题不进入工具执行节点。
- 订单问题进入 `sql_query_tool`。
- 用户问题进入 `http_api_tool`。
- 高风险任务无 confirm 返回失败结果。
- 高风险任务 confirm=true 可执行。
- 节点异常时进入 `fallback_node`。

## 目录说明

```text
app/
  config.py
  state.py
  graph.py
  rag/
    document_loader.py
    text_splitter.py
    embedding_service.py
    vector_store.py
    retriever.py
    prompt_builder.py
    query_terms.py
  services/
    rag_service.py
    agent_service.py
    log_service.py
  tools/
    tool_registry.py
    tool_plan.py
    mock_tools.py
    sql_query_tool.py
    http_api_tool.py
    script_task_tool.py
  prompts/
    rag_answer_prompt.txt
data/
  docs/
  mock/
tests/
vector_store/
run_demo.py
```

## 本轮没有做的内容

- 没有引入 FastAPI。
- 没有引入 Redis、Chroma、FAISS 或真实数据库。
- 没有调用真实外部 HTTP 接口。
- 没有重写已有 RAG 和 Tool 逻辑。

## 下一阶段计划

第四阶段建议进入 FastAPI 服务化：补充 `/knowledge/index`、`/agent/chat`、`/trace/{trace_id}` 接口；之后再补缓存、限流、Docker 和更完整的工程化测试。
