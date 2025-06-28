from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from ..utils.database import get_db_connection
import json

main_bp = Blueprint('main', __name__)

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