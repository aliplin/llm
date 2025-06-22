import os
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re
import glob

# Load environment variables from .env file
load_dotenv('db_credentials.env')

DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
DB_PATH = os.getenv('DB_PATH', 'shellm_sessions.db')


def parse_last_output(last_output):
    sessions = []
    failed_lines = []  # 用于记录解析失败的行

    # 逐行处理输出
    for line in last_output.splitlines():
        # 跳过空行或不相关的行
        if not line.strip() or line.startswith("wtmp") or "reboot" in line:
            continue

        parts = line.split()  # 将行拆分为多个部分

        # 确保有足够的部分来解析
        if len(parts) < 8:  # 至少需要8个部分才能正确解析
            print(f"警告: 无法解析行: '{line}'")
            failed_lines.append(line)
            continue

        # 基于固定列位置提取详细信息
        username = parts[0]
        terminal = parts[1]
        src_ip = parts[2] if parts[2] != ":0" else "127.0.0.1"  # 本地登录默认为localhost
        time_date_start = " ".join(parts[3:8])  # 合并时间和日期部分

        # 转换时间字符串为MySQL兼容格式
        try:
            time_date_start = datetime.strptime(time_date_start, "%a %b %d %H:%M:%S %Y").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            print(f"警告: 无法解析时间 '{time_date_start}', 使用当前时间替代")
            time_date_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 目标IP（你的服务器IP或测试用的localhost）
        dst_ip = "127.0.0.1"
        dst_port = 5656

        # 将解析的数据作为元组添加
        sessions.append((username, time_date_start, src_ip, dst_ip, dst_port))

    # 可选：返回失败的行以供进一步分析
    if failed_lines:
        print(f"解析了 {len(sessions)} 个会话，{len(failed_lines)} 行解析失败")

    return sessions


def connect_to_db():
    """连接到SQLite数据库"""
    try:
        db_file_path = os.path.join(os.path.dirname(__file__), DB_PATH)
        conn = sqlite3.connect(db_file_path)
        return conn, conn.cursor()
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None, None


# Function to insert data into SQLite
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


# Function to insert data into SQLite
def insert_into_attacker_session(data):
    conn, cursor = connect_to_db()
    for session in data:
        src_ip = session[2]
        cursor.execute(
            """
            INSERT INTO attacker_session (src_ip)
            VALUES (?)
            """, (src_ip,)
        )
    conn.commit()
    cursor.close()
    conn.close()


# Function to count how many new connections were to ssh since last database entry
def count_newest(data):
    """
    计算新会话数量
    :param data: 会话数据列表
    :return: 新会话数量
    """
    conn, cursor = connect_to_db()
    cursor.execute("SELECT time_date FROM ssh_session ORDER BY id DESC LIMIT 1;")
    latest_entry = cursor.fetchone()

    # 处理数据库无记录的情况
    if not latest_entry:
        time_date_str = "1970-01-01 00:00:00"
        print("警告: 数据库中无SSH会话记录，视为全部新连接")
    else:
        time_date = latest_entry[0]
        time_date_str = (
            time_date.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(time_date, datetime)
            else str(time_date)
        )

    # 从最早的会话开始计数，直到找到时间小于等于time_date_str的会话
    counter = 0
    for session in data:
        try:
            # 将字符串时间转换为datetime对象进行比较
            session_time = datetime.strptime(session[1], "%Y-%m-%d %H:%M:%S")
            latest_time = datetime.strptime(time_date_str, "%Y-%m-%d %H:%M:%S")
            
            if session_time > latest_time:
                counter += 1  # 新会话
            else:
                break  # 遇到旧会话，停止计数
        except ValueError as e:
            print(f"警告: 时间格式转换错误: {e}")
            continue

    print(f"检测到 {counter} 个新会话，最后数据库记录时间: {time_date_str}")
    conn.commit()
    cursor.close()
    conn.close()
    return counter


def create_filenames(data):
    filenames = []

    for session in data:
        # Extract the time_date value from the session tuple
        time_date = session[1]  # Assuming time_date is the second element in the tuple

        # Convert the time_date to a string if it's not already
        if isinstance(time_date, datetime):
            time_date = time_date + timedelta(seconds=1)
            time_date_str = time_date.strftime("%Y-%m-%d_%H-%M-%S")
        else:
            time_date_str = str(time_date).replace(" ", "_").replace(":", "-")

        # Create the filename using the formatted time_date
        filename = f"historySSH_{time_date_str}.txt"
        filenames.append(filename)

    return filenames


def get_latest_sessions_ids(counter):
    ids = []

    conn, cursor = connect_to_db()
    cursor.execute("SELECT id FROM ssh_session ORDER BY id DESC LIMIT ?;", (counter,))
    ids = [row[0] for row in cursor.fetchall()]

    return ids


