from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.conf.app_config import app_config


def get_db_engine(database: str = None):
    """
    创建数据库引擎

    Args:
        database: 数据库名称，如果不传则使用配置中的 database
    """
    config = app_config.db_meta if database is None else None

    # 如果指定了 database，使用 db_meta 的配置但替换 database
    if database:
        config = app_config.db_meta
        db_url = f"mysql+asyncmy://{config.user}:{config.password}@{config.host}:{config.port}/{database}?charset=utf8mb4"
    else:
        db_url = f"mysql+asyncmy://{config.user}:{config.password}@{config.host}:{config.port}/{config.database}?charset=utf8mb4"

    engine = create_engine(
        db_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    return engine


def get_db_session(database: str = None) -> Session:
    """获取数据库会话"""
    engine = get_db_engine(database)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


if __name__ == '__main__':
    # 测试连接
    try:
        session = get_db_session()
        print("✅ MySQL 连接成功！")
        session.close()
    except Exception as e:
        print(f"❌ MySQL 连接失败: {e}")