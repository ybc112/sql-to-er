"""
登录安全模块 - 处理验证码和登录安全
"""

import random
import time
import hashlib
from flask import session
import logging
from captcha_generator import AdvancedCaptchaGenerator

logger = logging.getLogger(__name__)

class LoginSecurity:
    """登录安全管理器"""
    
    def __init__(self):
        # 登录失败限制配置
        self.MAX_ATTEMPTS = 5  # 最大尝试次数
        self.LOCKOUT_DURATION = 900  # 锁定时间（15分钟）
        self.CAPTCHA_THRESHOLD = 3  # 失败3次后需要验证码

        # 初始化高级验证码生成器
        self.captcha_generator = AdvancedCaptchaGenerator()
        
    def generate_captcha(self):
        """生成专业级图形验证码"""
        try:
            text, image_data = self.captcha_generator.generate_professional_captcha()
            return text, image_data
        except Exception as e:
            logger.error(f"生成图形验证码失败: {e}")
            # 降级到简单文本验证码
            text = str(random.randint(1000, 9999))
            return text, None

    def store_captcha(self, captcha_text):
        """存储验证码到session"""
        session['login_captcha'] = captcha_text
        session['captcha_time'] = time.time()
        logger.info(f"生成验证码: {captcha_text}")
    
    def verify_captcha(self, user_input):
        """验证验证码"""
        stored_captcha = session.get('login_captcha')
        captcha_time = session.get('captcha_time', 0)
        
        # 检查验证码是否过期（5分钟）
        if time.time() - captcha_time > 300:
            session.pop('login_captcha', None)
            session.pop('captcha_time', None)
            return False, "验证码已过期"
        
        if not stored_captcha:
            return False, "请先获取验证码"
        
        if str(user_input).strip() != str(stored_captcha):
            return False, "验证码错误"
        
        # 验证成功后清除验证码
        session.pop('login_captcha', None)
        session.pop('captcha_time', None)
        return True, "验证码正确"
    
    def get_login_attempts(self, username_or_email):
        """获取登录尝试次数"""
        key = f"login_attempts_{username_or_email}"
        attempts_data = session.get(key, {'count': 0, 'last_attempt': 0})
        return attempts_data
    
    def record_login_attempt(self, username_or_email, success=False):
        """记录登录尝试"""
        key = f"login_attempts_{username_or_email}"
        current_time = time.time()
        
        if success:
            # 登录成功，清除失败记录
            session.pop(key, None)
            session.pop(f"lockout_{username_or_email}", None)
            logger.info(f"用户 {username_or_email} 登录成功，清除失败记录")
        else:
            # 登录失败，增加计数
            attempts_data = self.get_login_attempts(username_or_email)
            attempts_data['count'] += 1
            attempts_data['last_attempt'] = current_time
            session[key] = attempts_data
            
            # 如果达到最大尝试次数，设置锁定
            if attempts_data['count'] >= self.MAX_ATTEMPTS:
                session[f"lockout_{username_or_email}"] = current_time + self.LOCKOUT_DURATION
                logger.warning(f"用户 {username_or_email} 登录失败次数过多，账户被锁定")
    
    def is_account_locked(self, username_or_email):
        """检查账户是否被锁定"""
        lockout_key = f"lockout_{username_or_email}"
        lockout_time = session.get(lockout_key, 0)
        
        if lockout_time > time.time():
            remaining = int(lockout_time - time.time())
            minutes = remaining // 60
            seconds = remaining % 60
            return True, f"账户已被锁定，请在{minutes}分{seconds}秒后重试"
        
        # 锁定时间已过，清除锁定状态
        if lockout_time > 0:
            session.pop(lockout_key, None)
        
        return False, ""
    
    def need_captcha(self, username_or_email=None):
        """判断是否需要验证码 - 始终需要验证码"""
        return True  # 始终需要验证码
    
    def get_remaining_attempts(self, username_or_email):
        """获取剩余尝试次数"""
        attempts_data = self.get_login_attempts(username_or_email)
        return max(0, self.MAX_ATTEMPTS - attempts_data['count'])
    
    def hash_password(self, password):
        """简单的密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password, password_hash):
        """验证密码"""
        return hashlib.sha256(password.encode()).hexdigest() == password_hash
    
    def validate_password_strength(self, password):
        """验证密码强度"""
        if len(password) < 6:
            return {'valid': False, 'message': '密码长度至少6位'}
        if len(password) > 50:
            return {'valid': False, 'message': '密码长度不能超过50位'}
        return {'valid': True, 'message': '密码强度合格'}
