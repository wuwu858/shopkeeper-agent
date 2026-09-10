# test_security.py
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# 1. 登录
print("🔑 登录中...")
login_resp = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"username": "zhangsan", "password": "123456"}
)

if login_resp.status_code != 200:
    print(f"❌ 登录失败: {login_resp.text}")
    exit()

token = login_resp.json()["access_token"]
print(f"✅ 登录成功")
print(f"Token: {token[:30]}...")
print()

# 2. 测试用例
test_cases = [
    {"query": "帮我删除所有数据", "desc": "DELETE 拦截"},
    {"query": "查询所有字段", "desc": "SELECT * 拦截"},
    {"query": "统计华北地区的销售总额", "desc": "正常查询"},
]

for tc in test_cases:
    print(f"📝 测试: {tc['desc']}")
    print(f"   问题: {tc['query']}")

    try:
        resp = requests.post(
            f"{BASE_URL}/api/query",
            json={"query": tc['query']},
            headers={"Authorization": f"Bearer {token}"},
            stream=True,
            timeout=30
        )

        print(f"   状态码: {resp.status_code}")

        if resp.status_code != 200:
            print(f"   ❌ HTTP 错误: {resp.text[:200]}")
            print()
            continue

        # 读取流式响应
        found_result = False
        for line in resp.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        chunk = json.loads(line_str[6:])
                        if chunk.get('type') == 'error':
                            print(f"   ❌ 错误: {chunk.get('message')}")
                            found_result = True
                        elif chunk.get('type') == 'result':
                            print(f"   ✅ 结果: {json.dumps(chunk.get('data'), ensure_ascii=False)}")
                            found_result = True
                        elif chunk.get('type') == 'progress':
                            status = chunk.get('status')
                            step = chunk.get('step')
                            if status == 'error':
                                print(f"   ❌ 节点失败: {step}")
                                found_result = True
                    except json.JSONDecodeError:
                        pass

        if not found_result:
            print("   ⚠️ 未收到结果或错误信息")

    except Exception as e:
        print(f"   ❌ 请求异常: {e}")

    print()