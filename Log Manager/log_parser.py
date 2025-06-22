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
    解析历史日志文件，提取命令和LLM回应
    格式分析：
    - 命令行：root@honeypot:~$ command
    - LLM回应：命令执行后的输出内容
    - 退出：quit/exit命令
    """
    commands = []
    answers = []
    start_time = None
    end_time = None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print(f"解析历史日志文件: {file_path}")
        print(f"文件内容长度: {len(content)} 字符")
        
        # 提取会话开始时间
        session_start_match = re.search(r'Session started at: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', content)
        if session_start_match:
            start_time = session_start_match.group(1)
            print(f"会话开始时间: {start_time}")
        
        # 按行解析内容
        lines = content.split('\n')
        current_command = None
        current_answer = []

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            print(f"行 {line_num+1}: {line}")
            
            # 检查是否是命令提示符行（包含@和~$）
            if '@' in line and '~$' in line:
                # 如果已经有命令在处理，保存它
                if current_command and current_command.strip():
                    commands.append(current_command.strip())
                    answers.append('\n'.join(current_answer))
                    print(f"保存命令: {current_command.strip()}")
                    print(f"保存答案: {len(current_answer)} 行")
                    current_answer = []

                # 提取新命令
                # 格式: root@honeypot:~$ ls -l
                prompt_end = line.find('~$') + 2
                if prompt_end < len(line):
                    current_command = line[prompt_end:].strip()
                    print(f"提取新命令: {current_command}")
                else:
                    current_command = ""
                continue
            
            # 检查是否是退出命令
            elif line == "exit" or line == "quit":
                if current_command and current_command.strip():
                    commands.append(current_command.strip())
                    answers.append('\n'.join(current_answer))
                    print(f"保存退出命令: {current_command.strip()}")
                    current_answer = []
                current_command = None
                continue
            
            # 检查是否是新的提示符（不同格式）
            elif line.startswith('root@') and ':' in line and line.endswith('~'):
                # 如果已经有命令在处理，保存它
                if current_command and current_command.strip():
                    commands.append(current_command.strip())
                    answers.append('\n'.join(current_answer))
                    print(f"保存命令: {current_command.strip()}")
                    print(f"保存答案: {len(current_answer)} 行")
                    current_answer = []
                current_command = None
                continue
            
            # 其他行作为当前命令的LLM回应
            if current_command is not None:
                # 跳过一些不需要的行
                if (line.startswith('total') and 'drwx' in line) or \
                   (line.startswith('drwx') and len(line.split()) >= 9) or \
                   (line.startswith('-rwx') and len(line.split()) >= 9):
                    # 这是ls命令的输出，应该作为答案的一部分
                    current_answer.append(line)
                elif line.startswith('root@') and '~$' in line:
                    # 这是新的命令提示符，跳过
                    continue
                else:
                    # 其他所有内容都作为LLM回应
                    current_answer.append(line)
        
        # 处理最后一个命令
        if current_command and current_command.strip():
            commands.append(current_command.strip())
            answers.append('\n'.join(current_answer))
            print(f"保存最后一个命令: {current_command.strip()}")
        
        # 设置结束时间（如果没有明确的结束时间，使用开始时间+5分钟）
        if start_time and not end_time:
            try:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                end_dt = start_dt + timedelta(minutes=5)
                end_time = end_dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                end_time = start_time
        
        print(f"解析结果: {len(commands)} 个命令, {len(answers)} 个答案")
        for i, (cmd, ans) in enumerate(zip(commands, answers)):
            print(f"  命令 {i+1}: {cmd}")
            print(f"  答案 {i+1}: {ans[:100]}...")
        
        return commands, answers, start_time, end_time

    except Exception as e:
        print(f"解析历史日志文件时出错: {e}")
        import traceback
        traceback.print_exc()
        return [], [], None, None


def insert_into_commands_and_answers(commands, shellm_session_id, answers):
    conn, cursor = connect_to_db()
    if conn is None:
        print("数据库连接失败")
        return

    try:
        # Ensure we have a matching number of commands and answers
        if len(commands) != len(answers):
            print(f"警告: 命令数量({len(commands)})与答案数量({len(answers)})不匹配")
            # 调整长度，取较小的那个
            min_len = min(len(commands), len(answers))
            commands = commands[:min_len]
            answers = answers[:min_len]

        print(f"准备插入 {len(commands)} 个命令和答案")

        # Insert each command and its corresponding answer
        for i, (command, answer) in enumerate(zip(commands, answers)):
            print(f"插入命令 {i+1}: {command}")
            
            # Insert command into 'commands' table
            cursor.execute("""
            INSERT INTO commands (shellm_session_id, command)
            VALUES (?, ?)
            """, (shellm_session_id, command))

            # Fetch the last inserted 'command_id'
            cursor.execute("SELECT last_insert_rowid()")
            command_id = cursor.fetchone()[0]
            print(f"命令ID: {command_id}")

            # Insert answer into 'answers' table
            cursor.execute("""
            INSERT INTO answers (command_id, answer)
            VALUES (?, ?)
            """, (command_id, answer))

            print(f"插入答案: {answer[:50]}...")

        # Commit the transaction
        conn.commit()
        print(f"成功插入 {len(commands)} 个命令和答案")

    except Exception as e:
        print(f"插入命令和响应时出错: {e}")
        import traceback
        traceback.print_exc()
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
                    content = f.read().strip()
                    if not content:
                        continue
                    
                    # 解析SSH登录信息格式: username terminal src_ip time_date_start
                    # 例如: root pts/0 127.0.0.1 Sun Jun 22 09:48:19 2025
                    lines = content.split('\n')
                    for line in lines:
                        if not line.strip():
                            continue
                        
                        parts = line.split()
                        if len(parts) >= 8:  # 确保有足够的部分
                            username = parts[0]
                            terminal = parts[1]
                            src_ip = parts[2]
                            # 合并时间和日期部分
                            time_date_start = " ".join(parts[3:8])
                            
                            try:
                                # 转换时间格式
                                login_datetime = datetime.strptime(time_date_start, "%a %b %d %H:%M:%S %Y")
                                time_date_start = login_datetime.strftime("%Y-%m-%d %H:%M:%S")
                                
                                # 目标IP和端口
                                dst_ip = "127.0.0.1"
                                dst_port = 22
                                
                                ssh_sessions.append((username, time_date_start, src_ip, dst_ip, dst_port, log_file))
                                print(f"解析SSH会话: {username} {time_date_start} {src_ip}")
                            except ValueError as e:
                                print(f"时间格式解析错误: {e}, 行: {line}")
                                continue
        
        if not ssh_sessions:
            print("未找到SSH会话")
            return
            
        print(f"解析到 {len(ssh_sessions)} 个SSH会话")
        
        # 获取最新的数据库记录时间
        conn, cursor = connect_to_db()
        if conn is None:
            print("数据库连接失败")
            return
            
        cursor.execute("SELECT MAX(time_date) FROM ssh_session")
        result = cursor.fetchone()
        last_db_time = result[0] if result and result[0] else None
        cursor.close()
        conn.close()
        
        print(f"数据库中最新记录时间: {last_db_time}")
        
        # 强制重新处理所有会话（临时解决方案）
        new_sessions = ssh_sessions
        print(f"强制处理所有 {len(new_sessions)} 个会话")
        
        if new_sessions:
            print(f"检测到 {len(new_sessions)} 个新会话")
            
            # 插入新会话到ssh_session表
            insert_into_ssh_session([(s[0], s[1], s[2], s[3], s[4]) for s in new_sessions])
            
            # 插入攻击者会话
            insert_into_attacker_session([(s[0], s[1], s[2], s[3], s[4]) for s in new_sessions])
            
            # 获取最新的会话ID
            conn, cursor = connect_to_db()
            cursor.execute("SELECT id FROM ssh_session ORDER BY id DESC LIMIT ?", (len(new_sessions),))
            latest_sessions_ids = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            # 获取最新的攻击者ID
            conn, cursor = connect_to_db()
            cursor.execute("SELECT attacker_session_id FROM attacker_session ORDER BY attacker_session_id DESC LIMIT ?", (len(new_sessions),))
            latest_attacker_ids = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            print(f"最新会话ID: {latest_sessions_ids}")
            print(f"最新攻击者ID: {latest_attacker_ids}")
            
            # 处理历史文件
            for i, session in enumerate(new_sessions):
                username, timestamp, source_ip, dst_ip, dst_port, log_file = session
                print(f"处理会话 {i+1}: {username} {timestamp} {source_ip}")
                
                # 从日志文件名中提取UUID
                filename = os.path.basename(log_file)
                uuid_match = re.search(r'logSSH_([a-f0-9-]+)_', filename)
                if uuid_match:
                    uuid = uuid_match.group(1)
                    print(f"提取UUID: {uuid}")
                    
                    # 查找对应的history文件
                    history_files = glob.glob(f'./logs/historySSH_{uuid}_*.txt')
                    print(f"查找历史文件模式: historySSH_{uuid}_*.txt")
                    print(f"找到历史文件: {history_files}")
                    
                    if history_files:
                        history_file = history_files[0]  # 取第一个匹配的文件
                        print(f"使用历史文件: {history_file}")
                        
                    commands, answers, start_time, end_time = parse_historylog(history_file)
                    
                    if not end_time and start_time:
                        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                        end_dt = start_dt + timedelta(minutes=5)
                        end_time = end_dt.strftime("%Y-%m-%d %H:%M:%S")

            if start_time and end_time:
                start_time = format_datetime_for_db(start_time)
                end_time = format_datetime_for_db(end_time)
                
                # 使用对应的会话ID
                if i < len(latest_sessions_ids):
                    session_ids = [latest_sessions_ids[i]]
                    attacker_ids = [latest_attacker_ids[i]] if i < len(latest_attacker_ids) else []
                    
                    print(f"插入shellm_session: start={start_time}, end={end_time}")
                    insert_into_shellm_session(start_time, end_time, session_ids, attacker_ids)
                    shellm_session_id = get_latest_shellm_session()
                    
                    if shellm_session_id and shellm_session_id[0]:
                        print(f"插入命令和答案到shellm_session_id: {shellm_session_id[0]}")
                        insert_into_commands_and_answers(commands, shellm_session_id[0], answers)
                        print(f"已插入 {len(commands)} 条命令记录")
                    else:
                        print("获取shellm_session_id失败")
                else:
                    print(f"会话索引 {i} 超出范围")
            else:
                print("时间解析失败")
        else:
            print("没有新的会话需要处理")
            
    except Exception as e:
        print(f"处理日志文件时出错: {e}")
        import traceback
        traceback.print_exc()


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
            # 从文件名中提取UUID和时间信息
            filename = os.path.basename(log_file)
            # 匹配格式: logSSH_uuid_YYYY-MM-DD_HH-MM-SS.txt
            match = re.match(r'logSSH_([a-f0-9-]+)_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})\.txt', filename)
            if not match:
                print(f"无法解析文件名格式: {filename}")
                continue
                
            uuid, date_str, time_str = match.groups()
            
            # 读取日志文件内容
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read().strip()
            
            if not log_content:
                continue
            
            # 按行解析登录信息
            for line in log_content.split('\n'):
                if not line.strip():
                    continue
                    
                # 解析登录信息格式: username terminal src_ip time_date_start
                # 例如: root pts/0 127.0.0.1 Sun Jun 22 09:48:19 2025
                parts = line.split()
                if len(parts) >= 8:  # 确保有足够的部分
                    username = parts[0]
                    terminal = parts[1]
                    src_ip = parts[2]
                    # 合并时间和日期部分
                    login_time = " ".join(parts[3:8])
                    
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
                    history_file = os.path.join(logs_dir, f"historySSH_{uuid}_{date_str}_{time_str}.txt")
                    commands = []
                    
                    if os.path.exists(history_file):
                        with open(history_file, 'r', encoding='utf-8') as f:
                            history_content = f.read()
                        
                        # 解析命令历史
                        for cmd_line in history_content.split('\n'):
                            cmd_line = cmd_line.strip()
                            if cmd_line and not cmd_line.startswith('$') and not cmd_line.startswith('Session started at:'):
                                # 提取实际的命令（去除提示符）
                                if 'root@' in cmd_line and '$' in cmd_line:
                                    # 跳过包含提示符的行
                                    continue
                                elif cmd_line.startswith('total') or cmd_line.startswith('drwx') or cmd_line.startswith('-rwx'):
                                    # 跳过ls命令的输出
                                    continue
                                else:
                                    commands.append(cmd_line)
                        
                        parsed_logs.append({
                        'session_id': f"{uuid}_{date_str}_{time_str}",
                            'username': username,
                            'terminal': terminal,
                            'src_ip': src_ip,
                        'login_time': time_date_start,
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
            import traceback
            traceback.print_exc()
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