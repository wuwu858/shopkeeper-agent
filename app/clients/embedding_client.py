import requests

from app.conf.app_config import app_config


def get_embedding(text: str) -> list:
    """
    调用 Embedding 服务，将文本转换为向量

    Args:
        text: 输入文本

    Returns:
        向量列表
    """
    url = f"http://{app_config.embedding.host}:{app_config.embedding.port}/embed"

    payload = {
        "inputs": text,
        "parameters": {
            "truncate": True
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result[0] if isinstance(result, list) else result
    except requests.exceptions.RequestException as e:
        raise Exception(f"Embedding 服务调用失败: {e}")


def get_embedding_batch(texts: list) -> list:
    """
    批量调用 Embedding 服务

    Args:
        texts: 文本列表

    Returns:
        向量列表
    """
    url = f"http://{app_config.embedding.host}:{app_config.embedding.port}/embed"

    payload = {
        "inputs": texts,
        "parameters": {
            "truncate": True
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Embedding 服务调用失败: {e}")


if __name__ == '__main__':
    # 测试连接
    try:
        # 测试单个文本
        test_text = "测试文本"
        vector = get_embedding(test_text)
        print(f"✅ Embedding 服务连接成功！")
        print(f"   测试文本: {test_text}")
        print(f"   向量维度: {len(vector)}")
    except Exception as e:
        print(f"❌ Embedding 服务连接失败: {e}")