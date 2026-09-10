# check_tables.py
import asyncio
from sqlalchemy import text
from app.clients.mysql_client_manager import meta_mysql_client_manager


async def check():
    meta_mysql_client_manager.init()
    async with meta_mysql_client_manager.session_factory() as session:
        # 查看所有表
        result = await session.execute(text('SHOW TABLES'))
        tables = [row[0] for row in result.fetchall()]
        print('📋 meta 数据库中的表:')
        for t in tables:
            print(f'  - {t}')

        # 检查字典表
        if 'metric_dict' in tables:
            print('\n✅ metric_dict 表存在')
        else:
            print('\n❌ metric_dict 表不存在')

        if 'dimension_dict' in tables:
            print('✅ dimension_dict 表存在')
        else:
            print('❌ dimension_dict 表不存在')

    await meta_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(check())