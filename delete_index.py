from app.clients.es_client_manager import es_client_manager
import asyncio

async def delete():
    es_client_manager.init()
    client = es_client_manager.client
    if await client.indices.exists(index="value_index"):
        await client.indices.delete(index="value_index")
        print("✅ 已删除 value_index")
    else:
        print("value_index 不存在")
    await es_client_manager.close()

asyncio.run(delete())