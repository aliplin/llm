import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO
import re
import time
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import threading
import json
from scapy.all import sniff, Raw
from scapy.layers.inet import  IP, TCP
import logging
import pytz  # 导入 pytz 库
import csv
from flask import Response
import io

# 禁用 Flask 的开发服务器警告(消除WARNING)
#log = logging.getLogger('werkzeug')
#log.setLevel(logging.ERROR)
app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 初始化数据库
def init_db():
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    with open('schema.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()
    c.executescript(sql_script)
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        admin_password = generate_password_hash('admin123')
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('admin', admin_password, 'admin'))
    # 检查 events 表是否有 event_type 列，如果没有则添加
    c.execute("PRAGMA table_info(events)")
    columns = [col[1] for col in c.fetchall()]
    if 'event_type' not in columns:
        c.execute("ALTER TABLE events ADD COLUMN event_type TEXT")
    conn.commit()
    conn.close()

# 用户类
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 规则引擎类
class RuleEngine:
    def __init__(self):
        self.rules = []
        self.load_rules()
        self.lock = threading.Lock()
        self.blocked_ips = {}

    def load_rules(self):
        conn = sqlite3.connect('ids.db')
        c = conn.cursor()
        c.execute("SELECT * FROM rules WHERE enabled = 1")
        rules_data = c.fetchall()
        conn.close()
        self.rules = []
        for rule in rules_data:
            try:
                pattern = re.compile(rule[3], re.IGNORECASE)
                self.rules.append({
                    'id': rule[0],
                    'name': rule[1],
                    'pattern': pattern,
                    'severity': rule[4],
                    'category': rule[5],
                    'description': rule[2]
                })
            except re.error:
                print(f"无效的正则表达式模式: {rule[3]}")

    def check_request(self, request):
        ip = request.remote_addr
        if ip in self.blocked_ips:
            if time.time() < self.blocked_ips[ip]:
                return [{'type': 'blocked_ip', 'severity': 'high'}]
            else:
                del self.blocked_ips[ip]
        results = []
        request_data = {
            'path': request.path,
            'method': request.method,
            'args': dict(request.args),
            'form': dict(request.form),
            'headers': dict(request.headers),
            'ip': ip,
            'user_agent': request.user_agent.string
        }
        for rule in self.rules:
            targets = [
                request.path,
                str(request.args),
                str(request.form),
                request.user_agent.string
            ]
            for target in targets:
                if rule['pattern'].search(target):
                    results.append({
                        'rule_id': rule['id'],
                        'rule_name': rule['name'],
                        'event_type': rule['category'],
                        'severity': rule['severity'],
                        'description': rule['description'],
                        'matched_pattern': rule['pattern'].pattern,
                        'request_data': request_data
                    })
                    break
        return results

    def block_ip(self, ip, duration=3600):
        self.blocked_ips[ip] = time.time() + duration
        return True

# 日志记录类
class Logger:
    def __init__(self):
        # 配置日志记录器
        self.logger = logging.getLogger('IDSLogger')
        self.logger.setLevel(logging.INFO)

        # 创建控制台处理器
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # 创建日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)

        # 添加处理器到日志记录器
        self.logger.addHandler(ch)

        # 禁用重复日志
        self.logger.propagate = False

    def log_event(self, event_data):
        conn = sqlite3.connect('ids.db')
        c = conn.cursor()
        try:
            # 不提供timestamp值，让数据库自动生成
            c.execute('''
                      INSERT INTO events
                      (rule_id, ip_address, user_agent, request_path, request_method,
                       request_data, severity, status, event_type)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                      ''', (
                          event_data.get('rule_id'),
                          event_data['request_data']['ip'],
                          event_data['request_data']['user_agent'],
                          event_data['request_data']['path'],
                          event_data['request_data']['method'],
                          json.dumps(event_data['request_data']),
                          event_data['severity'],
                          'detected',
                          event_data['event_type']
                      ))
            c.execute("SELECT value FROM settings WHERE name = 'max_events'")
            max_events = int(c.fetchone()[0])
            c.execute("SELECT COUNT(*) FROM events")
            count = c.fetchone()[0]
            if count > max_events:
                delete_count = int(max_events * 0.2)
                c.execute('''
                          DELETE
                          FROM events
                          WHERE id IN (SELECT id
                                       FROM events
                                       ORDER BY timestamp ASC
                              LIMIT ?
                              )
                          ''', (delete_count,))
            conn.commit()
            self.logger.info(f"事件已记录: {event_data.get('rule_name')}")
        except Exception as e:
            self.logger.error(f"记录事件失败: {str(e)}")
            # 打印详细的错误堆栈信息
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            conn.close()

    # 添加更多日志方法，方便使用
    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

