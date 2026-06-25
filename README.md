# 企业知识库与业务 Agent 平台

面向秋招展示的企业级 RAG + Tool Calling 项目。当前完成第一阶段 RAG MVP，重点跑通知识库文档加载、文本切片、本地向量索引、TopK 检索、上下文拼接、引用来源和无答案拒答。

## 当前能力

- 加载 `data/docs` 下的 `.md` / `.txt` 示例企业文档。
- 按 `chunk_size=500`、`chunk_overlap=80` 切片，并保留 `source`、`title`、`chunk_id`、`start_index`、`end_index`。
- 使用可替换的本地 Hash Embedding 构建持久化向量索引。
- 支持 TopK 检索并返回 score 与引用来源。
- 基于检索上下文生成离线可运行的抽取式回答。
- 检索内容不足时返回统一拒答文案。

## 为什么要切片

企业文档通常较长，直接整体向量化会稀释局部语义，也会让上下文过长。切片可以把检索粒度控制在更接近问题答案的位置。

- chunk 太大：召回内容噪声多，模型上下文成本高，引用不够精确。
- chunk 太小：语义不完整，容易丢失步骤之间的上下文。
- overlap：让相邻片段保留部分重叠，降低答案被切断在边界处的概率。

## 快速演示

```bash
python run_demo.py --build-index
python run_demo.py --question "订单退款流程是什么？"
python run_demo.py --question "火星基地报销流程是什么？"
```

Windows 如果 `python` 命令被系统商店别名占用，可以改用：

```bash
py -X utf8 run_demo.py --build-index
py -X utf8 run_demo.py --question "错误码 E1001 是什么意思？"
```

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
  services/
    rag_service.py
  prompts/
    rag_answer_prompt.txt
data/docs/
  order_refund_guide.md
  api_manual.md
  error_code_manual.md
  operation_faq.md
vector_store/
run_demo.py
```

## 下一阶段计划

第二阶段将实现 Tool Calling MVP：Tool Registry、3 个 Mock 业务工具、Pydantic 参数校验、高风险工具 `confirm=true` 机制和工具调用日志。
