"""
管理员路由模块
处理管理员相关的所有路由
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from admin_auth import AdminAuth, admin_required
import logging

logger = logging.getLogger(__name__)

def create_admin_blueprint(admin_auth, admin_stats=None, user_manager=None):
    """创建管理员蓝图"""
    admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
    
    @admin_bp.route('/login', methods=['GET', 'POST'])
    def login():
        """管理员登录"""
        if admin_auth.is_admin_logged_in():
            return redirect(url_for('admin.dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('请输入用户名和密码', 'error')
                return render_template('admin/login.html')
            
            success, message = admin_auth.verify_admin(username, password)
            
            if success:
                flash(message, 'success')
                return redirect(url_for('admin.dashboard'))
            else:
                flash(message, 'error')
        
        return render_template('admin/login.html')
    
    @admin_bp.route('/logout')
    @admin_required
    def logout():
        """管理员登出"""
        admin_auth.logout()
        flash('已安全退出', 'info')
        return redirect(url_for('admin.login'))
    
    @admin_bp.route('/dashboard')
    @admin_required
    def dashboard():
        """管理员仪表盘"""
        admin_info = admin_auth.get_current_admin()
        
        # 获取统计数据
        if admin_stats:
            stats = admin_stats.get_dashboard_stats()
        else:
            # 空数据
            stats = {
                'users': {'total_users': 0, 'active_users': 0, 'today_new_users': 0, 'month_new_users': 0},
                'finance': {'total_revenue': 0, 'today_revenue': 0, 'month_revenue': 0, 'total_balance': 0, 'total_consumption': 0},
                'services': {'service_usage': [], 'today_usage': 0, 'total_papers': 0, 'total_defense_questions': 0},
                'activity': {'today_logins': 0, 'online_users': 0},
                'recent_transactions': [],
                'recent_users': []
            }
        
        return render_template('admin/dashboard.html', admin_info=admin_info, stats=stats)
    
    @admin_bp.route('/users')
    @admin_required
    def users():
        """用户管理"""
        admin_info = admin_auth.get_current_admin()
        
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '').strip()
        status = request.args.get('status', type=int)
        
        # 获取用户列表
        if admin_stats:
            user_data = admin_stats.get_user_list(page=page, search=search, status=status)
        else:
            user_data = {
                'users': [],
                'total': 0,
                'page': page,
                'per_page': 20,
                'total_pages': 0
            }
        
        return render_template('admin/users.html', 
                             admin_info=admin_info, 
                             user_data=user_data,
                             search=search,
                             status=status)
    
    @admin_bp.route('/announcements')
    @admin_required
    def announcements():
        """公告管理"""
        admin_info = admin_auth.get_current_admin()
        
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = 20
        search = request.args.get('search', '').strip()
        type_filter = request.args.get('type', '')
        status_filter = request.args.get('status', '')
        
        # 获取公告列表
        if admin_stats:
            announcement_data = admin_stats.get_announcement_list(page=page, search=search, type_filter=type_filter, status_filter=status_filter)
            announcements = announcement_data.get('announcements', [])
            total = announcement_data.get('total', 0)
            total_pages = announcement_data.get('total_pages', 0)
        else:
            announcements = []
            total = 0
            total_pages = 0
        
        return render_template('admin/announcements.html', 
                             admin_info=admin_info,
                             announcements=announcements,
                             page=page,
                             total=total,
                             total_pages=total_pages,
                             search=search,
                             type_filter=type_filter,
                             status_filter=status_filter)
    
    @admin_bp.route('/statistics')
    @admin_required
    def statistics():
        """数据统计"""
        admin_info = admin_auth.get_current_admin()
        return render_template('admin/statistics.html', admin_info=admin_info)
    
    @admin_bp.route('/settings')
    @admin_required
    def settings():
        """系统设置"""
        admin_info = admin_auth.get_current_admin()
        
        # 获取系统配置
        if admin_stats:
            configs = admin_stats.get_system_config()
        else:
            configs = {}
        
        return render_template('admin/settings.html', admin_info=admin_info, configs=configs)
    
    # API路由
    @admin_bp.route('/api/stats')
    @admin_required
    def api_stats():
        """获取统计数据API"""
        if admin_stats:
            stats = admin_stats.get_dashboard_stats()
            # 确保stats包含所需的键
            if stats and 'users' in stats and 'finance' in stats and 'activity' in stats:
                return jsonify({
                    'success': True,
                    'data': {
                        'total_users': stats['users']['total_users'],
                        'total_revenue': stats['finance']['total_revenue'],
                        'today_users': stats['users']['today_new_users'],
                        'today_revenue': stats['finance']['today_revenue'],
                        'active_users': stats['users']['active_users'],
                        'online_users': stats['activity']['online_users']
                    }
                })
        
        # 返回默认数据
        return jsonify({
            'success': True,
            'data': {
                'total_users': 0,
                'total_revenue': 0,
                'today_users': 0,
                'today_revenue': 0,
                'active_users': 0,
                'online_users': 0
            }
        })
    
    @admin_bp.route('/api/users/<int:user_id>/status', methods=['POST'])
    @admin_required
    def update_user_status(user_id):
        """更新用户状态"""
        if not user_manager:
            return jsonify({'success': False, 'message': '功能未启用'}), 400
        
        data = request.get_json()
        status = data.get('status')
        
        if status not in [0, 1]:
            return jsonify({'success': False, 'message': '无效的状态值'}), 400
        
        # 更新用户状态
        success = user_manager.update_user_status(user_id, status)
        
        if success:
            return jsonify({'success': True, 'message': '状态更新成功'})
        else:
            return jsonify({'success': False, 'message': '更新失败'}), 400
    
    @admin_bp.route('/api/users/<int:user_id>/detail')
    @admin_required
    def get_user_detail(user_id):
        """获取用户详细信息"""
        if not admin_stats:
            return jsonify({'success': False, 'message': '功能未启用'}), 400
        
        user = admin_stats.get_user_detail(user_id)
        if user:
            return jsonify({'success': True, 'user': user})
        else:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
    
    @admin_bp.route('/api/users/<int:user_id>/recharge', methods=['POST'])
    @admin_required
    def recharge_user(user_id):
        """管理员给用户充值"""
        if not user_manager:
            return jsonify({'success': False, 'message': '功能未启用'}), 400
        
        data = request.get_json()
        amount = data.get('amount', 0)
        description = data.get('description', '管理员手动充值')
        
        if amount <= 0:
            return jsonify({'success': False, 'message': '充值金额必须大于0'}), 400
        
        # 获取当前管理员ID
        admin_info = admin_auth.get_current_admin()
        admin_id = admin_info.get('id') if admin_info else None
        
        success = user_manager.add_balance(
            user_id=user_id,
            amount=amount,
            operator_id=admin_id,
            description=description,
            method='admin'
        )
        
        if success:
            return jsonify({'success': True, 'message': '充值成功'})
        else:
            return jsonify({'success': False, 'message': '充值失败'}), 400
    
    @admin_bp.route('/api/users/add', methods=['POST'])
    @admin_required
    def add_user():
        """管理员添加新用户"""
        if not user_manager:
            return jsonify({'success': False, 'message': '功能未启用'}), 400
        
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        balance = data.get('balance', 0)
        
        if not password:
            return jsonify({'success': False, 'message': '密码不能为空'}), 400
        
        if not username and not email:
            return jsonify({'success': False, 'message': '请至少提供用户名或邮箱'}), 400
        
        # 注册用户
        result = user_manager.register_user(
            username=username or None,
            email=email or None,
            password=password
        )
        
        if result['success']:
            # 如果需要设置初始余额
            if balance > 0:
                admin_info = admin_auth.get_current_admin()
                admin_id = admin_info.get('id') if admin_info else None
                
                user_manager.add_balance(
                    user_id=result['user_id'],
                    amount=balance,
                    operator_id=admin_id,
                    description='管理员设置初始余额',
                    method='admin'
                )
            
            return jsonify({
                'success': True,
                'message': '用户添加成功',
                'user_id': result['user_id']
            })
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
    
    @admin_bp.route('/api/config/update', methods=['POST'])
    @admin_required
    def update_config():
        """更新系统配置"""
        if not admin_stats:
            return jsonify({'success': False, 'message': '功能未启用'}), 400
        
        data = request.get_json()
        config_key = data.get('key')
        config_value = data.get('value')
        
        if not config_key or config_value is None:
            return jsonify({'success': False, 'message': '参数不完整'}), 400
        
        success = admin_stats.update_system_config(config_key, config_value)
        
        if success:
            return jsonify({'success': True, 'message': '配置更新成功'})
        else:
            return jsonify({'success': False, 'message': '更新失败'}), 400
    
    @admin_bp.route('/api/statistics')
    @admin_required
    def api_statistics():
        """获取详细统计数据API"""
        if not admin_stats:
            return jsonify({'success': False, 'message': '统计功能未启用'}), 400
        
        # 获取查询参数
        time_range = request.args.get('range', '7days')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 获取统计数据
        result = admin_stats.get_detailed_statistics(time_range, start_date, end_date)
        
        return jsonify(result)
    
    @admin_bp.route('/api/export-report')
    @admin_required
    def export_report():
        """导出统计报表"""
        # 获取参数
        time_range = request.args.get('range', '7days')
        format_type = request.args.get('format', 'excel')
        
        # TODO: 实现报表导出功能
        # 这里暂时返回提示信息
        return jsonify({
            'success': False,
            'message': '报表导出功能正在开发中'
        })
    
    # 公告管理API路由
    @admin_bp.route('/api/announcements', methods=['GET'])
    @admin_required
    def api_get_admin_announcements():
        """获取公告列表（管理端）"""
        # 这个接口用于管理端获取所有公告，包括禁用的
        # 与前台API不同，这里不过滤时间和状态
        return jsonify({
            'success': True,
            'announcements': []
        })
    
    @admin_bp.route('/api/announcements', methods=['POST'])
    @admin_required
    def api_create_announcement():
        """创建新公告"""
        if not admin_stats:
            return jsonify({'success': False, 'message': '功能未启用'}), 400
        
        data = request.get_json()
        admin_info = admin_auth.get_current_admin()
        
        result = admin_stats.create_announcement(
            title=data.get('title'),
            content=data.get('content'),
            type=data.get('type', 'info'),
            is_active=data.get('is_active', 1),
            is_sticky=data.get('is_sticky', 0),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            admin_id=admin_info.get('id')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @admin_bp.route('/api/announcements/<int:announcement_id>', methods=['GET'])
    @admin_required
    def api_get_announcement(announcement_id):
        """获取公告详情"""
        if not admin_stats:
            return jsonify({'success': False, 'message': '功能未启用'}), 400
        
        announcement = admin_stats.get_announcement_detail(announcement_id)
        if announcement:
            return jsonify({'success': True, 'data': announcement})
        else:
            return jsonify({'success': False, 'message': '公告不存在'}), 404
    
    @admin_bp.route('/api/announcements/<int:announcement_id>', methods=['PUT'])
    @admin_required
    def api_update_announcement(announcement_id):
        """更新公告"""
        if not admin_stats:
            return jsonify({'success': False, 'message': '功能未启用'}), 400
        
        data = request.get_json()
        result = admin_stats.update_announcement(
            announcement_id=announcement_id,
            title=data.get('title'),
            content=data.get('content'),
            type=data.get('type'),
            is_active=data.get('is_active'),
            is_sticky=data.get('is_sticky'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @admin_bp.route('/api/announcements/<int:announcement_id>/status', methods=['PUT'])
    @admin_required
    def api_toggle_announcement_status(announcement_id):
        """切换公告状态"""
        if not admin_stats:
            return jsonify({'success': False, 'message': '功能未启用'}), 400
        
        data = request.get_json()
        is_active = data.get('is_active', 0)
        
        result = admin_stats.update_announcement_status(announcement_id, is_active)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @admin_bp.route('/api/announcements/<int:announcement_id>', methods=['DELETE'])
    @admin_required
    def api_delete_announcement(announcement_id):
        """删除公告"""
        if not admin_stats:
            return jsonify({'success': False, 'message': '功能未启用'}), 400
        
        result = admin_stats.delete_announcement(announcement_id)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @admin_bp.route('/api/users/<int:user_id>/edit', methods=['POST'])
    @admin_required
    def edit_user(user_id):
        """编辑用户信息"""
        if not user_manager:
            return jsonify({'success': False, 'message': '功能未启用'}), 400

        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        result = user_manager.update_user_info(user_id, username, email, password)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    @admin_bp.route('/api/users/<int:user_id>/delete', methods=['DELETE'])
    @admin_required
    def delete_user(user_id):
        """删除用户"""
        if not user_manager:
            return jsonify({'success': False, 'message': '功能未启用'}), 400

        result = user_manager.delete_user(user_id)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    @admin_bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
    @admin_required
    def reset_user_password(user_id):
        """重置用户密码"""
        if not user_manager:
            return jsonify({'success': False, 'message': '功能未启用'}), 400

        data = request.get_json()
        new_password = data.get('password', '')

        result = user_manager.reset_user_password(user_id, new_password)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    @admin_bp.route('/api/users/<int:user_id>/role', methods=['POST'])
    @admin_required
    def update_user_role(user_id):
        """更新用户角色"""
        if not user_manager:
            return jsonify({'success': False, 'message': '功能未启用'}), 400

        data = request.get_json()
        new_role = data.get('role', 'user')

        result = user_manager.update_user_role(user_id, new_role)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    @admin_bp.route('/api/users/<int:user_id>/transactions')
    @admin_required
    def get_user_transactions(user_id):
        """获取用户交易记录"""
        if not user_manager:
            return jsonify({'success': False, 'message': '功能未启用'}), 400

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        result = user_manager.get_user_transactions(user_id, page, per_page)
        return jsonify({'success': True, 'data': result})

    @admin_bp.route('/api/users/batch/status', methods=['POST'])
    @admin_required
    def batch_update_user_status():
        """批量更新用户状态"""
        if not user_manager:
            return jsonify({'success': False, 'message': '功能未启用'}), 400

        data = request.get_json()
        user_ids = data.get('user_ids', [])
        status = data.get('status', 0)

        result = user_manager.batch_update_status(user_ids, status)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    @admin_bp.route('/api/users/batch/delete', methods=['POST'])
    @admin_required
    def batch_delete_users():
        """批量删除用户"""
        if not user_manager:
            return jsonify({'success': False, 'message': '功能未启用'}), 400

        data = request.get_json()
        user_ids = data.get('user_ids', [])

        result = user_manager.batch_delete_users(user_ids)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    @admin_bp.route('/api/users/export')
    @admin_required
    def export_users():
        """导出用户列表"""
        if not user_manager:
            return jsonify({'success': False, 'message': '功能未启用'}), 400

        from flask import Response
        import csv
        import io

        # 获取筛选参数
        search = request.args.get('search', '')
        status = request.args.get('status', type=int)
        date_start = request.args.get('date_start', '')
        date_end = request.args.get('date_end', '')
        balance_min = request.args.get('balance_min', type=float)
        balance_max = request.args.get('balance_max', type=float)
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'DESC')
        export_format = request.args.get('format', 'csv')

        users = user_manager.export_users(
            search=search if search else None,
            status=status,
            date_start=date_start if date_start else None,
            date_end=date_end if date_end else None,
            balance_min=balance_min,
            balance_max=balance_max,
            sort_by=sort_by,
            sort_order=sort_order
        )

        if export_format == 'csv':
            # 生成CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # 写入表头
            writer.writerow(['ID', '用户名', '邮箱', '余额', '累计充值', '累计消费',
                           '邀请收益', '状态', '注册时间', '最后登录', '邀请码'])

            # 写入数据
            for user in users:
                writer.writerow([
                    user['id'],
                    user['username'] or '',
                    user['email'] or '',
                    f"{user['balance']:.2f}",
                    f"{user['total_recharge']:.2f}",
                    f"{user['total_consumption']:.2f}",
                    f"{user['invite_earnings']:.2f}",
                    '正常' if user['status'] == 1 else '禁用',
                    user['created_at'].strftime('%Y-%m-%d %H:%M:%S') if user['created_at'] else '',
                    user['last_login_at'].strftime('%Y-%m-%d %H:%M:%S') if user['last_login_at'] else '',
                    user['invite_code'] or ''
                ])

            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=users_export.csv'}
            )
        else:
            # 返回JSON
            return jsonify({'success': True, 'data': users})

    # ============ 系统设置相关 API ============

    @admin_bp.route('/api/system/info')
    @admin_required
    def get_system_info():
        """获取系统信息"""
        result = admin_stats.get_system_info()
        return jsonify(result)

    @admin_bp.route('/api/system/clear-logs', methods=['POST'])
    @admin_required
    def clear_logs():
        """清理日志"""
        data = request.get_json() or {}
        days = data.get('days', 30)
        result = admin_stats.clear_logs(days=int(days))
        return jsonify(result)

    @admin_bp.route('/api/system/clear-expired', methods=['POST'])
    @admin_required
    def clear_expired_data():
        """清理过期数据"""
        data = request.get_json() or {}
        days = data.get('days', 90)
        result = admin_stats.clear_expired_data(days=int(days))
        return jsonify(result)

    @admin_bp.route('/api/config/export')
    @admin_required
    def export_config():
        """导出配置"""
        result = admin_stats.export_config()
        if result['success']:
            return Response(
                json.dumps(result['data'], ensure_ascii=False, indent=2),
                mimetype='application/json',
                headers={'Content-Disposition': 'attachment; filename=system_config.json'}
            )
        return jsonify(result)

    @admin_bp.route('/api/config/import', methods=['POST'])
    @admin_required
    def import_config():
        """导入配置"""
        try:
            if 'file' in request.files:
                file = request.files['file']
                config_data = json.load(file)
            else:
                config_data = request.get_json()

            result = admin_stats.import_config(config_data)
            return jsonify(result)
        except json.JSONDecodeError:
            return jsonify({'success': False, 'message': '无效的JSON格式'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    @admin_bp.route('/api/config/reset', methods=['POST'])
    @admin_required
    def reset_config():
        """重置配置为默认值"""
        result = admin_stats.reset_config_to_default()
        return jsonify(result)

    @admin_bp.route('/api/system/test-email', methods=['POST'])
    @admin_required
    def test_email():
        """测试邮件发送"""
        data = request.get_json() or {}
        test_to = data.get('email', '')

        if not test_to:
            return jsonify({'success': False, 'message': '请输入测试邮箱地址'})

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.header import Header

            # 获取配置
            configs = admin_stats.get_system_config()
            smtp_host = configs.get('smtp_host', {}).get('value', 'smtp.qq.com')
            smtp_port = int(configs.get('smtp_port', {}).get('value', '465'))
            smtp_username = configs.get('smtp_username', {}).get('value', '')
            smtp_password = configs.get('smtp_password', {}).get('value', '')
            site_name = configs.get('site_name', {}).get('value', '智能文档处理平台')

            if not smtp_username or not smtp_password:
                return jsonify({'success': False, 'message': '请先配置SMTP用户名和密码'})

            # 构建邮件
            message = MIMEText(f'这是一封来自 {site_name} 的测试邮件，如果您收到此邮件，说明邮件配置正确。', 'plain', 'utf-8')
            message['From'] = Header(f'{site_name} <{smtp_username}>', 'utf-8')
            message['To'] = Header(test_to, 'utf-8')
            message['Subject'] = Header(f'{site_name} - 邮件配置测试', 'utf-8')

            # 发送邮件
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()

            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, [test_to], message.as_string())
            server.quit()

            return jsonify({'success': True, 'message': f'测试邮件已发送到 {test_to}'})
        except Exception as e:
            logger.error(f"发送测试邮件失败: {e}")
            return jsonify({'success': False, 'message': f'发送失败: {str(e)}'})

    @admin_bp.route('/api/system/logs')
    @admin_required
    def get_operation_logs():
        """获取操作日志"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        log_type = request.args.get('type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        result = admin_stats.get_operation_logs(
            page=page,
            per_page=per_page,
            log_type=log_type,
            start_date=start_date,
            end_date=end_date
        )
        return jsonify(result)

    @admin_bp.route('/api/config/batch', methods=['POST'])
    @admin_required
    def batch_update_config():
        """批量更新配置"""
        data = request.get_json() or {}
        settings = data.get('settings', [])

        if not settings:
            return jsonify({'success': False, 'message': '没有要更新的配置'})

        success_count = 0
        error_count = 0

        for setting in settings:
            key = setting.get('key')
            value = setting.get('value')
            if key and value is not None:
                if admin_stats.update_system_config(key, value):
                    success_count += 1
                else:
                    error_count += 1

        if error_count == 0:
            return jsonify({'success': True, 'message': f'成功更新 {success_count} 项配置'})
        else:
            return jsonify({
                'success': success_count > 0,
                'message': f'成功 {success_count} 项，失败 {error_count} 项'
            })

    return admin_bp