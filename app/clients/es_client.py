from elasticsearch import Elasticsearch

from app.conf.app_config import app_config


def get_es_client() -> Elasticsearch:
    """获取 Elasticsearch 客户端"""
    client = Elasticsearch(
        [f"http://{app_config.es.host}:{app_config.es.port}"],
        request_timeout=30,
        max_retries=3,
        retry_on_timeout=True,
    )
    return client


if __name__ == '__main__':
    # 测试连接
    try:
        client = get_es_client()
        info = client.info()
        print(f"✅ Elasticsearch 连接成功！")
        print(f"   版本: {info.get('version', {}).get('number', 'unknown')}")
        print(f"   集群: {info.get('cluster_name', 'unknown')}")
    except Exception as e:
        print(f"❌ Elasticsearch 连接失败: {e}")