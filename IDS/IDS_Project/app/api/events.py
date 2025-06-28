"""
事件API模块
提供事件查询、过滤、操作等功能
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from ..utils.database import get_db_connection
import json

events_api_bp = Blueprint('events_api', __name__)

@events_api_bp.route('/events', methods=['GET'])
@login_required
def get_events():
    """获取事件列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    event_type = request.args.get('event_type', '')
    severity = request.args.get('severity', '')
    ip_address = request.args.get('ip_address', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    search = request.args.get('search', '')
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 构建查询条件
        where_conditions = []
        params = []
        
        if event_type:
            where_conditions.append("e.event_type LIKE ?")
            params.append(f"%{event_type}%")
        
        if severity:
            where_conditions.append("e.severity = ?")
            params.append(severity)
        
        if ip_address:
            where_conditions.append("e.ip_address LIKE ?")
            params.append(f"%{ip_address}%")
        
        if start_date:
            where_conditions.append("DATE(e.timestamp) >= ?")
            params.append(start_date)
        
        if end_date:
            where_conditions.append("DATE(e.timestamp) <= ?")
            params.append(end_date)
        
        if search:
            where_conditions.append("(e.ip_address LIKE ? OR e.request_path LIKE ? OR e.event_type LIKE ?)")
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # 获取总数
        count_query = f"""
            SELECT COUNT(*) 
            FROM events e 
            WHERE {where_clause}
        """
        c.execute(count_query, params)
        total = c.fetchone()[0]
        
        # 获取分页数据
        offset = (page - 1) * per_page
        query = f"""
            SELECT e.*, r.name as rule_name 
            FROM events e 
            LEFT JOIN rules r ON e.rule_id = r.id 
            WHERE {where_clause}
            ORDER BY e.timestamp DESC 
            LIMIT ? OFFSET ?
        """
        c.execute(query, params + [per_page, offset])
        
        events = []
        for row in c.fetchall():
            # 解析request_data JSON
            try:
                request_data = json.loads(row[7]) if row[7] else {}
            except:
                request_data = {}
            
            events.append({
                'id': row[0],
                'timestamp': row[2],
                'ip_address': row[3] or '-',
                'user_agent': row[4] or '-',
                'request_path': row[5] or '-',
                'request_method': row[6] or '-',
                'request_data': request_data,
                'severity': row[8] or 'low',
                'status': row[9] or '-',
                'event_type': row[10] or '未知类型',
                'rule_name': row[11] or '-'
            })
        
        return jsonify({
            'events': events,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@events_api_bp.route('/events/<int:event_id>', methods=['GET'])
@login_required
def get_event(event_id):
    """获取单个事件详情"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            SELECT e.*, r.name as rule_name, r.pattern as rule_pattern
            FROM events e 
            LEFT JOIN rules r ON e.rule_id = r.id 
            WHERE e.id = ?
        """, (event_id,))
        
        row = c.fetchone()
        if not row:
            return jsonify({"error": "事件不存在"}), 404
        
        # 解析request_data JSON
        try:
            request_data = json.loads(row[7]) if row[7] else {}
        except:
            request_data = {}
        
        event = {
            'id': row[0],
            'timestamp': row[2],
            'ip_address': row[3] or '-',
            'user_agent': row[4] or '-',
            'request_path': row[5] or '-',
            'request_method': row[6] or '-',
            'request_data': request_data,
            'severity': row[8] or 'low',
            'status': row[9] or '-',
            'event_type': row[10] or '未知类型',
            'rule_name': row[11] or '-',
            'rule_pattern': row[12] or '-'
        }
        
        return jsonify(event)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@events_api_bp.route('/events/<int:event_id>/block', methods=['POST'])
@login_required
def block_event(event_id):
    """阻止事件相关的IP地址"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 获取事件信息
        c.execute("SELECT ip_address FROM events WHERE id = ?", (event_id,))
        result = c.fetchone()
        
        if not result:
            return jsonify({"error": "事件不存在"}), 404
        
        ip_address = result[0]
        if not ip_address:
            return jsonify({"error": "事件没有IP地址信息"}), 400
        
        # 这里可以添加IP阻止逻辑
        # 例如：将IP添加到阻止列表，更新防火墙规则等
        
        # 更新事件状态
        c.execute("UPDATE events SET status = 'blocked' WHERE id = ?", (event_id,))
        conn.commit()
        
        return jsonify({
            "message": f"已阻止IP地址: {ip_address}",
            "ip_address": ip_address
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@events_api_bp.route('/events/<int:event_id>/ignore', methods=['POST'])
@login_required
def ignore_event(event_id):
    """忽略事件"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 检查事件是否存在
        c.execute("SELECT id FROM events WHERE id = ?", (event_id,))
        if not c.fetchone():
            return jsonify({"error": "事件不存在"}), 404
        
        # 更新事件状态
        c.execute("UPDATE events SET status = 'ignored' WHERE id = ?", (event_id,))
        conn.commit()
        
        return jsonify({"message": "事件已忽略"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@events_api_bp.route('/events/clear', methods=['POST'])
@login_required
def clear_events():
    """清空所有事件"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("DELETE FROM events")
        conn.commit()
        
        return jsonify({"message": "所有事件已清空"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@events_api_bp.route('/events/types', methods=['GET'])
@login_required
def get_event_types():
    """获取事件类型列表"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("SELECT DISTINCT event_type FROM events WHERE event_type IS NOT NULL AND event_type != '' ORDER BY event_type")
        event_types = [row[0] for row in c.fetchall()]
        
        return jsonify(event_types)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@events_api_bp.route('/block_ip', methods=['POST'])
@login_required
def block_ip():
    """阻止IP地址"""
    try:
        data = request.get_json()
        ip_address = data.get('ip')
        
        if not ip_address:
            return jsonify({"error": "缺少IP地址参数"}), 400
        
        # 导入规则引擎
        from ..services.rule_engine import RuleEngine
        rule_engine = RuleEngine()
        
        # 阻止IP地址（默认1小时）
        rule_engine.block_ip(ip_address, duration=3600)
        
        # 更新相关事件状态
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE events SET status = 'blocked' WHERE ip_address = ?", (ip_address,))
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": f"IP地址 {ip_address} 已被阻止",
            "ip_address": ip_address,
            "duration": "1小时"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
