import asyncio
from app.clients.qdrant_client_manager import qdrant_client_manager


async def check():
    qdrant_client_manager.init()
    client = qdrant_client_manager.client

    result = await client.scroll(
        collection_name="column_info_collection",
        limit=20,
        with_payload=True,
        with_vectors=False
    )

    print("Qdrant 中的字段数据:")
    for point in result[0]:
        payload = point.payload
        print(f"  ID: {point.id}")
        print(f"  Payload: {payload}")
        print()

    await qdrant_client_manager.close()


if __name__ == "__main__":
    asyncio.run(check())