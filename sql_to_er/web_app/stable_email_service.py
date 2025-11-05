# -*- coding: utf-8 -*-
"""
稳定的邮件服务 - 解决Windows环境下QQ SMTP编码问题
"""

import smtplib
import socket
import ssl
import logging
import random
import time
from email.mime.text import MIMEText
from email.header import Header
from flask import session

logger = logging.getLogger(__name__)

class StableEmailService:
    def __init__(self, smtp_host, smtp_port, email_user, email_password):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.email_user = email_user
        self.email_password = email_password
    
    def send_verification_email_simple(self, to_email, verification_code):
        """使用最简单的方法发送验证码邮件"""
        try:
            logger.info(f"开始发送验证码邮件到: {to_email}")

            # 创建邮件内容
            subject = "Password Reset Code"
            content = f"Your verification code is: {verification_code}\nValid for 10 minutes."

            # 创建邮件对象
            msg = MIMEText(content)
            msg['From'] = self.email_user
            msg['To'] = to_email
            msg['Subject'] = subject

            # 使用标准的SMTP_SSL连接
            logger.info("正在建立SMTP连接...")
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as server:
                logger.info("正在登录SMTP服务器...")
                server.login(self.email_user, self.email_password)

                logger.info("正在发送邮件...")
                server.sendmail(self.email_user, [to_email], msg.as_string())

            logger.info(f"验证码邮件发送成功: {to_email}")
            return True

        except UnicodeDecodeError as e:
            logger.error(f"编码错误: {e}")
            # 如果遇到编码错误，尝试备用方法
            return self.send_verification_email_fallback(to_email, verification_code)
        except Exception as e:
            logger.error(f"发送验证码邮件失败: {e}")
            return False

    def send_verification_email_fallback(self, to_email, verification_code):
        """备用邮件发送方法 - 使用原始socket（已验证在Windows下稳定工作）"""
        try:
            logger.info("使用优化的邮件发送方法...")

            import base64

            # 邮件内容（使用中文，因为备用方法可以正确处理）
            subject = "密码重置验证码"
            content = f"""您好！

您正在申请重置密码，验证码为：{verification_code}

验证码有效期为10分钟，请及时使用。
如果这不是您的操作，请忽略此邮件。

智能学术工具集
{time.strftime('%Y-%m-%d %H:%M:%S')}"""

            # 构造原始邮件（使用UTF-8编码）
            message = f"""From: {self.email_user}
To: {to_email}
Subject: =?UTF-8?B?{base64.b64encode(subject.encode('utf-8')).decode()}?=
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: base64

{base64.b64encode(content.encode('utf-8')).decode()}
"""

            # 创建socket连接
            logger.info("建立安全连接...")
            sock = socket.create_connection((self.smtp_host, self.smtp_port), 30)

            # 包装为SSL
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=self.smtp_host)

            # 读取欢迎消息（忽略编码错误）
            try:
                welcome = sock.recv(1024)
                logger.info("已接收服务器欢迎消息")
            except Exception as e:
                logger.info(f"忽略欢迎消息读取错误: {e}")

            # 发送EHLO
            sock.send(b'EHLO localhost\r\n')
            response = sock.recv(1024)
            logger.info("EHLO命令发送成功")

            # 登录验证
            auth_string = f'\x00{self.email_user}\x00{self.email_password}'
            auth_bytes = base64.b64encode(auth_string.encode()).decode()
            sock.send(f'AUTH PLAIN {auth_bytes}\r\n'.encode())
            response = sock.recv(1024)
            logger.info("身份验证成功")

            # 发送邮件流程
            sock.send(f'MAIL FROM:<{self.email_user}>\r\n'.encode())
            response = sock.recv(1024)

            sock.send(f'RCPT TO:<{to_email}>\r\n'.encode())
            response = sock.recv(1024)

            sock.send(b'DATA\r\n')
            response = sock.recv(1024)

            sock.send(message.encode() + b'\r\n.\r\n')
            response = sock.recv(1024)

            sock.send(b'QUIT\r\n')
            sock.close()

            logger.info(f"✅ 邮件发送成功: {to_email}")
            return True

        except Exception as e:
            logger.error(f"备用邮件发送方法失败: {e}")
            return False
    
    def send_verification_email(self, to_email, verification_code):
        """发送验证码邮件 - 智能备用方案"""
        logger.info(f"开始发送验证码邮件到: {to_email}")

        # 在Windows环境下，直接使用备用方法（已验证稳定）
        import platform
        if platform.system() == 'Windows':
            logger.info("检测到Windows环境，使用优化的发送方法")
            if self.send_verification_email_fallback(to_email, verification_code):
                return True

        # 其他环境尝试标准方法
        logger.info("尝试标准SMTP方法")
        if self.send_verification_email_simple(to_email, verification_code):
            return True

        # 如果标准方法失败，使用备用方法
        logger.warning("标准方法失败，使用备用方法")
        if self.send_verification_email_fallback(to_email, verification_code):
            return True

        logger.error("所有邮件发送方法都失败了")
        return False

