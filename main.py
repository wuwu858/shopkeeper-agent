# main.py
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router
from app.api.routers.auth_router import auth_router
from app.api.routers.dictionary_router import router as dictionary_router
from app.api.health import router as health_router  # ✅ 新增
from app.core.context import request_id_ctx_var
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler

app = FastAPI(
    lifespan=lifespan,
    title="电商问数 API",
    description="智能数据问数系统 API",
    version="1.0.0",
)

# ===== 注册路由 =====
app.include_router(health_router)  # ✅ 新增
app.include_router(query_router)
app.include_router(auth_router)
app.include_router(dictionary_router)

# ===== 中间件（后添加的先执行） =====

# 1. 先添加限流中间件（最后执行）
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 2. 后添加鉴权中间件（先执行）
app.add_middleware(AuthMiddleware)


# 3. 添加 request_id 中间件
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """为每个请求生成唯一的 request_id"""
    request_id = str(uuid.uuid4())
    request_id_ctx_var.set(request_id)

    response = await call_next(request)
    return response