"""
IDS入侵检测系统应用包
"""

__version__ = '1.0.0'
__author__ = 'IDS Team'

import os
from flask import Flask, request
from flask_login import LoginManager
from flask_socketio import SocketIO
from .config.settings import Config
from .models.user import User
from .utils.database import get_db_connection

# 创建SocketIO实例
socketio = SocketIO()

def create_app():
    """应用工厂函数"""
    # 获取项目根目录（从app目录向上两级）
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')
    
    print(f"项目根目录: {project_root}")
    print(f"模板目录: {template_dir}")
    print(f"静态文件目录: {static_dir}")
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    app.config.from_object(Config)
    
    # 初始化SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    
    # 初始化Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = c.fetchone()
        conn.close()
        
        if user_data:
            return User(
                id=user_data[0],
                username=user_data[1],
                password_hash=user_data[2]
            )
        return None
    
    # 注册蓝图
    from .api.auth import auth_bp
    from .api.events import events_api_bp
    from .api.rules import rules_api_bp
    from .api.dashboard import dashboard_api_bp
    from .routes.main import main_bp
    from .routes.events import events_bp
    from .routes.rules import rules_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(events_api_bp, url_prefix='/api')
    app.register_blueprint(rules_api_bp, url_prefix='/api')
    app.register_blueprint(dashboard_api_bp, url_prefix='/api')
    app.register_blueprint(main_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(rules_bp)
    
    # 注册WebSocket事件处理器
    from .services.socket_events import register_socket_events
    register_socket_events(socketio)
    
    # 初始化事件处理器
    try:
        from .services.event_handler import init_event_handler
        event_handler = init_event_handler(socketio)
        print("事件处理器初始化成功")
    except Exception as e:
        print(f"事件处理器初始化失败: {e}")
        event_handler = None
    
    # 初始化监控服务
    try:
        from .services.monitor import Monitor
        monitor_service = Monitor(None, socketio)
        monitor_service.start()
        print("监控服务启动成功")
    except Exception as e:
        print(f"监控服务启动失败: {e}")
    
    # 初始化数据包嗅探器
    try:
        from .services.packet_sniffer import PacketSniffer
        packet_sniffer = PacketSniffer(socketio)
        packet_sniffer.start()
        print("数据包嗅探器启动成功")
    except Exception as e:
        print(f"数据包嗅探器启动失败: {e}")
    
    # 注册请求前处理器来检查所有请求
    @app.before_request
    def check_request():
        """检查每个请求是否触发规则"""
        try:
            from .services.event_handler import get_event_handler
            event_handler = get_event_handler()
            if event_handler:
                event_handler.check_request(request)
        except Exception as e:
            print(f"请求检查失败: {e}")
    
    return app
