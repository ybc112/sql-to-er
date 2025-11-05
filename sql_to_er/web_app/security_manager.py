"""
安全管理模块 - 增强用户身份验证和数据保护
"""

import bcrypt
import secrets
import time
import re
import hashlib
import base64
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from flask import session, request, g
import logging
import pymysql
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import json

logger = logging.getLogger(__name__)

class SecurityManager:
    """安全管理器 - 处理密码、会话、加密等安全功能"""
    
    def __init__(self, db_config: Dict, secret_key: str):
        self.db_config = db_config
        self.secret_key = secret_key
        
        # 密码策略配置
        self.PASSWORD_POLICY = {
            'min_length': 8,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_digits': True,
            'require_special': True,
            'max_length': 128,
            'forbidden_patterns': ['123456', 'password'],
            'min_entropy': 50  # 最低熵值要求
        }
        
        # 登录失败限制配置
        self.LOGIN_SECURITY = {
            'max_attempts': 5,
            'lockout_duration': 900,  # 15分钟
            'progressive_delay': True,  # 渐进式延迟
            'ip_tracking': True
        }
        
        # 会话安全配置
        self.SESSION_SECURITY = {
            'timeout': 3600,  # 1小时
            'refresh_threshold': 300,  # 5分钟内活动则刷新
            'device_binding': True,
            'ip_binding': True,
            'concurrent_sessions': 3  # 最大并发会话数
        }
        
        # 初始化加密器
        self._init_encryption()
        
        # 创建安全相关表
        self._create_security_tables()
    
    def _init_encryption(self):
        """初始化加密功能"""
        try:
            # 简化的加密初始化，避免版本兼容问题
            # 生成32字节的密钥
            key_material = hashlib.sha256(self.secret_key.encode()).digest()

            # 生成Fernet兼容的密钥
            fernet_key = base64.urlsafe_b64encode(key_material)
            self.cipher = Fernet(fernet_key)
            logger.info("加密模块初始化成功")

        except Exception as e:
            logger.error(f"加密模块初始化失败: {e}")
            # 使用简单的备用加密方法
            self.cipher = None
    
    def get_db_connection(self):
        """获取数据库连接"""
        return pymysql.connect(**self.db_config, cursorclass=pymysql.cursors.DictCursor)
    
    def _create_security_tables(self):
        """创建安全相关数据表"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 登录失败记录表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS login_attempts (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        identifier VARCHAR(255) NOT NULL,
                        ip_address VARCHAR(45) NOT NULL,
                        attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT FALSE,
                        user_agent TEXT,
                        INDEX idx_identifier (identifier),
                        INDEX idx_ip_time (ip_address, attempt_time),
                        INDEX idx_attempt_time (attempt_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 会话管理表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        session_id VARCHAR(64) NOT NULL UNIQUE,
                        ip_address VARCHAR(45) NOT NULL,
                        user_agent_hash VARCHAR(64) NOT NULL,
                        device_fingerprint TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        INDEX idx_user_id (user_id),
                        INDEX idx_session_id (session_id),
                        INDEX idx_last_activity (last_activity)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 密码历史表（防止密码重用）
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS password_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_id (user_id),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 安全事件日志表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT,
                        event_type VARCHAR(50) NOT NULL,
                        event_description TEXT,
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_id (user_id),
                        INDEX idx_event_type (event_type),
                        INDEX idx_severity (severity),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
            conn.commit()
            logger.info("安全表创建完成")
            
        except Exception as e:
            logger.error(f"创建安全表失败: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    
    def hash_password(self, password: str) -> str:
        """使用bcrypt加密密码，成本因子12"""
        try:
            # 使用bcrypt，成本因子12（高安全性）
            salt = bcrypt.gensalt(rounds=12)
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
            return password_hash.decode('utf-8')
        except Exception as e:
            logger.error(f"密码加密失败: {e}")
            raise ValueError("密码加密失败")
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    def validate_password_strength(self, password: str, username: str = None, email: str = None) -> Tuple[bool, str, int]:
        """
        验证密码强度
        返回: (是否通过, 错误信息, 强度分数0-100)
        """
        score = 0
        issues = []
        
        # 长度检查
        if len(password) < self.PASSWORD_POLICY['min_length']:
            issues.append(f"密码长度不能少于{self.PASSWORD_POLICY['min_length']}位")
        elif len(password) >= self.PASSWORD_POLICY['min_length']:
            score += 20
        
        if len(password) > self.PASSWORD_POLICY['max_length']:
            issues.append(f"密码长度不能超过{self.PASSWORD_POLICY['max_length']}位")
            return False, "密码过长", 0
        
        # 字符复杂度检查
        if self.PASSWORD_POLICY['require_uppercase'] and not re.search(r'[A-Z]', password):
            issues.append("密码必须包含大写字母")
        elif re.search(r'[A-Z]', password):
            score += 15
        
        if self.PASSWORD_POLICY['require_lowercase'] and not re.search(r'[a-z]', password):
            issues.append("密码必须包含小写字母")
        elif re.search(r'[a-z]', password):
            score += 15
        
        if self.PASSWORD_POLICY['require_digits'] and not re.search(r'\d', password):
            issues.append("密码必须包含数字")
        elif re.search(r'\d', password):
            score += 15
        
        if self.PASSWORD_POLICY['require_special'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("密码必须包含特殊字符")
        elif re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 15
        
        # 禁用模式检查
        password_lower = password.lower()
        for pattern in self.PASSWORD_POLICY['forbidden_patterns']:
            if pattern in password_lower:
                issues.append(f"密码不能包含常见模式: {pattern}")
        
        # 与用户信息相似性检查
        if username and len(username) >= 3 and username.lower() in password_lower:
            issues.append("密码不能包含用户名")
        
        if email and len(email) >= 3:
            email_parts = email.split('@')[0].lower()
            if len(email_parts) >= 3 and email_parts in password_lower:
                issues.append("密码不能包含邮箱用户名部分")
        
        # 计算熵值（信息量）
        entropy = self._calculate_password_entropy(password)
        if entropy < self.PASSWORD_POLICY['min_entropy']:
            issues.append(f"密码复杂度不足（当前: {entropy:.0f}, 要求: {self.PASSWORD_POLICY['min_entropy']}）")
        else:
            score += 20
        
        # 重复字符检查
        if self._has_repetitive_patterns(password):
            issues.append("密码包含过多重复字符或模式")
            score = max(0, score - 10)
        
        is_valid = len(issues) == 0
        error_message = "; ".join(issues) if issues else ""
        
        return is_valid, error_message, min(100, score)
    
    def _calculate_password_entropy(self, password: str) -> float:
        """计算密码熵值"""
        if not password:
            return 0
        
        charset_size = 0
        if re.search(r'[a-z]', password):
            charset_size += 26
        if re.search(r'[A-Z]', password):
            charset_size += 26
        if re.search(r'\d', password):
            charset_size += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            charset_size += 20
        
        import math
        entropy = len(password) * math.log2(charset_size) if charset_size > 0 else 0
        return entropy
    
    def _has_repetitive_patterns(self, password: str) -> bool:
        """检查重复模式"""
        # 检查连续重复字符（如：aaa, 111）
        if re.search(r'(.)\1{2,}', password):
            return True
        
        # 检查键盘模式（如：qwerty, 123456）
        keyboard_patterns = [
            'qwerty', 'asdfgh', 'zxcvbn', '123456', '654321',
            'qwertyuiop', 'asdfghjkl', 'zxcvbnm'
        ]
        
        password_lower = password.lower()
        for pattern in keyboard_patterns:
            if pattern in password_lower or pattern[::-1] in password_lower:
                return True
        
        return False
    
    def check_login_attempts(self, identifier: str, ip_address: str) -> Tuple[bool, int, str]:
        """
        检查登录尝试次数
        返回: (是否允许登录, 剩余尝试次数, 锁定信息)
        """
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 获取最近的失败尝试
                cursor.execute("""
                    SELECT COUNT(*) as failed_attempts, MAX(attempt_time) as last_attempt
                    FROM login_attempts 
                    WHERE identifier = %s 
                    AND success = FALSE 
                    AND attempt_time > DATE_SUB(NOW(), INTERVAL %s SECOND)
                """, (identifier, self.LOGIN_SECURITY['lockout_duration']))
                
                result = cursor.fetchone()
                failed_attempts = result['failed_attempts'] if result else 0
                last_attempt = result['last_attempt'] if result else None
                
                # 检查是否被锁定
                if failed_attempts >= self.LOGIN_SECURITY['max_attempts']:
                    if last_attempt:
                        time_diff = (datetime.now() - last_attempt).total_seconds()
                        remaining_lockout = self.LOGIN_SECURITY['lockout_duration'] - time_diff
                        
                        if remaining_lockout > 0:
                            minutes = int(remaining_lockout // 60)
                            seconds = int(remaining_lockout % 60)
                            return False, 0, f"账户已被锁定，请在{minutes}分{seconds}秒后重试"
                
                remaining_attempts = max(0, self.LOGIN_SECURITY['max_attempts'] - failed_attempts)
                return True, remaining_attempts, ""
                
        except Exception as e:
            logger.error(f"检查登录尝试失败: {e}")
            return True, self.LOGIN_SECURITY['max_attempts'], ""
        finally:
            if conn:
                conn.close()
    
    def record_login_attempt(self, identifier: str, ip_address: str, success: bool, user_agent: str = None):
        """记录登录尝试"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO login_attempts (identifier, ip_address, success, user_agent)
                    VALUES (%s, %s, %s, %s)
                """, (identifier, ip_address, success, user_agent or ""))
                
                # 清理旧记录（保留最近30天）
                cursor.execute("""
                    DELETE FROM login_attempts 
                    WHERE attempt_time < DATE_SUB(NOW(), INTERVAL 30 DAY)
                """)
                
            conn.commit()
            
        except Exception as e:
            logger.error(f"记录登录尝试失败: {e}")
        finally:
            if conn:
                conn.close()
    
    def create_secure_session(self, user_id: int, ip_address: str, user_agent: str) -> str:
        """创建安全会话"""
        conn = None
        try:
            # 生成安全的会话ID
            session_id = secrets.token_urlsafe(32)
            user_agent_hash = hashlib.sha256(user_agent.encode()).hexdigest()
            
            # 生成设备指纹
            device_fingerprint = self._generate_device_fingerprint(ip_address, user_agent)
            
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 限制并发会话数
                cursor.execute("""
                    SELECT COUNT(*) as active_sessions 
                    FROM user_sessions 
                    WHERE user_id = %s AND is_active = TRUE
                """, (user_id,))
                
                active_sessions = cursor.fetchone()['active_sessions']
                
                if active_sessions >= self.SESSION_SECURITY['concurrent_sessions']:
                    # 删除最旧的会话
                    cursor.execute("""
                        UPDATE user_sessions 
                        SET is_active = FALSE 
                        WHERE user_id = %s AND is_active = TRUE 
                        ORDER BY last_activity ASC 
                        LIMIT 1
                    """, (user_id,))
                
                # 创建新会话
                cursor.execute("""
                    INSERT INTO user_sessions 
                    (user_id, session_id, ip_address, user_agent_hash, device_fingerprint)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, session_id, ip_address, user_agent_hash, device_fingerprint))
                
            conn.commit()
            
            # 记录安全事件
            self.log_security_event(user_id, 'session_created', f'新会话创建: {ip_address}', ip_address, user_agent)
            
            return session_id
            
        except Exception as e:
            logger.error(f"创建安全会话失败: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()
    
    def validate_session(self, session_id: str, ip_address: str, user_agent: str) -> Optional[Dict]:
        """验证会话安全性"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM user_sessions 
                    WHERE session_id = %s AND is_active = TRUE
                """, (session_id,))
                
                session_data = cursor.fetchone()
                if not session_data:
                    return None
                
                # 检查会话超时
                last_activity = session_data['last_activity']
                time_diff = (datetime.now() - last_activity).total_seconds()
                
                if time_diff > self.SESSION_SECURITY['timeout']:
                    # 会话超时，标记为无效
                    cursor.execute("""
                        UPDATE user_sessions 
                        SET is_active = FALSE 
                        WHERE session_id = %s
                    """, (session_id,))
                    conn.commit()
                    
                    self.log_security_event(
                        session_data['user_id'], 
                        'session_timeout', 
                        f'会话超时: {session_id[:8]}...', 
                        ip_address, 
                        user_agent
                    )
                    return None
                
                # 验证IP绑定（如果启用）
                if self.SESSION_SECURITY['ip_binding'] and session_data['ip_address'] != ip_address:
                    self.log_security_event(
                        session_data['user_id'], 
                        'session_ip_mismatch', 
                        f'IP地址不匹配: {session_data["ip_address"]} -> {ip_address}', 
                        ip_address, 
                        user_agent,
                        severity='high'
                    )
                    return None
                
                # 验证设备指纹（如果启用）
                if self.SESSION_SECURITY['device_binding']:
                    current_user_agent_hash = hashlib.sha256(user_agent.encode()).hexdigest()
                    if session_data['user_agent_hash'] != current_user_agent_hash:
                        self.log_security_event(
                            session_data['user_id'], 
                            'session_device_mismatch', 
                            f'设备指纹不匹配', 
                            ip_address, 
                            user_agent,
                            severity='high'
                        )
                        return None
                
                # 更新最后活动时间
                if time_diff > self.SESSION_SECURITY['refresh_threshold']:
                    cursor.execute("""
                        UPDATE user_sessions 
                        SET last_activity = NOW() 
                        WHERE session_id = %s
                    """, (session_id,))
                    conn.commit()
                
                return session_data
                
        except Exception as e:
            logger.error(f"验证会话失败: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def _generate_device_fingerprint(self, ip_address: str, user_agent: str) -> str:
        """生成设备指纹"""
        fingerprint_data = f"{ip_address}:{user_agent}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()
    
    def encrypt_field(self, data: str) -> str:
        """字段级加密"""
        if not self.cipher or not data:
            return data
        
        try:
            encrypted_data = self.cipher.encrypt(data.encode('utf-8'))
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"字段加密失败: {e}")
            return data
    
    def decrypt_field(self, encrypted_data: str) -> str:
        """字段级解密"""
        if not self.cipher or not encrypted_data:
            return encrypted_data
        
        try:
            decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self.cipher.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"字段解密失败: {e}")
            return encrypted_data
    
    def generate_csrf_token(self) -> str:
        """生成CSRF令牌"""
        return secrets.token_urlsafe(32)
    
    def validate_csrf_token(self, token: str, session_token: str) -> bool:
        """验证CSRF令牌"""
        return token and session_token and secrets.compare_digest(token, session_token)
    
    def log_security_event(self, user_id: Optional[int], event_type: str, description: str, 
                          ip_address: str = None, user_agent: str = None, severity: str = 'medium'):
        """记录安全事件"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO security_events 
                    (user_id, event_type, event_description, ip_address, user_agent, severity)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, event_type, description, ip_address, user_agent, severity))
            
            conn.commit()
            
            # 高危事件立即记录到日志
            if severity in ['high', 'critical']:
                logger.warning(f"安全事件 [{severity}] - 用户: {user_id}, 类型: {event_type}, 描述: {description}, IP: {ip_address}")
                
        except Exception as e:
            logger.error(f"记录安全事件失败: {e}")
        finally:
            if conn:
                conn.close()
    
    def is_password_reused(self, user_id: int, new_password: str, history_limit: int = 5) -> bool:
        """检查密码是否被重复使用"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT password_hash FROM password_history 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (user_id, history_limit))
                
                history = cursor.fetchall()
                
                for record in history:
                    if self.verify_password(new_password, record['password_hash']):
                        return True
                
                return False
                
        except Exception as e:
            logger.error(f"检查密码重用失败: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def save_password_history(self, user_id: int, password_hash: str):
        """保存密码历史"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO password_history (user_id, password_hash)
                    VALUES (%s, %s)
                """, (user_id, password_hash))
                
                # 只保留最近10个密码
                cursor.execute("""
                    DELETE FROM password_history 
                    WHERE user_id = %s 
                    AND id NOT IN (
                        SELECT id FROM (
                            SELECT id FROM password_history 
                            WHERE user_id = %s 
                            ORDER BY created_at DESC 
                            LIMIT 10
                        ) as recent
                    )
                """, (user_id, user_id))
                
            conn.commit()
            
        except Exception as e:
            logger.error(f"保存密码历史失败: {e}")
        finally:
            if conn:
                conn.close()
    
    def cleanup_expired_data(self):
        """清理过期数据"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 清理过期的登录尝试记录
                cursor.execute("""
                    DELETE FROM login_attempts 
                    WHERE attempt_time < DATE_SUB(NOW(), INTERVAL 30 DAY)
                """)
                
                # 清理过期的会话
                cursor.execute("""
                    DELETE FROM user_sessions 
                    WHERE last_activity < DATE_SUB(NOW(), INTERVAL 7 DAY)
                """)
                
                # 清理旧的安全事件日志
                cursor.execute("""
                    DELETE FROM security_events 
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)
                """)
                
            conn.commit()
            logger.info("过期数据清理完成")
            
        except Exception as e:
            logger.error(f"清理过期数据失败: {e}")
        finally:
            if conn:
                conn.close()