def get_latest_attackers_ids(counter):
    ids = []

    conn, cursor = connect_to_db()
    cursor.execute("SELECT attacker_session_id FROM attacker_session ORDER BY attacker_session_id DESC LIMIT ?;", (counter,))
    ids = [row[0] for row in cursor.fetchall()]

    return ids


def parse_historylog(file_path):
    """
    解析历史日志文件，提取命令和响应
    """
    commands = []
    answers = []
    start_time = None
    end_time = None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 提取命令和响应
        current_command = None
        current_answer = []

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue

            # 检查是否是命令（包含提示符的行）
            if '@' in line and '~$' in line:
                # 如果已经有命令在处理，保存它
                if current_command:
                    commands.append(current_command)
                    answers.append('\n'.join(current_answer))
                    current_answer = []

                # 提取新命令
                prompt_end = line.find('~$') + 2
                current_command = line[prompt_end:].strip()
                continue
            
            # 其他行作为当前命令的响应
            if current_command is not None:
                current_answer.append(line)
        
        # 处理最后一个命令
        if current_command:
            commands.append(current_command)
            answers.append('\n'.join(current_answer))
        
        # 解析时间
        time_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
        time_matches = re.findall(time_pattern, content)
        if len(time_matches) >= 2:
            start_time = time_matches[0]
            end_time = time_matches[-1]
        
        return commands, answers, start_time, end_time

    except Exception as e:
        print(f"解析历史日志文件时出错: {e}")
        return [], [], None, None


