# scripts/fix_password.py
import asyncio
import bcrypt
from sqlalchemy import text
from app.clients.mysql_client_manager import meta_mysql_client_manager

async def fix():
    meta_mysql_client_manager.init()
    async with meta_mysql_client_manager.session_factory() as session:
        # 使用您生成的哈希值
        hashed = '$2b$12$W.p2z/eNlZq89MVR4GTSaeGxA4wV5pig12QIoYRQez2sudzHAa4E.'
        sql = 'UPDATE sys_user SET password = :hashed WHERE username IN ("zhangsan", "lisi", "admin", "wangwu")'
        await session.execute(text(sql), {'hashed': hashed})
        await session.commit()
        print('✅ 所有用户密码已更新为: 123456')
    await meta_mysql_client_manager.close()

if __name__ == "__main__":
    asyncio.run(fix())