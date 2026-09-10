# app/api/routers/query_router.py

from fastapi import APIRouter, Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.services.query_service import QueryService
from app.core.auth import verify_token
from app.middleware.rate_limit import limiter

query_router = APIRouter()
security = HTTPBearer()


@query_router.post("/api/query")
@limiter.limit("2/minute")  # ✅ 添加限流：每分钟最多10次
async def query_handler(
        request: Request,  # ✅ 添加 Request 参数（limiter 需要）
        query: QuerySchema,
        query_service: QueryService = Depends(get_query_service),
        credentials: HTTPAuthorizationCredentials = Security(security),
):
    """
    查询接口

    需要 Authorization Header:
    Bearer <your_token>

    限流: 每分钟最多 10 次请求
    """
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    # 用户信息
    username = payload.get("username")
    role = payload.get("role", "viewer")
    regions = payload.get("regions", [])

    print(f"👤 用户: {username} ({role}) - 权限地区: {regions}")

    history = query.history if hasattr(query, 'history') else []

    return StreamingResponse(
        query_service.query(query.query, history=history),
        media_type="text/event-stream",
    )