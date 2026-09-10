# app/core/auth.py

import os
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt, JWTError

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 天


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证 JWT token"""
    # ✅ 1. 检查 token 是否为空
    if not token:
        print("❌ Token 为空")
        return None

    # ✅ 2. 检查 token 格式（JWT 应该有 3 个部分，用 . 分隔）
    parts = token.split('.')
    if len(parts) != 3:
        print(f"❌ Token 格式错误: 有 {len(parts)} 个部分，期望 3 个")
        return None

    # ✅ 3. 尝试解码
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"✅ Token 验证成功: {payload.get('sub')}")
        return payload
    except JWTError as e:
        print(f"❌ Token 验证失败: {e}")
        return None


def get_user_id_from_token(token: str) -> Optional[str]:
    """从 token 中获取用户 ID"""
    payload = verify_token(token)
    if payload:
        return payload.get("sub")
    return None