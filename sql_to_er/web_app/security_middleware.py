"""
安全中间件和工具函数
包含CSRF保护、频率限制、输入验证、安全头部等
"""

from flask import Flask, request, session, jsonify, g, render_template_string, redirect, url_for, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import time
import re
import html
import logging
from typing import Dict, Optional, Any, List
import hashlib
import secrets
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """安全中间件类"""
    
    def __init__(self, app: Flask, security_manager):
        self.app = app
        self.security_manager = security_manager
        
        # 初始化频率限制器
        self.limiter = Limiter(
            app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://"
        )
        
        # 输入验证配置
        self.INPUT_VALIDATION = {
            'max_length': {
                'username': 50,
                'email': 100,
                'password': 200,
                'general_text': 1000,
                'description': 5000
            },
            'patterns': {
                'username': r'^[a-zA-Z0-9_]{3,50}$',
                'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                'invite_code': r'^[A-Z]{2}\d{6}$'
            }
        }
        
        # XSS防护配置
        self.XSS_PATTERNS = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>',
            r'<embed[^>]*>.*?</embed>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'expression\s*\(',
            r'url\s*\(',
            r'@import'
        ]
        
        # 注册中间件
        self._register_middleware()
    
    def _register_middleware(self):
        """注册所有中间件"""
        
        @self.app.before_request
        def security_before_request():
            """请求前安全检查"""
            
            # 记录请求信息
            g.request_start_time = time.time()
            g.client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            g.user_agent = request.headers.get('User-Agent', '')
            
            # 验证会话安全性
            if 'user_id' in session and 'session_id' in session:
                session_data = self.security_manager.validate_session(
                    session['session_id'], g.client_ip, g.user_agent
                )
                if not session_data:
                    session.clear()
                    if request.is_json:
                        return jsonify({'success': False, 'message': '会话已过期，请重新登录'}), 401
            
            # CSRF检查（除了GET请求和登录注册）
            if request.method in ['POST', 'PUT', 'DELETE'] and request.endpoint not in ['api_login', 'api_register']:
                if not self._verify_csrf():
                    return jsonify({'success': False, 'message': 'CSRF验证失败'}), 403
        
        @self.app.after_request
        def security_after_request(response):
            """请求后安全处理"""
            
            # 添加安全头部
            self._add_security_headers(response)
            
            # 记录响应时间
            if hasattr(g, 'request_start_time'):
                response_time = time.time() - g.request_start_time
                if response_time > 5:  # 超过5秒的请求记录警告
                    logger.warning(f"慢请求: {request.endpoint} - {response_time:.2f}s")
            
            return response
    
    def _verify_csrf(self) -> bool:
        """验证CSRF令牌"""
        if 'user_id' not in session:
            return True  # 未登录用户不需要CSRF验证
        
        csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        session_token = session.get('csrf_token')
        
        if not csrf_token or not session_token:
            return False
        
        return self.security_manager.validate_csrf_token(csrf_token, session_token)
    
    def _add_security_headers(self, response):
        """添加安全HTTP头部"""
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.deepseek.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # 其他安全头部
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # HSTS (仅在HTTPS下)
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # 移除服务器信息
        response.headers.pop('Server', None)
    
    def generate_csrf_token(self) -> str:
        """生成并存储CSRF令牌"""
        token = self.security_manager.generate_csrf_token()
        session['csrf_token'] = token
        return token
    
    def rate_limit(self, limits: str):
        """频率限制装饰器"""
        def decorator(f):
            return self.limiter.limit(limits)(f)
        return decorator
    
    def validate_input(self, data: Dict[str, Any], rules: Dict[str, Dict]) -> tuple[bool, str]:
        """
        输入验证
        
        Args:
            data: 要验证的数据
            rules: 验证规则 {'field': {'type': 'string', 'required': True, 'max_length': 50}}
        
        Returns:
            (是否有效, 错误信息)
        """
        
        for field, rule in rules.items():
            value = data.get(field)
            
            # 必填检查
            if rule.get('required', False) and not value:
                return False, f"字段 {field} 是必填的"
            
            if value is None:
                continue
            
            # 类型检查
            field_type = rule.get('type', 'string')
            if field_type == 'string' and not isinstance(value, str):
                return False, f"字段 {field} 必须是字符串"
            elif field_type == 'int' and not isinstance(value, int):
                return False, f"字段 {field} 必须是整数"
            elif field_type == 'email':
                if not self._is_valid_email(value):
                    return False, f"字段 {field} 邮箱格式无效"
            
            # 长度检查
            if isinstance(value, str):
                max_length = rule.get('max_length', self.INPUT_VALIDATION['max_length'].get(field, 1000))
                if len(value) > max_length:
                    return False, f"字段 {field} 长度不能超过 {max_length} 字符"
                
                min_length = rule.get('min_length', 0)
                if len(value) < min_length:
                    return False, f"字段 {field} 长度不能少于 {min_length} 字符"
            
            # 正则表达式检查
            pattern = rule.get('pattern') or self.INPUT_VALIDATION['patterns'].get(field)
            if pattern and isinstance(value, str):
                if not re.match(pattern, value):
                    return False, f"字段 {field} 格式无效"
            
            # XSS检查
            if isinstance(value, str) and rule.get('xss_check', True):
                if self._contains_xss(value):
                    return False, f"字段 {field} 包含不安全内容"
        
        return True, ""
    
    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱格式"""
        pattern = self.INPUT_VALIDATION['patterns']['email']
        return bool(re.match(pattern, email))
    
    def _contains_xss(self, text: str) -> bool:
        """检查是否包含XSS内容"""
        text_lower = text.lower()
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                return True
        return False
    
    def sanitize_input(self, text: str) -> str:
        """清理输入内容"""
        if not isinstance(text, str):
            return text
        
        # HTML转义
        text = html.escape(text)
        
        # 移除危险字符
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        # 限制长度
        if len(text) > 10000:
            text = text[:10000]
        
        return text.strip()

def csrf_protect(f):
    """CSRF保护装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            session_token = session.get('csrf_token')
            
            if not csrf_token or not session_token or not secrets.compare_digest(csrf_token, session_token):
                return jsonify({'success': False, 'message': 'CSRF验证失败'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def secure_login_required(f):
    """增强的登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'session_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'message': '请先登录'}), 401
            else:
                return redirect(url_for('login'))
        
        # 验证会话有效性（这应该在before_request中已经验证过）
        return f(*args, **kwargs)
    return decorated_function



def input_validator(**validation_rules):
    """输入验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.is_json:
                data = request.get_json() or {}
            else:
                data = request.form.to_dict()
            
            # 获取安全中间件实例进行验证
            security_middleware = getattr(current_app, 'security_middleware', None)
            if security_middleware:
                is_valid, error_msg = security_middleware.validate_input(data, validation_rules)
                if not is_valid:
                    return jsonify({'success': False, 'message': error_msg}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class SecurityEventLogger:
    """安全事件记录器"""
    
    def __init__(self, security_manager):
        self.security_manager = security_manager
    
    def log_suspicious_activity(self, user_id: Optional[int], activity_type: str, 
                              description: str, severity: str = 'medium'):
        """记录可疑活动"""
        ip_address = getattr(g, 'client_ip', request.remote_addr)
        user_agent = getattr(g, 'user_agent', request.headers.get('User-Agent', ''))
        
        self.security_manager.log_security_event(
            user_id, activity_type, description, ip_address, user_agent, severity
        )
        
        # 高危事件立即记录到应用日志
        if severity in ['high', 'critical']:
            logger.warning(f"安全事件 [{severity}] - 用户: {user_id}, 类型: {activity_type}, IP: {ip_address}")

# 安全配置常量
SECURITY_CONFIG = {
    'session_timeout': 3600,  # 1小时
    'max_login_attempts': 5,
    'lockout_duration': 900,  # 15分钟
    'password_min_length': 8,
    'password_history_count': 5,
    'csrf_token_expiry': 3600,
    'rate_limits': {
        'login': "5 per minute",
        'register': "3 per minute", 
        'reset_password': "3 per 5 minutes",
        'api_general': "100 per hour"
    }
}