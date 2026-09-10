# app/middleware/auth.py

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.auth import verify_token

# 不需要鉴权的路径
PUBLIC_PATHS = {
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/auth/login",
    "/health",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """鉴权中间件"""

    async def dispatch(self, request: Request, call_next):
        # 检查是否在白名单中
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        # 获取 token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "未登录，请先登录"}
            )

        try:
            token = auth_header.replace("Bearer ", "")
            payload = verify_token(token)
            if not payload:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token 无效或已过期"}
                )

            # 将用户信息存入 request.state
            request.state.user_id = payload.get("sub")
            request.state.username = payload.get("username")
            request.state.role = payload.get("role")
            request.state.department = payload.get("department")
            request.state.regions = payload.get("regions", [])

            return await call_next(request)

        except Exception as e:
            return JSONResponse(
                status_code=401,
                content={"detail": f"鉴权失败: {str(e)}"}
            )