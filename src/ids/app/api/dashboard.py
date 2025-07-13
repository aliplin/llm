"""
仪表盘API模块
提供仪表盘统计数据和分析功能
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from ..utils.database import get_db_connection
from datetime import datetime, timedelta
import json
import logging

dashboard_api_bp = Blueprint('dashboard_api', __name__)

@dashboard_api_bp.route('/realtime-logs', methods=['GET'])
@login_required
def get_realtime_logs():
    """获取实时日志数据"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 获取最近的事件
        c.execute("""
            SELECT e.*, r.name as rule_name 
            FROM events e 
            LEFT JOIN rules r ON e.rule_id = r.id 
            ORDER BY e.timestamp DESC 
            LIMIT 50
        """)
        
        events = []
        for row in c.fetchall():
            # 解析request_data JSON
            try:
                request_data = json.loads(row[7]) if row[7] else {}
            except Exception as e:
                logging.warning(f"request_data解析失败: {e}, 原始值: {row[7]}")
                request_data = {}
            
            # 映射严重级别为中文
            severity_map = {
                'low': '低',
                'medium': '中',
                'high': '高'
            }
            severity_cn = severity_map.get(row[8], row[8] or '低')
            
            events.append({
                'id': row[0],                    # id
                'rule_id': row[1],               # rule_id
                'timestamp': row[2],             # timestamp
                'ip_address': row[3] or '-',     # ip_address
                'user_agent': row[4] or '-',     # user_agent
                'request_path': row[5] or '-',   # request_path
                'request_method': row[6] or '-', # request_method
                'request_data': request_data,    # request_data
                'severity': severity_cn,         # severity
                'status': row[9] or '-',         # status
                'event_type': row[10] or '未知类型', # event_type
                'rule_name': row[11] or '-'      # rule_name (来自JOIN)
            })
        
        return jsonify(events)
        
    except Exception as e:
        logging.error(f"获取实时日志失败: {e}")
        return jsonify({"error": f"获取实时日志失败: {str(e)}"}), 500
    finally:
        conn.close()

