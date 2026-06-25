# 企业知识库与业务 Agent 平台

面向秋招展示的企业级 RAG + Tool Calling 项目。当前已完成第一阶段 RAG MVP 和第二阶段 Tool Calling MVP，重点展示企业知识库问答、引用来源、无答案拒答，以及工具注册、参数校验、高风险确认和 mock 业务工具调用。

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
- 每次组合调用生成 `trace_id`，并写入 `logs/agent_trace.jsonl`。

## 为什么要切片

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

## RAG + Tool 组合服务

组合服务位于 `app/services/agent_service.py`，当前流程：

1. 调用 `RagService.answer(question)` 返回知识库回答和 citations。
2. 调用 Tool Planner 判断是否需要工具。
3. 如果需要工具，先校验参数，再执行 mock 工具。
4. 工具失败不会导致 RAG 问答崩溃。
5. 返回统一结果：`answer`、`citations`、`need_tool`、`tool_name`、`tool_result`、`error`。

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
- RAG + Tool 组合服务返回 RAG answer 和 tool_result。
- 普通 RAG 问题不会误触发工具。

## 目录说明

```text
app/
  config.py
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
- 没有引入 LangGraph。
- 没有引入 Redis、Chroma、FAISS 或真实数据库。
- 没有调用真实外部 HTTP 接口。

## 下一阶段计划

第三阶段建议实现 LangGraph 编排：定义 `AgentState`，拆分 intent、retrieve、answer、tool_plan、tool_validate、tool_execute、fallback 等节点；随后再进入 FastAPI 服务化，补充 `/knowledge/index`、`/agent/chat`、`/trace/{trace_id}` 接口。
