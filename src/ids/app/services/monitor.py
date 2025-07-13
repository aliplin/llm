"""
监控服务模块
负责系统状态监控和性能统计
"""

import threading
import time
import sqlite3
from datetime import datetime, timedelta
from ..utils.database import get_db_connection

class Monitor:
    def __init__(self, event_handler, socketio):
        self.event_handler = event_handler
        self.socketio = socketio
        self.running = False
        self.thread = None
        
    def start(self):
        """启动监控服务"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            print("监控服务已启动")
    
    def stop(self):
        """停止监控服务"""
        self.running = False
        if self.thread:
            self.thread.join()
            print("监控服务已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._collect_stats()
                time.sleep(30)  # 每30秒收集一次统计信息
            except Exception as e:
                print(f"监控服务错误: {e}")
                time.sleep(60)  # 出错时等待更长时间
    
    def _collect_stats(self):
        """收集系统统计信息"""
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            # 获取今日事件数量
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            c.execute("SELECT COUNT(*) FROM events WHERE timestamp >= ?", (today_start.strftime("%Y-%m-%d %H:%M:%S"),))
            today_result = c.fetchone()
            today_events = today_result[0] if today_result else 0
            
            # 获取高风险事件数量
            c.execute("SELECT COUNT(*) FROM events WHERE severity = 'high'")
            high_risk_result = c.fetchone()
            high_risk_events = high_risk_result[0] if high_risk_result else 0
            
            # 获取最近1小时的事件数量
            hour_ago = datetime.now() - timedelta(hours=1)
            c.execute("SELECT COUNT(*) FROM events WHERE timestamp >= ?", (hour_ago.strftime("%Y-%m-%d %H:%M:%S"),))
            recent_result = c.fetchone()
            recent_events = recent_result[0] if recent_result else 0
            
            # 获取事件总数
            c.execute("SELECT COUNT(*) FROM events")
            total_result = c.fetchone()
            total_events = total_result[0] if total_result else 0
            
            # 获取活跃规则数量
            c.execute("SELECT COUNT(*) FROM rules WHERE enabled = 1")
            active_rules_result = c.fetchone()
            active_rules = active_rules_result[0] if active_rules_result else 0
            
            conn.close()
            
            # 构建统计信息
            stats = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'today_events': today_events,
                'high_risk_events': high_risk_events,
                'recent_events': recent_events,
                'total_events': total_events,
                'active_rules': active_rules,
                'system_status': 'normal'
            }
            
            # 检查系统状态
            if high_risk_events > 10:
                stats['system_status'] = 'warning'
            if high_risk_events > 50:
                stats['system_status'] = 'critical'
            
            # 通过WebSocket发送统计信息
            if self.socketio:
                self.socketio.emit('system_stats', stats)
            
            print(f"系统统计: 今日事件={today_events}, 高风险={high_risk_events}, 状态={stats['system_status']}")
            
        except Exception as e:
            print(f"收集统计信息失败: {e}")
    
    def get_system_status(self):
        """获取系统状态"""
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            # 获取基本统计信息
            c.execute("SELECT COUNT(*) FROM events")
            total_events = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM events WHERE severity = 'high'")
            high_risk_events = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM rules WHERE enabled = 1")
            active_rules = c.fetchone()[0]
            
            conn.close()
            
            return {
                'total_events': total_events,
                'high_risk_events': high_risk_events,
                'active_rules': active_rules,
                'status': 'running'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'status': 'error'
            }
