"""
认证API模块
提供用户登录、登出等认证功能
"""

from flask import Blueprint, request, redirect, url_for, render_template, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from ..models.user import User
from ..utils.database import get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('login.html')
        
        # 验证用户
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = c.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[2], password):
            user = User(
                id=user_data[0],
                username=user_data[1],
                password_hash=user_data[2]
            )
            login_user(user, remember=True)
            
            # 获取下一个页面参数
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
            
            flash('登录成功！', 'success')
            return redirect(next_page)
        else:
            flash('用户名或密码错误', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('已成功登出', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """API登录接口"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': '请输入用户名和密码'}), 400
    
    # 验证用户
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_data = c.fetchone()
    conn.close()
    
    if user_data and check_password_hash(user_data[2], password):
        user = User(
            id=user_data[0],
            username=user_data[1],
            password_hash=user_data[2]
        )
        login_user(user, remember=True)
        return jsonify({'success': True, 'message': '登录成功'})
    else:
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

@auth_bp.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    """API登出接口"""
    logout_user()
    return jsonify({'success': True, 'message': '已成功登出'})

@auth_bp.route('/api/check-auth')
def api_check_auth():
    """检查用户认证状态"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username
            }
        })
    else:
        return jsonify({'authenticated': False}), 401
