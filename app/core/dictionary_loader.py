# app/core/dictionary_loader.py

import json
import time
from typing import Dict, Any, Optional
from app.core.log import logger


class DictionaryLoader:
    """字典加载器 - 带缓存（单例模式）"""

    _instance = None
    _metrics: Dict = {}
    _dimensions: Dict = {}
    _region_mapping: Dict = {}
    _loaded_at: float = 0
    _cache_ttl: int = 300  # 缓存5分钟

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def load_from_db(self, session, force: bool = False):
        """从数据库加载字典"""
        current_time = time.time()

        if not force and (current_time - self._loaded_at) < self._cache_ttl:
            logger.debug("✅ 使用缓存的字典")
            return

        try:
            from sqlalchemy import text

            logger.info("🔄 从数据库加载字典...")

            # ===== 加载指标 =====
            metric_result = await session.execute(
                text("""
                    SELECT 
                        id,
                        name, 
                        description, 
                        expression, 
                        relevant_columns,
                        alias,
                        is_active
                    FROM metric_dict 
                    WHERE is_active = 1
                """)
            )
            metrics = metric_result.fetchall()

            self._metrics = {}
            for m in metrics:
                if hasattr(m, '_mapping'):
                    m_dict = dict(m._mapping)
                else:
                    m_dict = dict(m)

                name = m_dict.get('name')
                if not name:
                    continue

                # 解析 relevant_columns (可能是 JSON 或逗号分隔)
                relevant_cols = m_dict.get('relevant_columns', '')
                if relevant_cols:
                    try:
                        relevant_cols = json.loads(relevant_cols)
                    except:
                        relevant_cols = [c.strip() for c in relevant_cols.split(',') if c.strip()]
                else:
                    relevant_cols = []

                # 解析 alias
                alias = m_dict.get('alias', '')
                if alias:
                    try:
                        alias = json.loads(alias)
                    except:
                        alias = [a.strip() for a in alias.split(',') if a.strip()]
                else:
                    alias = []

                self._metrics[name] = {
                    "id": m_dict.get('id'),
                    "name": name,
                    "description": m_dict.get('description', ''),
                    "expression": m_dict.get('expression', ''),
                    "relevant_columns": relevant_cols,
                    "alias": alias
                }

            # ===== 加载维度 =====
            dim_result = await session.execute(
                text("""
                    SELECT 
                        id,
                        name,
                        category,
                        mapping_values,
                        description,
                        alias,
                        is_active
                    FROM dimension_dict 
                    WHERE is_active = 1
                """)
            )
            dimensions = dim_result.fetchall()

            self._dimensions = {}
            self._region_mapping = {}

            for d in dimensions:
                if hasattr(d, '_mapping'):
                    d_dict = dict(d._mapping)
                else:
                    d_dict = dict(d)

                dim_name = d_dict.get('name')
                if not dim_name:
                    continue

                category = d_dict.get('category', '')
                values = d_dict.get('mapping_values', [])

                if isinstance(values, str):
                    try:
                        values = json.loads(values)
                    except:
                        values = [v.strip() for v in values.split(',') if v.strip()]
                elif not isinstance(values, list):
                    values = [str(values)]

                # 解析 alias
                alias = d_dict.get('alias', '')
                if alias:
                    try:
                        alias = json.loads(alias)
                    except:
                        alias = [a.strip() for a in alias.split(',') if a.strip()]
                else:
                    alias = []

                if dim_name not in self._dimensions:
                    self._dimensions[dim_name] = {
                        "id": d_dict.get('id'),
                        "category": category,
                        "values": {},
                        "description": d_dict.get('description', ''),
                        "alias": alias
                    }
                self._dimensions[dim_name]["values"] = values

                if category == 'region':
                    self._region_mapping[dim_name] = values

            self._loaded_at = current_time
            logger.info(f"✅ 字典加载完成: {len(self._metrics)} 个指标, {len(self._dimensions)} 个维度")

        except Exception as e:
            logger.error(f"❌ 字典加载失败: {e}")

    def get_metrics(self) -> Dict:
        return self._metrics

    def get_dimensions(self) -> Dict:
        return self._dimensions

    def get_region_mapping(self) -> Dict[str, list]:
        return self._region_mapping

    def invalidate(self):
        self._metrics = {}
        self._dimensions = {}
        self._region_mapping = {}
        self._loaded_at = 0
        logger.info("✅ 字典缓存已清除")

    async def reload(self, session):
        self.invalidate()
        await self.load_from_db(session, force=True)


dictionary_loader = DictionaryLoader()