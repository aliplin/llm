import os
import mysql.connector
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('db_credentials.env')

MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_HOST = os.getenv('MYSQL_HOST')


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
    # Connect to the MySQL server
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database='shellm_sessions'
    )
    cursor = conn.cursor()

    return conn, cursor


# Function to insert data into MySQL
def insert_into_ssh_session(data):
    conn, cursor = connect_to_db()

    # Insert data into ssh_session table
    for session in data:
        cursor.execute("""
            INSERT INTO ssh_session (username, time_date, src_ip, dst_ip, dst_port)
            VALUES (%s, %s, %s, %s, %s)
        """, session)

    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()


# Function to insert data into MySQL
def insert_into_attacker_session(data):
    conn, cursor = connect_to_db()

    # Insert data into attacker_session table
    for session in data:
        src_ip = session[2]
        cursor.execute("""
            INSERT INTO attacker_session (src_ip)
            VALUES (%s)
        """, (src_ip,))


    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()


# Function to count how many new connections were to ssh since last database entry
def count_newest(data):
    conn, cursor = connect_to_db()
    cursor.execute("""
        SELECT time_date FROM ssh_session ORDER BY id DESC LIMIT 1;
    """)
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
        if session[1] <= time_date_str:
            break  # 遇到旧会话，停止计数
        counter += 1  # 否则视为新会话

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
    cursor.execute("""
                    SELECT id FROM ssh_session ORDER BY id DESC LIMIT %s;
                """, (counter,))
    ids = [row[0] for row in cursor.fetchall()]

    return ids


def get_latest_attackers_ids(counter):
    ids = []

    conn, cursor = connect_to_db()
    cursor.execute("""
                    SELECT attacker_session_id FROM attacker_session ORDER BY attacker_session_id DESC LIMIT %s;
                """, (counter,))
    ids = [row[0] for row in cursor.fetchall()]

    return ids


import re  # 在文件顶部添加

def parse_historylog(filename):
    commands = []
    answers = []
    start_time = None
    end_time = None

    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as file:
            lines = file.readlines()

        # 提取登录时间
        for line in lines:
            if line.startswith("Last login:"):
                time_part = line.split("Last login: ")[1].strip().split(" on ")[0]
                try:
                    start_time = datetime.strptime(time_part, "%a %b %d %H:%M:%S %Y").strftime("%Y-%m-%d %H:%M:%S")
                except:
                    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break

        previous_line = None
        current_answer = []
        command_pattern = re.compile(r'^.*?([$#])\s*(.*)$')  # 匹配提示符和命令

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = command_pattern.match(line)
            if match:
                # 遇到新命令时，检查上一条命令是否已有响应
                if previous_line and command_pattern.match(previous_line):
                    # 若上一条命令无响应，添加空响应
                    if not current_answer:
                        answers.append("")
                    else:
                        answers.append('\n'.join(current_answer))
                        current_answer = []

                command = match.group(2).strip()
                if command:
                    commands.append(command)
                    print(f"提取命令: {command}")
                previous_line = line
            else:
                if previous_line and command_pattern.match(previous_line):
                    current_answer.append(line)
                    print(f"添加响应: {line}")

            # 处理最后一条命令的响应
        if previous_line and command_pattern.match(previous_line):
            if current_answer:
                answers.append('\n'.join(current_answer))
            else:
                answers.append("")  # 若无响应，添加空字符串
        # 设置结束时间
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if commands else start_time

    except Exception as e:
        print(f"解析失败: {e}")
        return [], [], None, None

    print(f"解析文件 {filename}...")
    print(f"提取的命令: {commands}")
    print(f"开始时间: {start_time}, 结束时间: {end_time}")
    return commands, answers, start_time, end_time


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
            VALUES (%s, %s)
            """, (shellm_session_id, command))

            # Fetch the last inserted 'command_id'
            cursor.execute("""
            SELECT LAST_INSERT_ID();
            """)
            command_id = cursor.fetchone()[0]  # Extract the value from the tuple

            # Insert answer into 'answers' table
            cursor.execute("""
            INSERT INTO answers (command_id, answer)
            VALUES (%s, %s)
            """, (command_id, answers[answer_counter]))

            answer_counter += 1

        # Commit the transaction
        conn.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()  # Rollback in case of error

    finally:
        # Clean up resources
        cursor.close()
        conn.close()


def insert_into_shellm_session(start_time, end_time, latest_session_ids, latest_attacker_ids):
    conn, cursor = connect_to_db()

    ssh_session_id = latest_session_ids[0]
    latest_attacker_id = latest_attacker_ids[0]

    cursor.execute("""
        INSERT INTO shellm_session (ssh_session_id, model, start_time, end_time, attacker_id)
        VALUES (%s, %s, %s, %s, %s)
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
    # Assuming 'last -F' command output is stored in a local file
    with open('ssh_login_history.txt', 'r') as file:
        docker_history = file.read()

    ssh_data = parse_last_output(docker_history)
    counter = count_newest(ssh_data)
    ssh_data = ssh_data[:counter][::-1]

    # Assuming history log files are stored in a local directory
    log_directory = './logs'
    shellm_histories = os.listdir(log_directory)
    shellm_histories = shellm_histories[-counter:] if counter > 0 else []

    print(f"解析到 {len(ssh_data)} 个SSH会话，counter={counter}")
    print(f"日志目录文件列表: {shellm_histories}")

    if counter > 0:
        if docker_history:
            insert_into_ssh_session(ssh_data)
            insert_into_attacker_session(ssh_data)
        else:
            print("Error reading SSH login history.")

        latest_sessions_ids = get_latest_sessions_ids(counter)
        latest_sessions_ids = latest_sessions_ids[::-1]
        latest_attacker_ids = get_latest_attackers_ids(counter)
        latest_attacker_ids = latest_attacker_ids[::-1]

        for filename in shellm_histories:
            file_path = os.path.join(log_directory, filename)
            print(f"正在解析文件: {file_path}")  # 添加调试打印
            commands, answers, start_time, end_time = parse_historylog(file_path)

            if start_time and end_time:
                start_time = format_datetime_for_db(start_time)
                end_time = format_datetime_for_db(end_time)
                insert_into_shellm_session(start_time, end_time, latest_sessions_ids, latest_attacker_ids)

                shellm_session_id = get_latest_shellm_session()
                if shellm_session_id and shellm_session_id[0]:
                    insert_into_commands_and_answers(commands, shellm_session_id[0], answers)
                else:
                    print("警告: 未获取到有效的shellm_session_id")

                latest_sessions_ids = latest_sessions_ids[1:]
                latest_attacker_ids = latest_attacker_ids[1:]
            else:
                print(f"跳过无效文件 {filename}（无有效时间）")

if __name__ == "__main__":
    get_logs_from_local()