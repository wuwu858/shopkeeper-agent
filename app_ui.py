# app_ui.py
import streamlit as st
import requests
import json
import time

# ========== 页面配置 ==========
st.set_page_config(
    page_title="智能问数助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 初始化 session 状态 ==========
if "history" not in st.session_state:
    st.session_state["history"] = []  # 显示用
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []  # 传给后端用

# ========== 侧边栏：登录 ==========
with st.sidebar:
    st.title("🔐 登录")

    with st.form("login_form"):
        username = st.text_input("用户名", value="zhangsan")
        password = st.text_input("密码", value="123456", type="password")
        submit_login = st.form_submit_button("登录")

    if submit_login:
        try:
            response = requests.post(
                "http://localhost:8000/api/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                st.session_state["token"] = data["access_token"]
                st.session_state["username"] = data["username"]
                st.session_state["regions"] = data["regions"]
                st.session_state["role"] = data["role"]
                st.success(f"✅ 登录成功！欢迎 {username}")
                st.rerun()
            else:
                st.error("❌ 登录失败，请检查用户名和密码")
        except Exception as e:
            st.error(f"❌ 连接失败: {e}")

    if "token" in st.session_state:
        st.success(f"👤 已登录: {st.session_state['username']}")
        st.info(f"📍 权限地区: {', '.join(st.session_state.get('regions', []))}")
        st.info(f"🎭 角色: {st.session_state.get('role', 'viewer')}")

        if st.button("🚪 退出登录"):
            for key in ["token", "username", "regions", "role"]:
                st.session_state.pop(key, None)
            st.session_state["history"] = []
            st.session_state["chat_history"] = []
            st.rerun()

# ========== 主界面 ==========
st.title("🤖 智能问数助手")

if "username" in st.session_state:
    st.markdown(f"### 👋 你好，{st.session_state['username']}！")
    st.markdown("💡 **试试以下问题：**")
    st.markdown("""
    - 华南地区的销售总额
    - 那华北呢？（追问，自动继承"销售总额"）
    - 哪个地区销量最多？（对比/排序追问）
    - 帮我按省份排序
    """)
else:
    st.markdown("### 👋 请先在左侧登录")
    st.stop()

# ========== 查询输入 ==========
col1, col2 = st.columns([4, 1])

with col1:
    query = st.text_input(
        "💬 输入你的问题：",
        placeholder="例如：华南地区的销售总额",
        key="query_input",
        label_visibility="collapsed"
    )

with col2:
    st.write("")
    submit = st.button("🚀 发送", type="primary", use_container_width=True)

# ========== 执行查询 ==========
if submit and query:
    if "token" not in st.session_state:
        st.error("❌ 请先登录")
    else:
        # ✅ 构建历史消息（传给后端）
        history_messages = []
        for msg in st.session_state["chat_history"]:
            if msg["type"] == "user":
                history_messages.append({"role": "user", "content": msg["content"]})
            elif msg["type"] == "assistant" and msg.get("sql"):
                history_messages.append({"role": "assistant", "content": msg["sql"]})

        # 添加到显示历史
        st.session_state["history"].append({"type": "user", "content": query})
        st.session_state["chat_history"].append({"type": "user", "content": query})

        with st.chat_message("assistant"):
            progress_placeholder = st.empty()
            sql_placeholder = st.empty()
            result_placeholder = st.empty()

            try:
                # ✅ 调用 API，带上历史记录
                response = requests.post(
                    "http://localhost:8000/api/query",
                    json={
                        "query": query,
                        "history": history_messages  # ✅ 关键：传递历史
                    },
                    headers={"Authorization": f"Bearer {st.session_state['token']}"},
                    stream=True
                )

                if response.status_code == 200:
                    sql = ""
                    result = None

                    for line in response.iter_lines():
                        if line:
                            try:
                                line_str = line.decode('utf-8')
                                if line_str.startswith("data: "):
                                    data = json.loads(line_str[6:])

                                    if data.get("type") == "progress":
                                        step = data.get("step", "")
                                        status = data.get("status", "")
                                        icon = "⏳" if status == "running" else "✅" if status == "success" else "❌"
                                        progress_placeholder.text(f"{icon} {step}...")

                                    if data.get("type") == "result":
                                        progress_placeholder.empty()
                                        sql_placeholder.code(sql, language="sql")
                                        result_placeholder.json(data.get("data", []))

                            except json.JSONDecodeError:
                                pass

                    # ✅ 保存到历史（包含 SQL）
                    st.session_state["history"].append({
                        "type": "assistant",
                        "content": sql,
                        "result": result
                    })
                    st.session_state["chat_history"].append({
                        "type": "assistant",
                        "sql": sql,
                        "result": result
                    })

                elif response.status_code == 429:
                    st.error("❌ 请求过于频繁，请稍后再试")
                elif response.status_code == 401:
                    st.error("❌ Token 已过期，请重新登录")
                    st.session_state.pop("token", None)
                else:
                    st.error(f"❌ 请求失败: {response.status_code}")

            except Exception as e:
                st.error(f"❌ 连接失败: {e}")

# ========== 显示历史对话 ==========
if st.session_state["history"]:
    st.divider()
    st.subheader("📋 对话历史")

    for msg in st.session_state["history"]:
        if msg["type"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            with st.chat_message("assistant"):
                if msg.get("content"):
                    st.code(msg["content"], language="sql")
                if msg.get("result"):
                    st.json(msg["result"])

# ========== 清除历史 ==========
if st.session_state["history"]:
    if st.button("🗑️ 清除历史"):
        st.session_state["history"] = []
        st.session_state["chat_history"] = []
        st.rerun()