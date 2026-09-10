# app/api/routers/auth_router.py

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth_schema import LoginRequest, LoginResponse, UserInfo
from app.api.dependencies import get_meta_session
from app.core.auth import create_access_token, verify_token
from app.core.security import verify_password

auth_router = APIRouter(prefix="/api/auth", tags=["认证"])
security = HTTPBearer(auto_error=False)


@auth_router.post("/login", response_model=LoginResponse)
async def login(
        request: LoginRequest,
        session: AsyncSession = Depends(get_meta_session),
):
    """用户登录接口"""
    # 1. 查询用户
    sql = """
        SELECT id, username, password, role, department, real_name
        FROM sys_user
        WHERE username = :username AND is_active = 1
    """
    result = await session.execute(text(sql), {"username": request.username})
    user = result.first()

    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 2. 验证密码
    if not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 3. 查询用户地区权限
    region_sql = """
        SELECT region FROM user_region_perm WHERE user_id = :user_id
    """
    region_result = await session.execute(text(region_sql), {"user_id": user.id})
    regions = [row[0] for row in region_result.fetchall()]

    # 4. 创建 JWT token
    token_data = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "department": user.department,
        "regions": regions,
    }
    access_token = create_access_token(token_data)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        role=user.role,
        department=user.department,
        regions=regions,
    )


@auth_router.get("/me", response_model=UserInfo)
async def get_current_user(
        session: AsyncSession = Depends(get_meta_session),
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
):
    """获取当前用户信息（需要鉴权）"""
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录")

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    user_id = payload.get("sub")

    # 查询用户信息
    sql = """
        SELECT id, username, role, department, real_name
        FROM sys_user
        WHERE id = :user_id AND is_active = 1
    """
    result = await session.execute(text(sql), {"user_id": user_id})
    user = result.first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 查询地区权限
    region_sql = """
        SELECT region FROM user_region_perm WHERE user_id = :user_id
    """
    region_result = await session.execute(text(region_sql), {"user_id": user_id})
    regions = [row[0] for row in region_result.fetchall()]

    return UserInfo(
        user_id=user.id,
        username=user.username,
        role=user.role,
        department=user.department,
        regions=regions,
    )