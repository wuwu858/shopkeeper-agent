# app/api/routers/dictionary_router.py
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List
import json
from app.core.dictionary_loader import dictionary_loader

router = APIRouter(prefix="/api/dictionary", tags=["字典管理"])

class MetricCreate(BaseModel):
    metric_name: str
    standard_name: str
    definition: str
    sql_template: str
    source_table: str
    source_column: str
    alias: Optional[List[str]] = []

class DimensionCreate(BaseModel):
    dimension_name: str
    dimension_type: str
    mapping_key: str
    mapping_values: List[str]
    alias: Optional[List[str]] = []

@router.get("/cache/status")
def cache_status(request: Request):
    """查看缓存状态"""
    return {
        "is_cached": bool(dictionary_loader._metrics),
        "loaded_at": dictionary_loader._loaded_at,
        "cache_ttl": dictionary_loader._cache_ttl,
        "metrics_count": len(dictionary_loader._metrics),
        "dimensions_count": len(dictionary_loader._dimensions),
        "region_mapping_count": len(dictionary_loader.get_region_mapping())
    }

@router.post("/cache/refresh")
async def refresh_cache(request: Request):
    """手动刷新字典缓存（需要 session）"""
    # 由于 reload 需要 session 参数，这里无法直接刷新
    # 提示用户通过重启服务或触发查询来刷新
    return {
        "message": "字典缓存刷新需要数据库 session，请通过查询触发自动加载，或重启服务",
        "hint": "发送任意查询请求即可触发字典加载",
        "current_status": cache_status(request)
    }

@router.get("/metrics")
def get_metrics(request: Request):
    """获取所有指标"""
    return dictionary_loader.get_metrics()

@router.get("/dimensions")
def get_dimensions(request: Request):
    """获取所有维度"""
    return dictionary_loader.get_dimensions()

@router.get("/region-mapping")
def get_region_mapping(request: Request):
    """获取地区映射"""
    return dictionary_loader.get_region_mapping()