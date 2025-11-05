#!/usr/bin/env python3
"""
数据库初始化脚本
运行此脚本来创建用户系统数据库和表
"""

import pymysql
import sys
import os

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'charset': 'utf8mb4'
}

def create_database():
    """创建数据库"""
    try:
        # 连接MySQL服务器（不指定数据库）
        connection = pymysql.connect(**DB_CONFIG)
        
        with connection.cursor() as cursor:
            # 创建数据库
            cursor.execute("CREATE DATABASE IF NOT EXISTS user_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print("✓ 数据库 'user_system' 创建成功")
            
        connection.commit()
        connection.close()
        
    except Exception as e:
        print(f"✗ 创建数据库失败: {e}")
        return False
    
    return True

def execute_sql_file():
    """执行SQL文件创建表结构"""
    try:
        # 连接到user_system数据库
        config = DB_CONFIG.copy()
        config['database'] = 'user_system'
        connection = pymysql.connect(**config)
        
        # 读取SQL文件
        sql_file_path = os.path.join(os.path.dirname(__file__), 'user_system.sql')
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # 先切换到正确的数据库
        with connection.cursor() as cursor:
            cursor.execute("USE user_system")

        # 分割SQL语句（以分号分隔）
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

        with connection.cursor() as cursor:
            for i, statement in enumerate(sql_statements):
                if statement.strip() and not statement.upper().startswith(('CREATE DATABASE', 'USE ')):
                    try:
                        cursor.execute(statement)
                        print(f"✓ 执行SQL语句 {i+1}/{len(sql_statements)}")
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            print(f"✗ SQL语句执行失败: {statement[:50]}... - {e}")
                        else:
                            print(f"✓ 跳过已存在的对象: {statement[:50]}...")
        
        connection.commit()
        connection.close()
        print("✓ 数据库表结构创建成功")
        
    except Exception as e:
        print(f"✗ 执行SQL文件失败: {e}")
        return False
    
    return True

def create_test_user():
    """创建测试用户"""
    try:
        config = DB_CONFIG.copy()
        config['database'] = 'user_system'
        connection = pymysql.connect(**config)
        
        with connection.cursor() as cursor:
            # 检查是否已存在测试用户
            cursor.execute("SELECT id FROM users WHERE username = 'testuser'")
            if cursor.fetchone():
                print("✓ 测试用户 'testuser' 已存在")
                return True

            # 创建测试用户
            import hashlib
            import random
            import string

            password_hash = hashlib.sha256('123456'.encode()).hexdigest()
            invite_code = ''.join(random.choices(string.ascii_uppercase, k=2)) + ''.join(random.choices(string.digits, k=6))

            cursor.execute("""
                INSERT INTO users (username, password_hash, balance, invite_code)
                VALUES (%s, %s, %s, %s)
            """, ('testuser', password_hash, 100.00, invite_code))

            connection.commit()
            print(f"✓ 测试用户创建成功")
            print(f"  用户名: testuser")
            print(f"  密码: 123456")
            print(f"  初始余额: ¥100.00")
            print(f"  邀请码: {invite_code}")
        
        connection.close()
        
    except Exception as e:
        print(f"✗ 创建测试用户失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("用户系统数据库初始化")
    print("=" * 50)
    
    # 检查MySQL连接
    try:
        connection = pymysql.connect(**DB_CONFIG)
        connection.close()
        print("✓ MySQL连接正常")
    except Exception as e:
        print(f"✗ MySQL连接失败: {e}")
        print("请检查MySQL服务是否启动，以及配置信息是否正确")
        return
    
    # 创建数据库
    if not create_database():
        return
    
    # 创建表结构
    if not execute_sql_file():
        return
    
    # 创建测试用户
    if not create_test_user():
        return
    
    print("\n" + "=" * 50)
    print("数据库初始化完成！")
    print("=" * 50)
    print("\n可以使用以下测试账号登录：")
    print("用户名: testuser")
    print("密码: 123456")
    print("\n现在可以启动Web应用了：")
    print("cd ../web_app && python app.py")

if __name__ == "__main__":
    main()
