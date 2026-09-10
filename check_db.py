import asyncio
from app.clients.mysql_client_manager import meta_mysql_client_manager
from sqlalchemy import text

async def check_db():
    meta_mysql_client_manager.init()
    
    async with meta_mysql_client_manager.session_factory() as session:
        # 查看 table_info 表
        result = await session.execute(text("SELECT * FROM table_info"))
        rows = result.fetchall()
        print(f"\n📊 table_info 表 ({len(rows)} 条记录):")
        for row in rows:
            print(f"  {row}")
        
        # 查看 column_info 表
        result = await session.execute(text("SELECT * FROM column_info"))
        rows = result.fetchall()
        print(f"\n📊 column_info 表 ({len(rows)} 条记录):")
        for row in rows:
            print(f"  {row}")
        
        # 查看 metric_info 表
        result = await session.execute(text("SELECT * FROM metric_info"))
        rows = result.fetchall()
        print(f"\n📊 metric_info 表 ({len(rows)} 条记录):")
        for row in rows:
            print(f"  {row}")
        
        # 查看 column_metric 表
        result = await session.execute(text("SELECT * FROM column_metric"))
        rows = result.fetchall()
        print(f"\n📊 column_metric 表 ({len(rows)} 条记录):")
        for row in rows:
            print(f"  {row}")
    
    await meta_mysql_client_manager.close()

if __name__ == "__main__":
    asyncio.run(check_db())