def insert_into_commands_and_answers(commands, shellm_session_id, answers):
    conn, cursor = connect_to_db()

    try:
        # Ensure we have a matching number of commands and answers
        if len(commands) != len(answers):
            raise ValueError("The number of commands and answers must be equal.")

        answer_counter = 0

        # Insert each command and its corresponding answer
        for command in commands:
            # Insert command into 'commands' table
            cursor.execute("""
            INSERT INTO commands (shellm_session_id, command)
            VALUES (?, ?, ?)
            """, (shellm_session_id, command))

            # Fetch the last inserted 'command_id'
            cursor.execute("""
            SELECT last_insert_rowid();
            """)
            command_id = cursor.fetchone()[0]

            # Insert answer into 'answers' table
            cursor.execute("""
            INSERT INTO answers (command_id, answer)
            VALUES (?, ?)
            """, (command_id, answers[answer_counter]))

            answer_counter += 1

        # Commit the transaction
        conn.commit()

    except Exception as e:
        print(f"插入命令和响应时出错: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()


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


def get_latest_shellm_session():
    conn, cursor = connect_to_db()

    cursor.execute("""
                    SELECT id FROM shellm_session ORDER BY id DESC LIMIT 1;
                """)

    shellm_session_id = cursor.fetchone()

    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()

    return shellm_session_id


def format_datetime_for_db(raw_time):
    # 清理时间字符串（移除多余空格，处理首尾符号）
    cleaned_time = raw_time.strip().replace('<>', '')  # 移除可能的角括号
    cleaned_time = ' '.join(cleaned_time.split())  # 压缩连续空格为单个空格

    # 解析时间（格式为 YYYY-MM-DD HH:MM:SS）
    datetime_obj = datetime.strptime(cleaned_time, "%Y-%m-%d %H:%M:%S")

    # 转换为MySQL DATETIME格式
    return datetime_obj.strftime("%Y-%m-%d %H:%M:%S")


def get_logs_from_local():
    """从本地获取日志文件"""
    try:
        # 获取所有日志文件
        log_files = glob.glob('./logs/*.txt')
        if not log_files:
            print("未找到日志文件")
            return
            
        print(f"找到 {len(log_files)} 个日志文件")
        
        # 解析SSH会话
        ssh_sessions = []
        for log_file in log_files:
            if 'logSSH_' in log_file:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    match = re.search(r'(\w+)\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', content)
                    if match:
                        username, timestamp, source_ip = match.groups()
                        ssh_sessions.append((username, timestamp, source_ip))
        
        if not ssh_sessions:
            print("未找到SSH会话")
            return
            
        print(f"解析到 {len(ssh_sessions)} 个SSH会话")
        
        # 获取最新的数据库记录时间
        conn, cursor = connect_to_db()
        cursor.execute("SELECT MAX(timestamp) FROM ssh_sessions")
        last_db_time = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        if not last_db_time:
            print("警告: 数据库中无SSH会话记录，视为全部新连接")
            last_db_time = datetime(1970, 1, 1)
        
        # 过滤新会话
        new_sessions = []
        for session in ssh_sessions:
            session_time = datetime.strptime(session[1], "%Y-%m-%d %H:%M:%S")
            if session_time > last_db_time:
                new_sessions.append(session)
        
        if new_sessions:
            print(f"检测到 {len(new_sessions)} 个新会话")
            
            # 插入新会话
            conn, cursor = connect_to_db()
            for session in new_sessions:
                username, timestamp, source_ip = session
                cursor.execute("""
                    INSERT INTO ssh_sessions (username, timestamp, source_ip)
                    VALUES (?, ?, ?)
                """, (username, timestamp, source_ip))
            conn.commit()
            cursor.close()
            conn.close()
            
            # 获取最新的会话ID
            conn, cursor = connect_to_db()
            cursor.execute("SELECT id FROM ssh_sessions ORDER BY timestamp DESC LIMIT ?", (len(new_sessions),))
            latest_sessions_ids = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            # 获取最新的攻击者ID
            conn, cursor = connect_to_db()
            cursor.execute("SELECT id FROM attackers ORDER BY id DESC LIMIT ?", (len(new_sessions),))
            latest_attacker_ids = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            # 处理历史文件
            for session in new_sessions:
                username, timestamp, source_ip = session
                history_file = f'./logs/historySSH_{source_ip}_{timestamp.replace(" ", "_").replace(":", "-")}.txt'
                
                if os.path.exists(history_file):
                    commands, answers, start_time, end_time = parse_historylog(history_file)
                    
                    if not end_time and start_time:
                        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                        end_dt = start_dt + timedelta(minutes=5)
                        end_time = end_dt.strftime("%Y-%m-%d %H:%M:%S")

            if start_time and end_time:
                start_time = format_datetime_for_db(start_time)
                end_time = format_datetime_for_db(end_time)
                insert_into_shellm_session(start_time, end_time, latest_sessions_ids, latest_attacker_ids)
                shellm_session_id = get_latest_shellm_session()
            if shellm_session_id and shellm_session_id[0]:
                insert_into_commands_and_answers(commands, shellm_session_id[0], answers)
                print(f"已插入 {len(commands)} 条命令记录")

                        # 更新ID列表
                latest_sessions_ids = latest_sessions_ids[1:]
                latest_attacker_ids = latest_attacker_ids[1:]
            else:
                print("没有新的会话需要处理")
            
    except Exception as e:
        print(f"处理日志文件时出错: {e}")


def parse_ssh_logs(logs_dir):
    """
    解析SSH日志文件
    :param logs_dir: 日志目录路径
    :return: 解析后的日志数据列表
    """
    parsed_logs = []
    
    # 获取所有logSSH文件
    log_files = glob.glob(os.path.join(logs_dir, "logSSH_*.txt"))
    
    for log_file in log_files:
        try:
            # 从文件名中提取日期
            filename = os.path.basename(log_file)
            match = re.match(r'logSSH_(\d{4}-\d{2}-\d{2})\.txt', filename)
            if not match:
                continue
                
            date_str = match.groups()[0]
            
            # 读取日志文件内容
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read().strip()
            
            # 按行解析登录信息
            for line in log_content.split('\n'):
                if not line.strip():
                    continue
                    
                # 解析登录信息
                # 格式: username terminal src_ip time_date_start
                login_match = re.match(r'(\S+)\s+(\S+)\s+(\S+)\s+(.+)', line)
                if login_match:
                    username, terminal, src_ip, login_time = login_match.groups()
                    
                    # 转换时间格式
                    try:
                        # 将时间字符串转换为datetime对象
                        login_datetime = datetime.strptime(login_time, "%a %b %d %H:%M:%S %Y")
                        # 转换为MySQL兼容格式
                        time_date_start = login_datetime.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        print(f"警告: 无法解析时间 '{login_time}'，使用当前时间替代")
                        time_date_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 查找对应的history文件
                    history_file = os.path.join(logs_dir, f"historySSH_{date_str}.txt")
                    if os.path.exists(history_file):
                        with open(history_file, 'r', encoding='utf-8') as f:
                            history_content = f.read()
                        
                        # 解析命令历史
                        commands = []
                        for cmd_line in history_content.split('\n'):
                            if cmd_line.strip() and not cmd_line.startswith('$'):
                                commands.append(cmd_line.strip())
                        
                        parsed_logs.append({
                            'session_id': f"{date_str}_{len(parsed_logs)}",  # 使用日期和序号作为会话ID
                            'username': username,
                            'terminal': terminal,
                            'src_ip': src_ip,
                            'login_time': time_date_start,  # 使用转换后的时间格式
                            'commands': commands
                        })
            print(f"\n[SSH会话] 日志文件: {log_file}")
            print(f"  用户名: {username}  终端: {terminal}  源IP: {src_ip}")
            print(f"  登录时间: {time_date_start}")
            print(f"  命令数: {len(commands)}")
            for cmd in commands:
                print(f"    CMD: {cmd}")
        except Exception as e:
            print(f"解析日志文件 {log_file} 时出错: {e}")
            continue
    
    return parsed_logs


def get_ssh_stats(logs_dir):
    """
    获取SSH统计信息
    :param logs_dir: 日志目录路径
    :return: 统计信息字典
    """
    parsed_logs = parse_ssh_logs(logs_dir)
    
    stats = {
        'total_sessions': len(parsed_logs),
        'unique_users': len(set(log['username'] for log in parsed_logs)),
        'unique_ips': len(set(log['src_ip'] for log in parsed_logs)),
        'total_commands': sum(len(log['commands']) for log in parsed_logs),
        'sessions_by_user': {},
        'sessions_by_ip': {},
        'commands_by_user': {},
        'commands_by_ip': {}
    }
    
    for log in parsed_logs:
        # 按用户统计
        stats['sessions_by_user'][log['username']] = stats['sessions_by_user'].get(log['username'], 0) + 1
        stats['commands_by_user'][log['username']] = stats['commands_by_user'].get(log['username'], 0) + len(log['commands'])
        
        # 按IP统计
        stats['sessions_by_ip'][log['src_ip']] = stats['sessions_by_ip'].get(log['src_ip'], 0) + 1
        stats['commands_by_ip'][log['src_ip']] = stats['commands_by_ip'].get(log['src_ip'], 0) + len(log['commands'])
    
    return stats


def get_recent_ssh_activity(logs_dir, hours=24):
    """
    获取最近的SSH活动
    :param logs_dir: 日志目录路径
    :param hours: 最近多少小时的活动
    :return: 活动列表
    """
    parsed_logs = parse_ssh_logs(logs_dir)
    recent_activity = []
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    for log in parsed_logs:
        try:
            login_time = datetime.strptime(log['login_time'], '%a %b %d %H:%M:%S %Y')
            if login_time >= cutoff_time:
                recent_activity.append({
                    'session_id': log['session_id'],
                    'username': log['username'],
                    'src_ip': log['src_ip'],
                    'login_time': log['login_time'],
                    'command_count': len(log['commands'])
                })
        except ValueError:
            continue
    
    return sorted(recent_activity, key=lambda x: x['login_time'], reverse=True)


def get_ssh_command_frequency(logs_dir):
    """
    获取SSH命令使用频率
    :param logs_dir: 日志目录路径
    :return: 命令频率字典
    """
    parsed_logs = parse_ssh_logs(logs_dir)
    command_freq = {}
    
    for log in parsed_logs:
        for cmd in log['commands']:
            # 提取命令（去除参数）
            base_cmd = cmd.split()[0] if cmd else ''
            if base_cmd:
                command_freq[base_cmd] = command_freq.get(base_cmd, 0) + 1
    
    return dict(sorted(command_freq.items(), key=lambda x: x[1], reverse=True))


def get_ssh_suspicious_activity(logs_dir):
    """
    检测可疑的SSH活动
    :param logs_dir: 日志目录路径
    :return: 可疑活动列表
    """
    parsed_logs = parse_ssh_logs(logs_dir)
    suspicious = []
    
    for log in parsed_logs:
        # 检查可疑命令
        suspicious_commands = ['wget', 'curl', 'nc', 'netcat', 'chmod', 'chown', 'passwd']
        found_suspicious = [cmd for cmd in log['commands'] if any(susp in cmd for susp in suspicious_commands)]
        
        if found_suspicious:
            suspicious.append({
                'session_id': log['session_id'],
                'username': log['username'],
                'src_ip': log['src_ip'],
                'login_time': log['login_time'],
                'suspicious_commands': found_suspicious
            })
    
    return suspicious


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


def get_mysql_stats(logs_dir):
    """
    获取MySQL统计信息
    :param logs_dir: 日志目录路径
    :return: MySQL统计信息字典
    """
    parsed_logs = parse_mysql_logs(logs_dir)
    stats = {
        'total_sessions': 0,
        'total_commands': 0,
        'command_types': {},
        'users': set(),
        'databases': set()
    }
    
    # 这里可以添加更详细的统计逻辑
    return stats


def get_mysql_recent_activity(logs_dir, hours=24):
    """
    获取最近的MySQL活动
    :param logs_dir: 日志目录路径
    :param hours: 小时数
    :return: 最近活动列表
    """
    # 这里可以添加获取最近活动的逻辑
    return []


if __name__ == "__main__":
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    get_logs_from_local()         # 解析SSH
    parse_pop3_logs(logs_dir)     # 解析POP3
    parse_http_logs(logs_dir)     # 解析HTTP
    parse_mysql_logs(logs_dir)    # 解析MySQL