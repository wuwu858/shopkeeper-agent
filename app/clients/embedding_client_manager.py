import asyncio
import httpx
from typing import List, Optional

from app.conf.app_config import app_config


class EmbeddingClientManager:
    def __init__(self, config):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None

    def _get_url(self) -> str:
        return f"http://{self.config.host}:{self.config.port}"

    def init(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        if self.client:
            await self.client.aclose()

    async def aembed_query(self, text: str) -> List[float]:
        """将单个文本转换为向量"""
        if not self.client:
            raise RuntimeError("Client not initialized. Call init() first.")
        
        payload = {"inputs": text}
        response = await self.client.post(f"{self._get_url()}/embed", json=payload)
        response.raise_for_status()
        result = response.json()
        return result[0] if isinstance(result, list) and len(result) > 0 else result

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量将文本转换为向量"""
        if not self.client:
            raise RuntimeError("Client not initialized. Call init() first.")
        
        payload = {"inputs": texts}
        response = await self.client.post(f"{self._get_url()}/embed", json=payload)
        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, list) and len(result) > 0 else []


embedding_client_manager = EmbeddingClientManager(app_config.embedding)


if __name__ == "__main__":
    embedding_client_manager.init()
    
    async def test():
        text = "测试文本"
        vector = await embedding_client_manager.aembed_query(text)
        print(f"文本: {text}")
        print(f"向量维度: {len(vector)}")
        print(f"向量前3个值: {vector[:3]}")

    asyncio.run(test())
    asyncio.run(embedding_client_manager.close())