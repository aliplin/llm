"""
事件处理服务
负责事件检测和WebSocket推送
"""

import threading
import time
from datetime import datetime
from ..utils.database import get_db_connection
from .rule_engine import RuleEngine
import json

class EventHandler:
    """事件处理器"""
    
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.rule_engine = RuleEngine()
        self.running = True
        self.event_queue = []
        self.queue_lock = threading.Lock()
        
        # 启动事件处理线程
        self.event_thread = threading.Thread(target=self._process_events, daemon=True)
        self.event_thread.start()
    
    def add_event(self, event_data):
        """添加事件到队列"""
        with self.queue_lock:
            self.event_queue.append(event_data)
    
    def _process_events(self):
        """处理事件队列"""
        while self.running:
            try:
                events_to_process = []
                
                # 获取队列中的事件
                with self.queue_lock:
                    if self.event_queue:
                        events_to_process = self.event_queue.copy()
                        self.event_queue.clear()
                
                # 处理事件
                for event_data in events_to_process:
                    self._save_event(event_data)
                    self._send_event_notification(event_data)
                
                time.sleep(0.1)  # 短暂休眠
                
            except Exception as e:
                print(f"事件处理错误: {e}")
                time.sleep(1)
    
    def _save_event(self, event_data):
        """保存事件到数据库"""
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            # 序列化request_data
            request_data_str = ''
            if event_data.get('request_data'):
                if isinstance(event_data['request_data'], dict):
                    request_data_str = json.dumps(event_data['request_data'], ensure_ascii=False)
                else:
                    request_data_str = str(event_data['request_data'])
            
            c.execute("""
                INSERT INTO events 
                (timestamp, ip_address, user_agent, request_path, request_method, request_data, severity, status, event_type, rule_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                event_data.get('ip_address', ''),
                event_data.get('user_agent', ''),
                event_data.get('request_path', ''),
                event_data.get('request_method', ''),
                request_data_str,
                event_data.get('severity', 'medium'),
                'detected',
                event_data.get('event_type', 'unknown'),
                event_data.get('rule_id')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"保存事件失败: {e}")
    
    def _send_event_notification(self, event_data):
        """发送事件通知到WebSocket"""
        if not self.socketio:
            return
        
        try:
            # 格式化事件数据
            formatted_event = {
                'id': event_data.get('rule_id'),
                'timestamp': datetime.now().isoformat(),
                'ip_address': event_data.get('ip_address', ''),
                'user_agent': event_data.get('user_agent', ''),
                'request_path': event_data.get('request_path', ''),
                'request_method': event_data.get('request_method', ''),
                'request_data': event_data.get('request_data', {}),
                'severity': event_data.get('severity', 'medium'),
                'status': 'detected',
                'event_type': event_data.get('event_type', 'unknown'),
                'rule_name': event_data.get('rule_name', ''),
                'description': event_data.get('description', ''),
                'matched_pattern': event_data.get('matched_pattern', '')
            }
            
            # 发送事件通知（用于实时监控页面）
            self.socketio.emit('event', {
                'type': 'event',
                'event': formatted_event
            })
            
            # 发送新事件通知（用于仪表盘页面）
            self.socketio.emit('new_event', formatted_event)
            
            # 发送系统状态更新
            self._update_system_status()
            
        except Exception as e:
            print(f"发送事件通知失败: {e}")
    
    def _update_system_status(self):
        """更新系统状态"""
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            # 获取事件统计
            c.execute("SELECT COUNT(*) FROM events")
            total_result = c.fetchone()
            total_events = total_result[0] if total_result else 0
            
            c.execute("SELECT COUNT(*) FROM events WHERE timestamp >= datetime('now', '-1 hour')")
            recent_result = c.fetchone()
            recent_events = recent_result[0] if recent_result else 0
            
            c.execute("SELECT severity, COUNT(*) FROM events GROUP BY severity")
            severity_counts = dict(c.fetchall())
            
            # 获取今日事件数
            c.execute("SELECT COUNT(*) FROM events WHERE DATE(timestamp) = DATE('now')")
            today_result = c.fetchone()
            today_events = today_result[0] if today_result else 0
            
            # 获取高风险事件数
            c.execute("SELECT COUNT(*) FROM events WHERE severity = 'high'")
            high_risk_result = c.fetchone()
            high_risk_events = high_risk_result[0] if high_risk_result else 0
            
            # 获取事件类型数
            c.execute("SELECT COUNT(DISTINCT event_type) FROM events WHERE event_type IS NOT NULL AND event_type != ''")
            event_types_result = c.fetchone()
            event_types = event_types_result[0] if event_types_result else 0
            
            conn.close()
            
            # 发送状态更新（用于实时监控页面）
            if self.socketio:
                self.socketio.emit('system_status', {
                    'total_events': total_events,
                    'recent_events': recent_events,
                    'severity_counts': severity_counts,
                    'timestamp': datetime.now().isoformat()
                })
                
                # 发送统计数据更新（用于仪表盘页面）
                self.socketio.emit('stats_update', {
                    'todayEvents': today_events,
                    'highRiskEvents': high_risk_events,
                    'eventTypes': event_types,
                    'totalEvents': total_events
                })
                
        except Exception as e:
            print(f"更新系统状态失败: {e}")
    
    def check_request(self, request):
        """检查请求是否触发规则"""
        try:
            # 使用规则引擎检查请求
            results = self.rule_engine.check_request(request)
            
            # 处理检测结果
            for result in results:
                if result.get('type') == 'blocked_ip':
                    # IP被封禁
                    self.add_event({
                        'rule_id': None,
                        'rule_name': 'IP封禁',
                        'event_type': 'blocked_ip',
                        'severity': 'high',
                        'description': f'IP {request.remote_addr} 已被封禁',
                        'ip_address': request.remote_addr,
                        'user_agent': request.user_agent.string,
                        'request_path': request.path,
                        'request_method': request.method,
                        'request_data': {
                            'path': request.path,
                            'method': request.method,
                            'args': dict(request.args),
                            'form': dict(request.form),
                            'headers': dict(request.headers)
                        }
                    })
                else:
                    # 规则匹配
                    self.add_event({
                        'rule_id': result.get('rule_id'),
                        'rule_name': result.get('rule_name'),
                        'event_type': result.get('event_type'),
                        'severity': result.get('severity'),
                        'description': result.get('description'),
                        'matched_pattern': result.get('matched_pattern'),
                        'ip_address': request.remote_addr,
                        'user_agent': request.user_agent.string,
                        'request_path': request.path,
                        'request_method': request.method,
                        'request_data': result.get('request_data', {})
                    })
            
            return results
            
        except Exception as e:
            print(f"检查请求失败: {e}")
            return []
    
    def stop(self):
        """停止事件处理器"""
        self.running = False

# 全局事件处理器实例
event_handler = None

def init_event_handler(socketio):
    """初始化事件处理器"""
    global event_handler
    event_handler = EventHandler(socketio)
    return event_handler

def get_event_handler():
    """获取事件处理器实例"""
    return event_handler 