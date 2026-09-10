import asyncio
from app.clients.mysql_client_manager import dw_mysql_client_manager
from sqlalchemy import text

async def fix_region_id():
    dw_mysql_client_manager.init()
    
    async with dw_mysql_client_manager.session_factory() as session:
        # 1. 查看 dim_region 数据
        result = await session.execute(text("SELECT region_id, province FROM dim_region"))
        regions = result.fetchall()
        print("📋 dim_region 数据:")
        for row in regions:
            print(f"  region_id: {row[0]}, province: {row[1]}")
        
        # 2. 更新 fact_order 的 region_id
        # 将字符串 'REG001' 转换为数字 1，依此类推
        await session.execute(text("""
            UPDATE fact_order 
            SET region_id = CAST(SUBSTRING(region_id, 4) AS UNSIGNED)
            WHERE region_id LIKE 'REG%'
        """))
        await session.commit()
        print("✅ 已更新 region_id 为数字")
        
        # 3. 修改字段类型为 INT
        try:
            await session.execute(text("ALTER TABLE fact_order MODIFY COLUMN region_id INT NULL"))
            await session.commit()
            print("✅ 已修改 region_id 类型为 INT")
        except Exception as e:
            print(f"修改类型失败（可能已经是 INT）: {e}")
        
        # 4. 验证数据
        result = await session.execute(text("""
            SELECT fo.order_id, fo.order_amount, dr.province
            FROM fact_order fo 
            JOIN dim_region dr ON fo.region_id = dr.region_id
        """))
        rows = result.fetchall()
        print("\n📊 验证结果:")
        for row in rows:
            print(f"  {row}")
    
    await dw_mysql_client_manager.close()

if __name__ == "__main__":
    asyncio.run(fix_region_id())