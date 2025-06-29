"""
蜜罐API模块
提供蜜罐系统相关的统计和分析功能
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from ..utils.database import get_db_connection
from datetime import datetime, timedelta
import json

honeypot_api_bp = Blueprint('honeypot_api', __name__)

@honeypot_api_bp.route('/overview-stats', methods=['GET'])
@login_required
def get_honeypot_overview_stats():
    """获取蜜罐概览统计数据"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 总会话数 - 所有会话的总数
        c.execute("""
            SELECT 
                (SELECT COUNT(*) FROM ssh_session) +
                (SELECT COUNT(*) FROM http_session) +
                (SELECT COUNT(*) FROM mysql_session) +
                (SELECT COUNT(*) FROM pop3_session) as total_sessions
        """)
        total_sessions = c.fetchone()[0] or 0
        
        # 攻击事件数量 - 高风险和中风险事件
        c.execute("""
            SELECT COUNT(*) FROM events 
            WHERE severity IN ('high', 'medium')
        """)
        total_attacks = c.fetchone()[0]
        
        # 活跃会话数 - 最近1小时内的会话
        one_hour_ago = datetime.now() - timedelta(hours=1)
        c.execute("""
            SELECT COUNT(DISTINCT ip_address) FROM events 
            WHERE timestamp >= ? AND ip_address IS NOT NULL AND ip_address != ''
        """, (one_hour_ago.strftime("%Y-%m-%d %H:%M:%S"),))
        active_sessions = c.fetchone()[0]
        
        # 今日新增会话数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        c.execute("""
            SELECT 
                (SELECT COUNT(*) FROM ssh_session WHERE DATE(time_date) = DATE('now')) +
                (SELECT COUNT(*) FROM http_session WHERE DATE(start_time) = DATE('now')) +
                (SELECT COUNT(*) FROM mysql_session WHERE DATE(time_date) = DATE('now')) +
                (SELECT COUNT(*) FROM pop3_session WHERE DATE(time_date) = DATE('now')) as today_sessions
        """)
        today_sessions = c.fetchone()[0] or 0
        
        return jsonify({
            'total_sessions': total_sessions,
            'total_attacks': total_attacks,
            'active_sessions': active_sessions,
            'today_sessions': today_sessions,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@honeypot_api_bp.route('/chart-data', methods=['GET'])
@login_required
def get_honeypot_chart_data():
    """获取蜜罐图表数据"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 服务分布统计 - 使用新的会话表
        c.execute("""
            SELECT 'SSH' as service_type, COUNT(*) as count FROM ssh_session
            UNION ALL
            SELECT 'HTTP' as service_type, COUNT(*) as count FROM http_session
            UNION ALL
            SELECT 'MySQL' as service_type, COUNT(*) as count FROM mysql_session
            UNION ALL
            SELECT 'POP3' as service_type, COUNT(*) as count FROM pop3_session
            ORDER BY count DESC
        """)
        
        service_data = c.fetchall()
        service_labels = [row[0] for row in service_data]
        service_counts = [row[1] for row in service_data]
        
        # 攻击类型统计 - 从events表获取
        c.execute("""
            SELECT event_type, COUNT(*) as count
            FROM events 
            WHERE event_type IS NOT NULL AND event_type != ''
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT 10
        """)
        
        attack_data = c.fetchall()
        attack_labels = [row[0] for row in attack_data]
        attack_counts = [row[1] for row in attack_data]
        
        return jsonify({
            'service_distribution': {
                'labels': service_labels,
                'data': service_counts
            },
            'attack_types': {
                'labels': attack_labels,
                'data': attack_counts
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@honeypot_api_bp.route('/session-trend', methods=['GET'])
@login_required
def get_honeypot_session_trend():
    """获取蜜罐会话趋势数据"""
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
            labels.append(t_start.strftime('%m-%d %H:00'))
            
            # SSH会话
            c.execute("""
                SELECT COUNT(*) FROM ssh_session 
                WHERE time_date >= ? AND time_date < ?
            """, (t_start.strftime("%Y-%m-%d %H:%M:%S"), t_end.strftime("%Y-%m-%d %H:%M:%S")))
            ssh_result = c.fetchone()
            ssh_sessions.append(ssh_result[0] if ssh_result else 0)
            
            # HTTP会话
            c.execute("""
                SELECT COUNT(*) FROM http_session 
                WHERE start_time >= ? AND start_time < ?
            """, (t_start.strftime("%Y-%m-%d %H:%M:%S"), t_end.strftime("%Y-%m-%d %H:%M:%S")))
            http_result = c.fetchone()
            http_sessions.append(http_result[0] if http_result else 0)
            
            # MySQL会话
            c.execute("""
                SELECT COUNT(*) FROM mysql_session 
                WHERE time_date >= ? AND time_date < ?
            """, (t_start.strftime("%Y-%m-%d %H:%M:%S"), t_end.strftime("%Y-%m-%d %H:%M:%S")))
            mysql_result = c.fetchone()
            mysql_sessions.append(mysql_result[0] if mysql_result else 0)
            
            # POP3会话
            c.execute("""
                SELECT COUNT(*) FROM pop3_session 
                WHERE time_date >= ? AND time_date < ?
            """, (t_start.strftime("%Y-%m-%d %H:%M:%S"), t_end.strftime("%Y-%m-%d %H:%M:%S")))
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
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@honeypot_api_bp.route('/realtime-logs', methods=['GET'])
@login_required
def get_honeypot_realtime_logs():
    """获取蜜罐实时日志"""
    level = request.args.get('level', 'all')
    limit = request.args.get('limit', 50, type=int)
    time_range = request.args.get('time_range', 24, type=int)  # 默认24小时
    search = request.args.get('search', '')
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_range)
        
        # 构建搜索条件
        search_condition = ""
        search_params = []
        if search:
            search_condition = "AND (c.command LIKE ? OR a.answer LIKE ?)"
            search_params = [f"%{search}%", f"%{search}%"]
        
        # 根据日志类型过滤
        type_condition = ""
        if level != 'all':
            if level == 'command':
                type_condition = "AND c.command IS NOT NULL"
            elif level == 'http':
                type_condition = "AND h.method IS NOT NULL"
            elif level == 'mysql':
                type_condition = "AND mc.command IS NOT NULL"
            elif level == 'ssh':
                type_condition = "AND s.username IS NOT NULL"
            elif level == 'pop3':
                type_condition = "AND p.username IS NOT NULL"
        
        # 获取最近的命令和响应
        if level in ['all', 'command']:
            c.execute(f"""
                SELECT 
                    c.command_id,
                    c.command,
                    a.answer,
                    c.command_id as timestamp,
                    'command' as type
                FROM commands c
                LEFT JOIN answers a ON c.command_id = a.command_id
                WHERE c.command_id >= ?
                {search_condition}
                {type_condition}
                ORDER BY c.command_id DESC
                LIMIT ?
            """, [int(start_time.timestamp() * 1000)] + search_params + [limit])
            
            command_logs = []
            for row in c.fetchall():
                command_logs.append({
                    'id': row[0],
                    'content': f"命令: {row[1]}",
                    'response': row[2] if row[2] else '无响应',
                    'timestamp': row[3],
                    'type': row[4]
                })
        else:
            command_logs = []
        
        # 获取最近的HTTP请求
        if level in ['all', 'http']:
            http_search_condition = ""
            http_search_params = []
            if search:
                http_search_condition = "AND (h.method LIKE ? OR h.path LIKE ? OR h.response LIKE ?)"
                http_search_params = [f"%{search}%", f"%{search}%", f"%{search}%"]
            
            c.execute(f"""
                SELECT 
                    h.request_id,
                    h.method,
                    h.path,
                    h.request_time,
                    h.response
                FROM http_request h
                WHERE h.request_time >= ?
                {http_search_condition}
                {type_condition}
                ORDER BY h.request_time DESC
                LIMIT ?
            """, [start_time.strftime('%Y-%m-%d %H:%M:%S')] + http_search_params + [limit])
            
            http_logs = []
            for row in c.fetchall():
                http_logs.append({
                    'id': row[0],
                    'content': f"{row[1]} {row[2]}",
                    'response': row[4],
                    'timestamp': row[3],
                    'type': 'http'
                })
        else:
            http_logs = []
        
        # 获取最近的MySQL命令
        if level in ['all', 'mysql']:
            mysql_search_condition = ""
            mysql_search_params = []
            if search:
                mysql_search_condition = "AND (mc.command LIKE ? OR mc.response LIKE ?)"
                mysql_search_params = [f"%{search}%", f"%{search}%"]
            
            c.execute(f"""
                SELECT 
                    mc.command_id,
                    mc.command,
                    mc.response,
                    mc.timestamp,
                    mc.command_type
                FROM mysql_command mc
                WHERE mc.timestamp >= ?
                {mysql_search_condition}
                {type_condition}
                ORDER BY mc.timestamp DESC
                LIMIT ?
            """, [start_time.strftime('%Y-%m-%d %H:%M:%S')] + mysql_search_params + [limit])
            
            mysql_logs = []
            for row in c.fetchall():
                mysql_logs.append({
                    'id': row[0],
                    'content': f"MySQL命令: {row[1]}",
                    'response': row[2] if row[2] else '无响应',
                    'timestamp': row[3],
                    'type': 'mysql'
                })
        else:
            mysql_logs = []
        
        # 获取SSH会话日志
        if level in ['all', 'ssh']:
            ssh_search_condition = ""
            ssh_search_params = []
            if search:
                ssh_search_condition = "AND (s.username LIKE ? OR s.src_ip LIKE ?)"
                ssh_search_params = [f"%{search}%", f"%{search}%"]
            
            c.execute(f"""
                SELECT 
                    s.id,
                    s.username,
                    s.time_date,
                    s.src_ip,
                    'SSH会话' as content,
                    'SSH连接' as response
                FROM ssh_session s
                WHERE s.time_date >= ?
                {ssh_search_condition}
                {type_condition}
                ORDER BY s.time_date DESC
                LIMIT ?
            """, [start_time.strftime('%Y-%m-%d %H:%M:%S')] + ssh_search_params + [limit])
            
            ssh_logs = []
            for row in c.fetchall():
                ssh_logs.append({
                    'id': row[0],
                    'content': f"SSH会话: {row[1]}@{row[3]}",
                    'response': row[5],
                    'timestamp': row[2],
                    'type': 'ssh'
                })
        else:
            ssh_logs = []
        
        # 获取POP3会话日志
        if level in ['all', 'pop3']:
            pop3_search_condition = ""
            pop3_search_params = []
            if search:
                pop3_search_condition = "AND (p.username LIKE ? OR p.src_ip LIKE ?)"
                pop3_search_params = [f"%{search}%", f"%{search}%"]
            
            c.execute(f"""
                SELECT 
                    p.id,
                    p.username,
                    p.time_date,
                    p.src_ip,
                    'POP3会话' as content,
                    'POP3连接' as response
                FROM pop3_session p
                WHERE p.time_date >= ?
                {pop3_search_condition}
                {type_condition}
                ORDER BY p.time_date DESC
                LIMIT ?
            """, [start_time.strftime('%Y-%m-%d %H:%M:%S')] + pop3_search_params + [limit])
            
            pop3_logs = []
            for row in c.fetchall():
                pop3_logs.append({
                    'id': row[0],
                    'content': f"POP3会话: {row[1]}@{row[3]}",
                    'response': row[5],
                    'timestamp': row[2],
                    'type': 'pop3'
                })
        else:
            pop3_logs = []
        
        # 合并并排序所有日志
        all_logs = command_logs + http_logs + mysql_logs + ssh_logs + pop3_logs
        all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'logs': all_logs[:limit],
            'total': len(all_logs),
            'filtered_count': len(all_logs[:limit])
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@honeypot_api_bp.route('/top-attackers', methods=['GET'])
@login_required
def get_top_attackers():
    """获取顶级攻击者统计"""
    limit = request.args.get('limit', 10, type=int)
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 从各个会话表中统计攻击者IP
        c.execute("""
            SELECT 
                src_ip,
                COUNT(*) as session_count,
                'SSH' as service_type
            FROM ssh_session 
            WHERE src_ip IS NOT NULL AND src_ip != ''
            GROUP BY src_ip
            UNION ALL
            SELECT 
                client_ip as src_ip,
                COUNT(*) as session_count,
                'HTTP' as service_type
            FROM http_session 
            WHERE client_ip IS NOT NULL AND client_ip != ''
            GROUP BY client_ip
            UNION ALL
            SELECT 
                src_ip,
                COUNT(*) as session_count,
                'MySQL' as service_type
            FROM mysql_session 
            WHERE src_ip IS NOT NULL AND src_ip != ''
            GROUP BY src_ip
            UNION ALL
            SELECT 
                src_ip,
                COUNT(*) as session_count,
                'POP3' as service_type
            FROM pop3_session 
            WHERE src_ip IS NOT NULL AND src_ip != ''
            GROUP BY src_ip
            ORDER BY session_count DESC
            LIMIT ?
        """, (limit,))
        
        attackers = []
        for row in c.fetchall():
            attackers.append({
                'ip_address': row[0],
                'session_count': row[1],
                'service_type': row[2]
            })
        
        return jsonify({
            'attackers': attackers,
            'total': len(attackers)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@honeypot_api_bp.route('/service-stats', methods=['GET'])
@login_required
def get_service_stats():
    """获取各服务详细统计"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # SSH服务统计
        c.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(DISTINCT src_ip) as unique_attackers,
                COUNT(DISTINCT username) as unique_users
            FROM ssh_session
        """)
        ssh_stats = c.fetchone()
        
        # HTTP服务统计
        c.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(DISTINCT client_ip) as unique_attackers,
                COUNT(DISTINCT method) as unique_methods
            FROM http_session
        """)
        http_stats = c.fetchone()
        
        # MySQL服务统计
        c.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(DISTINCT src_ip) as unique_attackers,
                COUNT(DISTINCT username) as unique_users
            FROM mysql_session
        """)
        mysql_stats = c.fetchone()
        
        # POP3服务统计
        c.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(DISTINCT src_ip) as unique_attackers,
                COUNT(DISTINCT username) as unique_users
            FROM pop3_session
        """)
        pop3_stats = c.fetchone()
        
        return jsonify({
            'ssh': {
                'total_sessions': ssh_stats[0],
                'unique_attackers': ssh_stats[1],
                'unique_users': ssh_stats[2]
            },
            'http': {
                'total_sessions': http_stats[0],
                'unique_attackers': http_stats[1],
                'unique_methods': http_stats[2]
            },
            'mysql': {
                'total_sessions': mysql_stats[0],
                'unique_attackers': mysql_stats[1],
                'unique_users': mysql_stats[2]
            },
            'pop3': {
                'total_sessions': pop3_stats[0],
                'unique_attackers': pop3_stats[1],
                'unique_users': pop3_stats[2]
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@honeypot_api_bp.route('/session-details/<service_type>', methods=['GET'])
@login_required
def get_session_details(service_type):
    """获取特定服务的会话详情"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        offset = (page - 1) * per_page
        
        if service_type.lower() == 'ssh':
            # SSH会话详情
            c.execute("""
                SELECT 
                    id, username, time_date, src_ip, dst_ip, src_port, dst_port
                FROM ssh_session
                ORDER BY time_date DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            
            sessions = []
            for row in c.fetchall():
                sessions.append({
                    'id': row[0],
                    'username': row[1],
                    'time_date': row[2],
                    'src_ip': row[3],
                    'dst_ip': row[4],
                    'src_port': row[5],
                    'dst_port': row[6]
                })
                
        elif service_type.lower() == 'http':
            # HTTP会话详情
            c.execute("""
                SELECT 
                    id, client_ip, start_time, end_time
                FROM http_session
                ORDER BY start_time DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            
            sessions = []
            for row in c.fetchall():
                sessions.append({
                    'id': row[0],
                    'client_ip': row[1],
                    'start_time': row[2],
                    'end_time': row[3]
                })
                
        elif service_type.lower() == 'mysql':
            # MySQL会话详情
            c.execute("""
                SELECT 
                    id, username, time_date, src_ip, dst_ip, src_port, dst_port, database_name
                FROM mysql_session
                ORDER BY time_date DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            
            sessions = []
            for row in c.fetchall():
                sessions.append({
                    'id': row[0],
                    'username': row[1],
                    'time_date': row[2],
                    'src_ip': row[3],
                    'dst_ip': row[4],
                    'src_port': row[5],
                    'dst_port': row[6],
                    'database_name': row[7]
                })
                
        elif service_type.lower() == 'pop3':
            # POP3会话详情
            c.execute("""
                SELECT 
                    id, username, time_date, src_ip, dst_ip, src_port, dst_port
                FROM pop3_session
                ORDER BY time_date DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            
            sessions = []
            for row in c.fetchall():
                sessions.append({
                    'id': row[0],
                    'username': row[1],
                    'time_date': row[2],
                    'src_ip': row[3],
                    'dst_ip': row[4],
                    'src_port': row[5],
                    'dst_port': row[6]
                })
        else:
            return jsonify({"error": "不支持的服务类型"}), 400
        
        return jsonify({
            'sessions': sessions,
            'page': page,
            'per_page': per_page,
            'service_type': service_type
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@honeypot_api_bp.route('/shell-sessions', methods=['GET'])
@login_required
def get_shell_sessions():
    """获取Shell会话列表"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            SELECT 
                id, ssh_session_id, model, start_time, end_time, attacker_id
            FROM shellm_session
            ORDER BY start_time DESC
            LIMIT 50
        """)
        
        sessions = []
        for row in c.fetchall():
            sessions.append({
                'id': row[0],
                'ssh_session_id': row[1],
                'model': row[2],
                'start_time': row[3],
                'end_time': row[4],
                'attacker_id': row[5]
            })
        
        return jsonify({
            'sessions': sessions,
            'total': len(sessions)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@honeypot_api_bp.route('/llm-stats', methods=['GET'])
@login_required
def get_llm_stats():
    """获取LLM相关统计数据"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Shell会话数量
        c.execute("SELECT COUNT(*) FROM shellm_session")
        shell_sessions = c.fetchone()[0]
        
        # 命令执行数量
        c.execute("SELECT COUNT(*) FROM commands")
        commands_executed = c.fetchone()[0]
        
        # 攻击者数量
        c.execute("SELECT COUNT(*) FROM attacker_session")
        attackers = c.fetchone()[0]
        
        # 活跃会话数量（未结束的）
        c.execute("SELECT COUNT(*) FROM shellm_session WHERE end_time IS NULL")
        active_sessions = c.fetchone()[0]
        
        return jsonify({
            'shell_sessions': shell_sessions,
            'commands_executed': commands_executed,
            'attackers': attackers,
            'active_sessions': active_sessions
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@honeypot_api_bp.route('/commands/<int:session_id>', methods=['GET'])
@login_required
def get_session_commands(session_id):
    """获取特定会话的命令列表"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            SELECT 
                c.command_id,
                c.command,
                a.answer
            FROM commands c
            LEFT JOIN answers a ON c.command_id = a.command_id
            WHERE c.shellm_session_id = ?
            ORDER BY c.command_id
        """, (session_id,))
        
        commands = []
        for row in c.fetchall():
            commands.append({
                'command_id': row[0],
                'command': row[1],
                'answer': row[2] if row[2] else '无响应'
            })
        
        return jsonify({
            'session_id': session_id,
            'commands': commands,
            'total': len(commands)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@honeypot_api_bp.route('/export-report', methods=['GET'])
@login_required
def export_honeypot_report():
    """导出蜜罐分析报告"""
    report_type = request.args.get('type', 'csv')  # csv, json
    time_range = request.args.get('time_range', '24')  # 小时数
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=int(time_range))
        
        # 收集报告数据
        report_data = {
            'report_info': {
                'title': '蜜罐网络安全分析报告',
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'time_range': f'最近{time_range}小时'
            },
            'overview_stats': {},
            'service_distribution': {},
            'attack_analysis': {},
            'top_attackers': []
        }
        
        # 概览统计
        c.execute("""
            SELECT 
                (SELECT COUNT(*) FROM ssh_session WHERE time_date >= ?) +
                (SELECT COUNT(*) FROM http_session WHERE start_time >= ?) +
                (SELECT COUNT(*) FROM mysql_session WHERE time_date >= ?) +
                (SELECT COUNT(*) FROM pop3_session WHERE time_date >= ?) as total_sessions
        """, (start_time.strftime('%Y-%m-%d %H:%M:%S'),) * 4)
        total_sessions = c.fetchone()[0] or 0
        
        c.execute("""
            SELECT COUNT(*) FROM events 
            WHERE severity IN ('high', 'medium') AND timestamp >= ?
        """, (start_time.strftime('%Y-%m-%d %H:%M:%S'),))
        total_attacks = c.fetchone()[0] or 0
        
        report_data['overview_stats'] = {
            'total_sessions': total_sessions,
            'total_attacks': total_attacks
        }
        
        # 服务分布
        c.execute("""
            SELECT 'SSH' as service_type, COUNT(*) as count FROM ssh_session WHERE time_date >= ?
            UNION ALL
            SELECT 'HTTP' as service_type, COUNT(*) as count FROM http_session WHERE start_time >= ?
            UNION ALL
            SELECT 'MySQL' as service_type, COUNT(*) as count FROM mysql_session WHERE time_date >= ?
            UNION ALL
            SELECT 'POP3' as service_type, COUNT(*) as count FROM pop3_session WHERE time_date >= ?
            ORDER BY count DESC
        """, (start_time.strftime('%Y-%m-%d %H:%M:%S'),) * 4)
        
        service_data = c.fetchall()
        report_data['service_distribution'] = {
            'services': [row[0] for row in service_data],
            'counts': [row[1] for row in service_data]
        }
        
        # 攻击分析
        c.execute("""
            SELECT event_type, COUNT(*) as count
            FROM events 
            WHERE event_type IS NOT NULL AND event_type != '' AND timestamp >= ?
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT 10
        """, (start_time.strftime('%Y-%m-%d %H:%M:%S'),))
        
        attack_data = c.fetchall()
        report_data['attack_analysis'] = {
            'attack_types': [row[0] for row in attack_data],
            'counts': [row[1] for row in attack_data]
        }
        
        # 顶级攻击者
        c.execute("""
            SELECT 
                src_ip,
                COUNT(*) as session_count,
                'SSH' as service_type
            FROM ssh_session 
            WHERE src_ip IS NOT NULL AND src_ip != '' AND time_date >= ?
            GROUP BY src_ip
            UNION ALL
            SELECT 
                client_ip as src_ip,
                COUNT(*) as session_count,
                'HTTP' as service_type
            FROM http_session 
            WHERE client_ip IS NOT NULL AND client_ip != '' AND start_time >= ?
            GROUP BY client_ip
            ORDER BY session_count DESC
            LIMIT 10
        """, (start_time.strftime('%Y-%m-%d %H:%M:%S'),) * 2)
        
        for row in c.fetchall():
            report_data['top_attackers'].append({
                'ip_address': row[0],
                'session_count': row[1],
                'service_type': row[2]
            })
        
        if report_type == 'json':
            return jsonify(report_data)
        else:
            return generate_csv_report(report_data)
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

def generate_csv_report(report_data):
    """生成CSV格式的报告"""
    from flask import Response
    
    csv_content = []
    
    # 报告信息
    csv_content.append("蜜罐网络安全分析报告")
    csv_content.append(f"生成时间: {report_data['report_info']['generated_at']}")
    csv_content.append(f"时间范围: {report_data['report_info']['time_range']}")
    csv_content.append("")
    
    # 概览统计
    csv_content.append("概览统计")
    csv_content.append("指标,数值")
    csv_content.append(f"总会话数,{report_data['overview_stats']['total_sessions']}")
    csv_content.append(f"攻击事件,{report_data['overview_stats']['total_attacks']}")
    csv_content.append("")
    
    # 服务分布
    csv_content.append("服务分布")
    csv_content.append("服务类型,会话数量")
    for i, service in enumerate(report_data['service_distribution']['services']):
        csv_content.append(f"{service},{report_data['service_distribution']['counts'][i]}")
    csv_content.append("")
    
    # 攻击分析
    csv_content.append("攻击类型分析")
    csv_content.append("攻击类型,次数")
    for i, attack_type in enumerate(report_data['attack_analysis']['attack_types']):
        csv_content.append(f"{attack_type},{report_data['attack_analysis']['counts'][i]}")
    csv_content.append("")
    
    # 顶级攻击者
    csv_content.append("顶级攻击者")
    csv_content.append("IP地址,会话数量,服务类型")
    for attacker in report_data['top_attackers']:
        csv_content.append(f"{attacker['ip_address']},{attacker['session_count']},{attacker['service_type']}")
    
    csv_text = '\n'.join(csv_content)
    
    response = Response(csv_text, mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=honeypot_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response 