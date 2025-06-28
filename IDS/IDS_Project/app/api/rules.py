from flask import Blueprint, request, jsonify
from flask_login import login_required
from ..utils.database import get_db_connection

rules_api_bp = Blueprint('rules_api', __name__)

@rules_api_bp.route('/rules', methods=['GET'])
@login_required
def get_rules():
    """获取所有规则"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 使用子查询确保每个规则名称只返回一个记录（最新的）
        c.execute("""
            SELECT r.id, r.name, r.pattern, r.description, r.severity, r.category, r.enabled, r.created_at, r.updated_at
            FROM rules r
            INNER JOIN (
                SELECT name, MAX(id) as max_id
                FROM rules
                GROUP BY name
            ) latest ON r.name = latest.name AND r.id = latest.max_id
            ORDER BY r.created_at DESC
        """)
        
        rules = []
        for row in c.fetchall():
            rules.append({
                'id': row[0],
                'name': row[1],
                'pattern': row[2],
                'description': row[3],
                'severity': row[4],
                'category': row[5] or '未知',
                'enabled': bool(row[6]),
                'created_at': row[7],
                'updated_at': row[8]
            })
        
        return jsonify(rules)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@rules_api_bp.route('/rules', methods=['POST'])
@login_required
def create_rule():
    """创建新规则"""
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('pattern'):
        return jsonify({"error": "规则名称和模式是必需的"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            INSERT INTO rules (name, pattern, description, severity, category, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            data.get('name'),
            data.get('pattern'),
            data.get('description', ''),
            data.get('severity', 'medium'),
            data.get('category', '未知'),
            data.get('enabled', True)
        ))
        
        conn.commit()
        rule_id = c.lastrowid
        
        return jsonify({
            "message": "规则创建成功",
            "rule_id": rule_id
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@rules_api_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@login_required
def update_rule(rule_id):
    """更新规则"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "没有提供更新数据"}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 检查规则是否存在
        c.execute("SELECT id FROM rules WHERE id = ?", (rule_id,))
        if not c.fetchone():
            return jsonify({"error": "规则不存在"}), 404
        
        c.execute("""
            UPDATE rules 
            SET name = ?, pattern = ?, description = ?, severity = ?, category = ?, enabled = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (
            data.get('name'),
            data.get('pattern'),
            data.get('description', ''),
            data.get('severity', 'medium'),
            data.get('category', '未知'),
            data.get('enabled', True),
            rule_id
        ))
        
        conn.commit()
        
        return jsonify({"message": "规则更新成功"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@rules_api_bp.route('/rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
def toggle_rule(rule_id):
    """切换规则启用状态"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 获取当前状态
        c.execute("SELECT enabled FROM rules WHERE id = ?", (rule_id,))
        result = c.fetchone()
        
        if not result:
            return jsonify({"error": "规则不存在"}), 404
        
        current_status = bool(result[0])
        new_status = not current_status
        
        # 更新状态
        c.execute("""
            UPDATE rules 
            SET enabled = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (new_status, rule_id))
        
        conn.commit()
        
        return jsonify({
            "message": "规则状态更新成功",
            "enabled": new_status
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@rules_api_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_rule(rule_id):
    """删除规则"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 检查规则是否存在
        c.execute("SELECT id FROM rules WHERE id = ?", (rule_id,))
        if not c.fetchone():
            return jsonify({"error": "规则不存在"}), 404
        
        c.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        conn.commit()
        
        return jsonify({"message": "规则删除成功"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@rules_api_bp.route('/rules/<int:rule_id>', methods=['GET'])
@login_required
def get_rule(rule_id):
    """获取单个规则详情"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            SELECT id, name, pattern, description, severity, category, enabled, created_at, updated_at
            FROM rules 
            WHERE id = ?
        """, (rule_id,))
        
        row = c.fetchone()
        if not row:
            return jsonify({"error": "规则不存在"}), 404
        
        rule = {
            'id': row[0],
            'name': row[1],
            'pattern': row[2],
            'description': row[3],
            'severity': row[4],
            'category': row[5] or '未知',
            'enabled': bool(row[6]),
            'created_at': row[7],
            'updated_at': row[8]
        }
        
        return jsonify(rule)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close() 