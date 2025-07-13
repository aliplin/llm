from flask import Flask, jsonify, render_template
from flask_cors import CORS #import Flask-CORS
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables from .env file
load_dotenv('config/db_credentials.env')

DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
DB_PATH = os.getenv('DB_PATH', 'shellm_sessions.db')

def connect_to_db():
    """连接到SQLite数据库"""
    try:
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent
        
        # 获取数据库文件的完整路径
        db_file_path = project_root / "src" / "log_manager" / DB_PATH
        conn = sqlite3.connect(str(db_file_path))
        # 设置行工厂，使查询结果返回字典格式
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None, None

current_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__,
            template_folder=os.path.join(current_dir, 'templates'),
            static_folder=os.path.join(current_dir, 'static'))

CORS(app)
print("Current working directory:", os.getcwd())
print("Template folder path:", app.template_folder)

# Route to fetch SSH sessions from the database
@app.route('/ssh_sessions', methods=['GET'])
def get_ssh_sessions():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor.execute("SELECT * FROM ssh_session ORDER BY id DESC;")
        sessions = cursor.fetchall()
        # 将sqlite3.Row对象转换为字典列表
        sessions_list = [dict(row) for row in sessions]
        return jsonify(sessions_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/shellm_sessions', methods=['GET'])
def get_shellm_sessions():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor.execute("SELECT * FROM shellm_session ORDER BY id DESC;")
        sessions = cursor.fetchall()
        sessions_list = [dict(row) for row in sessions]
        return jsonify(sessions_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/commands', methods=['GET'])
def get_commands():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor.execute("SELECT * FROM commands ORDER BY command_id DESC;")
        commands = cursor.fetchall()
        commands_list = [dict(row) for row in commands]
        return jsonify(commands_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/answers', methods=['GET'])
def get_answers():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor.execute("SELECT * FROM answers ORDER BY answer_id DESC;")
        answers = cursor.fetchall()
        answers_list = [dict(row) for row in answers]
        return jsonify(answers_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 在/app.py中添加一个新的路由获取攻击者会话
@app.route('/attacker_sessions', methods=['GET'])
def get_attacker_sessions():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor.execute("SELECT * FROM attacker_session ORDER BY attacker_session_id DESC;")
        sessions = cursor.fetchall()
        sessions_list = [dict(row) for row in sessions]
        return jsonify(sessions_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Route to render the dashboard
@app.route('/', methods=['GET'])
def dashboard():
    return render_template('dashboard.html')

@app.route('/commands_answers/<int:shellm_session_id>', methods=['GET'])
def get_commands_answers(shellm_session_id):
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Fetch commands and their associated answers
        cursor.execute("""
            SELECT c.command_id, c.command, a.answer_id, COALESCE(a.answer, 'No answer') AS answer
            FROM commands c
            LEFT JOIN answers a ON c.command_id = a.command_id
            WHERE c.shellm_session_id = ?
        """, (shellm_session_id,))

        results = cursor.fetchall()
        
        # Return as a JSON response
        return jsonify([
            {
                "command_id": row[0],
                "command": row[1],
                "answer_id": row[2],
                "answer": row[3]
            }
            for row in results
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/pop3_sessions', methods=['GET'])
def get_pop3_sessions():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor.execute("""
            SELECT ps.*, COUNT(pc.command_id) as command_count 
            FROM pop3_session ps 
            LEFT JOIN pop3_command pc ON ps.id = pc.pop3_session_id 
            GROUP BY ps.id 
            ORDER BY ps.id DESC;
        """)
        sessions = cursor.fetchall()
        sessions_list = [dict(row) for row in sessions]
        return jsonify(sessions_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/pop3_commands/<int:session_id>', methods=['GET'])
def get_pop3_commands(session_id):
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor.execute("SELECT * FROM pop3_command WHERE pop3_session_id = ? ORDER BY command_id ASC;", (session_id,))
        commands = cursor.fetchall()
        commands_list = [dict(row) for row in commands]
        return jsonify(commands_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/http_sessions', methods=['GET'])
def get_http_sessions():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor.execute("""
            SELECT hs.*, COUNT(hr.request_id) as request_count 
            FROM http_session hs 
            LEFT JOIN http_request hr ON hs.id = hr.http_session_id 
            GROUP BY hs.id 
            ORDER BY hs.id DESC;
        """)
        sessions = cursor.fetchall()
        sessions_list = [dict(row) for row in sessions]
        return jsonify(sessions_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/http_requests/<int:session_id>', methods=['GET'])
def get_http_requests(session_id):
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor.execute("SELECT * FROM http_request WHERE http_session_id = ? ORDER BY request_id ASC;", (session_id,))
        requests = cursor.fetchall()
        requests_list = [dict(row) for row in requests]
        return jsonify(requests_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# MySQL相关路由
@app.route('/mysql_sessions', methods=['GET'])
def get_mysql_sessions():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor.execute("""
            SELECT ms.*, COUNT(mc.command_id) as command_count 
            FROM mysql_session ms 
            LEFT JOIN mysql_command mc ON ms.id = mc.mysql_session_id 
            GROUP BY ms.id 
            ORDER BY ms.id DESC;
        """)
        sessions = cursor.fetchall()
        sessions_list = [dict(row) for row in sessions]
        return jsonify(sessions_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/mysql_commands/<int:session_id>', methods=['GET'])
def get_mysql_commands(session_id):
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor.execute("SELECT * FROM mysql_command WHERE mysql_session_id = ? ORDER BY command_id ASC;", (session_id,))
        commands = cursor.fetchall()
        commands_list = [dict(row) for row in commands]
        return jsonify(commands_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 统计数据API端点
@app.route('/api/overview-stats', methods=['GET'])
def get_overview_stats():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        # 获取各服务的会话数量
        stats = {}
        
        # SSH会话数
        cursor.execute("SELECT COUNT(*) as count FROM ssh_session")
        stats['ssh_sessions'] = cursor.fetchone()[0]
        
        # HTTP会话数
        cursor.execute("SELECT COUNT(*) as count FROM http_session")
        stats['http_sessions'] = cursor.fetchone()[0]
        
        # MySQL会话数
        cursor.execute("SELECT COUNT(*) as count FROM mysql_session")
        stats['mysql_sessions'] = cursor.fetchone()[0]
        
        # POP3会话数
        cursor.execute("SELECT COUNT(*) as count FROM pop3_session")
        stats['pop3_sessions'] = cursor.fetchone()[0]
        
        # 总会话数
        stats['total_sessions'] = sum([
            stats['ssh_sessions'],
            stats['http_sessions'],
            stats['mysql_sessions'],
            stats['pop3_sessions']
        ])
        
        # 唯一IP数
        cursor.execute("""
            SELECT COUNT(DISTINCT ip) as unique_ips FROM (
                SELECT src_ip as ip FROM ssh_session
                UNION
                SELECT client_ip as ip FROM http_session
                UNION
                SELECT src_ip as ip FROM mysql_session
                UNION
                SELECT src_ip as ip FROM pop3_session
            ) WHERE ip IS NOT NULL AND ip != ''
        """)
        stats['unique_ips'] = cursor.fetchone()[0]
        
        # 威胁等级计算
        total_attacks = stats['total_sessions']
        if total_attacks == 0:
            stats['threat_level'] = '低'
        elif total_attacks < 10:
            stats['threat_level'] = '中'
        elif total_attacks < 50:
            stats['threat_level'] = '高'
        else:
            stats['threat_level'] = '极高'
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/chart-data', methods=['GET'])
def get_chart_data():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        # 服务分布数据
        cursor.execute("SELECT COUNT(*) as count FROM ssh_session")
        ssh_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM http_session")
        http_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM mysql_session")
        mysql_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM pop3_session")
        pop3_count = cursor.fetchone()[0]
        
        service_distribution = {
            'labels': ['SSH', 'HTTP', 'MySQL', 'POP3'],
            'data': [ssh_count, http_count, mysql_count, pop3_count]
        }
        
        # 攻击类型统计
        attack_types = {
            'labels': ['暴力破解', 'SQL注入', 'XSS攻击', '命令注入', '其他'],
            'data': [ssh_count, mysql_count, http_count, 0, 0]  # 简化的分类
        }
        
        # 地理分布数据（基于IP）
        cursor.execute("""
            SELECT ip, COUNT(*) as count FROM (
                SELECT src_ip as ip FROM ssh_session
                UNION ALL
                SELECT client_ip as ip FROM http_session
                UNION ALL
                SELECT src_ip as ip FROM mysql_session
                UNION ALL
                SELECT src_ip as ip FROM pop3_session
            ) WHERE ip IS NOT NULL AND ip != ''
            GROUP BY ip
            ORDER BY count DESC
            LIMIT 10
        """)
        
        geo_data = []
        for row in cursor.fetchall():
            geo_data.append({
                'name': row[0],
                'value': row[1]
            })
        
        return jsonify({
            'service_distribution': service_distribution,
            'attack_types': attack_types,
            'geo_distribution': geo_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/realtime-logs', methods=['GET'])
def get_realtime_logs():
    """获取实时日志数据"""
    try:
        # 这里可以返回最近的日志数据
        # 实际实现中可能需要从日志文件或数据库读取
        logs = [
            {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'level': 'info',
                'message': '系统正常运行中...',
                'service': 'system'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'level': 'warning',
                'message': '检测到可疑连接尝试',
                'service': 'ssh'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S'),
                'level': 'info',
                'message': 'HTTP请求已记录',
                'service': 'http'
            }
        ]
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)