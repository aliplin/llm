import os
import re
import threading
import uuid
from datetime import datetime
import paramiko
from paramiko import ServerInterface, Transport
import select
import openai
from pathlib import Path

SSH_PORT = 5656
SSH_USER = "root"
SSH_PASS = "123456"
today = datetime.now()
line_ending="\r\n"
# 目录切换命令处理

#目录切换模拟
def handle_cd_command(user_input, current_dir, username):
    if user_input.startswith("cd "):
        new_dir = user_input[3:].strip()
        if not new_dir or new_dir == "~":
            return f"/home/{username}"
        elif new_dir == "/":
            return new_dir
        elif new_dir.startswith("/"):
            return new_dir
        else:
            if current_dir == f"/home/{username}":
                return f"/home/{username}/{new_dir}"
            else:
                return os.path.join(current_dir, new_dir)
    return current_dir

#对Shell输出进行格式化，清理多余的空行和空格，生成更加整洁的终端输出内容
def format_shell_output(text):
    # 去除多余空行和首尾空格，合并多余换行
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and lines[0] == '':
        lines.pop(0)
    while lines and lines[-1] == '':
        lines.pop()
    return f'{line_ending}'.join(lines)


def format_ai_response(response, command):
    import re, os
    # 匹配所有命令行提示符（如 root@honeypot:~#、root@honeypot:/bin$ 等）
    prompt_pattern = r'[\w.-]+@[\w.-]+:[~\w/\.-]*[#$]'
    matches = list(re.finditer(prompt_pattern, response))
    if len(matches) >= 2:
        # 只保留第一个和最后一个提示符之间的内容
        start = matches[0].end()
        end = matches[-1].start()
        response = response[start:end]
    else:
        # 如果只剩下提示符（或全是提示符），直接返回空
        if re.fullmatch(r'\s*' + prompt_pattern + r'\s*', response):
            return ''
    # 去除首尾多余换行
    response = response.strip('\r\n')
    # 其余格式化逻辑（如ls、pwd等）可保留
    command_lower = command.lower().strip()
    if command_lower == 'ls' or command_lower.startswith('ls '):
        lines = response.split('\n')
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('$') and not line.startswith(command_lower):
                if not re.match(r'^[d-][rwx-]{9}\s+\d+', line):
                    if os.path.basename(line):
                        formatted_lines.append(line)
                else:
                    formatted_lines.append(line)
        return '\n'.join(formatted_lines) if formatted_lines else response
    elif command_lower == 'pwd':
        path_match = re.search(r'/([^/\s]+/?)*', response)
        if path_match:
            return path_match.group(0)
        return response.strip()
    elif command_lower == 'whoami':
        cleaned_response = re.sub(r'^whoami\s*', '', response)
        username_match = re.search(r'\b\w+\b', cleaned_response)
        if username_match:
            return username_match.group(0)
        return cleaned_response.strip()
    elif command_lower.startswith('cat ') or command_lower.startswith('head ') or command_lower.startswith('tail '):
        return re.sub(r'^.*?\$\s*', '', response)
    elif command_lower in ['clear', 'reset']:
        return '\033[2J\033[H'
    else:
        return response.strip()

