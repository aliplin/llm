from flask import Flask, jsonify, render_template
from flask_cors import CORS  # Import Flask-CORS
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv('db_credentials.env')

DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
DB_PATH = os.getenv('DB_PATH', 'shellm_sessions.db')

def connect_to_db():
    """连接到SQLite数据库"""
    try:
        # 获取数据库文件的完整路径
        db_file_path = os.path.join(os.path.dirname(__file__), DB_PATH)
        conn = sqlite3.connect(db_file_path)
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
        cursor.execute("SELECT * FROM pop3_session ORDER BY id DESC;")
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
        cursor.execute("SELECT * FROM http_session ORDER BY id DESC;")
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
        cursor.execute("SELECT * FROM mysql_session ORDER BY id DESC;")
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

if __name__ == "__main__":
    app.run(debug=True)