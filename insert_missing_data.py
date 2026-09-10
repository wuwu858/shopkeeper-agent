import asyncio
from app.clients.mysql_client_manager import meta_mysql_client_manager
from app.models.column_info import ColumnInfoMySQL
from app.models.table_info import TableInfoMySQL
from app.models.metric_info import MetricInfoMySQL
from app.models.column_metric import ColumnMetricMySQL
from sqlalchemy import text

async def insert_missing_data():
    meta_mysql_client_manager.init()
    
    async with meta_mysql_client_manager.session_factory() as session:
        # 1. 插入缺失的表
        tables = [
            TableInfoMySQL(
                id="fact_order",
                name="fact_order",
                role="fact",
                description="订单事实表"
            ),
        ]
        
        for table in tables:
            existing = await session.get(TableInfoMySQL, table.id)
            if existing:
                print(f"✅ 表已存在: {table.id}")
            else:
                session.add(table)
                print(f"➕ 添加表: {table.id}")
        
        # 2. 插入缺失的字段
        columns = [
            ColumnInfoMySQL(
                id="fact_order.order_amount",
                name="order_amount",
                type="decimal",
                role="measure",
                examples=[],
                description="订单金额",
                alias=["成交金额", "销售金额"],
                table_id="fact_order"
            ),
            ColumnInfoMySQL(
                id="fact_order.region_id",
                name="region_id",
                type="string",
                role="foreign_key",
                examples=[],
                description="地区ID（外键）",
                alias=[],
                table_id="fact_order"
            ),
            ColumnInfoMySQL(
                id="fact_order.order_id",
                name="order_id",
                type="string",
                role="primary_key",
                examples=[],
                description="订单ID",
                alias=[],
                table_id="fact_order"
            ),
            ColumnInfoMySQL(
                id="dim_region.region_id",
                name="region_id",
                type="string",
                role="primary_key",
                examples=[],
                description="地区ID",
                alias=[],
                table_id="dim_region"
            ),
        ]
        
        for column in columns:
            existing = await session.get(ColumnInfoMySQL, column.id)
            if existing:
                print(f"✅ 字段已存在: {column.id}")
            else:
                session.add(column)
                print(f"➕ 添加字段: {column.id}")
        
        # 3. 插入指标-字段关联（修复版本）
        # 先检查 column_metric 表结构
        try:
            result = await session.execute(text("DESCRIBE column_metric"))
            columns_info = result.fetchall()
            print("\n📋 column_metric 表结构:")
            for col in columns_info:
                print(f"  {col}")
        except Exception as e:
            print(f"无法获取表结构: {e}")
        
        # 插入关联数据
        try:
            # 检查是否已存在
            check_result = await session.execute(
                text("SELECT * FROM column_metric WHERE metric_id = :metric_id AND column_id = :column_id"),
                {"metric_id": "GMV", "column_id": "fact_order.order_amount"}
            )
            existing_assoc = check_result.fetchone()
            
            if existing_assoc:
                print(f"✅ 指标-字段关联已存在: GMV -> fact_order.order_amount")
            else:
                # 使用正确的字段名插入
                # 根据你的模型，可能字段名是 metric_id 和 column_id，或者其他的
                # 这里尝试两种方式
                try:
                    # 方式1: 使用模型
                    column_metric = ColumnMetricMySQL(
                        metric_id="GMV",
                        column_id="fact_order.order_amount"
                    )
                    session.add(column_metric)
                    print(f"➕ 添加指标-字段关联: GMV -> fact_order.order_amount")
                except TypeError as e:
                    print(f"模型插入失败: {e}")
                    # 方式2: 使用原生 SQL
                    await session.execute(
                        text("INSERT INTO column_metric (metric_id, column_id) VALUES (:metric_id, :column_id)"),
                        {"metric_id": "GMV", "column_id": "fact_order.order_amount"}
                    )
                    print(f"➕ 使用 SQL 添加指标-字段关联: GMV -> fact_order.order_amount")
        except Exception as e:
            print(f"插入关联失败: {e}")
        
        await session.commit()
        print("\n🎉 数据补充完成！")
    
    await meta_mysql_client_manager.close()

if __name__ == "__main__":
    asyncio.run(insert_missing_data())