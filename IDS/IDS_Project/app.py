import os
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

# 导入ids_llm模块以获取token状态
try:
    from ids_llm import token_monitor
except ImportError:
    # 如果导入失败，创建一个模拟的token监控器
    class MockTokenMonitor:
        def get_token_status(self):
            return {
                "total_tokens_used": 0,
                "daily_tokens_used": 0,
                "token_limit": 1000000,
                "is_limit_exceeded": False,
                "remaining_tokens": 1000000
            }
    token_monitor = MockTokenMonitor()

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
    conn = sqlite3.connect('packet_stats.db')
    c = conn.cursor()
    with open('schema.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()
    c.executescript(sql_script)
    c.execute("SELECT DISTINCT * FROM users WHERE username = 'admin'")
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
        conn = sqlite3.connect('packet_stats.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT * FROM rules WHERE enabled = 1")
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

    def check_rule(self, rule, targets, request_data, results):    #每个线程执行的具体规则匹配逻辑
        for target in targets:
            if rule['pattern'].search(target):
                with self.lock:
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

    def check_request(self, request):      #多线程规则匹配
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
        targets = [
            request.path,
            str(request.args),
            str(request.form),
            request.user_agent.string
        ]
        threads = []
        for rule in self.rules:
            thread = threading.Thread(target=self.check_rule, args=(rule, targets, request_data, results))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

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
        conn = sqlite3.connect('packet_stats.db')
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
            c.execute("SELECT DISTINCT value FROM settings WHERE name = 'max_events'")
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

        # 初始化默认值
        src_ip = 'N/A'
        dst_ip = 'N/A'
        src_port = 'N/A'
        dst_port = 'N/A'

        # 检查IP层是否存在
        if IP in packet:
            src_ip = packet[IP].src
            dst_ip = packet[IP].dst

            # 检查TCP层是否存在
            if TCP in packet:
                src_port = packet[TCP].sport
                dst_port = packet[TCP].dport

        packet_data = {
            'time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
            'summary': packet.summary(),
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'src_port': src_port,
            'dst_port': dst_port,
            'protocol': packet.__class__.__name__,
            'payload': str(packet[Raw].load) if Raw in packet else None
        }
        socketio.emit('packet', {'type': 'packet', 'packet': packet_data})

        # 只处理包含Raw层的数据包
        if packet.haslayer(Raw):
            payload = packet[Raw].load.decode('utf-8', errors='ignore')
            # 只有在存在IP层时才进行规则匹配
            if IP in packet:
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
            conn = sqlite3.connect('packet_stats.db')
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
    conn = sqlite3.connect('packet_stats.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT * FROM users WHERE id = ?", (user_id,))
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
    conn = sqlite3.connect('packet_stats.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT * FROM events ORDER BY timestamp DESC LIMIT 10")
    recent_events = c.fetchall()
    c.execute("SELECT DISTINCT event_type, COUNT(*) as count FROM events GROUP BY event_type ORDER BY count DESC")
    event_stats = c.fetchall()
    c.execute("SELECT DISTINCT severity, COUNT(*) as count FROM events GROUP BY severity")
    severity_stats = c.fetchall()
    conn.close()
    return render_template('index.html',
                           recent_events=recent_events,
                           event_stats=event_stats,
                           severity_stats=severity_stats)

# 设置响应头来禁用缓存
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response



# 事件日志路由
@app.route('/events')
@login_required
def events():
    conn = sqlite3.connect('packet_stats.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT * FROM events ORDER BY timestamp DESC")
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
    conn = sqlite3.connect('packet_stats.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT * FROM rules")
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
    enabled = int(request.form.get('enabled', 1))

    conn = sqlite3.connect('packet_stats.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO rules (name, pattern, category, severity, enabled) VALUES (?, ?, ?, ?, ?)",
                  (rule_name, pattern, event_type, severity, enabled))
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
    conn = sqlite3.connect('packet_stats.db')
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

# 获取规则详情路由
@app.route('/rules/details/<int:rule_id>', methods=['GET'])
@login_required
def get_rule_details(rule_id):
    conn = sqlite3.connect('packet_stats.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT * FROM rules WHERE id = ?", (rule_id,))
    rule = c.fetchone()
    conn.close()
    if rule:
        rule_dict = {
            'id': rule[0],
            'name': rule[1],
            'pattern': rule[2],
            'event_type': rule[3],
            'severity': rule[4],
            'enabled': rule[5]
        }
        return jsonify(rule_dict)
    else:
        return jsonify({"status": "error", "message": "规则不存在"})

# 更新规则
@app.route('/rules/update/<int:rule_id>', methods=['POST'])
@login_required
def update_rule(rule_id):
    rule_name = request.form.get('rule_name')
    pattern = request.form.get('pattern')
    event_type = request.form.get('event_type')
    severity = request.form.get('severity')
    enabled = int(request.form.get('enabled', 1))

    conn = sqlite3.connect('packet_stats.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE rules SET name = ?, pattern = ?, category = ?, severity = ?, enabled = ? WHERE id = ?",
                  (rule_name, pattern, event_type, severity, enabled, rule_id))
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

# 切换规则状态
@app.route('/rules/toggle/<int:rule_id>', methods=['POST'])
@login_required
def toggle_rule_status(rule_id):
    conn = sqlite3.connect('packet_stats.db')
    c = conn.cursor()
    c.execute("SELECT enabled FROM rules WHERE id = ?", (rule_id,))
    rule = c.fetchone()
    if rule:
        new_status = 1 if rule[0] == 0 else 0
        try:
            c.execute("UPDATE rules SET enabled = ? WHERE id = ?", (new_status, rule_id))
            conn.commit()
            rule_engine.load_rules()
            status = "success"
            message = "规则状态切换成功"
        except Exception as e:
            status = "error"
            message = f"切换规则状态失败: {str(e)}"
    else:
        status = "error"
        message = "规则不存在"
    conn.close()
    return jsonify({"status": status, "message": message})

# 删除规则
@app.route('/rules/delete/<int:rule_id>', methods=['POST'])
@login_required
def delete_rule(rule_id):
    conn = sqlite3.connect('packet_stats.db')
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

#---events.html事件日志页面---------------------------------------------------------------------------------------------

#API 接口，允许用户根据严重级别获取事件列表
@app.route('/api/events/severity/<string:severity>', methods=['GET'])
@login_required
def get_events_by_severity(severity):
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    conn = sqlite3.connect('packet_stats.db')
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

    conn = sqlite3.connect('packet_stats.db')
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
    conn = sqlite3.connect('packet_stats.db')
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

    conn = sqlite3.connect('packet_stats.db')
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
    conn = sqlite3.connect('packet_stats.db')
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
        conn = sqlite3.connect('packet_stats.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT * FROM users WHERE username = ?", (username,))
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

# Token状态监控API路由
@app.route('/api/token_status', methods=['GET'])
@login_required
def get_token_status():
    """获取当前token使用状态"""
    try:
        status = token_monitor.get_token_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "error": "获取token状态失败",
            "message": str(e),
            "total_tokens_used": 0,
            "daily_tokens_used": 0,
            "token_limit": 1000000,
            "is_limit_exceeded": False,
            "remaining_tokens": 1000000
        })

# LLM分析状态页面
@app.route('/llm_status')
@login_required
def llm_status():
    """LLM分析状态页面"""
    return render_template('llm_status.html')

# WebSocket连接处理
@socketio.on('connect')
def handle_connect():
    print('客户端已连接')

@socketio.on('disconnect')
def handle_disconnect():
    print('客户端已断开连接')

#-------------------------------------------以下为合并后蜜罐事件日志分析---------------------------------------------
# 添加honeypot_log_analysis路由
@app.route('/honeypot_log_analysis')
@login_required
def honeypot_log_analysis():
    return render_template('honeypot_log_analysis.html')

DB_TYPE='sqlite'
DB_PATH='packet_stats.db'
# 连接到SQLite数据库
def connect_to_db():
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

# 初始化SQLite数据库
def init_sqlite_database():
    """初始化SQLite数据库"""
    # 数据库文件路径
    db_path = os.path.join(os.path.dirname(__file__), 'shellm_sessions.db')
    # 连接到SQLite数据库（如果不存在会自动创建）
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"正在初始化SQLite数据库: {db_path}")
    # 创建attacker_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attacker_session (
            attacker_session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            src_ip VARCHAR(45) NOT NULL
        )
    ''')
    # 创建ssh_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ssh_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255) NOT NULL,
            time_date DATETIME NOT NULL,
            src_ip VARCHAR(45) NOT NULL,
            dst_ip VARCHAR(45) NOT NULL,
            src_port INTEGER,
            dst_port INTEGER
        )
    ''')
    # 创建shellm_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shellm_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ssh_session_id INTEGER,
            model VARCHAR(255) NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            attacker_id INTEGER,
            FOREIGN KEY (ssh_session_id) REFERENCES ssh_session (id),
            FOREIGN KEY (attacker_id) REFERENCES attacker_session (attacker_session_id)
        )
    ''')
    # 创建commands表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commands (
            command_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shellm_session_id INTEGER,
            command TEXT NOT NULL,
            FOREIGN KEY (shellm_session_id) REFERENCES shellm_session (id)
        )
    ''')
    # 创建answers表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            command_id INTEGER,
            answer TEXT NOT NULL,
            FOREIGN KEY (command_id) REFERENCES commands (command_id)
        )
    ''')
    # 创建http_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS http_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_ip VARCHAR(45) NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME
        )
    ''')
    # 创建http_request表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS http_request (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            http_session_id INTEGER,
            method VARCHAR(16) NOT NULL,
            path VARCHAR(1024) NOT NULL,
            headers TEXT,
            request_time DATETIME NOT NULL,
            response TEXT NOT NULL,
            FOREIGN KEY (http_session_id) REFERENCES http_session (id)
        )
    ''')
    # 创建pop3_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pop3_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255) NOT NULL,
            time_date DATETIME NOT NULL,
            src_ip VARCHAR(45) NOT NULL,
            dst_ip VARCHAR(45) NOT NULL,
            src_port INTEGER,
            dst_port INTEGER
        )
    ''')
    # 创建pop3_command表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pop3_command (
            command_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pop3_session_id INTEGER,
            command TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            FOREIGN KEY (pop3_session_id) REFERENCES pop3_session (id)
        )
    ''')
    # 创建mysql_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mysql_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255) NOT NULL,
            time_date DATETIME NOT NULL,
            src_ip VARCHAR(45) NOT NULL,
            dst_ip VARCHAR(45) NOT NULL,
            src_port INTEGER,
            dst_port INTEGER,
            database_name VARCHAR(255)
        )
    ''')
    # 创建mysql_command表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mysql_command (
            command_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mysql_session_id INTEGER,
            command TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            command_type VARCHAR(50),
            affected_rows INTEGER,
            FOREIGN KEY (mysql_session_id) REFERENCES mysql_session (id)
        )
    ''')
    # 提交更改
    conn.commit()
    # 创建索引以提高查询性能
    print("正在创建索引...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ssh_session_time ON ssh_session(time_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shellm_session_ssh ON shellm_session(ssh_session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shellm_session_attacker ON shellm_session(attacker_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_commands_session ON commands(shellm_session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_answers_command ON answers(command_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_http_request_session ON http_request(http_session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pop3_command_session ON pop3_command(pop3_session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mysql_session_time ON mysql_session(time_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mysql_command_session ON mysql_command(mysql_session_id)')
    conn.commit()
    # 关闭连接
    cursor.close()
    conn.close()
    print("SQLite数据库初始化完成！")
    print(f"数据库文件位置: {db_path}")
    return db_path

# 检查数据库表结构
def check_table_structure():
    """检查数据库表结构"""
    db_path = os.path.join(os.path.dirname(__file__), 'shellm_sessions.db')
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # 要检查的表
    tables = ['mysql_session', 'mysql_command', 'http_session', 'http_request', 'ssh_session', 'pop3_session', 'pop3_command']
    for table in tables:
        print(f"\n=== {table} 表结构 ===")
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'} - {'PRIMARY KEY' if col[5] else ''}")
            # 显示示例数据
            cursor.execute(f"SELECT DISTINCT * FROM {table} LIMIT 1")
            sample = cursor.fetchone()
            if sample:
                print(f"\n示例数据:")
                for i, col in enumerate(columns):
                    print(f"  {col[1]}: {sample[i]}")
        except sqlite3.OperationalError as e:
            print(f"  表不存在: {e}")
    conn.close()

# 检查数据库内容
def check_database():
    """检查数据库内容"""
    db_path = os.path.join(os.path.dirname(__file__), 'shellm_sessions.db')
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # 检查表
    cursor.execute("SELECT DISTINCT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("数据库中的表:")
    for table in tables:
        print(f"  - {table[0]}")
    print("\n各表的数据统计:")
    # 检查MySQL相关表
    try:
        cursor.execute("SELECT COUNT(*) FROM mysql_session")
        mysql_sessions = cursor.fetchone()[0]
        print(f"MySQL会话数: {mysql_sessions}")
        cursor.execute("SELECT COUNT(*) FROM mysql_command")
        mysql_commands = cursor.fetchone()[0]
        print(f"MySQL命令数: {mysql_commands}")
        if mysql_sessions > 0:
            cursor.execute("SELECT DISTINCT * FROM mysql_session LIMIT 3")
            sessions = cursor.fetchall()
            print("\nMySQL会话示例:")
            for session in sessions:
                print(f"  ID: {session[0]}, 用户: {session[1]}, 时间: {session[2]}, IP: {session[3]}")
        if mysql_commands > 0:
            cursor.execute("SELECT DISTINCT * FROM mysql_command LIMIT 3")
            commands = cursor.fetchall()
            print("\nMySQL命令示例:")
            for cmd in commands:
                print(f"  ID: {cmd[0]}, 会话ID: {cmd[1]}, 命令: {cmd[2][:50]}...")
    except sqlite3.OperationalError as e:
        print(f"MySQL表不存在: {e}")
    # 检查其他表
    try:
        cursor.execute("SELECT COUNT(*) FROM ssh_session")
        ssh_sessions = cursor.fetchone()[0]
        print(f"SSH会话数: {ssh_sessions}")
    except:
        print("SSH会话表不存在")
    try:
        cursor.execute("SELECT COUNT(*) FROM pop3_session")
        pop3_sessions = cursor.fetchone()[0]
        print(f"POP3会话数: {pop3_sessions}")
    except:
        print("POP3会话表不存在")
    try:
        cursor.execute("SELECT COUNT(*) FROM http_session")
        http_sessions = cursor.fetchone()[0]
        print(f"HTTP会话数: {http_sessions}")
    except:
        print("HTTP会话表不存在")
    conn.close()

# 解析POP3日志文件并写入数据库
def parse_pop3_logs(logs_dir):
    """
    解析POP3日志文件并写入数据库
    :param logs_dir: 日志目录路径
    """
    import glob
    import re
    from datetime import datetime
    log_files = glob.glob(os.path.join(logs_dir, "logPOP3_*.txt"))
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            session_start, session_end = None, None
            src_ip, dst_ip, src_port, dst_port, username = '', '', None, None, ''
            commands = []
            responses = []
            timestamps = []
            session_start_time = None
            for line in lines:
                if line.startswith('POP3 session start:'):
                    session_start = re.search(r'start: (.*?) from ([\d\.]+):(\d+)', line)
                    if session_start:
                        session_start_time = session_start.group(1).strip()
                        src_ip = session_start.group(2)
                        src_port = int(session_start.group(3))
                        dst_ip = '127.0.0.1'
                        dst_port = None
                elif line.startswith('POP3 session end:'):
                    session_end = line.strip().split('end:')[-1].strip()
                elif '[CMD]' in line:
                    m = re.match(r'\[(.*?)\] \[CMD\] (.*)', line)
                    if m:
                        timestamps.append(m.group(1))
                        commands.append(m.group(2))
                        # 只在第一次遇到USER命令时设置username
                        if m.group(2).lower().startswith('user ') and not username:
                            username = m.group(2).split(' ', 1)[-1].strip()
                elif '[RESP]' in line:
                    m = re.match(r'\[(.*?)\] \[RESP\] (.*)', line)
                    if m:
                        responses.append(m.group(2))
            # 输出详细调试信息
            print(f"\n[POP3会话] 日志文件: {log_file}")
            print(f"  源IP: {src_ip}:{src_port} -> 目标IP: {dst_ip}")
            print(f"  用户名: {username}")
            print(f"  会话起始: {session_start_time}")
            print(f"  命令数: {len(commands)}")
            for i, cmd in enumerate(commands):
                print(f"    [{timestamps[i] if i < len(timestamps) else ''}] CMD: {cmd}")
                print(f"      RESP: {responses[i] if i < len(responses) else ''}")
            # 插入pop3_session
            if session_start_time and src_ip:
                conn, cursor = connect_to_db()
                cursor.execute("""
                    INSERT INTO pop3_session (username, time_date, src_ip, dst_ip, src_port, dst_port)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username or 'unknown', session_start_time, src_ip, dst_ip, src_port, dst_port))
                conn.commit()
                cursor.execute("SELECT last_insert_rowid();")
                pop3_session_id = cursor.fetchone()[0]
                # 插入命令与响应
                for i, cmd in enumerate(commands):
                    resp = responses[i] if i < len(responses) else ''
                    ts = timestamps[i] if i < len(timestamps) else session_start_time
                    cursor.execute("""
                        INSERT INTO pop3_command (pop3_session_id, command, response, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (pop3_session_id, cmd, resp, ts))
                conn.commit()
                cursor.close()
                conn.close()
                print(f"已写入POP3会话: {log_file}")
        except Exception as e:
            print(f"解析POP3日志 {log_file} 时出错: {e}")

# 解析HTTP日志文件并写入数据库
def parse_http_logs(logs_dir):
    """
    解析HTTP日志文件并写入数据库
    :param logs_dir: 日志目录路径
    """
    import glob
    import re
    import json
    from datetime import datetime
    log_files = glob.glob(os.path.join(logs_dir, "logHTTP_*.txt"))
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            requests = []
            responses = []
            request_times = []
            client_ip = None
            session_start = None
            session_end = None
            for line in lines:
                if 'HTTP Request:' in line:
                    m = re.match(r'HTTP Request: (.*)', line)
                    if m:
                        req = json.loads(m.group(1))
                        requests.append(req)
                        request_times.append(req.get('time', None))
                        if not client_ip:
                            client_ip = req.get('client_ip', None)
                        if not session_start:
                            session_start = req.get('time', None)
                        session_end = req.get('time', None)  # 最后一个请求时间为会话结束
                elif 'Response:' in line:
                    m = re.match(r'Response: (.*)', line)
                    if m:
                        responses.append(m.group(1))
            # 输出详细调试信息
            print(f"\n[HTTP请求] 日志文件: {log_file}")
            for i, req in enumerate(requests):
                print(f"  [{req.get('time', '')}] {req.get('method', '')} {req.get('path', '')} from {req.get('client_ip', '')}")
                print(f"    Headers: {json.dumps(req.get('headers', {}), ensure_ascii=False)}")
                print(f"    RESP: {responses[i] if i < len(responses) else ''}")
            # 插入http_session
            if client_ip and session_start:
                conn, cursor = connect_to_db()
                cursor.execute("""
                    INSERT INTO http_session (client_ip, start_time, end_time)
                    VALUES (?, ?, ?)
                """, (client_ip, session_start, session_end))
                conn.commit()
                cursor.execute("SELECT last_insert_rowid();")
                http_session_id = cursor.fetchone()[0]
                # 插入请求与响应
                for i, req in enumerate(requests):
                    resp = responses[i] if i < len(responses) else ''
                    ts = request_times[i] if i < len(request_times) else session_start
                    cursor.execute("""
                        INSERT INTO http_request (http_session_id, method, path, headers, request_time, response)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (http_session_id, req.get('method', ''), req.get('path', ''), json.dumps(req.get('headers', {})), ts, resp))
                conn.commit()
                cursor.close()
                conn.close()
                print(f"已写入HTTP会话: {log_file}")
        except Exception as e:
            print(f"解析HTTP日志 {log_file} 时出错: {e}")

# 解析MySQL日志文件并写入数据库
def parse_mysql_logs(logs_dir):
    """
    解析MySQL日志文件并写入数据库
    :param logs_dir: 日志目录路径
    """
    import glob
    import re
    import json
    from datetime import datetime
    log_files = glob.glob(os.path.join(logs_dir, "logMySQL_*.txt"))
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            session_start, session_end = None, None
            src_ip, dst_ip, src_port, dst_port, username = '', '', None, None, ''
            database_name = ''
            commands = []
            responses = []
            timestamps = []
            command_types = []
            affected_rows = []
            session_start_time = None
            for line in lines:
                if line.startswith('MySQL session start:'):
                    session_start = re.search(r'start: (.*?) from ([\d\.]+):(\d+)', line)
                    if session_start:
                        session_start_time = session_start.group(1).strip()
                        src_ip = session_start.group(2)
                        src_port = int(session_start.group(3))
                        dst_ip = '127.0.0.1'
                        dst_port = 3306
                elif line.startswith('MySQL session end:'):
                    session_end = line.strip().split('end:')[-1].strip()
                elif '[CMD]' in line:
                    m = re.match(r'\[(.*?)\] \[CMD\] (.*)', line)
                    if m:
                        timestamps.append(m.group(1))
                        cmd = m.group(2)
                        commands.append(cmd)
                        # 解析命令类型
                        cmd_upper = cmd.upper().strip()
                        if cmd_upper.startswith('SELECT'):
                            command_types.append('SELECT')
                        elif cmd_upper.startswith('INSERT'):
                            command_types.append('INSERT')
                        elif cmd_upper.startswith('UPDATE'):
                            command_types.append('UPDATE')
                        elif cmd_upper.startswith('DELETE'):
                            command_types.append('DELETE')
                        elif cmd_upper.startswith('CREATE'):
                            command_types.append('CREATE')
                        elif cmd_upper.startswith('DROP'):
                            command_types.append('DROP')
                        elif cmd_upper.startswith('USE'):
                            command_types.append('USE')
                            # 提取数据库名
                            use_match = re.match(r'USE\s+(\w+)', cmd_upper)
                            if use_match:
                                database_name = use_match.group(1)
                        elif cmd_upper.startswith('SHOW'):
                            command_types.append('SHOW')
                        else:
                            command_types.append('OTHER')
                        # 设置用户名（通常在连接时设置）
                        if not username and ('root' in cmd.lower() or 'user' in cmd.lower()):
                            user_match = re.search(r'(\w+)@', cmd)
                            if user_match:
                                username = user_match.group(1)
                        # 模拟影响行数
                        if cmd_upper.startswith('INSERT') or cmd_upper.startswith('UPDATE') or cmd_upper.startswith('DELETE'):
                            affected_rows.append(1)  # 模拟影响1行
                        else:
                            affected_rows.append(0)
                elif '[RESP]' in line:
                    m = re.match(r'\[(.*?)\] \[RESP\] (.*)', line)
                    if m:
                        responses.append(m.group(2))
            # 输出详细调试信息
            print(f"\n[MySQL会话] 日志文件: {log_file}")
            print(f"  源IP: {src_ip}:{src_port} -> 目标IP: {dst_ip}:{dst_port}")
            print(f"  用户名: {username}")
            print(f"  数据库: {database_name}")
            print(f"  会话起始: {session_start_time}")
            print(f"  命令数: {len(commands)}")
            for i, cmd in enumerate(commands):
                print(f"    [{timestamps[i] if i < len(timestamps) else ''}] CMD: {cmd}")
                print(f"      Type: {command_types[i] if i < len(command_types) else ''}")
                print(f"      RESP: {responses[i] if i < len(responses) else ''}")
            # 插入mysql_session
            if session_start_time and src_ip:
                conn, cursor = connect_to_db()
                cursor.execute("""
                    INSERT INTO mysql_session (username, time_date, src_ip, dst_ip, src_port, dst_port, database_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (username or 'root', session_start_time, src_ip, dst_ip, src_port, dst_port, database_name))
                conn.commit()
                cursor.execute("SELECT last_insert_rowid();")
                mysql_session_id = cursor.fetchone()[0]
                # 插入命令与响应
                for i, cmd in enumerate(commands):
                    resp = responses[i] if i < len(responses) else ''
                    ts = timestamps[i] if i < len(timestamps) else session_start_time
                    cmd_type = command_types[i] if i < len(command_types) else 'OTHER'
                    affected = affected_rows[i] if i < len(affected_rows) else 0
                    cursor.execute("""
                        INSERT INTO mysql_command (mysql_session_id, command, response, timestamp, command_type, affected_rows)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (mysql_session_id, cmd, resp, ts, cmd_type, affected))
                conn.commit()
                cursor.close()
                conn.close()
                print(f"已写入MySQL会话: {log_file}")
        except Exception as e:
            print(f"解析MySQL日志 {log_file} 时出错: {e}")

# 插入到ssh_session表
def insert_into_ssh_session(data):
    conn, cursor = connect_to_db()
    for session in data:
        cursor.execute(
            """
            INSERT INTO ssh_session (username, time_date, src_ip, dst_ip, dst_port)
            VALUES (?, ?, ?, ?, ?)
            """, session
        )
    conn.commit()
    cursor.close()
    conn.close()

# 插入到shellm_session表
def insert_into_shellm_session(start_time, end_time, latest_session_ids, latest_attacker_ids):
    conn, cursor = connect_to_db()
    ssh_session_id = latest_session_ids[0]
    latest_attacker_id = latest_attacker_ids[0]
    cursor.execute("""
        INSERT INTO shellm_session (ssh_session_id, model, start_time, end_time, attacker_id)
        VALUES (?, ?, ?, ?, ?)
            """, (ssh_session_id, "moonshot-v1-8k", start_time, end_time, latest_attacker_id))
    conn.commit()
    cursor.close()
    conn.close()

# 获取answers数据
@app.route('/answers', methods=['GET'])
def get_answers():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor.execute("SELECT DISTINCT * FROM answers ORDER BY answer_id DESC;")
        answers = cursor.fetchall()
        answers_list = [dict(row) for row in answers]
        return jsonify(answers_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 获取http_sessions数据
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

# 获取overview_stats数据
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

# 获取chart_data数据
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

# 获取shellm_sessions数据
@app.route('/shellm_sessions', methods=['GET'])
def get_shellm_sessions():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor.execute("SELECT DISTINCT * FROM shellm_session ORDER BY id DESC;")
        sessions = cursor.fetchall()
        sessions_list = [dict(row) for row in sessions]
        return jsonify(sessions_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 获取pop3_sessions数据
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

# 获取ssh_sessions数据
@app.route('/ssh_sessions', methods=['GET'])
def get_ssh_sessions():
    conn, cursor = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor.execute("SELECT DISTINCT * FROM ssh_session ORDER BY id DESC;")
        sessions = cursor.fetchall()
        # 将sqlite3.Row对象转换为字典列表
        sessions_list = [dict(row) for row in sessions]
        return jsonify(sessions_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 获取mysql_sessions数据
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


if __name__ == '__main__':
    init_db()
    rule_engine = RuleEngine()
    logger = Logger()
    packet_sniffer = PacketSniffer(rule_engine)
    packet_sniffer.start()
    monitor = Monitor(rule_engine)
    monitor.start()
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
