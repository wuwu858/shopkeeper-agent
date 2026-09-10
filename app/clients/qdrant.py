from qdrant_client import QdrantClient

from app.conf.app_config import app_config


def get_qdrant_client() -> QdrantClient:
    """获取 Qdrant 客户端"""
    client = QdrantClient(
        host=app_config.qdrant.host,
        port=app_config.qdrant.port,
        timeout=30,
    )
    return client


if __name__ == '__main__':
    # 测试连接
    try:
        client = get_qdrant_client()
        # 获取所有 collections
        collections = client.get_collections()
        print(f"✅ Qdrant 连接成功！")
        print(f"   现有 collections: {[c.name for c in collections.collections] if collections.collections else '无'}")
    except Exception as e:
        print(f"❌ Qdrant 连接失败: {e}")