"""
WebSocket事件处理模块
提供实时日志推送功能
"""

import json
import logging
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from datetime import datetime, timedelta
from ..utils.database import get_db_connection

def register_socket_events(socketio):
    """注册SocketIO事件处理器"""
    
    @socketio.on('connect')
    def handle_connect():
        """客户端连接处理"""
        if not current_user.is_authenticated:
            return False  # 拒绝未认证的连接
        
        logging.info(f"WebSocket客户端连接: {current_user.username}")
        emit('connected', {'message': '连接成功', 'user': current_user.username})

    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开连接处理"""
        logging.info(f"WebSocket客户端断开连接: {current_user.username if current_user.is_authenticated else 'Unknown'}")

    @socketio.on('join_honeypot_logs')
    def handle_join_honeypot_logs(data):
        """加入蜜罐日志房间"""
        if not current_user.is_authenticated:
            return
        
        room = f"honeypot_logs_{current_user.id}"
        join_room(room)
        logging.info(f"用户 {current_user.username} 加入蜜罐日志房间: {room}")
        emit('joined_room', {'room': room, 'message': '已加入蜜罐日志房间'})

    @socketio.on('leave_honeypot_logs')
    def handle_leave_honeypot_logs(data):
        """离开蜜罐日志房间"""
        if not current_user.is_authenticated:
            return
        
        room = f"honeypot_logs_{current_user.id}"
        leave_room(room)
        logging.info(f"用户 {current_user.username} 离开蜜罐日志房间: {room}")
        emit('left_room', {'room': room, 'message': '已离开蜜罐日志房间'})

    @socketio.on('request_log_stats')
    def handle_request_log_stats():
        """处理客户端请求日志统计"""
        if not current_user.is_authenticated:
            return
        
        broadcast_log_stats(socketio)

def broadcast_honeypot_log(socketio, log_data):
    """广播蜜罐日志到所有连接的客户端"""
    try:
        # 获取所有在线用户
        conn = get_db_connection()
        c = conn.cursor()
        
        # 这里可以添加获取在线用户的逻辑
        # 目前简单地向所有房间广播
        
        socketio.emit('new_honeypot_log', log_data, namespace='/')
        logging.info(f"广播蜜罐日志: {log_data.get('type', 'unknown')}")
        
    except Exception as e:
        logging.error(f"广播蜜罐日志失败: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def broadcast_log_stats(socketio):
    """广播日志统计信息"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 获取最近1小时的日志统计
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        # 命令日志统计
        c.execute("""
            SELECT COUNT(*) FROM commands 
            WHERE command_id >= ?
        """, (int(one_hour_ago.timestamp() * 1000),))
        command_count = c.fetchone()[0]
        
        # HTTP请求统计
        c.execute("""
            SELECT COUNT(*) FROM http_request 
            WHERE request_time >= ?
        """, (one_hour_ago.strftime('%Y-%m-%d %H:%M:%S'),))
        http_count = c.fetchone()[0]
        
        # MySQL命令统计
        c.execute("""
            SELECT COUNT(*) FROM mysql_command 
            WHERE timestamp >= ?
        """, (one_hour_ago.strftime('%Y-%m-%d %H:%M:%S'),))
        mysql_count = c.fetchone()[0]
        
        # SSH会话统计
        c.execute("""
            SELECT COUNT(*) FROM ssh_session 
            WHERE time_date >= ?
        """, (one_hour_ago.strftime('%Y-%m-%d %H:%M:%S'),))
        ssh_count = c.fetchone()[0]
        
        stats = {
            'timestamp': datetime.now().isoformat(),
            'command_count': command_count,
            'http_count': http_count,
            'mysql_count': mysql_count,
            'ssh_count': ssh_count,
            'total_count': command_count + http_count + mysql_count + ssh_count
        }
        
        socketio.emit('log_stats_update', stats, namespace='/')
        
    except Exception as e:
        logging.error(f"广播日志统计失败: {e}")
    finally:
        if 'conn' in locals():
            conn.close() 