# 数据包嗅探类
class PacketSniffer(threading.Thread):
    def __init__(self, rule_engine, iface='WLAN'):
        super().__init__()
        self.rule_engine = rule_engine
        self.iface = iface
        self.daemon = True
        self.running = True

    def run(self):
        sniff(iface=self.iface, prn=self.process_packet, store=False)

    def process_packet(self, packet):
        # 生成完整的日期时间，指定时区为 UTC+8
        tz = pytz.timezone('Asia/Shanghai')
        current_time = datetime.now(tz)
        packet_data = {
            'time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
            'summary': packet.summary(),
            'src_ip': packet[IP].src if IP in packet else 'N/A',
            'dst_ip': packet[IP].dst if IP in packet else 'N/A',
            'src_port': packet[TCP].sport if TCP in packet else 'N/A',
            'dst_port': packet[TCP].dport if TCP in packet else 'N/A',
            'protocol': packet.__class__.__name__,
            'payload': str(packet[Raw].load) if Raw in packet else None
        }
        socketio.emit('packet', {'type': 'packet', 'packet': packet_data})
        if packet.haslayer(Raw):
            payload = packet[Raw].load.decode('utf-8', errors='ignore')
            src_ip = packet[IP].src
            for rule in self.rule_engine.rules:
                if rule['pattern'].search(payload):
                    request_data = {
                        'path': 'raw_packet',
                        'method': 'N/A',
                        'args': {},
                        'form': {},
                        'headers': {},
                        'ip': src_ip,
                        'user_agent': 'N/A'
                    }
                    event_data = {
                        'rule_id': rule['id'],
                        'rule_name': rule['name'],
                        'event_type': rule['category'],
                        'severity': rule['severity'],
                        'description': rule['description'],
                        'matched_pattern': rule['pattern'].pattern,
                        'ip': src_ip,
                        'path': 'raw_packet',
                        'time': current_time.strftime("%H:%M:%S"),
                        'request_data': request_data
                    }
                    logger.log_event(event_data)
                    socketio.emit('event', {'type': 'event', 'event': event_data})
                    print(f"[ALERT] Detected raw traffic match: {event_data}")

# 监控类
class Monitor(threading.Thread):
    def __init__(self, rule_engine):
        super().__init__()
        self.rule_engine = rule_engine
        self.running = True
        self.daemon = True

    def run(self):
        while self.running:
            conn = sqlite3.connect('ids.db')
            c = conn.cursor()
            tz = pytz.timezone('Asia/Shanghai')
            five_min_ago = datetime.now(tz) - timedelta(minutes=5)
            c.execute('''
                      SELECT COUNT(*)
                      FROM events
                      WHERE severity = 'high'
                        AND timestamp
                          > ?
                      ''', (five_min_ago.strftime("%Y-%m-%d %H:%M:%S"),))
            high_severity_count = c.fetchone()[0]
            if high_severity_count > 10:
                self.send_alert(f"检测到{high_severity_count}个高严重性事件")
            self.rule_engine.load_rules()
            conn.close()
            time.sleep(60)

    def send_alert(self, message):
        print(f"[ALERT] {message}")

