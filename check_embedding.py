from app.clients.embedding_client_manager import embedding_client_manager

embedding_client_manager.init()
client = embedding_client_manager.client

print(f"client 类型: {type(client)}")
print(f"client 属性: {dir(client)}")

if hasattr(client, "embed_query"):
    print("✅ 有 embed_query 方法")
elif hasattr(client, "aembed_query"):
    print("✅ 有 aembed_query 方法")
elif hasattr(client, "encode"):
    print("✅ 有 encode 方法")
else:
    print("❌ 没有找到 embedding 相关方法")