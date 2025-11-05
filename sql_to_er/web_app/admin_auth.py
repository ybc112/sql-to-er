"""
管理员认证模块
处理管理员登录、权限验证等功能
"""

import bcrypt
from flask import session, request, jsonify, redirect, url_for
from functools import wraps
import pymysql
import logging

logger = logging.getLogger(__name__)

class AdminAuth:
    def __init__(self, db_config):
        self.db_config = db_config
        # 默认管理员账号（首次使用时创建）
        self.default_admin = {
            'username': 'admin',
            'password': 'admin123456'  # 请立即修改此密码
        }
    
    def get_db_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.db_config['host'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            database=self.db_config['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def init_admin_table(self):
        """初始化管理员相关表"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 为users表添加role字段（如果不存在）
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'users' 
                    AND COLUMN_NAME = 'role'
                """, (self.db_config['database'],))
                
                if cursor.fetchone()['count'] == 0:
                    logger.info("Adding role column to users table...")
                    cursor.execute("""
                        ALTER TABLE users 
                        ADD COLUMN role VARCHAR(20) DEFAULT 'user' 
                        COMMENT '用户角色：user/admin'
                    """)
                    conn.commit()
                    logger.info("Successfully added role column to users table")
                else:
                    logger.info("Role column already exists in users table")
                
                # 检查是否已有管理员账号
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
                admin_count = cursor.fetchone()['count']
                logger.info(f"Found {admin_count} admin accounts in database")
                
                if admin_count == 0:
                    # 创建默认管理员账号
                    logger.info(f"Creating default admin account with username: {self.default_admin['username']}")
                    password_hash = bcrypt.hashpw(
                        self.default_admin['password'].encode('utf-8'), 
                        bcrypt.gensalt()
                    ).decode('utf-8')
                    
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, balance, invite_code, role, status)
                        VALUES (%s, %s, 0.00, 'ADMIN001', 'admin', 1)
                    """, (self.default_admin['username'], password_hash))
                    conn.commit()
                    logger.info(f"Successfully created default admin account: {self.default_admin['username']}")
                    print(f"\n=== 管理员账号已创建 ===")
                    print(f"用户名: {self.default_admin['username']}")
                    print(f"密码: {self.default_admin['password']}")
                    print(f"请立即登录并修改密码！\n")
                else:
                    logger.info("Admin account already exists, skipping creation")
                    
        except Exception as e:
            logger.error(f"初始化管理员表失败: {e}")
            print(f"错误：初始化管理员失败 - {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def verify_admin(self, username, password):
        """验证管理员账号"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 查询管理员用户
                cursor.execute("""
                    SELECT id, username, password_hash, status
                    FROM users 
                    WHERE username = %s AND role = 'admin'
                """, (username,))
                
                admin = cursor.fetchone()
                if not admin:
                    return False, "管理员账号不存在"
                
                if admin['status'] != 1:
                    return False, "管理员账号已被禁用"
                
                # 验证密码
                if bcrypt.checkpw(password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
                    # 更新最后登录时间
                    cursor.execute("""
                        UPDATE users 
                        SET last_login_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """, (admin['id'],))
                    conn.commit()
                    
                    # 设置session
                    session['admin_id'] = admin['id']
                    session['admin_username'] = admin['username']
                    session['is_admin'] = True
                    
                    return True, "登录成功"
                else:
                    return False, "密码错误"
                    
        except Exception as e:
            logger.error(f"验证管理员失败: {e}")
            return False, "系统错误"
        finally:
            if conn:
                conn.close()
    
    def logout(self):
        """管理员登出"""
        session.pop('admin_id', None)
        session.pop('admin_username', None)
        session.pop('is_admin', None)
    
    def is_admin_logged_in(self):
        """检查是否已登录管理员"""
        return session.get('is_admin', False)
    
    def get_current_admin(self):
        """获取当前登录的管理员信息"""
        if not self.is_admin_logged_in():
            return None
        
        return {
            'id': session.get('admin_id'),
            'username': session.get('admin_username')
        }

# 管理员权限装饰器
def admin_required(f):
    """要求管理员权限的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin', False):
            if request.is_json:
                return jsonify({'success': False, 'message': '需要管理员权限'}), 403
            else:
                return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function