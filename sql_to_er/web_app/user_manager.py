"""
用户管理模块
包含用户注册、登录、额度管理、邀请码等功能
"""

import hashlib
import secrets
import string
import random
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, jsonify, redirect, url_for
import pymysql
import logging
from login_security import LoginSecurity

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self, db_config, email_service=None):
        """初始化用户管理器"""
        self.db_config = db_config
        self.email_service = email_service

        # 初始化登录安全管理器
        self.login_security = LoginSecurity()

    def get_db_connection(self):
        """获取数据库连接"""
        # 确保使用utf8mb4字符集处理中文字符
        connection_params = {
            'host': self.db_config['host'],
            'user': self.db_config['user'],
            'password': self.db_config['password'],
            'database': self.db_config['database'],
            'charset': 'utf8mb4',
            'use_unicode': True,
            'autocommit': False,
            'cursorclass': pymysql.cursors.DictCursor
        }

        return pymysql.connect(**connection_params)

    def hash_password(self, password):
        """密码哈希"""
        return self.login_security.hash_password(password)

    def verify_password(self, password, password_hash):
        """验证密码"""
        return self.login_security.verify_password(password, password_hash)

    def validate_password_strength(self, password):
        """验证密码强度"""
        return self.login_security.validate_password_strength(password)

    def is_valid_email(self, email):
        """验证邮箱格式"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def check_email_exists(self, email):
        """检查邮箱是否已注册"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"检查邮箱存在性失败: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def generate_invite_code(self):
        """生成邀请码"""
        while True:
            # 生成格式：2个大写字母 + 6位数字
            letters = ''.join(random.choices(string.ascii_uppercase, k=2))
            numbers = ''.join(random.choices(string.digits, k=6))
            code = letters + numbers

            # 检查是否已存在
            conn = None
            try:
                conn = self.get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM users WHERE invite_code = %s", (code,))
                    if not cursor.fetchone():
                        return code
            except Exception as e:
                logger.error(f"生成邀请码失败: {e}")
                return None
            finally:
                if conn:
                    conn.close()

    def register_user(self, username=None, email=None, password=None, invite_code=None):
        """用户注册 - 支持用户名或邮箱注册"""
        conn = None
        try:
            # 参数验证
            if not password:
                return {'success': False, 'message': '密码不能为空'}

            if not username and not email:
                return {'success': False, 'message': '请提供用户名或邮箱'}

            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 检查用户名是否已存在（如果提供了用户名）
                if username:
                    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                    if cursor.fetchone():
                        return {'success': False, 'message': '用户名已存在'}

                # 检查邮箱是否已存在（如果提供了邮箱）
                if email:
                    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                    if cursor.fetchone():
                        return {'success': False, 'message': '邮箱已被注册'}

                # 验证邀请码（如果提供）
                inviter_id = None
                if invite_code:
                    cursor.execute("SELECT id FROM users WHERE invite_code = %s", (invite_code,))
                    inviter = cursor.fetchone()
                    if not inviter:
                        return {'success': False, 'message': '邀请码无效'}
                    inviter_id = inviter['id']

                # 生成新用户的邀请码
                user_invite_code = self.generate_invite_code()

                # 创建用户
                password_hash = self.hash_password(password)
                new_user_bonus = self.get_system_config('new_user_bonus', 10.00)

                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, balance, invite_code, invited_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (username, email, password_hash, new_user_bonus, user_invite_code, invite_code))

                user_id = cursor.lastrowid

                # 如果有邀请人，给邀请人奖励
                if inviter_id:
                    invite_reward = self.get_system_config('invite_reward', 5.00)

                    # 更新邀请人余额
                    cursor.execute("""
                        UPDATE users SET
                            balance = balance + %s,
                            invite_earnings = invite_earnings + %s
                        WHERE id = %s
                    """, (invite_reward, invite_reward, inviter_id))

                    # 记录邀请记录
                    cursor.execute("""
                        INSERT INTO invite_records (inviter_id, invitee_id, invite_code, reward_amount)
                        VALUES (%s, %s, %s, %s)
                    """, (inviter_id, user_id, invite_code, invite_reward))

                conn.commit()

                return {
                    'success': True,
                    'message': '注册成功',
                    'user_id': user_id,
                    'invite_code': user_invite_code,
                    'bonus': new_user_bonus
                }

        except Exception as e:
            logger.error(f"用户注册失败: {e}")
            return {'success': False, 'message': '注册失败，请稍后重试'}
        finally:
            if conn:
                conn.close()

    def login_user(self, username_or_email, password, captcha=None):
        """用户登录（带安全检查和验证码）"""
        conn = None
        try:
            # 检查账户是否被锁定
            is_locked, lock_message = self.login_security.is_account_locked(username_or_email)
            if is_locked:
                return {'success': False, 'message': lock_message}

            # 始终需要验证码
            if not captcha:
                return {
                    'success': False,
                    'message': '请输入验证码',
                    'need_captcha': True
                }

            # 验证验证码
            captcha_valid, captcha_message = self.login_security.verify_captcha(captcha)
            if not captcha_valid:
                return {
                    'success': False,
                    'message': captcha_message,
                    'need_captcha': True
                }

            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 查询用户
                cursor.execute("""
                    SELECT id, username, email, password_hash, balance, invite_code, status, role
                    FROM users
                    WHERE username = %s OR email = %s
                """, (username_or_email, username_or_email))

                user = cursor.fetchone()

                # 验证密码
                if not user or not self.verify_password(password, user['password_hash']):
                    # 记录失败尝试
                    self.login_security.record_login_attempt(username_or_email, success=False)
                    remaining = self.login_security.get_remaining_attempts(username_or_email)

                    if remaining > 0:
                        message = f'用户名/邮箱或密码错误，还可尝试{remaining}次'
                    else:
                        message = '用户名/邮箱或密码错误，账户已被锁定'

                    return {
                        'success': False,
                        'message': message,
                        'need_captcha': self.login_security.need_captcha(username_or_email)
                    }

                if user['status'] != 1:
                    return {'success': False, 'message': '账户已被禁用'}

                # 登录成功，记录成功尝试
                self.login_security.record_login_attempt(username_or_email, success=True)

                # 更新最后登录时间
                cursor.execute("""
                    UPDATE users SET last_login_at = NOW() WHERE id = %s
                """, (user['id'],))
                conn.commit()

                return {
                    'success': True,
                    'message': '登录成功',
                    'user': user
                }

        except Exception as e:
            logger.error(f"用户登录失败: {e}")
            return {'success': False, 'message': '登录失败，请稍后重试'}
        finally:
            if conn:
                conn.close()

    def get_user_info(self, user_id):
        """获取用户信息"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, balance, invite_code, total_recharge,
                           total_consumption, invite_earnings, created_at, last_login_at, role
                    FROM users WHERE id = %s
                """, (user_id,))

                user = cursor.fetchone()
                if user:
                    # 获取邀请统计
                    cursor.execute("""
                        SELECT COUNT(*) as invite_count, COALESCE(SUM(reward_amount), 0) as total_rewards
                        FROM invite_records WHERE inviter_id = %s
                    """, (user_id,))
                    invite_stats = cursor.fetchone()

                    user.update(invite_stats)

                return user

        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_system_config(self, key, default_value):
        """获取系统配置"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT config_value FROM system_config WHERE config_key = %s", (key,))
                result = cursor.fetchone()
                if result:
                    try:
                        # 尝试转换为数字
                        return float(result['config_value'])
                    except ValueError:
                        # 如果不是数字，返回字符串
                        return result['config_value']
                else:
                    return default_value
        except Exception as e:
            logger.error(f"获取系统配置失败: {e}")
            # 如果数据库查询失败，返回默认值
            config_map = {
                'new_user_bonus': 10.00,
                'invite_reward': 5.00,
                'sql_to_er_cost': 1.00,
                'doc_generation_cost': 2.00,
                'ai_test_case_cost': 3.00,
                'thesis_defense_cost': 5.00,
                'paper_structure_cost': 4.00
            }
            return config_map.get(key, default_value)
        finally:
            if conn:
                conn.close()



    def add_balance(self, user_id, amount, operator_id=None, description="", method="alipay", transaction_id=None, trade_order_id=None):
        """给用户增加余额 - 完善版"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 检查用户是否存在
                cursor.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    logger.error(f"用户不存在: {user_id}")
                    return False

                # 更新用户余额和累计充值
                cursor.execute("""
                    UPDATE users SET
                        balance = balance + %s,
                        total_recharge = total_recharge + %s
                    WHERE id = %s
                """, (amount, amount, user_id))

                # 插入充值记录（表已存在，不需要创建）
                cursor.execute("""
                    INSERT INTO recharge_records
                    (user_id, amount, payment_method, status, description, admin_id, trade_no, trade_order_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, amount, method, 'success', description, operator_id, transaction_id, trade_order_id))

                conn.commit()
                logger.info(f"用户 {user['username']} (ID:{user_id}) 充值成功: {amount}元")
                return True

        except Exception as e:
            logger.error(f"增加余额失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def get_recharge_records(self, user_id, limit=50):
        """获取用户充值记录"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT amount, method, status, description, created_at, transaction_id, trade_order_id
                    FROM recharge_records
                    WHERE user_id = %s AND status = 'success'
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, limit))

                return cursor.fetchall()

        except Exception as e:
            logger.error(f"获取充值记录失败: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def consume_balance(self, user_id, amount, service_type, description=""):
        """扣除用户余额"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 检查余额是否足够
                cursor.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if not user or user['balance'] < amount:
                    return {'success': False, 'message': '余额不足'}

                # 扣除余额
                cursor.execute("""
                    UPDATE users SET
                        balance = balance - %s,
                        total_consumption = total_consumption + %s
                    WHERE id = %s
                """, (amount, amount, user_id))

                # 记录消费记录
                cursor.execute("""
                    INSERT INTO consumption_records (user_id, amount, service_type, description)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, amount, service_type, description))

                conn.commit()
                return {'success': True, 'message': '扣费成功'}

        except Exception as e:
            logger.error(f"扣除余额失败: {e}")
            return {'success': False, 'message': '扣费失败'}
        finally:
            if conn:
                conn.close()

    def get_consumption_records(self, user_id, limit=50):
        """获取用户消费记录"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT amount, service_type, description, created_at
                    FROM consumption_records
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, limit))

                return cursor.fetchall()

        except Exception as e:
            logger.error(f"获取消费记录失败: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def save_defense_question_history(self, user_id, session_id, generation_mode, thesis_data, questions_data, generation_time=0):
        """保存答辩问题历史记录"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 从thesis_data中提取字段
                thesis_title = thesis_data.get('thesisTitle', '')
                research_field = thesis_data.get('researchField', '')
                thesis_abstract = thesis_data.get('thesisAbstract', '')
                system_name = thesis_data.get('systemName', '')
                tech_stack = thesis_data.get('techStack', '')
                system_description = thesis_data.get('systemDescription', '')
                thesis_fragment = thesis_data.get('fragment', '')
                fragment_context = thesis_data.get('context', '')
                question_count = len(questions_data) if isinstance(questions_data, list) else 0
                difficulty_level = thesis_data.get('difficultyLevel', 'intermediate')
                category = thesis_data.get('category', '')

                cursor.execute("""
                    INSERT INTO defense_question_history
                    (user_id, session_id, generation_mode, thesis_title, research_field,
                     thesis_abstract, system_name, tech_stack, system_description,
                     thesis_fragment, fragment_context, question_count, difficulty_level,
                     category, questions_data, generation_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, session_id, generation_mode, thesis_title, research_field,
                      thesis_abstract, system_name, tech_stack, system_description,
                      thesis_fragment, fragment_context, question_count, difficulty_level,
                      category, json.dumps(questions_data, ensure_ascii=False), generation_time))

                conn.commit()
                return cursor.lastrowid

        except Exception as e:
            logger.error(f"保存答辩问题历史失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_defense_question_history(self, user_id, page=1, per_page=20):
        """获取答辩问题历史记录"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                offset = (page - 1) * per_page
                cursor.execute("""
                    SELECT id, thesis_title, research_field, generation_mode,
                           question_count, created_at
                    FROM defense_question_history
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (user_id, per_page, offset))

                records = cursor.fetchall()

                # 获取总数
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM defense_question_history
                    WHERE user_id = %s
                """, (user_id,))
                total = cursor.fetchone()['total']

                return {
                    'records': records,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page
                }

        except Exception as e:
            logger.error(f"获取答辩问题历史失败: {e}")
            return {'records': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0}
        finally:
            if conn:
                conn.close()

    def get_defense_question_detail(self, user_id, record_id):
        """获取答辩问题详情"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM defense_question_history
                    WHERE id = %s AND user_id = %s
                """, (record_id, user_id))

                return cursor.fetchone()

        except Exception as e:
            logger.error(f"获取答辩问题详情失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def delete_defense_question_history(self, user_id, record_id):
        """删除答辩问题历史记录"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM defense_question_history
                    WHERE id = %s AND user_id = %s
                """, (record_id, user_id))

                conn.commit()
                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"删除答辩问题历史失败: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def clear_defense_question_history(self, user_id):
        """清空用户所有答辩问题历史记录"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM defense_question_history
                    WHERE user_id = %s
                """, (user_id,))

                count = cursor.rowcount
                conn.commit()
                return count

        except Exception as e:
            logger.error(f"清空答辩问题历史失败: {e}")
            return 0
        finally:
            if conn:
                conn.close()

    def save_paper(self, user_id, title, field, paper_type, target_words, abstract, keywords, content, html_content):
        """保存论文到数据库"""
        conn = None
        try:
            conn = self.get_db_connection()

            # 首先确保papers表存在
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS papers (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT,
                        title VARCHAR(500) NOT NULL,
                        field VARCHAR(200),
                        paper_type VARCHAR(100),
                        target_words INT,
                        abstract TEXT,
                        keywords TEXT,
                        content JSON,
                        html_content LONGTEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        status VARCHAR(50) DEFAULT 'completed',
                        INDEX idx_user_id (user_id),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)

                # 插入论文数据
                cursor.execute("""
                    INSERT INTO papers (
                        user_id, title, field, paper_type, target_words,
                        abstract, keywords, content, html_content, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id, title, field, paper_type, target_words,
                    abstract, keywords,
                    json.dumps(content, ensure_ascii=False) if content else None,
                    html_content, 'completed'
                ))

                paper_id = cursor.lastrowid
                conn.commit()

                logger.info(f"论文保存成功 - ID: {paper_id}, 用户: {user_id}, 标题: {title}")
                return paper_id

        except Exception as e:
            logger.error(f"保存论文失败: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def get_user_papers(self, user_id, page=1, per_page=20):
        """获取用户的论文列表"""
        conn = None
        try:
            conn = self.get_db_connection()

            with conn.cursor() as cursor:
                # 获取总数
                cursor.execute("SELECT COUNT(*) as total FROM papers WHERE user_id = %s", (user_id,))
                total = cursor.fetchone()['total']

                # 获取分页数据
                offset = (page - 1) * per_page
                cursor.execute("""
                    SELECT id, title, field, paper_type, target_words,
                           abstract, keywords, created_at, updated_at, status,
                           CHAR_LENGTH(html_content) as content_length
                    FROM papers
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (user_id, per_page, offset))

                papers = cursor.fetchall()

                return {
                    'papers': papers,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page
                }

        except Exception as e:
            logger.error(f"获取用户论文列表失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_paper_detail(self, user_id, paper_id):
        """获取论文详细内容"""
        conn = None
        try:
            conn = self.get_db_connection()

            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM papers
                    WHERE id = %s AND (user_id = %s OR user_id IS NULL)
                """, (paper_id, user_id))

                paper = cursor.fetchone()

                if paper and paper['content']:
                    try:
                        paper['content'] = json.loads(paper['content'])
                    except:
                        paper['content'] = {}

                return paper

        except Exception as e:
            logger.error(f"获取论文详情失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def email_exists(self, email):
        """检查邮箱是否存在"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"检查邮箱存在性失败: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def reset_password_by_email(self, email, new_password):
        """通过邮箱重置密码"""
        conn = None
        try:
            if len(new_password) < 6:
                return {'success': False, 'message': '密码长度不能少于6位'}

            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 先检查邮箱是否存在，并获取当前密码哈希
                logger.info(f"开始重置密码，邮箱: {email}")
                cursor.execute("SELECT id, email, password_hash FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()

                if not user:
                    logger.error(f"重置密码失败：邮箱不存在 - {email}")
                    return {'success': False, 'message': '邮箱不存在'}

                logger.info(f"找到用户: ID={user['id']}, Email={user['email']}")

                # 检查新密码是否与当前密码相同
                new_password_hash = self.hash_password(new_password)
                if new_password_hash == user['password_hash']:
                    logger.info(f"用户尝试设置相同密码: {email}")
                    return {'success': False, 'message': '新密码不能与当前密码相同，请设置一个不同的密码'}

                # 执行密码更新
                cursor.execute("""
                    UPDATE users SET password_hash = %s WHERE email = %s
                """, (new_password_hash, email))

                if cursor.rowcount == 0:
                    logger.error(f"UPDATE语句影响行数为0，邮箱: {email}")
                    return {'success': False, 'message': '密码更新失败'}

                conn.commit()
                logger.info(f"密码重置成功: {email}")
                return {'success': True, 'message': '密码重置成功'}

        except Exception as e:
            logger.error(f"重置密码失败: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': '重置失败，请稍后重试'}
        finally:
            if conn:
                conn.close()

    def get_user_detail(self, user_id):
        """获取用户详细信息（管理员功能）"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 获取用户基本信息
                cursor.execute("""
                    SELECT id, username, email, balance, total_recharge, total_consumption,
                           invite_earnings, status, role, created_at, last_login_at, last_login_ip,
                           invite_code, invited_by
                    FROM users WHERE id = %s
                """, (user_id,))

                user = cursor.fetchone()
                if not user:
                    return None

                return user

        except Exception as e:
            logger.error(f"获取用户详情失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_all_users(self, page=1, per_page=20, search_term=None, status_filter=None, role_filter=None):
        """获取所有用户列表（管理员功能）"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 构建查询条件
                where_conditions = []
                params = []

                if search_term:
                    where_conditions.append("(username LIKE %s OR email LIKE %s)")
                    params.extend([f"%{search_term}%", f"%{search_term}%"])

                if status_filter is not None:
                    where_conditions.append("status = %s")
                    params.append(status_filter)

                if role_filter:
                    where_conditions.append("role = %s")
                    params.append(role_filter)

                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

                # 获取总数
                cursor.execute(f"SELECT COUNT(*) as total FROM users WHERE {where_clause}", params)
                total = cursor.fetchone()['total']

                # 获取分页数据
                offset = (page - 1) * per_page
                cursor.execute(f"""
                    SELECT id, username, email, balance, total_recharge, total_consumption,
                           status, role, created_at, last_login_at
                    FROM users
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, params + [per_page, offset])

                users = cursor.fetchall()

                return {
                    'users': users,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page
                }

        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return {
                'users': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0
            }
        finally:
            if conn:
                conn.close()


    def get_user_detail(self, user_id):
        """获取用户详细信息（管理员功能）"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 获取用户基本信息
                cursor.execute("""
                    SELECT id, username, email, balance, total_recharge, total_consumption,
                           invite_earnings, status, role, created_at, last_login_at, last_login_ip,
                           invite_code, invited_by
                    FROM users WHERE id = %s
                """, (user_id,))

                user = cursor.fetchone()
                if not user:
                    return None

                # 获取邀请统计
                cursor.execute("""
                    SELECT COUNT(*) as invite_count, COALESCE(SUM(reward_amount), 0) as total_rewards
                    FROM invite_records WHERE inviter_id = %s
                """, (user_id,))
                invite_stats = cursor.fetchone()

                # 获取最近充值记录
                cursor.execute("""
                    SELECT * FROM recharge_records
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 10
                """, (user_id,))
                recent_recharges = cursor.fetchall()

                # 获取最近消费记录
                cursor.execute("""
                    SELECT * FROM consumption_records
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 10
                """, (user_id,))
                recent_consumptions = cursor.fetchall()

                user.update(invite_stats)
                user['recent_recharges'] = recent_recharges
                user['recent_consumptions'] = recent_consumptions

                return user

        except Exception as e:
            logger.error(f"获取用户详情失败: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def update_user_status(self, user_id, status, admin_id=None):
        """更新用户状态（管理员功能）"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 获取用户信息
                cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    return {'success': False, 'message': '用户不存在'}

                # 更新状态
                cursor.execute("UPDATE users SET status = %s WHERE id = %s", (status, user_id))

                if cursor.rowcount > 0:
                    conn.commit()
                    return {'success': True, 'message': '状态更新成功'}
                else:
                    return {'success': False, 'message': '更新失败'}

        except Exception as e:
            logger.error(f"更新用户状态失败: {e}")
            return {'success': False, 'message': '更新失败'}
        finally:
            if conn:
                conn.close()

    def get_all_users(self, page=1, per_page=20, search_term=None, status_filter=None, role_filter=None):
        """获取所有用户列表（管理员功能）"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 构建查询条件
                where_conditions = []
                params = []

                if search_term:
                    where_conditions.append("(username LIKE %s OR email LIKE %s)")
                    params.extend([f"%{search_term}%", f"%{search_term}%"])

                if status_filter is not None:
                    where_conditions.append("status = %s")
                    params.append(status_filter)

                if role_filter:
                    where_conditions.append("role = %s")
                    params.append(role_filter)

                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

                # 获取总数
                cursor.execute(f"SELECT COUNT(*) as total FROM users WHERE {where_clause}", params)
                total = cursor.fetchone()['total']

                # 获取分页数据
                offset = (page - 1) * per_page
                cursor.execute(f"""
                    SELECT id, username, email, balance, total_recharge, total_consumption,
                           status, role, created_at, last_login_at
                    FROM users
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, params + [per_page, offset])

                users = cursor.fetchall()

                return {
                    'users': users,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page
                }

        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return {
                'users': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0
            }
        finally:
            if conn:
                conn.close()

    # 新增：流程图存取
    def save_flowchart(self, user_id, title, diagram: dict):
        """保存流程图，未登录用户user_id可为空"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 创建表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS flowcharts (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NULL,
                        title VARCHAR(300) NOT NULL,
                        diagram JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_user_id (user_id),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                # 插入
                cursor.execute(
                    """
                    INSERT INTO flowcharts (user_id, title, diagram)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, title, json.dumps(diagram, ensure_ascii=False))
                )
                fc_id = cursor.lastrowid
                conn.commit()
                return fc_id
        except Exception as e:
            logger.error(f"保存流程图失败: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def get_user_flowcharts(self, user_id, page=1, per_page=20):
        """获取用户流程图列表，未登录返回空列表结构"""
        if not user_id:
            return {'flowcharts': [], 'total': 0, 'page': page, 'per_page': per_page, 'pages': 0}
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM flowcharts WHERE user_id = %s", (user_id,))
                total = cursor.fetchone()['total']
                offset = (page - 1) * per_page
                cursor.execute(
                    """
                    SELECT id, title, created_at, updated_at
                    FROM flowcharts
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, per_page, offset)
                )
                rows = cursor.fetchall()
                return {
                    'flowcharts': rows,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page
                }
        except Exception as e:
            logger.error(f"获取流程图列表失败: {e}")
            return {'flowcharts': [], 'total': 0, 'page': page, 'per_page': per_page, 'pages': 0}
        finally:
            if conn:
                conn.close()

    def get_flowchart_detail(self, user_id, flowchart_id: int):
        """获取流程图详情；如果传入user_id则必须归属该用户才返回"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                if user_id:
                    cursor.execute(
                        "SELECT id, user_id, title, diagram, created_at, updated_at FROM flowcharts WHERE id = %s AND user_id = %s",
                        (flowchart_id, user_id)
                    )
                else:
                    cursor.execute(
                        "SELECT id, user_id, title, diagram, created_at, updated_at FROM flowcharts WHERE id = %s",
                        (flowchart_id,)
                    )
                row = cursor.fetchone()
                if row and isinstance(row.get('diagram'), (str, bytes)):
                    try:
                        row['diagram'] = json.loads(row['diagram'])
                    except Exception:
                        pass
                return row
        except Exception as e:
            logger.error(f"获取流程图详情失败: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def update_user_status(self, user_id, status):
        """更新用户状态（管理员功能）"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users 
                    SET status = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = %s AND role = 'user'
                """, (status, user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"更新用户状态失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()


# 装饰器：检查用户登录状态
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'message': '请先登录'}), 401
            else:
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# 装饰器：检查用户登录状态
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'message': '请先登录'}), 401
            else:
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
