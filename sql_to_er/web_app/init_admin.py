#!/usr/bin/env python3
"""
手动初始化管理员账号
"""

import pymysql
import bcrypt
import sys
import os

# 添加父目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'user_system',
    'charset': 'utf8mb4'
}

def init_admin():
    """初始化管理员账号"""
    try:
        # 连接数据库
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG['charset'],
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print("=== 管理员账号初始化工具 ===\n")
        
        with conn.cursor() as cursor:
            # 1. 检查并添加role字段
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME = 'role'
            """, (DB_CONFIG['database'],))
            
            if cursor.fetchone()['count'] == 0:
                print("⏳ 正在为users表添加role字段...")
                cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN role VARCHAR(20) DEFAULT 'user' 
                    COMMENT '用户角色：user/admin'
                """)
                conn.commit()
                print("✅ role字段添加成功")
            else:
                print("✅ role字段已存在")
            
            # 2. 检查是否已有管理员
            cursor.execute("SELECT username FROM users WHERE role = 'admin'")
            existing_admins = cursor.fetchall()
            
            if existing_admins:
                print(f"\n⚠️  已存在 {len(existing_admins)} 个管理员账号：")
                for admin in existing_admins:
                    print(f"   - {admin['username']}")
                
                response = input("\n是否继续创建新的管理员账号？(y/n): ").lower()
                if response != 'y':
                    print("已取消操作")
                    return
            
            # 3. 创建新管理员账号
            print("\n=== 创建新管理员账号 ===")
            
            # 输入用户名
            while True:
                username = input("请输入管理员用户名 (默认: admin): ").strip()
                if not username:
                    username = "admin"
                
                # 检查用户名是否已存在
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE username = %s", (username,))
                if cursor.fetchone()['count'] > 0:
                    print(f"❌ 用户名 '{username}' 已存在，请选择其他用户名")
                    continue
                break
            
            # 输入密码
            while True:
                password = input("请输入管理员密码 (默认: admin123456): ").strip()
                if not password:
                    password = "admin123456"
                
                if len(password) < 6:
                    print("❌ 密码长度至少需要6位")
                    continue
                    
                confirm = input("请再次输入密码确认: ").strip()
                if password != confirm:
                    print("❌ 两次输入的密码不一致")
                    continue
                break
            
            # 生成密码哈希
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # 生成邀请码
            invite_code = f"ADMIN{username.upper()[:3]}{len(existing_admins) + 1:03d}"
            
            # 插入管理员账号
            cursor.execute("""
                INSERT INTO users (username, password_hash, balance, invite_code, role, status)
                VALUES (%s, %s, 0.00, %s, 'admin', 1)
            """, (username, password_hash, invite_code))
            
            conn.commit()
            
            print("\n✅ 管理员账号创建成功！")
            print(f"=========================")
            print(f"用户名: {username}")
            print(f"密码: {password}")
            print(f"邀请码: {invite_code}")
            print(f"=========================")
            print(f"\n访问 http://localhost:5000/admin/login 进行登录")
            print(f"请妥善保管账号信息，并在首次登录后修改密码！")
            
    except pymysql.err.OperationalError as e:
        print(f"❌ 数据库连接失败：{e}")
        print("\n请检查：")
        print("1. MySQL服务是否已启动")
        print("2. 数据库 'user_system' 是否存在")
        print("3. 数据库用户名和密码是否正确")
    except Exception as e:
        print(f"❌ 发生错误：{e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    init_admin()