# 用户加载回调
@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    return None

# 登录前处理
@app.before_request
def before_request():
    if request.path.startswith('/static/') or request.path == '/login' or request.path == '/static/favicon.ico':
        return
    if not current_user.is_authenticated:
        if request.method == 'POST':
            return jsonify({"error": "未授权访问"}), 401
        return redirect(url_for('login'))
    matches = rule_engine.check_request(request)
    for match in matches:
        request_data = {
            'path': request.path,
            'method': request.method,
            'args': dict(request.args),
            'form': dict(request.form),
            'headers': dict(request.headers),
            'ip': request.remote_addr,
            'user_agent': request.user_agent.string
        }
        logger.log_event({
            'rule_id': match['rule_id'],
            'rule_name': match['rule_name'],
            'event_type': match['event_type'],
            'severity': match['severity'],
            'description': match['description'],
            'matched_pattern': match['matched_pattern'],
            'request_data': request_data
        })

# 首页路由
@app.route('/')
@login_required
def index():
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    c.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 10")
    recent_events = c.fetchall()
    c.execute("SELECT event_type, COUNT(*) as count FROM events GROUP BY event_type ORDER BY count DESC")
    event_stats = c.fetchall()
    c.execute("SELECT severity, COUNT(*) as count FROM events GROUP BY severity")
    severity_stats = c.fetchall()
    conn.close()
    return render_template('index.html',
                           recent_events=recent_events,
                           event_stats=event_stats,
                           severity_stats=severity_stats)

# 事件日志路由
@app.route('/events')
@login_required
def events():
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    c.execute("SELECT * FROM events ORDER BY timestamp DESC")
    events = c.fetchall()
    conn.close()
    return render_template('events.html', events=events)

# 实时监控路由
@app.route('/realtime')
@login_required
def realtime():
    return render_template('realtime.html')

# 检测规则路由
@app.route('/rules')
@login_required
def rules():
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    c.execute("SELECT * FROM rules")
    rules = c.fetchall()
    conn.close()
    return render_template('rules.html', rules=rules)

# 添加规则路由
@app.route('/rules/add', methods=['POST'])
@login_required
def add_rule():
    rule_name = request.form.get('rule_name')
    pattern = request.form.get('pattern')
    event_type = request.form.get('event_type')
    severity = request.form.get('severity')
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO rules (rule_name, pattern, event_type, severity) VALUES (?, ?, ?, ?)",
                  (rule_name, pattern, event_type, severity))
        conn.commit()
        rule_engine.load_rules()
        status = "success"
        message = "规则添加成功"
    except sqlite3.IntegrityError:
        status = "error"
        message = "规则名称已存在"
    except Exception as e:
        status = "error"
        message = f"添加规则失败: {str(e)}"
    conn.close()
    return jsonify({"status": status, "message": message})

# 切换规则状态路由
@app.route('/rules/toggle/<int:rule_id>', methods=['POST'])
@login_required
def toggle_rule(rule_id):
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    c.execute("SELECT enabled FROM rules WHERE id = ?", (rule_id,))
    result = c.fetchone()
    if result:
        current_status = result[0]
        new_status = 0 if current_status else 1
        c.execute("UPDATE rules SET enabled = ? WHERE id = ?", (new_status, rule_id))
        conn.commit()
        rule_engine.load_rules()
        status = "success"
        message = f"规则状态已更新为: {'启用' if new_status else '禁用'}"
    else:
        status = "error"
        message = "规则不存在"
    conn.close()
    return jsonify({"status": status, "message": message})

# 获取规则列表路由
@app.route('/api/rules', methods=['GET'])
@login_required
def get_rules():
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    c.execute("SELECT * FROM rules")
    rules = []
    for row in c.fetchall():
        rules.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'pattern': row[3],
            'severity': row[4],
            'category': row[5],
            'enabled': bool(row[6])
        })
    conn.close()
    return jsonify(rules)

