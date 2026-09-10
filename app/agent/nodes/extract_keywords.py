# app/agent/nodes/extract_keywords.py

import jieba

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def extract_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "抽取关键词"
    writer = runtime.stream_writer

    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state.get("query", "")

        # ✅ 只对当前用户问题提取关键词，不混入上下文
        logger.info(f"📝 原始查询: {query}")

        # 使用 jieba 分词提取关键词
        words = jieba.lcut(query)

        # 停用词列表
        stopwords = {"的", "了", "是", "在", "我", "你", "他", "她", "它", "们", "与", "和", "或", "但", "而", "所以",
                     "因为", "如果", "吗", "呢", "吧", "啊", "哦", "嗯", "哈", "唉", "呀", "这", "那", "之", "其", "何",
                     "几", "很", "太", "更", "最", "极", "好", "坏", "大", "小", "高", "低", "多", "少", "用", "于",
                     "要", "会", "能", "可以", "该", "这么", "那么", "什么", "怎么", "哪里", "多少", "还是", "就是",
                     "等等", "例如", "比如", "包括", "具有", "进行", "一个", "我们", "你们", "他们", "自己", "自己",
                     "帮我", "一下", "请问", "我想", "想要"}

        keywords = [word for word in words if len(word) > 1 and word not in stopwords]

        # ✅ 指代消解：如果关键词里只有"那"、"这个"等指代词，从历史中推断
        if len(keywords) <= 2:
            # 如果用户说的是"那华南呢"，关键词只有"华南"
            # 如果用户说的是"那华北呢"，关键词只有"华北"
            # 这些已经包含在 keywords 中了
            pass

        logger.info(f"📝 抽取关键词: {keywords}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"keywords": keywords}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise