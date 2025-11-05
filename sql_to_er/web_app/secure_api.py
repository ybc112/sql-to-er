"""
安全增强的API端点
包含增强的用户认证、注册、密码重置等功能
"""

from flask import Flask, request, jsonify, session, g
from security_middleware import SecurityMiddleware, csrf_protect, input_validator, SECURITY_CONFIG
from security_manager import SecurityManager
from user_manager import UserManager
import logging

logger = logging.getLogger(__name__)

def register_secure_api_routes(app: Flask, user_manager: UserManager, security_middleware: SecurityMiddleware):
    """注册安全增强的API路由"""
    
    @app.route('/api/csrf-token', methods=['GET'])
    def get_csrf_token():
        """获取CSRF令牌"""
        try:
            token = security_middleware.generate_csrf_token()
            return jsonify({'csrf_token': token})
        except Exception as e:
            logger.error(f"生成CSRF令牌失败: {e}")
            return jsonify({'error': '生成安全令牌失败'}), 500
    
    @app.route('/api/register', methods=['POST'])
    @security_middleware.rate_limit(SECURITY_CONFIG['rate_limits']['register'])
    @input_validator(
        username={'type': 'string', 'required': True, 'min_length': 3, 'max_length': 50, 'pattern': r'^[a-zA-Z0-9_]{3,50}$'},
        email={'type': 'email', 'required': True, 'max_length': 100},
        password={'type': 'string', 'required': True, 'min_length': 8, 'max_length': 200},
        confirm_password={'type': 'string', 'required': True},
        invite_code={'type': 'string', 'required': False, 'pattern': r'^[A-Z]{2}\d{6}$'}
    )
    def api_register():
        """增强的用户注册API"""
        try:
            data = request.get_json()
            
            # 验证密码确认
            if data['password'] != data['confirm_password']:
                return jsonify({'success': False, 'message': '两次输入的密码不一致'}), 400
            
            # 验证密码强度
            is_valid, error_msg, strength_score = user_manager.validate_password_strength(
                data['password'], data['username'], data['email']
            )
            if not is_valid:
                return jsonify({'success': False, 'message': error_msg}), 400
            
            # 检查密码强度分数
            if strength_score < 60:
                return jsonify({
                    'success': False, 
                    'message': f'密码强度不足（当前: {strength_score}/100），请使用更复杂的密码'
                }), 400
            
            # 清理输入数据
            clean_data = {
                'username': security_middleware.sanitize_input(data['username']),
                'email': security_middleware.sanitize_input(data['email']),
                'password': data['password'],  # 密码不需要清理
                'invite_code': security_middleware.sanitize_input(data.get('invite_code', '')) or None
            }
            
            # 注册用户
            result = user_manager.register_user(
                username=clean_data['username'],
                email=clean_data['email'],
                password=clean_data['password'],
                invite_code=clean_data['invite_code'],
                ip_address=g.client_ip,
                user_agent=g.user_agent
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"用户注册API失败: {e}")
            return jsonify({'success': False, 'message': '注册失败，请稍后重试'}), 500
    
    @app.route('/api/login', methods=['POST'])
    @security_middleware.rate_limit(SECURITY_CONFIG['rate_limits']['login'])
    @input_validator(
        username={'type': 'string', 'required': True, 'max_length': 100},
        password={'type': 'string', 'required': True, 'max_length': 200}
    )
    def api_login():
        """增强的用户登录API"""
        try:
            data = request.get_json()
            
            # 清理输入数据
            username_or_email = security_middleware.sanitize_input(data['username'])
            password = data['password']  # 密码不需要清理
            
            # 尝试登录
            result = user_manager.login_user(
                username_or_email, 
                password,
                ip_address=g.client_ip,
                user_agent=g.user_agent
            )
            
            if result['success']:
                # 设置会话
                session['user_id'] = result['user']['id']
                session['username'] = result['user']['username']
                session['session_id'] = result.get('session_id')
                
                # 生成新的CSRF令牌
                csrf_token = security_middleware.generate_csrf_token()
                
                return jsonify({
                    'success': True,
                    'message': '登录成功',
                    'user': result['user'],
                    'csrf_token': csrf_token
                })
            else:
                return jsonify(result), 401
                
        except Exception as e:
            logger.error(f"用户登录API失败: {e}")
            return jsonify({'success': False, 'message': '登录失败，请稍后重试'}), 500
    
    @app.route('/api/logout', methods=['POST'])
    @csrf_protect
    def api_logout():
        """安全退出登录"""
        try:
            user_id = session.get('user_id')
            session_id = session.get('session_id')
            
            # 记录安全事件
            if user_id:
                user_manager.security_manager.log_security_event(
                    user_id, 'user_logout', 
                    f'用户主动退出登录', 
                    g.client_ip, g.user_agent
                )
            
            # 清除会话
            session.clear()
            
            # 标记会话为无效（如果有session_id）
            if session_id:
                try:
                    conn = user_manager.get_db_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE user_sessions 
                            SET is_active = FALSE 
                            WHERE session_id = %s
                        """, (session_id,))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"标记会话无效失败: {e}")
            
            return jsonify({'success': True, 'message': '退出登录成功'})
            
        except Exception as e:
            logger.error(f"退出登录失败: {e}")
            return jsonify({'success': False, 'message': '退出登录失败'}), 500
    
    @app.route('/api/send-reset-code', methods=['POST'])
    @security_middleware.rate_limit(SECURITY_CONFIG['rate_limits']['reset_password'])
    @input_validator(
        email={'type': 'email', 'required': True, 'max_length': 100}
    )
    def api_send_reset_code():
        """发送密码重置验证码"""
        try:
            data = request.get_json()
            email = security_middleware.sanitize_input(data['email'])
            
            # 检查邮箱是否存在
            if not user_manager.email_exists(email):
                # 为了安全，不泄露邮箱是否存在的信息
                return jsonify({'success': True, 'message': '如果该邮箱已注册，验证码将发送至您的邮箱'})
            
            # 发送重置验证码
            from stable_email_service import PasswordResetManager
            reset_manager = PasswordResetManager(user_manager.email_service, user_manager)
            result = reset_manager.send_reset_code(email)
            
            # 记录安全事件
            user_manager.security_manager.log_security_event(
                None, 'password_reset_requested', 
                f'密码重置请求: {email}', 
                g.client_ip, g.user_agent
            )
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"发送重置验证码失败: {e}")
            return jsonify({'success': False, 'message': '发送失败，请稍后重试'}), 500
    
    @app.route('/api/reset-password', methods=['POST'])
    @security_middleware.rate_limit(SECURITY_CONFIG['rate_limits']['reset_password'])
    @input_validator(
        email={'type': 'email', 'required': True, 'max_length': 100},
        code={'type': 'string', 'required': True, 'min_length': 6, 'max_length': 6},
        new_password={'type': 'string', 'required': True, 'min_length': 8, 'max_length': 200}
    )
    def api_reset_password():
        """重置密码"""
        try:
            data = request.get_json()
            
            email = security_middleware.sanitize_input(data['email'])
            code = security_middleware.sanitize_input(data['code'])
            new_password = data['new_password']
            
            # 验证密码强度
            is_valid, error_msg, strength_score = user_manager.validate_password_strength(
                new_password, None, email
            )
            if not is_valid:
                return jsonify({'success': False, 'message': error_msg}), 400
            
            # 重置密码
            from stable_email_service import PasswordResetManager
            reset_manager = PasswordResetManager(user_manager.email_service, user_manager)
            result = reset_manager.verify_and_reset(email, code, new_password)
            
            if result['success']:
                # 记录安全事件
                user_manager.security_manager.log_security_event(
                    None, 'password_reset_success', 
                    f'密码重置成功: {email}', 
                    g.client_ip, g.user_agent
                )
            else:
                # 记录失败的重置尝试
                user_manager.security_manager.log_security_event(
                    None, 'password_reset_failed', 
                    f'密码重置失败: {email} - {result.get("message", "")}', 
                    g.client_ip, g.user_agent, 'medium'
                )
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"重置密码失败: {e}")
            return jsonify({'success': False, 'message': '重置失败，请稍后重试'}), 500
    
    @app.route('/api/password-strength', methods=['POST'])
    @security_middleware.rate_limit("20 per minute")
    @input_validator(
        password={'type': 'string', 'required': True, 'max_length': 200},
        username={'type': 'string', 'required': False, 'max_length': 50},
        email={'type': 'string', 'required': False, 'max_length': 100}
    )
    def api_password_strength():
        """检查密码强度"""
        try:
            data = request.get_json()
            
            password = data['password']
            username = data.get('username')
            email = data.get('email')
            
            is_valid, error_msg, strength_score = user_manager.validate_password_strength(
                password, username, email
            )
            
            # 确定强度等级
            if strength_score >= 80:
                level = 'strong'
                level_text = '强'
            elif strength_score >= 60:
                level = 'medium'
                level_text = '中等'
            else:
                level = 'weak'
                level_text = '弱'
            
            return jsonify({
                'success': True,
                'is_valid': is_valid,
                'error_message': error_msg,
                'strength_score': strength_score,
                'strength_level': level,
                'strength_text': level_text
            })
            
        except Exception as e:
            logger.error(f"检查密码强度失败: {e}")
            return jsonify({'success': False, 'message': '检查失败'}), 500

def init_security_system(app: Flask, user_manager: UserManager):
    """初始化安全系统"""
    
    # 创建安全中间件
    security_middleware = SecurityMiddleware(app, user_manager.security_manager)
    app.security_middleware = security_middleware
    
    # 注册安全API路由
    register_secure_api_routes(app, user_manager, security_middleware)
    
    # 启动定期清理任务
    import threading
    import time
    
    def cleanup_task():
        """定期清理过期数据"""
        while True:
            try:
                time.sleep(3600)  # 每小时执行一次
                user_manager.security_manager.cleanup_expired_data()
                logger.info("定期清理任务完成")
            except Exception as e:
                logger.error(f"定期清理任务失败: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()
    
    logger.info("安全系统初始化完成")
    
    return security_middleware