@app.route('/api/rules/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_rule(rule_id):
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        conn.commit()
        rule_engine.load_rules()
        status = "success"
        message = "规则删除成功"
    except Exception as e:
        status = "error"
        message = f"删除规则失败: {str(e)}"
    conn.close()
    return jsonify({"status": status, "message": message})

#API 接口，允许用户根据严重级别获取事件列表
@app.route('/api/events/severity/<string:severity>', methods=['GET'])
@login_required
def get_events_by_severity(severity):
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM events WHERE severity = ?", (severity,))
    total = c.fetchone()[0]
    c.execute('''
              SELECT e.*, r.name as rule_name
              FROM events e
                       LEFT JOIN rules r ON e.rule_id = r.id
              WHERE e.severity = ?
              ORDER BY e.timestamp DESC LIMIT ?
              OFFSET ?
              ''', (severity, per_page, offset))
    events = []
    for row in c.fetchall():
        events.append({
            'id': row[0],
            'timestamp': row[2],
            'ip_address': row[3],
            'rule_name': row[9],
            'severity': row[7],
            'status': row[8]
        })
    conn.close()
    return jsonify({
        'events': events,
        'total': total,
        'page': page,
        'per_page': per_page
    })

# API 接口，允许用户更新规则的信息
@app.route('/api/rules/<int:rule_id>', methods=['PUT'])
@login_required
def update_rule(rule_id):
    rule_name = request.form.get('rule_name')
    pattern = request.form.get('pattern')
    event_type = request.form.get('event_type')
    severity = request.form.get('severity')
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE rules SET rule_name = ?, pattern = ?, event_type = ?, severity = ? WHERE id = ?",
                  (rule_name, pattern, event_type, severity, rule_id))
        conn.commit()
        rule_engine.load_rules()
        status = "success"
        message = "规则更新成功"
    except sqlite3.IntegrityError:
        status = "error"
        message = "规则名称已存在"
    except Exception as e:
        status = "error"
        message = f"更新规则失败: {str(e)}"
    conn.close()
    return jsonify({"status": status, "message": message})

# 获取事件列表路由
@app.route('/api/events', methods=['GET'])
@login_required
def get_events():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    # 获取筛选参数
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    event_type = request.args.get('event_type')
    severity = request.args.get('severity')
    ip_address = request.args.get('ip_address')

    conn = sqlite3.connect('ids.db')
    c = conn.cursor()

    # 构建 SQL 查询条件
    conditions = []
    values = []

    if start_date and end_date:
        conditions.append("timestamp BETWEEN ? AND ?")
        values.extend([start_date, end_date])
    if event_type:
        conditions.append("event_type = ?")
        values.append(event_type)
    if severity:
        conditions.append("severity = ?")
        values.append(severity)
    if ip_address:
        conditions.append("ip_address = ?")
        values.append(ip_address)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # 查询总事件数
    c.execute(f"SELECT COUNT(*) FROM events WHERE {where_clause}", values)
    total = c.fetchone()[0]

    # 查询事件列表
    c.execute(f'''
              SELECT e.*, r.name as rule_name
              FROM events e
                       LEFT JOIN rules r ON e.rule_id = r.id
              WHERE {where_clause}
              ORDER BY e.timestamp DESC LIMIT ?
              OFFSET ?
              ''', values + [per_page, offset])
    events = []
    for row in c.fetchall():
        events.append({
            'id': row[0],
            'timestamp': row[2],
            'ip_address': row[3],
            'rule_name': row[9],
            'severity': row[7],
            'status': row[8]
        })
    conn.close()
    return jsonify({
        'events': events,
        'total': total,
        'page': page,
        'per_page': per_page
    })