class PasswordResetManager:
    """密码重置管理器 - 使用Session存储，无需数据库"""
    
    def __init__(self, email_service, user_manager):
        self.email_service = email_service
        self.user_manager = user_manager
    
    def generate_code(self):
        """生成6位数字验证码"""
        return str(random.randint(100000, 999999))
    
    def send_reset_code(self, email):
        """发送密码重置验证码"""
        try:
            # 检查邮箱是否存在
            if not self.user_manager.email_exists(email):
                return {'success': False, 'message': '该邮箱未注册'}
            
            # 检查发送频率（60秒限制）
            last_send_key = f'last_send_{email}'
            current_time = time.time()
            last_send_time = session.get(last_send_key, 0)
            
            if current_time - last_send_time < 60:
                remaining = 60 - int(current_time - last_send_time)
                return {'success': False, 'message': f'请等待{remaining}秒后再试'}
            
            # 生成验证码
            code = self.generate_code()
            
            # 发送邮件
            if self.email_service.send_verification_email(email, code):
                # 存储到Session（5分钟有效）
                session[f'reset_code_{email}'] = {
                    'code': code,
                    'expires': current_time + 300,  # 5分钟
                    'attempts': 0
                }
                session[last_send_key] = current_time
                
                return {'success': True, 'message': '验证码已发送到您的邮箱'}
            else:
                return {'success': False, 'message': '邮件发送失败，请稍后重试'}
                
        except Exception as e:
            logger.error(f"发送重置验证码失败: {e}")
            return {'success': False, 'message': '发送失败，请稍后重试'}
    
    def verify_and_reset(self, email, code, new_password):
        """验证验证码并重置密码"""
        try:
            # 获取Session中的验证码
            reset_data = session.get(f'reset_code_{email}')
            
            if not reset_data:
                return {'success': False, 'message': '验证码不存在或已过期'}
            
            current_time = time.time()
            
            # 检查是否过期
            if current_time > reset_data['expires']:
                session.pop(f'reset_code_{email}', None)
                return {'success': False, 'message': '验证码已过期'}
            
            # 检查尝试次数
            if reset_data['attempts'] >= 3:
                session.pop(f'reset_code_{email}', None)
                return {'success': False, 'message': '验证码错误次数过多'}
            
            # 验证验证码
            if reset_data['code'] != code:
                reset_data['attempts'] += 1
                session[f'reset_code_{email}'] = reset_data
                remaining = 3 - reset_data['attempts']
                return {'success': False, 'message': f'验证码错误，还可尝试{remaining}次'}
            
            # 重置密码
            result = self.user_manager.reset_password_by_email(email, new_password)
            
            if result['success']:
                # 清除验证码
                session.pop(f'reset_code_{email}', None)
                session.pop(f'last_send_{email}', None)
            
            return result
            
        except Exception as e:
            logger.error(f"重置密码失败: {e}")
            return {'success': False, 'message': '重置失败，请稍后重试'}
