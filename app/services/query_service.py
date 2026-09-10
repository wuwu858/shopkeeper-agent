# app/services/query_service.py（更新版）

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.clients.embedding_client_manager import EmbeddingClientManager
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class QueryService:
    def __init__(
            self,
            meta_mysql_repository: MetaMySQLRepository,
            embedding_client: EmbeddingClientManager,
            dw_mysql_repository: DWMySQLRepository,
            column_qdrant_repository: ColumnQdrantRepository,
            metric_qdrant_repository: MetricQdrantRepository,
            value_es_repository: ValueESRepository,
    ):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.embedding_client = embedding_client
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

    async def query(self, query: str, history: Optional[List[Dict]] = None):
        """
        执行查询，支持多轮对话

        Args:
            query: 用户问题
            history: 对话历史列表，每条消息包含 role, content, sql, result
        """
        if history is None:
            history = []

        # ✅ ===== 限制历史长度（防止噪声累积） =====
        MAX_HISTORY = 10  # 最多保存 10 条历史消息（约 5 轮对话）
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]
            print(f"📝 历史被截断，保留最近 {MAX_HISTORY} 条")

        print(f"📝 传入历史记录: {len(history)} 条")

        state = DataAgentState(
            query=query,
            keywords=[],
            retrieved_column_infos=[],
            retrieved_metric_infos=[],
            retrieved_value_infos=[],
            table_infos=[],
            metric_infos=[],
            date_info={},
            db_info={},
            sql="",
            error="",
            history=history,
            compressed_context="",
        )

        context = DataAgentContext(
            column_qdrant_repository=self.column_qdrant_repository,
            embedding_client=self.embedding_client,
            metric_qdrant_repository=self.metric_qdrant_repository,
            value_es_repository=self.value_es_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository,
        )

        try:
            async for chunk in graph.astream(
                    input=state,
                    context=context,
                    stream_mode="custom",
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:
            error = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error, ensure_ascii=False, default=str)}\n\n"