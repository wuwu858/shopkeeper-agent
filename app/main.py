# app/main.py

import asyncio
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.agent.graph import run_agent, session_manager
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository


class DataAgent:
    """
    数据分析智能体（支持多轮对话）

    使用示例:
        agent = DataAgent()
        await agent.init()

        # 第一轮
        result = await agent.chat("华北地区的销售总额是多少？")
        print(result["sql"])

        # 第二轮（追问）
        result = await agent.chat("那华南呢？")
        print(result["sql"])

        await agent.close()
    """

    def __init__(self):
        self._initialized = False
        self._context = None
        self._session_id = None
        self._state = None

    async def init(self, session_id: Optional[str] = None):
        """
        初始化 Agent

        Args:
            session_id: 会话 ID（不传则自动生成）
        """
        if self._initialized:
            logger.warning("Agent 已初始化，跳过")
            return

        logger.info("🚀 正在初始化 DataAgent...")

        # 生成或使用传入的 session_id
        self._session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
        logger.info(f"📝 会话 ID: {self._session_id}")

        # 初始化所有客户端
        qdrant_client_manager.init()
        embedding_client_manager.init()
        es_client_manager.init()
        meta_mysql_client_manager.init()
        dw_mysql_client_manager.init()

        # 创建 Repository 实例
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)
        metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)
        value_es_repository = ValueESRepository(es_client_manager.client)

        # 创建 Context
        self._context = DataAgentContext(
            column_qdrant_repository=column_qdrant_repository,
            embedding_client=embedding_client_manager,
            metric_qdrant_repository=metric_qdrant_repository,
            value_es_repository=value_es_repository,
            meta_mysql_repository=None,  # 在会话中注入
            dw_mysql_repository=None,
        )

        self._initialized = True
        logger.info("✅ DataAgent 初始化完成")

    async def chat(
            self,
            query: str,
            meta_mysql_repository=None,
            dw_mysql_repository=None
    ) -> Dict[str, Any]:
        """
        对话接口（支持多轮）

        Args:
            query: 用户问题
            meta_mysql_repository: 元数据仓库
            dw_mysql_repository: 数据仓库

        Returns:
            包含 SQL、结果、历史等信息的字典
        """
        if not self._initialized:
            raise RuntimeError("请先调用 init() 初始化 Agent")

        # 注入数据库仓库
        if meta_mysql_repository:
            self._context.meta_mysql_repository = meta_mysql_repository
        if dw_mysql_repository:
            self._context.dw_mysql_repository = dw_mysql_repository

        logger.info(f"💬 用户: {query}")

        # 执行 Agent
        self._state = await run_agent(
            query=query,
            session_id=self._session_id,
            context=self._context,
            state_initial=self._state
        )

        # 提取返回信息
        result = {
            "query": query,
            "sql": self._state.get("sql", ""),
            "error": self._state.get("error", ""),
            "turn": self._state.get("turn", 0),
            "history_count": len(self._state.get("history", [])),
            "session_id": self._session_id,
        }

        # 如果有执行结果，从历史中提取
        history = self._state.get("history", [])
        if history and history[-1].get("role") == "assistant":
            result["result"] = history[-1].get("result")
            result["answer"] = history[-1].get("content")

        logger.info(f"✅ 第 {result['turn']} 轮完成")

        return result

    def get_history(self) -> list:
        """获取对话历史"""
        return session_manager.get_session_history(self._session_id)

    def get_state(self) -> Optional[DataAgentState]:
        """获取当前状态"""
        return self._state

    def clear_history(self):
        """清除对话历史"""
        session_manager.clear_session(self._session_id)
        self._state = None
        logger.info(f"🗑️ 已清除会话 {self._session_id} 的历史")

    async def close(self):
        """关闭所有连接"""
        logger.info("🔌 正在关闭连接...")
        await qdrant_client_manager.close()
        await es_client_manager.close()
        await meta_mysql_client_manager.close()
        await dw_mysql_client_manager.close()
        self._initialized = False
        logger.info("✅ 连接已关闭")

    @property
    def session_id(self) -> str:
        return self._session_id


# ============================================================
# 快速使用函数
# ============================================================

async def quick_chat():
    """快速对话示例"""

    # 1. 创建 Agent
    agent = DataAgent()

    # 2. 初始化
    await agent.init()

    # 3. 创建数据库会话
    async with (
        meta_mysql_client_manager.session_factory() as meta_session,
        dw_mysql_client_manager.session_factory() as dw_session,
    ):
        meta_mysql_repository = MetaMySQLRepository(meta_session)
        dw_mysql_repository = DWMySQLRepository(dw_session)

        # 4. 多轮对话
        questions = [
            "华北地区的销售总额是多少？",
            "那华南呢？",
            "帮我按省份排序",
            "只要广东省的"
        ]

        for i, q in enumerate(questions, 1):
            print("\n" + "=" * 60)
            print(f"🔄 第 {i} 轮")
            print("=" * 60)

            result = await agent.chat(
                query=q,
                meta_mysql_repository=meta_mysql_repository,
                dw_mysql_repository=dw_mysql_repository
            )

            print(f"📝 问题: {result['query']}")
            print(f"📊 SQL: {result['sql']}")
            if result.get('answer'):
                print(f"💬 回答: {result['answer']}")
            if result.get('error'):
                print(f"❌ 错误: {result['error']}")

            print(f"📊 轮次: {result['turn']}")
            print(f"📝 历史消息: {result['history_count']} 条")

    # 5. 查看完整历史
    print("\n" + "=" * 60)
    print("📋 完整对话历史")
    print("=" * 60)
    history = agent.get_history()
    for i, msg in enumerate(history, 1):
        role = "👤 用户" if msg["role"] == "user" else "🤖 系统"
        content = msg["content"]
        sql = msg.get("sql", "")
        print(f"\n[{i}] {role}")
        print(f"    {content[:100]}")
        if sql:
            print(f"    SQL: {sql[:100]}...")

    # 6. 清理
    await agent.close()