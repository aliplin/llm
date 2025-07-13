from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from ..utils.database import get_db_connection
from ..services.rule_engine import RuleEngine
import json

main_bp = Blueprint('main', __name__)
rule_engine = RuleEngine()

@main_bp.route('/')
@login_required
def index():
    """仪表盘页面"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # 获取今日事件数量（从今天00:00:00开始）
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    c.execute("SELECT COUNT(*) FROM events WHERE timestamp >= ?", (today_start.strftime("%Y-%m-%d %H:%M:%S"),))
    today_result = c.fetchone()
    today_events_count = today_result[0] if today_result else 0
    
    # 获取高风险事件数量
    c.execute("SELECT COUNT(*) FROM events WHERE severity = 'high'")
    high_risk_result = c.fetchone()
    high_risk_count = high_risk_result[0] if high_risk_result else 0
    
    # 获取事件类型数量（去重）
    c.execute("SELECT COUNT(DISTINCT event_type) FROM events WHERE event_type IS NOT NULL AND event_type != ''")
    event_types_result = c.fetchone()
    event_types_count = event_types_result[0] if event_types_result else 0
    
    # 获取事件总数
    c.execute("SELECT COUNT(*) FROM events")
    total_events_result = c.fetchone()
    total_events_count = total_events_result[0] if total_events_result else 0
    
    # 获取最近10条事件，包含规则名称
    c.execute("""
        SELECT e.*, r.name as rule_name 
        FROM events e 
        LEFT JOIN rules r ON e.rule_id = r.id 
        ORDER BY e.timestamp DESC 
        LIMIT 10
    """)
    recent_events = c.fetchall()
    
    # 获取事件类型统计
    c.execute("SELECT event_type, COUNT(*) as count FROM events WHERE event_type IS NOT NULL AND event_type != '' GROUP BY event_type ORDER BY count DESC")
    event_stats = c.fetchall()
    
    # 获取严重级别统计
    c.execute("SELECT severity, COUNT(*) as count FROM events GROUP BY severity")
    severity_stats = c.fetchall()
    
    conn.close()
    
    return render_template('index.html',
                           today_events_count=today_events_count,
                           high_risk_count=high_risk_count,
                           event_types_count=event_types_count,
                           total_events_count=total_events_count,
                           recent_events=recent_events,
                           event_stats=event_stats,
                           severity_stats=severity_stats)

@main_bp.route('/realtime')
@login_required
def realtime():
    """实时监控页面"""
    return render_template('realtime.html')

@main_bp.route('/honeypot_log_analysis')
@login_required
def honeypot_log_analysis():
    """蜜罐网络安全日志分析页面"""
    return render_template('honeypot_log_analysis.html')

@main_bp.route('/llm_status')
@login_required
def llm_status():
    """LLM状态页面"""
    return render_template('llm_status.html')

@main_bp.route('/test')
def test():
    """测试路由 - 用于接收攻击载荷并触发规则检测"""
    # 检查请求是否匹配任何规则
    results = rule_engine.check_request(request)
    
    # 如果有检测结果，记录事件
    if results:
        conn = get_db_connection()
        c = conn.cursor()
        
        for result in results:
            if result.get('type') == 'blocked_ip':
                # IP被封禁
                c.execute("""
                    INSERT INTO events (timestamp, ip_address, user_agent, request_path, 
                                      request_method, request_data, severity, status, event_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    request.remote_addr,
                    request.user_agent.string,
                    request.path,
                    request.method,
                    json.dumps(dict(request.args)),
                    'high',
                    'blocked',
                    'ip_block'
                ))
            else:
                # 规则匹配
                c.execute("""
                    INSERT INTO events (rule_id, timestamp, ip_address, user_agent, request_path, 
                                      request_method, request_data, severity, status, event_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.get('rule_id'),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    request.remote_addr,
                    request.user_agent.string,
                    request.path,
                    request.method,
                    json.dumps(dict(request.args)),
                    result.get('severity', 'medium'),
                    'detected',
                    result.get('event_type', 'unknown')
                ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'detected',
            'message': f'检测到 {len(results)} 个安全威胁',
            'results': results
        }), 403  # 返回403表示检测到威胁
    
    return jsonify({
        'status': 'clean',
        'message': '请求正常'
    }), 200

@main_bp.route('/test/<path:filename>')
def test_file(filename):
    """测试文件访问路由"""
    # 检查请求是否匹配任何规则
    results = rule_engine.check_request(request)
    
    # 如果有检测结果，记录事件
    if results:
        conn = get_db_connection()
        c = conn.cursor()
        
        for result in results:
            c.execute("""
                INSERT INTO events (rule_id, timestamp, ip_address, user_agent, request_path, 
                                  request_method, request_data, severity, status, event_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.get('rule_id'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                request.remote_addr,
                request.user_agent.string,
                request.path,
                request.method,
                json.dumps(dict(request.args)),
                result.get('severity', 'medium'),
                'detected',
                result.get('event_type', 'unknown')
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'detected',
            'message': f'检测到 {len(results)} 个安全威胁',
            'results': results
        }), 403
    
    return jsonify({
        'status': 'clean',
        'message': f'文件访问正常: {filename}'
    }), 200

@main_bp.route('/test/deserialize', methods=['POST'])
def test_deserialize():
    """测试反序列化路由"""
    data = request.form.get('data', '')
    
    # 检查请求是否匹配任何规则
    results = rule_engine.check_request(request)
    
    # 如果有检测结果，记录事件
    if results:
        conn = get_db_connection()
        c = conn.cursor()
        
        for result in results:
            c.execute("""
                INSERT INTO events (rule_id, timestamp, ip_address, user_agent, request_path, 
                                  request_method, request_data, severity, status, event_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.get('rule_id'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                request.remote_addr,
                request.user_agent.string,
                request.path,
                request.method,
                json.dumps({'data': data}),
                result.get('severity', 'medium'),
                'detected',
                result.get('event_type', 'unknown')
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'detected',
            'message': f'检测到 {len(results)} 个安全威胁',
            'results': results
        }), 403
    
    return jsonify({
        'status': 'clean',
        'message': '反序列化数据正常'
    }), 200

@main_bp.route('/test/login', methods=['POST'])
def test_login():
    """测试登录绕过路由"""
    # 检查请求是否匹配任何规则
    results = rule_engine.check_request(request)
    
    # 如果有检测结果，记录事件
    if results:
        conn = get_db_connection()
        c = conn.cursor()
        
        for result in results:
            c.execute("""
                INSERT INTO events (rule_id, timestamp, ip_address, user_agent, request_path, 
                                  request_method, request_data, severity, status, event_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.get('rule_id'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                request.remote_addr,
                request.user_agent.string,
                request.path,
                request.method,
                json.dumps(dict(request.form)),
                result.get('severity', 'medium'),
                'detected',
                result.get('event_type', 'unknown')
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'detected',
            'message': f'检测到 {len(results)} 个安全威胁',
            'results': results
        }), 403
    
    return jsonify({
        'status': 'clean',
        'message': '登录尝试正常'
    }), 200

@main_bp.route('/test/upload', methods=['POST'])
def test_upload():
    """测试文件上传路由"""
    # 检查请求是否匹配任何规则
    results = rule_engine.check_request(request)
    
    # 如果有检测结果，记录事件
    if results:
        conn = get_db_connection()
        c = conn.cursor()
        
        for result in results:
            c.execute("""
                INSERT INTO events (rule_id, timestamp, ip_address, user_agent, request_path, 
                                  request_method, request_data, severity, status, event_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.get('rule_id'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                request.remote_addr,
                request.user_agent.string,
                request.path,
                request.method,
                json.dumps({'files': list(request.files.keys())}),
                result.get('severity', 'medium'),
                'detected',
                result.get('event_type', 'unknown')
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'detected',
            'message': f'检测到 {len(results)} 个安全威胁',
            'results': results
        }), 403
    
    return jsonify({
        'status': 'clean',
        'message': '文件上传正常'
    }), 200

@main_bp.route('/test/eval', methods=['POST'])
def test_eval():
    """测试代码执行路由"""
    code = request.form.get('code', '')
    
    # 检查请求是否匹配任何规则
    results = rule_engine.check_request(request)
    
    # 如果有检测结果，记录事件
    if results:
        conn = get_db_connection()
        c = conn.cursor()
        
        for result in results:
            c.execute("""
                INSERT INTO events (rule_id, timestamp, ip_address, user_agent, request_path, 
                                  request_method, request_data, severity, status, event_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.get('rule_id'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                request.remote_addr,
                request.user_agent.string,
                request.path,
                request.method,
                json.dumps({'code': code}),
                result.get('severity', 'medium'),
                'detected',
                result.get('event_type', 'unknown')
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'detected',
            'message': f'检测到 {len(results)} 个安全威胁',
            'results': results
        }), 403
    
    return jsonify({
        'status': 'clean',
        'message': '代码执行正常'
    }), 200 