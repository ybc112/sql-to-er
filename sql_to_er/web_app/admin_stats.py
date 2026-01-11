"""
管理员统计数据模块
提供仪表盘所需的各种统计数据
"""

import pymysql
import logging
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

class AdminStats:
    def __init__(self, db_config):
        self.db_config = db_config
    
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
    
    def get_dashboard_stats(self):
        """获取仪表盘统计数据"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                stats = {}
                
                # 用户统计
                stats['users'] = self._get_user_stats(cursor)
                
                # 财务统计
                stats['finance'] = self._get_finance_stats(cursor)
                
                # 服务使用统计
                stats['services'] = self._get_service_stats(cursor)
                
                # 系统活动统计
                stats['activity'] = self._get_activity_stats(cursor)
                
                # 最近交易
                stats['recent_transactions'] = self._get_recent_transactions(cursor)
                
                # 最近用户
                stats['recent_users'] = self._get_recent_users(cursor)
                
                return stats
        except Exception as e:
            logger.error(f"获取统计数据失败: {e}")
            # 返回默认数据结构
            return {
                'users': {'total_users': 0, 'active_users': 0, 'today_new_users': 0, 'month_new_users': 0},
                'finance': {'total_revenue': 0, 'today_revenue': 0, 'month_revenue': 0, 'total_balance': 0, 'total_consumption': 0},
                'services': {'service_usage': [], 'today_usage': 0, 'total_papers': 0, 'total_defense_questions': 0},
                'activity': {'today_logins': 0, 'online_users': 0},
                'recent_transactions': [],
                'recent_users': []
            }
        finally:
            if conn:
                conn.close()
    
    def _get_user_stats(self, cursor):
        """获取用户统计"""
        stats = {}
        
        # 总用户数
        cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'user'")
        stats['total_users'] = cursor.fetchone()['total']
        
        # 活跃用户数（最近7天登录）
        cursor.execute("""
            SELECT COUNT(*) as active FROM users 
            WHERE role = 'user' AND last_login_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        stats['active_users'] = cursor.fetchone()['active']
        
        # 今日新增用户
        cursor.execute("""
            SELECT COUNT(*) as today_new FROM users 
            WHERE role = 'user' AND DATE(created_at) = CURDATE()
        """)
        stats['today_new_users'] = cursor.fetchone()['today_new']
        
        # 本月新增用户
        cursor.execute("""
            SELECT COUNT(*) as month_new FROM users 
            WHERE role = 'user' AND DATE_FORMAT(created_at, '%Y-%m') = DATE_FORMAT(NOW(), '%Y-%m')
        """)
        stats['month_new_users'] = cursor.fetchone()['month_new']
        
        return stats
    
    def _get_finance_stats(self, cursor):
        """获取财务统计"""
        stats = {}
        
        # 总收入（成功的充值记录）- 兼容不同的status值
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total 
            FROM recharge_records 
            WHERE status IN ('success', 'paid', '1', 1)
        """)
        stats['total_revenue'] = float(cursor.fetchone()['total'])
        
        # 今日收入
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as today 
            FROM recharge_records 
            WHERE status IN ('success', 'paid', '1', 1) 
            AND DATE(COALESCE(paid_at, created_at)) = CURDATE()
        """)
        stats['today_revenue'] = float(cursor.fetchone()['today'])
        
        # 本月收入
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as month 
            FROM recharge_records 
            WHERE status IN ('success', 'paid', '1', 1) 
            AND DATE_FORMAT(COALESCE(paid_at, created_at), '%Y-%m') = DATE_FORMAT(NOW(), '%Y-%m')
        """)
        stats['month_revenue'] = float(cursor.fetchone()['month'])
        
        # 用户总余额
        cursor.execute("SELECT COALESCE(SUM(balance), 0) as total FROM users WHERE role = 'user'")
        stats['total_balance'] = float(cursor.fetchone()['total'])
        
        # 总消费
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM consumption_records")
        stats['total_consumption'] = float(cursor.fetchone()['total'])
        
        # 获取每日收入数据（最近7天）
        cursor.execute("""
            SELECT 
                DATE(COALESCE(paid_at, created_at)) as date,
                COALESCE(SUM(amount), 0) as revenue
            FROM recharge_records
            WHERE status IN ('success', 'paid', '1', 1)
            AND DATE(COALESCE(paid_at, created_at)) >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY DATE(COALESCE(paid_at, created_at))
            ORDER BY date
        """)
        stats['daily_revenue'] = cursor.fetchall()
        
        # 获取服务类型收入分布
        cursor.execute("""
            SELECT 
                service_type,
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as revenue
            FROM consumption_records
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY service_type
            ORDER BY revenue DESC
        """)
        stats['service_revenue'] = cursor.fetchall()
        
        return stats
    
    def _get_service_stats(self, cursor):
        """获取服务使用统计"""
        stats = {}
        
        # 各服务使用次数和收入
        cursor.execute("""
            SELECT 
                service_type,
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as revenue
            FROM consumption_records
            GROUP BY service_type
            ORDER BY count DESC
        """)
        stats['service_usage'] = cursor.fetchall()
        
        # 今日服务使用
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM consumption_records
            WHERE DATE(created_at) = CURDATE()
        """)
        stats['today_usage'] = cursor.fetchone()['count']
        
        # 论文生成统计（使用 papers 表）
        try:
            cursor.execute("SELECT COUNT(*) as total FROM papers")
            stats['total_papers'] = cursor.fetchone()['total']
        except:
            stats['total_papers'] = 0
        
        # 答辩问题生成统计
        try:
            cursor.execute("SELECT COUNT(*) as total FROM defense_question_history")
            stats['total_defense_questions'] = cursor.fetchone()['total']
        except:
            stats['total_defense_questions'] = 0
        
        return stats
    
    def _get_activity_stats(self, cursor):
        """获取系统活动统计"""
        stats = {}

        # 今日登录次数
        try:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM login_logs
                WHERE DATE(created_at) = CURDATE() AND status = 'success'
            """)
            stats['today_logins'] = cursor.fetchone()['count']
        except:
            stats['today_logins'] = 0
        
        # 在线用户数（基于最近登录时间）
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM users
            WHERE last_login_at > DATE_SUB(NOW(), INTERVAL 30 MINUTE) 
            AND role = 'user'
        """)
        stats['online_users'] = cursor.fetchone()['count']
        
        return stats
    
    def _get_recent_transactions(self, cursor):
        """获取最近交易记录"""
        cursor.execute("""
            SELECT 
                r.order_no,
                r.amount,
                r.status,
                r.paid_at,
                u.username
            FROM recharge_records r
            JOIN users u ON r.user_id = u.id
            ORDER BY r.created_at DESC
            LIMIT 10
        """)
        return cursor.fetchall()
    
    def _get_recent_users(self, cursor):
        """获取最近注册用户"""
        cursor.execute("""
            SELECT 
                id,
                username,
                email,
                balance,
                created_at,
                status
            FROM users
            WHERE role = 'user'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        return cursor.fetchall()
    
    def get_user_list(self, page=1, per_page=20, search=None, status=None):
        """获取用户列表"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 构建查询条件
                where_conditions = ["role = 'user'"]
                params = []
                
                if search:
                    where_conditions.append("(username LIKE %s OR email LIKE %s)")
                    params.extend([f"%{search}%", f"%{search}%"])
                
                if status is not None:
                    where_conditions.append("status = %s")
                    params.append(status)
                
                where_clause = " WHERE " + " AND ".join(where_conditions)
                
                # 获取总数
                cursor.execute(f"SELECT COUNT(*) as total FROM users{where_clause}", params)
                total = cursor.fetchone()['total']
                
                # 获取分页数据
                offset = (page - 1) * per_page
                cursor.execute(f"""
                    SELECT 
                        id, username, email, balance, total_recharge, 
                        total_consumption, invite_earnings, status, 
                        created_at, last_login_at, last_login_ip
                    FROM users{where_clause}
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
        """获取用户详细信息用于管理员查看"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 获取用户基本信息
                cursor.execute("""
                    SELECT 
                        id, username, email, balance, total_recharge, 
                        total_consumption, invite_earnings, status, role,
                        created_at, updated_at, last_login_at, last_login_ip,
                        invite_code, invited_by
                    FROM users
                    WHERE id = %s
                """, (user_id,))
                
                user = cursor.fetchone()
                if not user:
                    return None
                
                # 获取最近的消费记录
                cursor.execute("""
                    SELECT 
                        id, service_type, amount, description, created_at
                    FROM consumption_records
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 10
                """, (user_id,))
                
                user['recent_consumptions'] = cursor.fetchall()
                
                # 获取最近的充值记录
                cursor.execute("""
                    SELECT 
                        id, amount, payment_method as method, status, description, created_at, paid_at
                    FROM recharge_records
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 10
                """, (user_id,))
                
                user['recent_recharges'] = cursor.fetchall()
                
                # 获取邀请统计
                cursor.execute("""
                    SELECT COUNT(*) as invite_count
                    FROM users
                    WHERE invited_by = %s
                """, (user['invite_code'],))
                
                user['invite_count'] = cursor.fetchone()['invite_count']
                
                return user
                
        except Exception as e:
            logger.error(f"获取用户详情失败: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_system_config(self):
        """获取系统配置"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM system_config ORDER BY config_key")
                configs = cursor.fetchall()
                
                # 按类别组织配置
                config_dict = {}
                for config in configs:
                    config_dict[config['config_key']] = {
                        'value': config['config_value'],
                        'description': config['description']
                    }
                
                return config_dict
        except Exception as e:
            logger.error(f"获取系统配置失败: {e}")
            return {}
        finally:
            if conn:
                conn.close()
    
    def update_system_config(self, config_key, config_value, description=None):
        """更新系统配置"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                if description:
                    cursor.execute("""
                        INSERT INTO system_config (config_key, config_value, description)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                        config_value = VALUES(config_value),
                        description = VALUES(description)
                    """, (config_key, config_value, description))
                else:
                    cursor.execute("""
                        INSERT INTO system_config (config_key, config_value)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE 
                        config_value = VALUES(config_value)
                    """, (config_key, config_value))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"更新系统配置失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def get_detailed_statistics(self, time_range='7days', start_date=None, end_date=None):
        """获取详细的统计数据用于数据统计页面"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 根据时间范围设置日期条件
                date_condition = self._get_date_condition(time_range, start_date, end_date)
                
                # 获取关键指标
                total_revenue = self._get_total_revenue_in_range(cursor, date_condition)
                avg_revenue_per_user = self._get_avg_revenue_per_user(cursor, date_condition)
                conversion_rate = self._get_conversion_rate(cursor, date_condition)
                active_rate = self._get_active_rate(cursor, date_condition)
                
                # 获取图表数据
                revenue_trend = self._get_revenue_trend(cursor, date_condition)
                revenue_source = self._get_revenue_source(cursor, date_condition)
                user_growth = self._get_user_growth(cursor, date_condition)
                service_usage = self._get_service_usage_chart(cursor, date_condition)
                hourly_activity = self._get_hourly_activity(cursor, date_condition)
                
                # 获取表格数据
                service_revenue = self._get_service_revenue_detail(cursor, date_condition)
                retention = self._get_retention_data(cursor, date_condition)
                
                return {
                    'success': True,
                    'data': {
                        'totalRevenue': total_revenue,
                        'avgRevenuePerUser': avg_revenue_per_user,
                        'conversionRate': conversion_rate,
                        'activeRate': active_rate,
                        'revenueTrend': revenue_trend,
                        'revenueSource': revenue_source,
                        'userGrowth': user_growth,
                        'serviceUsage': service_usage,
                        'hourlyActivity': hourly_activity,
                        'serviceRevenue': service_revenue,
                        'retention': retention
                    }
                }
                
        except Exception as e:
            logger.error(f"获取详细统计数据失败: {e}")
            return {
                'success': False,
                'message': '获取统计数据失败'
            }
        finally:
            if conn:
                conn.close()
    
    def _get_date_condition(self, time_range, start_date, end_date):
        """根据时间范围生成SQL日期条件"""
        if time_range == '7days':
            return "DATE_SUB(CURDATE(), INTERVAL 6 DAY) <= DATE(created_at)"
        elif time_range == '30days':
            return "DATE_SUB(CURDATE(), INTERVAL 29 DAY) <= DATE(created_at)"
        elif time_range == '90days':
            return "DATE_SUB(CURDATE(), INTERVAL 89 DAY) <= DATE(created_at)"
        elif time_range == 'custom' and start_date and end_date:
            return f"DATE(created_at) BETWEEN '{start_date}' AND '{end_date}'"
        else:
            return "DATE_SUB(CURDATE(), INTERVAL 6 DAY) <= DATE(created_at)"
    
    def _get_total_revenue_in_range(self, cursor, date_condition):
        """获取时间范围内的总收入"""
        cursor.execute(f"""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM recharge_records
            WHERE status IN ('success', 'paid', '1', 1) AND {date_condition}
        """)
        return float(cursor.fetchone()['total'])
    
    def _get_avg_revenue_per_user(self, cursor, date_condition):
        """获取人均收入"""
        cursor.execute(f"""
            SELECT 
                COUNT(DISTINCT user_id) as user_count,
                COALESCE(SUM(amount), 0) as total_revenue
            FROM recharge_records
            WHERE status IN ('success', 'paid', '1', 1) AND {date_condition}
        """)
        result = cursor.fetchone()
        if result['user_count'] > 0:
            return float(result['total_revenue']) / result['user_count']
        return 0
    
    def _get_conversion_rate(self, cursor, date_condition):
        """获取付费转化率"""
        # 获取总用户数
        cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'user'")
        total_users = cursor.fetchone()['total']
        
        # 获取付费用户数
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as paying_users
            FROM recharge_records
            WHERE status IN ('success', 'paid', '1', 1)
        """)
        paying_users = cursor.fetchone()['paying_users']
        
        if total_users > 0:
            return (paying_users / total_users) * 100
        return 0
    
    def _get_active_rate(self, cursor, date_condition):
        """获取用户活跃率"""
        # 获取总用户数
        cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'user'")
        total_users = cursor.fetchone()['total']
        
        # 获取活跃用户数（最近7天登录）
        cursor.execute("""
            SELECT COUNT(*) as active FROM users 
            WHERE role = 'user' AND last_login_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        active_users = cursor.fetchone()['active']
        
        if total_users > 0:
            return (active_users / total_users) * 100
        return 0
    
    def _get_revenue_trend(self, cursor, date_condition):
        """获取收入趋势数据"""
        # 获取每日收入和订单数
        cursor.execute(f"""
            SELECT 
                DATE(COALESCE(paid_at, created_at)) as date,
                COALESCE(SUM(amount), 0) as revenue,
                COUNT(*) as orders
            FROM recharge_records
            WHERE status IN ('success', 'paid', '1', 1) AND {date_condition}
            GROUP BY DATE(COALESCE(paid_at, created_at))
            ORDER BY date
        """)
        
        results = cursor.fetchall()
        labels = []
        revenue = []
        orders = []
        
        for row in results:
            labels.append(row['date'].strftime('%m-%d'))
            revenue.append(float(row['revenue']))
            orders.append(row['orders'])
        
        return {
            'labels': labels,
            'revenue': revenue,
            'orders': orders
        }
    
    def _get_revenue_source(self, cursor, date_condition):
        """获取收入来源分布"""
        cursor.execute(f"""
            SELECT 
                service_type,
                COALESCE(SUM(amount), 0) as revenue
            FROM consumption_records
            WHERE {date_condition}
            GROUP BY service_type
            ORDER BY revenue DESC
        """)
        
        results = cursor.fetchall()
        labels = []
        values = []
        
        service_names = {
            'sql_to_er': 'SQL转ER图',
            'defense_questions': '答辩问题',
            'paper_generation': '论文生成',
            'ai_translation': 'AI翻译',
            'er_optimization': 'ER优化',
            'database_design': '数据库设计'
        }
        
        for row in results:
            labels.append(service_names.get(row['service_type'], row['service_type']))
            values.append(float(row['revenue']))
        
        return {
            'labels': labels,
            'values': values
        }
    
    def _get_user_growth(self, cursor, date_condition):
        """获取用户增长数据"""
        # 获取每日新增用户和活跃用户
        cursor.execute(f"""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as new_users
            FROM users
            WHERE role = 'user' AND {date_condition}
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        
        new_users_data = {row['date']: row['new_users'] for row in cursor.fetchall()}
        
        # 获取每日活跃用户
        cursor.execute(f"""
            SELECT 
                DATE(created_at) as date,
                COUNT(DISTINCT user_id) as active_users
            FROM consumption_records
            WHERE {date_condition}
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        
        active_users_data = {row['date']: row['active_users'] for row in cursor.fetchall()}
        
        # 合并数据
        all_dates = sorted(set(list(new_users_data.keys()) + list(active_users_data.keys())))
        labels = []
        new_users = []
        active_users = []
        
        for date in all_dates:
            labels.append(date.strftime('%m-%d'))
            new_users.append(new_users_data.get(date, 0))
            active_users.append(active_users_data.get(date, 0))
        
        return {
            'labels': labels,
            'newUsers': new_users,
            'activeUsers': active_users
        }
    
    def _get_service_usage_chart(self, cursor, date_condition):
        """获取服务使用频次数据（雷达图）"""
        cursor.execute(f"""
            SELECT 
                service_type,
                COUNT(*) as count
            FROM consumption_records
            WHERE {date_condition}
            GROUP BY service_type
        """)
        
        results = cursor.fetchall()
        
        service_names = {
            'sql_to_er': 'SQL转ER图',
            'defense_questions': '答辩问题',
            'paper_generation': '论文生成',
            'ai_translation': 'AI翻译',
            'er_optimization': 'ER优化',
            'database_design': '数据库设计'
        }
        
        # 确保所有服务类型都包含在内
        labels = list(service_names.values())
        values = []
        service_data = {row['service_type']: row['count'] for row in results}
        
        for service_type, service_name in service_names.items():
            values.append(service_data.get(service_type, 0))
        
        return {
            'labels': labels,
            'values': values
        }
    
    def _get_hourly_activity(self, cursor, date_condition):
        """获取每小时活动数据"""
        cursor.execute(f"""
            SELECT 
                HOUR(created_at) as hour,
                COUNT(*) as count
            FROM consumption_records
            WHERE {date_condition}
            GROUP BY HOUR(created_at)
            ORDER BY hour
        """)
        
        results = cursor.fetchall()
        activity_data = {row['hour']: row['count'] for row in results}
        
        labels = []
        values = []
        
        for hour in range(24):
            labels.append(f"{hour}:00")
            values.append(activity_data.get(hour, 0))
        
        return {
            'labels': labels,
            'values': values
        }
    
    def _get_service_revenue_detail(self, cursor, date_condition):
        """获取服务收入明细"""
        # 获取当前时间段的数据
        cursor.execute(f"""
            SELECT 
                service_type,
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as revenue
            FROM consumption_records
            WHERE {date_condition}
            GROUP BY service_type
        """)
        
        current_data = {row['service_type']: row for row in cursor.fetchall()}
        
        # 获取上一个时间段的数据用于计算趋势
        # 这里简化处理，比较最近7天和前7天
        cursor.execute("""
            SELECT 
                service_type,
                COALESCE(SUM(amount), 0) as revenue
            FROM consumption_records
            WHERE DATE(created_at) BETWEEN DATE_SUB(CURDATE(), INTERVAL 13 DAY) 
                AND DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY service_type
        """)
        
        previous_data = {row['service_type']: row['revenue'] for row in cursor.fetchall()}
        
        # 计算总收入
        total_revenue = sum(float(data['revenue']) for data in current_data.values())
        
        service_names = {
            'sql_to_er': 'SQL转ER图',
            'defense_questions': '答辩问题',
            'paper_generation': '论文生成',
            'ai_translation': 'AI翻译',
            'er_optimization': 'ER优化',
            'database_design': '数据库设计'
        }
        
        results = []
        for service_type, data in current_data.items():
            revenue = float(data['revenue'])
            count = data['count']
            avg_price = revenue / count if count > 0 else 0
            percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            
            # 计算趋势
            prev_revenue = float(previous_data.get(service_type, 0))
            if prev_revenue > 0:
                trend = ((revenue - prev_revenue) / prev_revenue) * 100
            else:
                trend = 100 if revenue > 0 else 0
            
            results.append({
                'service': service_names.get(service_type, service_type),
                'count': count,
                'revenue': revenue,
                'avgPrice': avg_price,
                'percentage': percentage,
                'trend': round(trend, 1)
            })
        
        # 按收入排序
        results.sort(key=lambda x: x['revenue'], reverse=True)
        
        return results
    
    def _get_retention_data(self, cursor, date_condition):
        """获取用户留存数据"""
        # 简化的留存计算，获取最近几个时间点的数据
        results = []
        
        for days_ago in [0, 7, 14, 21, 28]:
            target_date = f"DATE_SUB(CURDATE(), INTERVAL {days_ago} DAY)"
            
            # 获取该日新增用户
            cursor.execute(f"""
                SELECT COUNT(*) as new_users
                FROM users
                WHERE role = 'user' AND DATE(created_at) = {target_date}
            """)
            new_users = cursor.fetchone()['new_users']
            
            if new_users > 0:
                # 计算次日留存
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT u.id) as retained
                    FROM users u
                    INNER JOIN consumption_records c ON u.id = c.user_id
                    WHERE u.role = 'user' 
                    AND DATE(u.created_at) = {target_date}
                    AND DATE(c.created_at) = DATE_ADD({target_date}, INTERVAL 1 DAY)
                """)
                day1_retained = cursor.fetchone()['retained']
                day1_rate = round((day1_retained / new_users) * 100, 1)
                
                # 计算7日留存
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT u.id) as retained
                    FROM users u
                    INNER JOIN consumption_records c ON u.id = c.user_id
                    WHERE u.role = 'user' 
                    AND DATE(u.created_at) = {target_date}
                    AND DATE(c.created_at) BETWEEN DATE_ADD({target_date}, INTERVAL 1 DAY) 
                        AND DATE_ADD({target_date}, INTERVAL 7 DAY)
                """)
                day7_retained = cursor.fetchone()['retained']
                day7_rate = round((day7_retained / new_users) * 100, 1)
                
                # 计算30日留存（如果时间足够）
                if days_ago >= 30:
                    cursor.execute(f"""
                        SELECT COUNT(DISTINCT u.id) as retained
                        FROM users u
                        INNER JOIN consumption_records c ON u.id = c.user_id
                        WHERE u.role = 'user' 
                        AND DATE(u.created_at) = {target_date}
                        AND DATE(c.created_at) BETWEEN DATE_ADD({target_date}, INTERVAL 1 DAY) 
                            AND DATE_ADD({target_date}, INTERVAL 30 DAY)
                    """)
                    day30_retained = cursor.fetchone()['retained']
                    day30_rate = round((day30_retained / new_users) * 100, 1)
                else:
                    day30_rate = '-'
                
                results.append({
                    'date': (datetime.now() - timedelta(days=days_ago)).strftime('%m-%d'),
                    'newUsers': new_users,
                    'day1': day1_rate,
                    'day7': day7_rate,
                    'day30': day30_rate
                })
        
        return results
    
    def get_announcement_list(self, page=1, per_page=20, search=None, type_filter=None, status_filter=None):
        """获取公告列表（管理端）"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 构建查询条件
                where_conditions = []
                params = []
                
                if search:
                    where_conditions.append("(title LIKE %s OR content LIKE %s)")
                    params.extend([f"%{search}%", f"%{search}%"])
                
                if type_filter:
                    where_conditions.append("type = %s")
                    params.append(type_filter)
                
                if status_filter:
                    where_conditions.append("is_active = %s")
                    params.append(int(status_filter))
                
                where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                # 获取总数
                cursor.execute(f"SELECT COUNT(*) as total FROM announcements{where_clause}", params)
                total = cursor.fetchone()['total']
                
                # 获取分页数据
                offset = (page - 1) * per_page
                cursor.execute(f"""
                    SELECT 
                        id, title, content, type, is_active, is_sticky,
                        start_time, end_time, view_count, created_at, updated_at
                    FROM announcements{where_clause}
                    ORDER BY is_sticky DESC, created_at DESC
                    LIMIT %s OFFSET %s
                """, params + [per_page, offset])
                
                announcements = cursor.fetchall()
                
                return {
                    'announcements': announcements,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page
                }
        except Exception as e:
            logger.error(f"获取公告列表失败: {e}")
            return {
                'announcements': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0
            }
        finally:
            if conn:
                conn.close()
    
    def create_announcement(self, title, content, type='info', is_active=1, is_sticky=0, 
                           start_time=None, end_time=None, admin_id=None):
        """创建公告"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO announcements 
                    (title, content, type, is_active, is_sticky, start_time, end_time, admin_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (title, content, type, is_active, is_sticky, start_time, end_time, admin_id))
                
                conn.commit()
                return {'success': True, 'message': '公告创建成功', 'id': cursor.lastrowid}
        except Exception as e:
            logger.error(f"创建公告失败: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': '创建失败'}
        finally:
            if conn:
                conn.close()
    
    def get_announcement_detail(self, announcement_id):
        """获取公告详情"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, title, content, type, is_active, is_sticky,
                        start_time, end_time, view_count, created_at, updated_at
                    FROM announcements
                    WHERE id = %s
                """, (announcement_id,))
                
                announcement = cursor.fetchone()
                if announcement:
                    # 格式化时间
                    if announcement['created_at']:
                        announcement['created_at'] = announcement['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                    if announcement['updated_at']:
                        announcement['updated_at'] = announcement['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
                    if announcement['start_time']:
                        announcement['start_time'] = announcement['start_time'].strftime('%Y-%m-%d %H:%M:%S')
                    if announcement['end_time']:
                        announcement['end_time'] = announcement['end_time'].strftime('%Y-%m-%d %H:%M:%S')
                
                return announcement
        except Exception as e:
            logger.error(f"获取公告详情失败: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def update_announcement(self, announcement_id, title=None, content=None, type=None, 
                           is_active=None, is_sticky=None, start_time=None, end_time=None):
        """更新公告"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 构建更新语句
                update_fields = []
                params = []
                
                if title is not None:
                    update_fields.append("title = %s")
                    params.append(title)
                if content is not None:
                    update_fields.append("content = %s")
                    params.append(content)
                if type is not None:
                    update_fields.append("type = %s")
                    params.append(type)
                if is_active is not None:
                    update_fields.append("is_active = %s")
                    params.append(is_active)
                if is_sticky is not None:
                    update_fields.append("is_sticky = %s")
                    params.append(is_sticky)
                if start_time is not None:
                    update_fields.append("start_time = %s")
                    params.append(start_time if start_time else None)
                if end_time is not None:
                    update_fields.append("end_time = %s")
                    params.append(end_time if end_time else None)
                
                if update_fields:
                    params.append(announcement_id)
                    cursor.execute(f"""
                        UPDATE announcements 
                        SET {', '.join(update_fields)}
                        WHERE id = %s
                    """, params)
                    
                    conn.commit()
                    return {'success': True, 'message': '更新成功'}
                else:
                    return {'success': False, 'message': '没有要更新的内容'}
        except Exception as e:
            logger.error(f"更新公告失败: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': '更新失败'}
        finally:
            if conn:
                conn.close()
    
    def update_announcement_status(self, announcement_id, is_active):
        """更新公告状态"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE announcements 
                    SET is_active = %s
                    WHERE id = %s
                """, (is_active, announcement_id))
                
                conn.commit()
                return {'success': True, 'message': '状态更新成功'}
        except Exception as e:
            logger.error(f"更新公告状态失败: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': '更新失败'}
        finally:
            if conn:
                conn.close()
    
    def delete_announcement(self, announcement_id):
        """删除公告"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM announcements WHERE id = %s", (announcement_id,))
                conn.commit()
                return {'success': True, 'message': '删除成功'}
        except Exception as e:
            logger.error(f"删除公告失败: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': '删除失败'}
        finally:
            if conn:
                conn.close()

    def get_system_info(self):
        """获取系统信息"""
        import platform
        import sys
        import os

        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 获取数据库信息
                cursor.execute("SELECT VERSION() as version")
                db_version = cursor.fetchone()['version']

                # 获取数据库大小
                cursor.execute("""
                    SELECT
                        ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb
                    FROM information_schema.tables
                    WHERE table_schema = %s
                """, (self.db_config['database'],))
                db_size = cursor.fetchone()['size_mb'] or 0

                # 获取表数量
                cursor.execute("""
                    SELECT COUNT(*) as table_count
                    FROM information_schema.tables
                    WHERE table_schema = %s
                """, (self.db_config['database'],))
                table_count = cursor.fetchone()['table_count']

                # 获取总记录数（主要表）
                cursor.execute("SELECT COUNT(*) as c FROM users")
                user_count = cursor.fetchone()['c']
                cursor.execute("SELECT COUNT(*) as c FROM consumption_records")
                consumption_count = cursor.fetchone()['c']
                cursor.execute("SELECT COUNT(*) as c FROM recharge_records")
                recharge_count = cursor.fetchone()['c']

            return {
                'success': True,
                'data': {
                    'server': {
                        'os': platform.system(),
                        'os_version': platform.version(),
                        'hostname': platform.node(),
                        'python_version': sys.version.split()[0],
                        'platform': platform.platform(),
                    },
                    'database': {
                        'version': db_version,
                        'name': self.db_config['database'],
                        'size_mb': float(db_size),
                        'table_count': table_count,
                    },
                    'statistics': {
                        'user_count': user_count,
                        'consumption_count': consumption_count,
                        'recharge_count': recharge_count,
                    },
                    'app': {
                        'version': '2.0.0',
                        'env': os.environ.get('FLASK_ENV', 'production'),
                    }
                }
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()

    def clear_logs(self, days=30):
        """清理日志记录"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                deleted_count = 0

                # 清理登录日志
                cursor.execute("""
                    DELETE FROM login_logs
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (days,))
                deleted_count += cursor.rowcount

                conn.commit()

                return {
                    'success': True,
                    'message': f'成功清理 {deleted_count} 条日志记录',
                    'deleted_count': deleted_count
                }
        except Exception as e:
            logger.error(f"清理日志失败: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()

    def clear_expired_data(self, days=90):
        """清理过期数据"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                deleted_counts = {}

                # 清理过期的未支付订单
                cursor.execute("""
                    DELETE FROM recharge_records
                    WHERE status IN ('pending', 'unpaid', '0')
                    AND created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (days,))
                deleted_counts['expired_orders'] = cursor.rowcount

                # 清理过期的论文生成历史（可选）
                cursor.execute("""
                    DELETE FROM paper_generation_history
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (days * 2,))
                deleted_counts['paper_history'] = cursor.rowcount

                # 清理过期的答辩问题历史
                cursor.execute("""
                    DELETE FROM defense_question_history
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (days * 2,))
                deleted_counts['defense_history'] = cursor.rowcount

                conn.commit()

                total_deleted = sum(deleted_counts.values())
                return {
                    'success': True,
                    'message': f'成功清理 {total_deleted} 条过期数据',
                    'details': deleted_counts
                }
        except Exception as e:
            logger.error(f"清理过期数据失败: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()

    def export_config(self):
        """导出系统配置"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT config_key, config_value, description
                    FROM system_config
                    ORDER BY config_key
                """)
                configs = cursor.fetchall()

                # 转换为可导出的格式
                export_data = {
                    'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'version': '2.0.0',
                    'configs': {}
                }

                for config in configs:
                    # 敏感信息脱敏
                    key = config['config_key']
                    value = config['config_value']

                    if any(s in key.lower() for s in ['password', 'secret', 'private_key', 'api_key']):
                        value = '******'  # 脱敏处理

                    export_data['configs'][key] = {
                        'value': value,
                        'description': config['description']
                    }

                return {'success': True, 'data': export_data}
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()

    def import_config(self, config_data):
        """导入系统配置"""
        conn = None
        try:
            if not config_data or 'configs' not in config_data:
                return {'success': False, 'message': '无效的配置数据'}

            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                imported_count = 0
                skipped_count = 0

                for key, item in config_data['configs'].items():
                    value = item.get('value', '')
                    description = item.get('description', '')

                    # 跳过脱敏的值
                    if value == '******':
                        skipped_count += 1
                        continue

                    cursor.execute("""
                        INSERT INTO system_config (config_key, config_value, description)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        config_value = VALUES(config_value),
                        description = COALESCE(VALUES(description), description)
                    """, (key, value, description))
                    imported_count += 1

                conn.commit()

                return {
                    'success': True,
                    'message': f'成功导入 {imported_count} 项配置，跳过 {skipped_count} 项敏感配置',
                    'imported': imported_count,
                    'skipped': skipped_count
                }
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()

    def reset_config_to_default(self):
        """重置配置为默认值"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                # 默认配置
                default_configs = [
                    ('site_name', '智能文档处理平台', '网站名称'),
                    ('site_description', '专业的智能文档处理和AI工具平台', '网站描述'),
                    ('maintenance_mode', '0', '维护模式'),
                    ('allow_registration', '1', '允许注册'),
                    ('new_user_bonus', '10.00', '新用户注册奖励'),
                    ('invite_reward', '5.00', '邀请奖励'),

                    # 价格设置
                    ('sql_to_er_cost', '1.00', 'SQL转ER图价格'),
                    ('thesis_defense_cost', '5.00', '答辩问题生成价格'),
                    ('paper_generation_cost', '10.00', '论文生成价格'),
                    ('paper_structure_cost', '4.00', '论文结构生成价格'),
                    ('ai_translation_cost', '2.00', 'AI翻译价格'),
                    ('flowchart_cost', '2.00', '流程图生成价格'),
                    ('text_optimizer_cost', '1.50', '文本优化价格'),
                    ('ai_detector_cost', '1.00', 'AI检测价格'),

                    # 系统设置
                    ('debug_mode', '0', '调试模式'),
                    ('api_rate_limit', '60', 'API速率限制'),
                    ('session_timeout', '1440', '会话超时时间（分钟）'),

                    # AI设置
                    ('ai_model_name', 'deepseek-chat', 'AI模型名称'),
                    ('ai_api_base', 'https://api.deepseek.com', 'AI API地址'),
                ]

                for key, value, desc in default_configs:
                    cursor.execute("""
                        INSERT INTO system_config (config_key, config_value, description)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        config_value = VALUES(config_value),
                        description = VALUES(description)
                    """, (key, value, desc))

                conn.commit()
                return {'success': True, 'message': f'成功重置 {len(default_configs)} 项配置'}
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()

    def get_operation_logs(self, page=1, per_page=50, log_type=None, start_date=None, end_date=None):
        """获取操作日志"""
        conn = None
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                where_conditions = []
                params = []

                if log_type:
                    where_conditions.append("status = %s")
                    params.append(log_type)

                if start_date:
                    where_conditions.append("DATE(created_at) >= %s")
                    params.append(start_date)

                if end_date:
                    where_conditions.append("DATE(created_at) <= %s")
                    params.append(end_date)

                where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                # 获取总数
                cursor.execute(f"SELECT COUNT(*) as total FROM login_logs{where_clause}", params)
                total = cursor.fetchone()['total']

                # 获取分页数据
                offset = (page - 1) * per_page
                cursor.execute(f"""
                    SELECT
                        l.id, l.user_id, l.ip_address, l.user_agent,
                        l.status, l.created_at,
                        u.username
                    FROM login_logs l
                    LEFT JOIN users u ON l.user_id = u.id
                    {where_clause}
                    ORDER BY l.created_at DESC
                    LIMIT %s OFFSET %s
                """, params + [per_page, offset])

                logs = cursor.fetchall()

                return {
                    'success': True,
                    'data': {
                        'logs': logs,
                        'total': total,
                        'page': page,
                        'per_page': per_page,
                        'total_pages': (total + per_page - 1) // per_page
                    }
                }
        except Exception as e:
            logger.error(f"获取操作日志失败: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()