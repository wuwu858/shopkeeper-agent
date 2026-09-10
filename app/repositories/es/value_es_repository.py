import json
from elasticsearch import AsyncElasticsearch
from dataclasses import asdict

from app.entities.value_info import ValueInfo


class ValueESRepository:
    index_name = "value_index"
    index_mappings = {
        "dynamic": False,
        "properties": {
            "id": {"type": "keyword"},
            "value": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "standard",
            },
            "column_id": {"type": "keyword"},
        },
    }

    def __init__(self, client: AsyncElasticsearch):
        self.client = client

    async def ensure_index(self):
        if not await self.client.indices.exists(index=self.index_name):
            await self.client.indices.create(
                index=self.index_name,
                mappings=self.index_mappings,
            )
            print(f"✅ 创建索引: {self.index_name}")

    async def index(self, value_infos: list[ValueInfo], batch_size: int = 20):
        if not value_infos:
            return

        for i in range(0, len(value_infos), batch_size):
            batch = value_infos[i:i + batch_size]
            operations = []
            for value_info in batch:
                source = {
                    "id": value_info.id,
                    "value": value_info.value,
                    "column_id": value_info.column_id
                }
                source_json = json.dumps(source, ensure_ascii=False)
                operations.append(
                    {"index": {"_index": self.index_name, "_id": value_info.id}}
                )
                operations.append(json.loads(source_json))
            await self.client.bulk(operations=operations)
        print(f"✅ 写入 {len(value_infos)} 条字段值到 {self.index_name}")

    async def search(
        self,
        keyword: str,
        score_threshold: float = 0.1,
        limit: int = 20,
    ) -> list[ValueInfo]:
        """按关键词检索字段取值"""
        # 先尝试直接匹配中文
        resp = await self.client.search(
            index=self.index_name,
            query={
                "match_phrase": {
                    "value": keyword
                }
            },
            size=limit,
            min_score=score_threshold,
        )
        
        # 如果没有结果，尝试使用 ES 中存储的乱码格式
        if not resp["hits"]["hits"]:
            # 常见中文到乱码的映射
            keyword_map = {
                "广东省": "å¹¿ä¸œçœ",
                "北京市": "åŒ—äº¬å¸‚",
                "上海市": "ä¸Šæµ·å¸‚",
                "广东": "å¹¿ä¸œ",
                "北京": "åŒ—äº¬",
                "上海": "ä¸Šæµ·",
            }
            query_keyword = keyword_map.get(keyword, keyword)
            
            resp = await self.client.search(
                index=self.index_name,
                query={
                    "match": {
                        "value": query_keyword
                    }
                },
                size=limit,
                min_score=score_threshold,
            )
        
        return [ValueInfo(**hit["_source"]) for hit in resp["hits"]["hits"]]