import asyncio
from app.clients.es_client_manager import es_client_manager

async def test():
    es_client_manager.init()
    client = es_client_manager.client
    
    # 尝试 term 查询
    resp = await client.search(
        index="value_index",
        query={
            "term": {
                "value": "广东省"
            }
        }
    )
    print(f"term 查询结果: {len(resp['hits']['hits'])} 条")
    
    # 尝试 match_phrase 查询
    resp2 = await client.search(
        index="value_index",
        query={
            "match_phrase": {
                "value": "广东省"
            }
        }
    )
    print(f"match_phrase 查询结果: {len(resp2['hits']['hits'])} 条")
    
    # 查看 ES 中实际存储的数据
    resp3 = await client.search(
        index="value_index",
        query={"match_all": {}},
        size=10
    )
    print("\nES 中存储的数据:")
    for hit in resp3['hits']['hits']:
        print(f"  value: {hit['_source']['value']}")
    
    await es_client_manager.close()

asyncio.run(test())