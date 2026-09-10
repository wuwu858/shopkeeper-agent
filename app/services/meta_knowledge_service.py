# app/services/meta_knowledge_service.py

import uuid
import httpx
from dataclasses import asdict
from pathlib import Path

from omegaconf import OmegaConf

from app.conf.app_config import app_config
from app.conf.meta_config import MetaConfig
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class MetaKnowledgeService:
    def __init__(
            self,
            meta_mysql_repository: MetaMySQLRepository,
            dw_mysql_repository: DWMySQLRepository,
            column_qdrant_repository: ColumnQdrantRepository = None,
            embedding_client=None,
            value_es_repository: ValueESRepository = None,
            metric_qdrant_repository: MetricQdrantRepository = None,
    ):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.embedding_client = embedding_client
        self.value_es_repository = value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository

    async def build(self, config_path: Path):
        context = OmegaConf.load(config_path)
        schema = OmegaConf.structured(MetaConfig)
        meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
        logger.info("加载配置文件成功")

        if meta_config.tables:
            column_infos = await self._save_tables_to_meta_db(meta_config)
            logger.info("保存表信息和字段信息到 Meta MySQL")

            await self._save_column_info_to_qdrant(column_infos)
            logger.info("为字段信息建立向量索引")

            await self._save_value_info_to_es(meta_config, column_infos)
            logger.info("为字段取值建立全文索引")

        if meta_config.metrics:
            metric_infos = await self._save_metrics_to_meta_db(meta_config)
            logger.info("保存指标信息到数据库成功")

            await self._save_metrics_to_qdrant(metric_infos)
            logger.info("为指标信息建立向量索引成功")

        logger.info("元数据知识库构建完成")

    async def _save_tables_to_meta_db(self, meta_config: MetaConfig) -> list[ColumnInfo]:
        """保存表信息和字段信息到元数据库"""
        table_infos: list[TableInfo] = []
        column_infos: list[ColumnInfo] = []

        # 按表分组存储字段，用于分别保存
        table_column_map: dict[str, list[ColumnInfo]] = {}

        for table in meta_config.tables:
            table_info = TableInfo(
                id=table.name,
                name=table.name,
                role=table.role,
                description=table.description,
            )
            table_infos.append(table_info)
            logger.info(f"处理表: {table.name}")

            column_types = await self.dw_mysql_repository.get_column_types(table.name)
            logger.info(f"  获取到 {len(column_types)} 个字段类型")

            table_columns = []
            for column in table.columns:
                column_values = await self.dw_mysql_repository.get_column_values(
                    table.name, column.name, 10
                )

                # ✅ 修复：从字典中只取 data_type 字符串
                column_type_info = column_types.get(column.name, {})
                column_type_str = column_type_info.get('data_type', 'unknown') if isinstance(column_type_info,
                                                                                             dict) else 'unknown'

                column_info = ColumnInfo(
                    id=f"{table.name}.{column.name}",
                    name=column.name,
                    type=column_type_str,
                    role=column.role,
                    examples=column_values,
                    description=column.description,
                    alias=column.alias,
                    table_id=table.name,
                )
                column_infos.append(column_info)
                table_columns.append(column_info)
                logger.info(f"    字段: {column.name} (类型: {column_info.type}, 示例: {len(column_values)} 个)")

            table_column_map[table.name] = table_columns

        # ✅ 只使用一个事务上下文，统一管理事务
        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_table_infos(table_infos)
            for table_name, columns in table_column_map.items():
                await self.meta_mysql_repository.save_column_infos(table_name, columns)
            # 事务会在退出 context manager 时自动提交
            logger.info(f"事务提交成功: {len(table_infos)} 张表, {len(column_infos)} 个字段")

        return column_infos

    async def _save_metrics_to_meta_db(self, meta_config: MetaConfig) -> list[MetricInfo]:
        """保存指标信息到元数据库"""
        metric_infos: list[MetricInfo] = []
        column_metrics: list[ColumnMetric] = []

        for metric in meta_config.metrics:
            metric_info = MetricInfo(
                id=metric.name,
                name=metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias,
            )
            metric_infos.append(metric_info)

            for column in metric.relevant_columns:
                column_metric = ColumnMetric(column_id=column, metric_id=metric.name)
                column_metrics.append(column_metric)

        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_metric_infos(metric_infos)
            await self.meta_mysql_repository.save_column_metrics(column_metrics)

        return metric_infos

    async def _save_column_info_to_qdrant(self, column_infos: list[ColumnInfo]):
        """为字段信息建立向量索引"""
        await self.column_qdrant_repository.ensure_collection()

        points = []
        for column_info in column_infos:
            points.append({
                "id": str(uuid.uuid4()),
                "embedding_text": column_info.name,
                "payload": asdict(column_info),
            })
            if column_info.description:
                points.append({
                    "id": str(uuid.uuid4()),
                    "embedding_text": column_info.description,
                    "payload": asdict(column_info),
                })
            for alias in (column_info.alias or []):
                points.append({
                    "id": str(uuid.uuid4()),
                    "embedding_text": alias,
                    "payload": asdict(column_info),
                })

        # 直接调用 Embedding 服务 HTTP 接口
        embedding_url = f"http://{app_config.embedding.host}:{app_config.embedding.port}/embed"
        embeddings = []
        texts = [p["embedding_text"] for p in points]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(texts), 20):
                batch = texts[i:i + 20]
                response = await client.post(embedding_url, json={"inputs": batch})
                response.raise_for_status()
                batch_embeddings = response.json()
                if isinstance(batch_embeddings, list) and len(batch_embeddings) > 0:
                    embeddings.extend(batch_embeddings)
                else:
                    logger.warning(f"Embedding 返回空结果: {batch_embeddings}")

        # 写入 Qdrant
        ids = [p["id"] for p in points]
        payloads = [p["payload"] for p in points]
        await self.column_qdrant_repository.upsert(ids, embeddings, payloads)
        logger.info(f"字段向量索引构建完成: {len(points)} 个向量点")

    async def _save_value_info_to_es(self, meta_config: MetaConfig, column_infos: list[ColumnInfo]):
        """为字段取值建立全文索引"""
        await self.value_es_repository.ensure_index()

        # 构建同步开关映射
        column2sync = {}
        for table in meta_config.tables:
            for column in table.columns:
                column2sync[f"{table.name}.{column.name}"] = column.sync

        value_infos = []
        for column_info in column_infos:
            if column2sync.get(column_info.id, False):
                values = await self.dw_mysql_repository.get_column_values(
                    column_info.table_id, column_info.name, 100000
                )
                for v in values:
                    if v is not None and v != "":
                        value_infos.append(ValueInfo(
                            id=f"{column_info.id}.{v}",
                            value=str(v),
                            column_id=column_info.id,
                        ))

        await self.value_es_repository.index(value_infos)
        logger.info(f"字段值全文索引构建完成: {len(value_infos)} 条记录")

    async def _save_metrics_to_qdrant(self, metric_infos: list[MetricInfo]):
        """为指标信息建立向量索引"""
        await self.metric_qdrant_repository.ensure_collection()

        points = []
        for metric_info in metric_infos:
            points.append({
                "id": str(uuid.uuid4()),
                "embedding_text": metric_info.name,
                "payload": asdict(metric_info),
            })
            if metric_info.description:
                points.append({
                    "id": str(uuid.uuid4()),
                    "embedding_text": metric_info.description,
                    "payload": asdict(metric_info),
                })
            for alias in (metric_info.alias or []):
                points.append({
                    "id": str(uuid.uuid4()),
                    "embedding_text": alias,
                    "payload": asdict(metric_info),
                })

        # 直接调用 Embedding 服务 HTTP 接口
        embedding_url = f"http://{app_config.embedding.host}:{app_config.embedding.port}/embed"
        embeddings = []
        texts = [p["embedding_text"] for p in points]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(texts), 20):
                batch = texts[i:i + 20]
                response = await client.post(embedding_url, json={"inputs": batch})
                response.raise_for_status()
                batch_embeddings = response.json()
                if isinstance(batch_embeddings, list) and len(batch_embeddings) > 0:
                    embeddings.extend(batch_embeddings)
                else:
                    logger.warning(f"Embedding 返回空结果: {batch_embeddings}")

        # 写入 Qdrant
        ids = [p["id"] for p in points]
        payloads = [p["payload"] for p in points]
        await self.metric_qdrant_repository.upsert(ids, embeddings, payloads)
        logger.info(f"指标向量索引构建完成: {len(points)} 个向量点")