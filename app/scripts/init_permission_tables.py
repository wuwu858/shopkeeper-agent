# scripts/init_permission_tables.py

import asyncio
from sqlalchemy import text
from app.clients.mysql_client_manager import meta_mysql_client_manager


async def create_permission_tables():
    """创建权限相关的表"""
    meta_mysql_client_manager.init()

    async with meta_mysql_client_manager.session_factory() as session:
        # 1. 用户表
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS sys_user (
                id VARCHAR(50) PRIMARY KEY COMMENT '用户ID',
                username VARCHAR(100) UNIQUE NOT NULL COMMENT '用户名',
                password VARCHAR(255) NOT NULL COMMENT '密码(bcrypt加密)',
                role VARCHAR(50) DEFAULT 'viewer' COMMENT '角色: admin/sales/manager/viewer',
                department VARCHAR(100) COMMENT '部门',
                real_name VARCHAR(100) COMMENT '真实姓名',
                email VARCHAR(100) COMMENT '邮箱',
                is_active TINYINT DEFAULT 1 COMMENT '是否启用',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
            ) COMMENT='系统用户表'
        """))
        print("✅ 创建 sys_user 表")

        # 2. 地区权限表
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS user_region_perm (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id VARCHAR(50) NOT NULL COMMENT '用户ID',
                region VARCHAR(50) NOT NULL COMMENT '允许访问的地区',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE CASCADE,
                UNIQUE KEY uk_user_region (user_id, region)
            ) COMMENT='用户地区权限表'
        """))
        print("✅ 创建 user_region_perm 表")

        # 3. 敏感列配置表
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS column_deny_list (
                id INT PRIMARY KEY AUTO_INCREMENT,
                column_name VARCHAR(100) NOT NULL COMMENT '字段名',
                table_name VARCHAR(100) COMMENT '表名',
                description VARCHAR(255) COMMENT '说明',
                role_whitelist VARCHAR(255) COMMENT '允许查看的角色(逗号分隔)',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) COMMENT='敏感列配置表'
        """))
        print("✅ 创建 column_deny_list 表")

        # 4. 审计日志表
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS query_audit (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                user_id VARCHAR(50) NOT NULL COMMENT '用户ID',
                user_name VARCHAR(100) COMMENT '用户名',
                query_text TEXT NOT NULL COMMENT '用户原始问题',
                generated_sql TEXT COMMENT '生成的SQL',
                exec_status VARCHAR(20) COMMENT '执行状态',
                exec_time INT COMMENT '执行耗时(毫秒)',
                return_rows INT COMMENT '返回行数',
                llm_token INT COMMENT 'LLM Token消耗',
                err_msg TEXT COMMENT '错误信息',
                ip_address VARCHAR(50) COMMENT '客户端IP',
                user_agent VARCHAR(255) COMMENT 'User-Agent',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                INDEX idx_user_id (user_id),
                INDEX idx_created_at (created_at),
                INDEX idx_status (exec_status)
            ) COMMENT='查询审计日志表'
        """))
        print("✅ 创建 query_audit 表")

        # 5. 插入测试数据（✅ 使用 INSERT IGNORE）
        await session.execute(text("""
            INSERT IGNORE INTO sys_user (id, username, password, role, department, real_name) VALUES
            ('user_001', 'zhangsan', '$2b$12$CwTdS0N2P1hNYDqWhYvV7e5gVpQwR', 'sales', '销售部', '张三'),
            ('user_002', 'lisi', '$2b$12$CwTdS0N2P1hNYDqWhYvV7e5gVpQwR', 'manager', '销售部', '李四'),
            ('user_003', 'admin', '$2b$12$CwTdS0N2P1hNYDqWhYvV7e5gVpQwR', 'admin', '', '管理员'),
            ('user_004', 'wangwu', '$2b$12$CwTdS0N2P1hNYDqWhYvV7e5gVpQwR', 'viewer', '市场部', '王五')
        """))
        print("✅ 插入测试用户")

        await session.execute(text("""
            INSERT IGNORE INTO user_region_perm (user_id, region) VALUES
            ('user_001', '华北'),
            ('user_001', '华南'),
            ('user_002', '华北'),
            ('user_002', '华南'),
            ('user_002', '华东'),
            ('user_004', '华南')
        """))
        print("✅ 插入用户地区权限")

        await session.execute(text("""
            INSERT IGNORE INTO column_deny_list (column_name, table_name, description, role_whitelist) VALUES
            ('cost_price', 'fact_order', '成本价', 'admin,manager'),
            ('profit_margin', 'fact_order', '利润率', 'admin'),
            ('customer_phone', 'dim_customer', '客户电话', 'admin,manager')
        """))
        print("✅ 插入敏感列配置")

        await session.commit()
        print("\n🎉 所有权限表创建完成！")

    await meta_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(create_permission_tables())