@dashboard_api_bp.route('/index-stats', methods=['GET'])
def get_index_stats():
    """获取仪表盘统计数据"""
    # 获取时间范围参数，支持多种时间范围
    time_range = request.args.get('time_range', '30d')  # 默认30天
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 事件分类统计
        c.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type")
        event_type_stats = [{'type': row[0] or '未知', 'count': row[1]} for row in c.fetchall()]
        
        # 根据时间范围生成事件趋势数据
        trend = []
        
        if time_range == '24h':  # 最近24小时，按小时统计
            # 生成最近24小时的时间点
            now = datetime.now()
            for i in range(23, -1, -1):
                hour_start = (now - timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
                hour_end = hour_start + timedelta(hours=1)
                
                c.execute("""
                    SELECT COUNT(*) FROM events 
                    WHERE timestamp >= ? AND timestamp < ?
                """, (hour_start.strftime("%Y-%m-%d %H:%M:%S"), hour_end.strftime("%Y-%m-%d %H:%M:%S")))
                
                count_result = c.fetchone()
                count = count_result[0] if count_result else 0
                trend.append({
                    'date': hour_start.strftime("%m-%d %H:00"),
                    'count': count,
                    'full_date': hour_start.strftime("%Y-%m-%d %H:%M:%S")
                })
        
        elif time_range == '7d':  # 最近7天，按天统计
            c.execute("""
                SELECT strftime('%m-%d', timestamp) as day, COUNT(*)
                FROM events
                WHERE timestamp >= date('now', '-6 days')
                GROUP BY day
                ORDER BY day ASC
            """)
            trend = [{'date': row[0], 'count': row[1], 'full_date': row[0]} for row in c.fetchall()]
        
        elif time_range == '30d':  # 最近30天，按天统计
            c.execute("""
                SELECT strftime('%m-%d', timestamp) as day, COUNT(*)
                FROM events
                WHERE timestamp >= date('now', '-29 days')
                GROUP BY day
                ORDER BY day ASC
            """)
            trend = [{'date': row[0], 'count': row[1], 'full_date': row[0]} for row in c.fetchall()]
        
        elif time_range == '90d':  # 最近90天，按周统计
            c.execute("""
                SELECT strftime('%Y-W%W', timestamp) as week, COUNT(*)
                FROM events
                WHERE timestamp >= date('now', '-89 days')
                GROUP BY week
                ORDER BY week ASC
            """)
            trend = [{'date': f"第{row[0].split('-W')[1]}周", 'count': row[1], 'full_date': row[0]} for row in c.fetchall()]
        
        elif time_range == '1y':  # 最近1年，按月统计
            c.execute("""
                SELECT strftime('%Y-%m', timestamp) as month, COUNT(*)
                FROM events
                WHERE timestamp >= date('now', '-364 days')
                GROUP BY month
                ORDER BY month ASC
            """)
            trend = [{'date': row[0][5:], 'count': row[1], 'full_date': row[0]} for row in c.fetchall()]
        
        else:  # 默认30天
            c.execute("""
                SELECT strftime('%m-%d', timestamp) as day, COUNT(*)
                FROM events
                WHERE timestamp >= date('now', '-29 days')
                GROUP BY day
                ORDER BY day ASC
            """)
            trend = [{'date': row[0], 'count': row[1], 'full_date': row[0]} for row in c.fetchall()]
        
        return jsonify({
            'event_type_stats': event_type_stats,
            'trend': trend,
            'time_range': time_range
        })
        
    except Exception as e:
        logging.error(f"获取仪表盘统计数据失败: {e}")
        return jsonify({"error": f"获取仪表盘统计数据失败: {str(e)}"}), 500
    finally:
        conn.close()

@dashboard_api_bp.route('/session-trend', methods=['GET'])
def get_session_trend():
    """获取会话趋势数据"""
    time_range = int(request.args.get('time_range', 24))  # 小时数，默认24小时
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        now = datetime.now()
        labels = []
        ssh_sessions, http_sessions, mysql_sessions, pop3_sessions = [], [], [], []
        
        for i in range(time_range-1, -1, -1):
            t_start = (now - timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
            t_end = t_start + timedelta(hours=1)
            labels.append(t_start.strftime('%Y-%m-%d %H:00'))
            
            # SSH攻击事件
            c.execute("SELECT COUNT(*) FROM events WHERE event_type = 'SSH攻击' AND timestamp >= ? AND timestamp < ?", 
                     (t_start.strftime("%Y-%m-%d %H:%M:%S"), t_end.strftime("%Y-%m-%d %H:%M:%S")))
            ssh_result = c.fetchone()
            ssh_sessions.append(ssh_result[0] if ssh_result else 0)
            
            # HTTP攻击事件
            c.execute("SELECT COUNT(*) FROM events WHERE event_type IN ('HTTP攻击', 'XSS攻击') AND timestamp >= ? AND timestamp < ?", 
                     (t_start.strftime("%Y-%m-%d %H:%M:%S"), t_end.strftime("%Y-%m-%d %H:%M:%S")))
            http_result = c.fetchone()
            http_sessions.append(http_result[0] if http_result else 0)
            
            # MySQL攻击事件
            c.execute("SELECT COUNT(*) FROM events WHERE event_type = 'SQL注入' AND timestamp >= ? AND timestamp < ?", 
                     (t_start.strftime("%Y-%m-%d %H:%M:%S"), t_end.strftime("%Y-%m-%d %H:%M:%S")))
            mysql_result = c.fetchone()
            mysql_sessions.append(mysql_result[0] if mysql_result else 0)
            
            # POP3攻击事件
            c.execute("SELECT COUNT(*) FROM events WHERE event_type = 'POP3攻击' AND timestamp >= ? AND timestamp < ?", 
                     (t_start.strftime("%Y-%m-%d %H:%M:%S"), t_end.strftime("%Y-%m-%d %H:%M:%S")))
            pop3_result = c.fetchone()
            pop3_sessions.append(pop3_result[0] if pop3_result else 0)
        
        return jsonify({
            'labels': labels,
            'ssh_sessions': ssh_sessions,
            'http_sessions': http_sessions,
            'mysql_sessions': mysql_sessions,
            'pop3_sessions': pop3_sessions
        })
        
    except Exception as e:
        logging.error(f"获取会话趋势数据失败: {e}")
        return jsonify({"error": f"获取会话趋势数据失败: {str(e)}"}), 500
    finally:
        conn.close()

@dashboard_api_bp.route('/dashboard/stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    """获取仪表盘统计数据"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 今日事件数
        c.execute("""
            SELECT COUNT(*) FROM events 
            WHERE DATE(timestamp) = DATE('now')
        """)
        today_events = c.fetchone()[0]
        
        # 高风险事件数
        c.execute("""
            SELECT COUNT(*) FROM events 
            WHERE severity = 'high'
        """)
        high_risk_events = c.fetchone()[0]
        
        # 事件类型数
        c.execute("""
            SELECT COUNT(DISTINCT event_type) FROM events 
            WHERE event_type IS NOT NULL AND event_type != ''
        """)
        event_types = c.fetchone()[0]
        
        # 事件总数
        c.execute("SELECT COUNT(*) FROM events")
        total_events = c.fetchone()[0]
        
        return jsonify({
            'today_events': today_events,
            'high_risk_events': high_risk_events,
            'event_types': event_types,
            'total_events': total_events
        })
        
    except Exception as e:
        logging.error(f"获取仪表盘统计数据失败: {e}")
        return jsonify({"error": f"获取仪表盘统计数据失败: {str(e)}"}), 500
    finally:
        conn.close()

@dashboard_api_bp.route('/dashboard/recent-events', methods=['GET'])
@login_required
def get_recent_events():
    """获取最近事件列表"""
    limit = request.args.get('limit', 10, type=int)
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 获取最近事件
        c.execute("""
            SELECT e.*, r.name as rule_name, r.pattern as rule_pattern
            FROM events e 
            LEFT JOIN rules r ON e.rule_id = r.id 
            ORDER BY e.timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        events = []
        for row in c.fetchall():
            # 解析request_data JSON
            try:
                request_data = json.loads(row[7]) if row[7] else {}
            except Exception as e:
                logging.warning(f"request_data解析失败: {e}, 原始值: {row[7]}")
                request_data = {}
            
            # 映射严重级别为中文
            severity_map = {
                'low': '低',
                'medium': '中',
                'high': '高'
            }
            severity_cn = severity_map.get(row[8], row[8] or '低')
            
            events.append({
                'id': row[0],                    # id
                'rule_id': row[1],               # rule_id
                'timestamp': row[2],             # timestamp
                'ip_address': row[3] or '-',     # ip_address
                'user_agent': row[4] or '-',     # user_agent
                'request_path': row[5] or '-',   # request_path
                'request_method': row[6] or '-', # request_method
                'request_data': request_data,    # request_data
                'severity': severity_cn,         # severity
                'status': row[9] or '-',         # status
                'event_type': row[10] or '未知类型', # event_type
                'rule_name': row[11] or '-',     # rule_name (来自JOIN)
                'rule_pattern': row[12] or '-'   # rule_pattern (来自JOIN)
            })
        
        return jsonify({
            'events': events,
            'total': len(events)
        })
        
    except Exception as e:
        logging.error(f"获取最近事件失败: {e}")
        return jsonify({"error": f"获取最近事件失败: {str(e)}"}), 500
    finally:
        conn.close()

@dashboard_api_bp.route('/dashboard/trend', methods=['GET'])
@login_required
def get_trend_data():
    """获取趋势数据"""
    time_range = request.args.get('range', '7d')  # 7d, 30d, 90d
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        if time_range == '7d':
            c.execute("""
                SELECT strftime('%Y-%m-%d', timestamp) as date, COUNT(*) as count
                FROM events
                WHERE timestamp >= date('now', '-6 days')
                GROUP BY date
                ORDER BY date ASC
            """)
        elif time_range == '30d':
            c.execute("""
                SELECT strftime('%Y-%m-%d', timestamp) as date, COUNT(*) as count
                FROM events
                WHERE timestamp >= date('now', '-29 days')
                GROUP BY date
                ORDER BY date ASC
            """)
        elif time_range == '90d':
            c.execute("""
                SELECT strftime('%Y-W%W', timestamp) as week, COUNT(*) as count
                FROM events
                WHERE timestamp >= date('now', '-89 days')
                GROUP BY week
                ORDER BY week ASC
            """)
        else:
            return jsonify({"error": "不支持的时间范围"}), 400
        
        trend_data = [{'date': row[0], 'count': row[1]} for row in c.fetchall()]
        
        return jsonify({
            'range': time_range,
            'data': trend_data
        })
        
    except Exception as e:
        logging.error(f"获取趋势数据失败: {e}")
        return jsonify({"error": f"获取趋势数据失败: {str(e)}"}), 500
    finally:
        conn.close()

@dashboard_api_bp.route('/dashboard/top-ips', methods=['GET'])
@login_required
def get_top_ips():
    """获取最活跃的IP地址"""
    limit = request.args.get('limit', 10, type=int)
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            SELECT ip_address, COUNT(*) as count
            FROM events
            WHERE ip_address IS NOT NULL AND ip_address != ''
            GROUP BY ip_address
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        top_ips = [{'ip': row[0], 'count': row[1]} for row in c.fetchall()]
        
        return jsonify(top_ips)
        
    except Exception as e:
        logging.error(f"获取最活跃IP失败: {e}")
        return jsonify({"error": f"获取最活跃IP失败: {str(e)}"}), 500
    finally:
        conn.close()

@dashboard_api_bp.route('/dashboard/severity-distribution', methods=['GET'])
@login_required
def get_severity_distribution():
    """获取严重级别分布"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            SELECT severity, COUNT(*) as count
            FROM events
            GROUP BY severity
            ORDER BY count DESC
        """)
        
        distribution = [{'severity': row[0] or 'unknown', 'count': row[1]} for row in c.fetchall()]
        
        return jsonify(distribution)
        
    except Exception as e:
        logging.error(f"获取严重级别分布失败: {e}")
        return jsonify({"error": f"获取严重级别分布失败: {str(e)}"}), 500
    finally:
        conn.close()