# SSH蜜罐主类
class HoneyPotServer(ServerInterface):
    def __init__(self, openai_client, identity, model_name, temperature, max_tokens, output_dir, log_file, username,
                 hostname):
        self.openai_client = openai_client
        self.identity = identity
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.output_dir = output_dir
        self.log_file = log_file
        self.username = username
        self.hostname = hostname
        self.channel = None
        self.pty_kwargs = {}
        self.input_buffer = ""
        self.running = True
        self.input_cond = threading.Condition()
        self.debug = True  # 调试模式开关
        # 生成会话唯一标识符
        self.session_uuid = str(uuid.uuid4())
        self.session_start_time = datetime.now()

        # 创建日志文件路径
        timestamp = self.session_start_time.strftime("%Y-%m-%d_%H-%M-%S")
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)  # 确保目录存在
        self.log_ssh_file = logs_dir / f"logSSH_{self.session_uuid}_{timestamp}.txt"
        self.history_ssh_file = logs_dir / f"historySSH_{self.session_uuid}_{timestamp}.txt"

    def log_login_info(self):
        """记录登录信息到logSSH文件，格式与ssh_module.py可解析的格式一致"""
        try:
            # 获取客户端IP地址
            client_ip = "127.0.0.1"  # 默认值

            # 优先从transport获取客户端IP
            if hasattr(self, 'transport') and self.transport:
                try:
                    client_ip = self.transport.getpeername()[0]
                except:
                    pass
            # 如果transport不可用，尝试从channel获取
            elif hasattr(self, 'channel') and self.channel:
                try:
                    client_ip = self.channel.getpeername()[0]
                except:
                    pass

            # 生成会话ID
            session_id = str(uuid.uuid4())
            timestamp = self.session_start_time.strftime('%Y-%m-%d_%H-%M-%S')

            # 创建日志文件路径
            project_root = Path(__file__).parent.parent.parent
            logs_dir = project_root / "logs"
            logs_dir.mkdir(exist_ok=True)  # 确保目录存在

            # 使用会话ID和时间戳作为文件名
            log_ssh_file = logs_dir / f"logSSH_{session_id}_{timestamp}.txt"

            # 生成符合ssh_module.py解析格式的登录记录
            # 格式: username terminal src_ip time_date_start
            # 例如: root pts/0 192.168.1.100 Mon Aug 15 08:44:32 2024
            login_record = f"{self.username} pts/0 {client_ip} {self.session_start_time.strftime('%a %b %d %H:%M:%S %Y')}\n"

            # 写入登录记录
            with open(log_ssh_file, 'w', encoding='utf-8') as f:
                f.write(login_record)

            print(f"[SSH蜜罐] 登录信息已记录到: {log_ssh_file}")

            # 创建命令历史文件
            history_ssh_file = logs_dir / f"historySSH_{session_id}_{timestamp}.txt"
            self.history_ssh_file = history_ssh_file

            # 写入会话开始时间
            with open(history_ssh_file, 'w', encoding='utf-8') as f:
                f.write(f"Session started at: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

            print(f"[SSH蜜罐] 历史记录文件已创建: {history_ssh_file}")

        except Exception as e:
            print(f"[SSH蜜罐] 记录登录信息失败: {e}")

    def check_auth_password(self, username, password):
        # 记录登录尝试
        with open(self.log_file, 'a') as f:
            f.write(f"[{datetime.now()}] 登录尝试 - 用户: {username}, 密码: {password}\n")

        # 验证用户名密码
        if username == SSH_USER and password == SSH_PASS:
            print(f"[SSH蜜罐] {username} 登录成功")
            # 不要手动发送认证响应，让paramiko处理
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        # 只允许密码认证
        return 'password'

    def check_channel_request(self, kind, chanid):
        # 只允许会话通道
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, width_pixels, height_pixels, modes):
        # 处理PTY请求
        print("[SSH蜜罐] PTY请求已接受")
        self.pty_kwargs = {
            'term': term,
            'width': width,
            'height': height,
            'width_pixels': width_pixels,
            'height_pixels': height_pixels,
            'modes': modes
        }
        return True

    def check_channel_shell_request(self, channel):
        # 处理Shell请求
        print("[SSH蜜罐] Shell请求已接受")
        self.channel = channel

        # 在shell建立时记录登录信息（此时channel已可用）
        self.log_login_info()

        # 创建新线程处理Shell会话
        threading.Thread(target=self.handle_shell, daemon=True).start()
        return True

    def check_channel_direct_tcpip_request(self, channel, dest_addr, dest_port, origin_addr, origin_port):
        print(f"[SSH蜜罐] 收到直接TCP/IP请求: {dest_addr}:{dest_port}")
        return False

    def check_channel_x11_request(self, channel, single_connection, auth_protocol, auth_cookie, screen_number):
        print("[SSH蜜罐] 收到X11请求")
        return False

    def check_channel_forward_agent_request(self, channel):
        print("[SSH蜜罐] 收到代理转发请求")
        return False

    def check_channel_window_change_request(self, channel, width, height, width_pixels, height_pixels):
        print(f"[SSH蜜罐] 收到窗口大小改变请求: {width}x{height}")
        return True

    def check_channel_env_request(self, channel, name, value):
        print(f"[SSH蜜罐] 收到环境变量请求: {name}={value}")
        return True

    def check_channel_subsystem_request(self, channel, subsystem):
        print(f"[SSH蜜罐] 收到子系统请求: {subsystem}")
        return False

    def check_port_forward_request(self, address, port):
        print(f"[SSH蜜罐] 收到端口转发请求: {address}:{port}")
        return False

    def handle_shell(self):
        personality = self.identity['prompt'] + self.identity['final_instr']
        fixed_identity = f"User is {self.username}@{self.hostname}. "
        initial_prompt = f"Your personality is: {fixed_identity}{personality}"
        messages = [{"role": "system", "content": initial_prompt}]
        current_dir = f"/home/{self.username}"
        self.input_buffer = ""
        client_ip = self.channel.getpeername()[0] if self.channel else "unknown"
        welcome_lines = [
            f"Last login: {today.strftime('%a %b %d %H:%M:%S %Y')} from {client_ip}{line_ending}",
            f"Welcome to Ubuntu 20.04.6 LTS (GNU/Linux 5.4.0-100-generic x86_64){line_ending}",
            f"{line_ending}",
            f" * Documentation:  https://help.ubuntu.com/{line_ending}",
            f" * Management:     https://landscape.canonical.com{line_ending}",
            f" * Support:        https://ubuntu.com/advantage{line_ending}",
            f"{line_ending}",
            f"  System information as of {today.strftime('%a %b %d %H:%M:%S %Y')}{line_ending}",
            f"{line_ending}",
            f"  System load:  0.52    Users logged in:    1{line_ending}",
            f"  Usage of /:   23.4% of 251.0GB    IPv4 address: 192.168.1.100{line_ending}",
            f"  Memory usage: 45%      System uptime: 2 days{line_ending}",
            f"  Swap usage:   0%{line_ending}",
            f"{line_ending}",
            f"0 updates can be applied immediately.{line_ending}",
            f"The list of available updates is more than a week old.{line_ending}",
            f"To check for new updates run: sudo apt update{line_ending}",
            f"{line_ending}"
        ]
        def send_prompt():
            prompt_display_dir = current_dir
            if current_dir.startswith(f"/home/{self.username}"):
                prompt_display_dir = "~" + current_dir[len(f"/home/{self.username}"):]
            prompt = f"{self.username}@{self.hostname}:{prompt_display_dir}$ "
            self.channel.send(prompt)
        self.channel.send(format_shell_output("".join(welcome_lines)) + f"{line_ending}")
        send_prompt()
        while self.running and self.channel is not None and self.channel.active:
            command = self.read_until_newline()
            if command is None:
                break
            command = command.rstrip(f'{line_ending}')
            if command.strip() == "":
                send_prompt()
                continue

            print(f"[SSH蜜罐] 收到命令: {command}")
            current_dir = handle_cd_command(command, current_dir, self.username)
            cmd_lower = command.strip().lower()

            if cmd_lower in ("exit", "logout", "\q"):
                self.channel.send(format_shell_output(f"{line_ending}logout") + f"{line_ending}")
                self.running = False
                break
            if cmd_lower == "clear":
                self.channel.send("\033[2J\033[H")
                send_prompt()
                continue
            if cmd_lower.startswith("cd "):
                send_prompt()
                continue

            messages.append({"role": "user", "content": command})

            try:
                if self.debug: print(f"[SSH蜜罐] 正在调用LLM API，命令: {command}")
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                ai_response = response.choices[0].message.content
                if self.debug: print(f"[SSH蜜罐] LLM原始响应: {repr(ai_response)}")
                ai_response = format_ai_response(ai_response, command)
                formatted = format_shell_output(ai_response)
                if formatted.strip():
                    self.channel.send(formatted + f"{line_ending}")
                    messages.append({"role": "assistant", "content": ai_response})
                    if self.debug: print(f"[SSH蜜罐] LLM响应已发送，长度: {len(ai_response)}")
                    # 写入历史
                    try:
                        with open(self.history_ssh_file, "a", encoding="utf-8") as f:
                            display_dir = current_dir
                            f.write(f"{self.username}@{self.hostname}:{display_dir}$ {command}\n")
                            f.write(f"{ai_response}\n")
                    except Exception as e:
                        print(f"[SSH蜜罐] 记录交互历史失败: {e}")
                else:
                    self.channel.send("")
                    if self.debug: print("[SSH蜜罐] AI响应为空，跳过记录assistant消息")
            except Exception as e:
                error_msg = format_shell_output(f"bash: {command}: command not found")
                self.channel.send(error_msg + f"{line_ending}")
                print(f"[SSH蜜罐] LLM调用失败，发送默认错误消息: {e}")
            send_prompt()
        if self.channel is not None:
            self.channel.close()
        print(f"[SSH蜜罐] 连接已关闭")

    def read_until_newline(self):
        """使用select监听数据，实时回显用户输入"""
        buffer = self.input_buffer
        self.input_buffer = ""  # 重用现有缓冲区

        if self.debug: print(f"[SSH蜜罐] 开始读取输入，初始缓冲区: {repr(buffer)}")

        while self.running and self.channel is not None and self.channel.active:
            # 使用select监听通道可读事件
            try:
                readable, _, _ = select.select([self.channel], [], [], 0.1)  # 100ms超时，提高响应性
                if not readable:
                    continue  # 超时继续循环

                data = self.channel.recv(1)  # 一次读取一个字符
                if not data:
                    if self.debug: print("[SSH蜜罐] 收到空数据，连接可能已关闭")
                    break

                char = data.decode('utf-8', errors='ignore')
                if self.debug: print(f"[SSH蜜罐] 收到字符: {repr(char)} (ASCII: {ord(char)})")

                # 处理特殊字符
                if char == '\r' or char == '\n':  # 回车或换行键
                    # 发送换行符给客户端，让用户看到换行
                    self.channel.send(f"{line_ending}")
                    if self.debug: print(f"[SSH蜜罐] 收到回车/换行键，返回命令: {repr(buffer)}")
                    return buffer.strip()
                elif char == '\x7f':  # 退格键 (Backspace)
                    if buffer:
                        buffer = buffer[:-1]
                        # 发送退格序列：退格、空格、退格
                        self.channel.send('\b \b')
                        if self.debug: print(f"[SSH蜜罐] 退格，缓冲区: {repr(buffer)}")
                elif char == '\x03':  # Ctrl+C
                    buffer = ""
                    self.channel.send(f"{line_ending}")
                    if self.debug: print("[SSH蜜罐] 收到Ctrl+C")
                    return ""
                elif char == '\x04':  # Ctrl+D (EOF)
                    if self.debug: print("[SSH蜜罐] 收到Ctrl+D")
                    return ""
                elif char == '\x1b':  # ESC键，可能是ANSI转义序列的开始
                    if self.debug: print("[SSH蜜罐] 收到ESC键，忽略")
                    continue
                elif ord(char) >= 32 and ord(char) != 127:  # 可打印字符，排除DEL
                    buffer += char
                    # 实时回显字符
                    self.channel.send(char)
                    if self.debug: print(f"[SSH蜜罐] 添加字符，缓冲区: {repr(buffer)}")
                else:
                    if self.debug: print(f"[SSH蜜罐] 忽略控制字符: {repr(char)} (ASCII: {ord(char)})")

            except Exception as e:
                print(f"[SSH蜜罐] 读取错误: {e}")
                break

        # 保存未解析的缓冲区
        self.input_buffer = buffer
        if self.debug and buffer:
            print(f"[SSH蜜罐] 返回剩余缓冲区命令: {repr(buffer)}")
        return buffer.strip()

    def global_request(self, channel, request_type, want_reply):
        print(f"[SSH蜜罐] 收到全局请求: {request_type}")

        # 处理认证后的会话请求
        if request_type == "pty-req":
            print("[SSH蜜罐] 处理伪终端请求")
            return True
        elif request_type == "shell":
            print("[SSH蜜罐] 处理Shell请求")
            return True
        elif request_type == "env":
            print("[SSH蜜罐] 处理环境变量请求")
            return True
        elif request_type == "agent-forward":
            print("[SSH蜜罐] 处理SSH代理转发请求")
            return want_reply

        # 原有处理逻辑
        if request_type == "hostkeys-00@openssh.com":
            return True
        return want_reply

    def auth_response(self, success):
        """重写认证响应方法，主动发送认证成功包"""
        from paramiko.message import Message

        msg = Message()
        if success:
            msg.add_byte(paramiko.common.cMSG_USERAUTH_SUCCESS)
            self.transport._send_message(msg)
            print("[SSH蜜罐] 已发送认证成功响应 (31号包)")
        else:
            super().auth_response(success)



