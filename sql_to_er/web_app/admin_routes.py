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
    
    return admin_bp