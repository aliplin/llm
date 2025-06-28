"""
WebSocket事件处理器
处理实时通信功能
"""

def register_socket_events(socketio):
    """注册WebSocket事件处理器"""
    
    @socketio.on('connect')
    def handle_connect():
        """客户端连接事件"""
        print('客户端已连接')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开连接事件"""
        print('客户端已断开连接')
    
    @socketio.on('join_room')
    def handle_join_room(data):
        """加入房间事件"""
        room = data.get('room')
        if room:
            from flask_socketio import join_room
            join_room(room)
            print(f'客户端加入房间: {room}')
    
    @socketio.on('leave_room')
    def handle_leave_room(data):
        """离开房间事件"""
        room = data.get('room')
        if room:
            from flask_socketio import leave_room
            leave_room(room)
            print(f'客户端离开房间: {room}')
    
    @socketio.on('send_message')
    def handle_send_message(data):
        """发送消息事件"""
        message = data.get('message')
        room = data.get('room')
        if message and room:
            socketio.emit('receive_message', {
                'message': message,
                'timestamp': data.get('timestamp')
            }, room=room)
    
    return socketio 