# shopkeeper-agent · 电商问数 NL2SQL 智能体

用自然语言向电商数仓提问（如"统计华北地区的销售总额"），系统自动召回元数据、生成 SQL、安全校验后执行查询并返回结果，支持多轮对话追问。

## 功能特性

- **NL2SQL**：自然语言 → SQL → 查询结果，全流程自动
- **多轮对话**：上下文压缩、追问继承（如"那华北呢？"自动沿用上一轮指标）
- **元数据智能召回**：三路并行召回（列 / 指标 / 维度值），向量检索 + 全文检索结合
- **SQL 安全防护**：仅允许 SELECT、禁止 `SELECT *`、强制 LIMIT、危险关键字拦截、敏感列按角色控制、行级权限过滤
- **可审计**：每次查询执行前后写入审计日志（query_audit 表）
- **鉴权与限流**：JWT 登录鉴权 + slowapi 接口限流

## 技术栈

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI + Streamlit（前端） |
| Agent 编排 | LangGraph / LangChain |
| LLM | DeepSeek（langchain-deepseek） |
| 向量召回 | Qdrant + BGE 中文 Embedding（bge-large-zh-v1.5） |
| 全文检索 | Elasticsearch（维度值召回） |
| 存储 | MySQL：meta（元数据/字典/审计）+ dw（数仓） |
| 其他 | SQLAlchemy(asyncmy)、sqlglot、JWT(python-jose)、slowapi、loguru |

## 系统架构

```
用户 ──▶ Streamlit 前端 (app_ui.py, :8501)
            │ HTTP + SSE 流式
            ▼
        FastAPI API (main.py, :8000)
        鉴权中间件 · 限流中间件 · request_id
            │
            ▼
      LangGraph 智能体（13 节点工作流）
            │
   ┌────────┼─────────┬──────────┐
   ▼        ▼         ▼          ▼
 MySQL meta  Qdrant  Elasticsearch  MySQL dw
(元数据/字典) (列/指标) (维度值)      (执行查询)
            │
   DeepSeek LLM（生成/校正 SQL） · BGE Embedding (:8081)
```

## Agent 工作流

```
压缩上下文 → 抽取关键词 → 三路并行召回（列/指标/值）→ 合并召回结果
→ 并行过滤（表/指标）→ 添加上下文 → 生成 SQL → 校验 SQL
   ├─ 通过 → 执行 SQL（安全校验 → 审计 → 查询数仓）
   └─ 失败 → 校正 SQL → 执行 SQL
```

## 使用前需要自行准备（必读）

仓库**不包含**任何密钥、模型权重和业务数据，clone 后需要自己准备：

**1. Python 环境（≥ 3.11）与依赖**

```powershell
uv sync            # 推荐（已提供 uv.lock）
# 或
pip install -e .
```

**2. DeepSeek API Key**

- 到 [platform.deepseek.com](https://platform.deepseek.com) 注册并创建 API Key
- 填入 `.env` 的 `DEEPSEEK_API_KEY`（LLM 配置见 `conf/app_config.yaml`）

**3. 五个外部服务**（端口固定，需先启动）

| 服务 | 端口 | 用途 | 启动方式 |
|---|---|---|---|
| MySQL 8.0 | 3306 | meta 元数据库 + dw 数仓 | `docker-compose.yml` 或本地安装 |
| Qdrant | 6333 | 列/指标向量召回 | `docker-compose.yml` |
| Elasticsearch 8 | 9200 | 维度值全文召回 | `docker-compose.yml` |
| Redis 7 | 6379 | 缓存 / 限流存储 | `docker-compose.yml` |
| BGE Embedding | 8081 | 文本向量化 | 自行部署（见下） |

- 前四个服务可用根目录 `docker-compose.yml` 启动
- **BGE 模型权重（约 1.2GB）未随仓库上传**：需自行下载 `BAAI/bge-large-zh-v1.5` 并部署 embedding 服务

**4. 数据库与数据**

- **一键初始化**（推荐）：`mysql -uroot -p < sql/init.sql` —— 自动创建 `meta` + `dw` 两库、全部表结构及演示数据
- 或手动执行：`python app/scripts/init_permission_tables.py` 建权限表，参考 `insert_missing_data.py`、`fix_region_id.py` 准备业务数据
- 构建元数据向量知识库：`python app/scripts/build_meta_knowledge.py`

**5. 配置文件**

- 创建 `.env`（仓库不提供，模板如下）：
  ```
  DEEPSEEK_API_KEY=你的key
  MYSQL_PASSWORD=你的密码
  JWT_SECRET_KEY=随机长字符串
  DICT_CACHE_TTL=300
  ```
- 修改 `conf/app_config.yaml`：数据库口令、各服务地址改为你自己的（当前为本地开发默认值）

## 快速启动

```powershell
# 1. 安装依赖
uv sync

# 2. 启动依赖服务（MySQL / Qdrant / ES / Redis；BGE Embedding 需自行部署）
docker compose up -d mysql qdrant elasticsearch redis

# 3. 初始化数据库（一键建库建表 + 演示数据；前提见"使用前需要自行准备"）
mysql -uroot -p < sql/init.sql

# 3b. 构建元数据向量知识库（需 embedding 服务已启动）
python app/scripts/build_meta_knowledge.py

# 4. 配置 .env 与 conf/app_config.yaml

# 5. 启动
uvicorn main:app --reload     # API :8000
streamlit run app_ui.py       # 前端 :8501
```

> 连接参数（数据库/向量库/LLM）位于 `conf/app_config.yaml`，元数据表结构定义位于 `conf/meta_config.yaml`。

## 目录结构

```
app/
  agent/           LangGraph 工作流（graph、state、13 个节点）
  api/             FastAPI 路由（auth / query / dictionary / health）
  clients/         外部服务客户端（MySQL / Qdrant / ES / Embedding）
  core/            安全与基础设施（SQL 校验、JWT、审计、限流、字典加载）
  entities/        领域实体
  middleware/      鉴权 / 限流中间件
  models/          SQLAlchemy ORM 模型
  prompt/          提示词加载
  repositories/    数据访问层（MySQL meta/dw、Qdrant、ES）
  scripts/         初始化与维护脚本
  services/        业务服务（query_service、meta_knowledge_service）
conf/              配置文件（app_config.yaml、meta_config.yaml）
prompts/           LLM 提示词模板
eval/              评估用例与评估脚本（run_eval.py、questions.json）
tests/             测试用例（test_nl2sql.py、nl2sql_cases.json）
docker/            Docker 编排与 BGE 模型权重
```

## 测试与评估

```powershell
# 单元/集成测试
pytest tests/

# NL2SQL 评估（需依赖服务已启动）
python eval/run_eval.py
```

## 说明

- 数据库口令等敏感信息请通过环境变量或 `.env` 提供，`conf/app_config.yaml` 中的明文口令仅作本地开发默认值。
- 项目处于开发阶段；根目录脚本（check_* / fix_* / insert_missing_data 等）为开发调试用。