# 获取事件详情路由
@app.route('/api/events/<int:event_id>', methods=['GET'])
@login_required
def get_event_details(event_id):
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    c.execute('''
              SELECT e.*, r.name as rule_name, r.description as rule_description
              FROM events e
                       LEFT JOIN rules r ON e.rule_id = r.id
              WHERE e.id = ?
              ''', (event_id,))
    event = c.fetchone()
    if not event:
        return jsonify({"error": "事件不存在"}), 404
    event_data = {
        'id': event[0],
        'timestamp': event[2],
        'ip_address': event[3],
        'user_agent': event[4],
        'request_path': event[5],
        'request_method': event[6],
        'request_data': json.loads(event[7]),
        'severity': event[8],
        'status': event[9],
        'rule_name': event[10],
        'rule_description': event[11]
    }
    conn.close()
    return jsonify(event_data)

# 阻止IP路由
@app.route('/api/block_ip', methods=['POST'])
@login_required
def block_ip():
    ip = request.json.get('ip')
    duration = request.json.get('duration', 3600)
    if not ip:
        return jsonify({"error": "缺少IP参数"}), 400
    rule_engine.block_ip(ip, duration)
    return jsonify({"success": True, "message": f"IP {ip} 已被阻止"})

#事件数据导出，CSV格式
@app.route('/api/events/export', methods=['GET'])
@login_required
def export_events():
    # 获取筛选参数
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    event_type = request.args.get('event_type')
    severity = request.args.get('severity')
    ip_address = request.args.get('ip_address')

    conn = sqlite3.connect('ids.db')
    c = conn.cursor()

    # 构建 SQL 查询条件
    conditions = []
    values = []

    if start_date and end_date:
        conditions.append("timestamp BETWEEN ? AND ?")
        values.extend([start_date, end_date])
    if event_type:
        conditions.append("event_type = ?")
        values.append(event_type)
    if severity:
        conditions.append("severity = ?")
        values.append(severity)
    if ip_address:
        conditions.append("ip_address = ?")
        values.append(ip_address)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # 查询事件列表
    c.execute(f'''
              SELECT e.*, r.name as rule_name
              FROM events e
                       LEFT JOIN rules r ON e.rule_id = r.id
              WHERE {where_clause}
              ORDER BY e.timestamp DESC
              ''', values)

    events = c.fetchall()
    conn.close()

    # 创建 CSV 响应
    def generate():
        header = ['id', 'timestamp', 'ip_address', 'user_agent', 'request_path', 'request_method', 'request_data', 'severity', 'status', 'event_type', 'rule_name']
        writer = csv.writer(buffer)
        writer.writerow(header)
        for event in events:
            writer.writerow(event)
            buffer.seek(0)
            data = buffer.read()
            buffer.seek(0)
            buffer.truncate()
            yield data

    buffer = io.StringIO()
    response = Response(generate(), mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename='events.csv')
    return response

#事件清除
@app.route('/api/events/clear', methods=['POST'])
@login_required
def clear_events():
    conn = sqlite3.connect('ids.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM events")
        conn.commit()
        status = "success"
        message = "事件已清空"
    except Exception as e:
        status = "error"
        message = f"清空事件失败: {str(e)}"
    conn.close()
    return jsonify({"status": status, "message": message})


# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect('ids.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = c.fetchone()
        conn.close()
        if user_data:
            user = User(user_data[0], user_data[1], user_data[2])
            if user.check_password(password):
                login_user(user)
                return redirect(url_for('index'))
        return render_template('login.html', error="用户名或密码错误")
    return render_template('login.html')

# 登出路由
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# WebSocket连接处理
@socketio.on('connect')
def handle_connect():
    print('客户端已连接')

@socketio.on('disconnect')
def handle_disconnect():
    print('客户端已断开连接')

if __name__ == '__main__':
    init_db()
    rule_engine = RuleEngine()
    logger = Logger()
    packet_sniffer = PacketSniffer(rule_engine)
    packet_sniffer.start()
    monitor = Monitor(rule_engine)
    monitor.start()
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