# SSH连接处理
def handle_ssh_connection(client_socket, openai_client, identity, model_name,
                          temperature, max_tokens, output_dir, log_file, username, hostname):
    try:
        # 生成或加载RSA密钥
        project_root = Path(__file__).parent.parent.parent.parent
        key_file = project_root / "config" / "host_key"
        if not os.path.exists(key_file):
            host_key = paramiko.RSAKey.generate(2048)
            host_key.write_private_key_file(key_file)
            print(f"[SSH蜜罐] 已生成新的主机密钥: {key_file}")
        else:
            host_key = paramiko.RSAKey(filename=key_file)

        # 创建SSH传输
        transport = Transport(client_socket)
        transport.add_server_key(host_key)

        # 设置服务器接口
        server = HoneyPotServer(openai_client, identity, model_name, temperature, max_tokens, output_dir, log_file,
                                username, hostname)
        server.transport = transport

        # 启动服务器模式
        print("[SSH蜜罐] 开始SSH协议协商...")

        # 设置服务器版本
        transport.local_version = "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5"

        # 启动服务器
        transport.start_server(server=server)
        print("[SSH蜜罐] SSH协议协商完成")

        # 等待连接关闭
        transport.join()

    except Exception as e:
        error_msg = f"[SSH蜜罐错误]: {e}\n"
        print(error_msg)
        print("[SSH蜜罐] 详细错误信息:")
        import traceback
        traceback.print_exc()
        if 'transport' in locals():
            transport.close()
