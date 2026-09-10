# clear_qdrant.py
import asyncio
from app.clients.qdrant_client_manager import qdrant_client_manager

async def clear():
    qdrant_client_manager.init()
    client = qdrant_client_manager.client
    for name in ['column_info_collection', 'metric_info_collection']:
        if await client.collection_exists(name):
            await client.delete_collection(name)
            print(f'✅ 已删除 {name}')
    await qdrant_client_manager.close()

if __name__ == "__main__":
    asyncio.run(clear())