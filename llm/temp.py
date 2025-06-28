import argparse
import errno
import os
import random
import re
import time
from datetime import datetime
from time import sleep
import yaml
from dotenv import dotenv_values
import tiktoken
from openai import OpenAI
import threading
import paramiko
import socket
import os
import select
import uuid
from paramiko import ServerInterface, Transport
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import struct

# 设置 Kimi API 的基础 URL
OpenAI.api_base = "https://api.moonshot.cn/v1"
today = datetime.now()

# 服务配置
SSH_PORT = 5656
HTTP_PORT = 8080
SSH_USER = "root"
SSH_PASS = "123456"


def read_arguments():
    parser = argparse.ArgumentParser(description='LLM驱动的SSH蜜罐服务')

    # 必需参数
    parser.add_argument('-e', '--env', required=True, help='环境变量文件路径 (.env)')
    parser.add_argument('-c', '--config', required=True, help='配置文件路径 (yaml)')

    # 可选参数
    parser.add_argument('-m', '--model', help='模型名称')
    parser.add_argument('-t', '--temperature', type=float, help='温度参数')
    parser.add_argument('-mt', '--max_tokens', type=int, help='最大token数')
    parser.add_argument('-o', '--output', help='输出目录')
    parser.add_argument('-l', '--log', help='日志文件')

    args = parser.parse_args()

    return (args.config, args.env, args.model, args.temperature,
            args.max_tokens, args.output, args.log)


def set_key(env_path):
    env = dotenv_values(env_path)
    if "KIMI_API_KEY" not in env:
        raise ValueError("未找到 API 密钥")
    return OpenAI(
        api_key=env["KIMI_API_KEY"],
        base_url="https://api.moonshot.cn/v1",
        timeout=60
    )


def read_history(identity, output_dir, reset_prompt):
    history = open(output_dir, "a+", encoding="utf-8")
    TOKEN_COUNT = 0

    if os.stat(output_dir).st_size != 0:
        history.write(reset_prompt)
        history.seek(0)
        prompt = history.read()

        encoding = tiktoken.get_encoding("cl100k_base")
        TOKEN_COUNT = len(encoding.encode(prompt))

    if TOKEN_COUNT > 15100 or os.stat(output_dir).st_size == 0:
        prompt = identity['prompt']
        history.truncate(0)

    history.close()
    return prompt


def set_parameters(identity, model_name, model_temperature, model_max_tokens, output_dir, log_file):
    if model_name is None:
        model_name = identity.get('model', '').strip()
        if not model_name:
            raise ValueError("配置文件中缺少 model 参数")

    if model_max_tokens is None:
        max_tokens_value = identity.get('max_tokens')
        if max_tokens_value is None:
            raise ValueError("配置文件中缺少 max_tokens 参数")
        try:
            model_max_tokens = int(max_tokens_value) if isinstance(max_tokens_value, str) else max_tokens_value
        except (ValueError, TypeError):
            raise ValueError(f"max_tokens 参数格式错误: {max_tokens_value}")

    if model_temperature is None:
        temperature_value = identity.get('temperature')
        if temperature_value is None:
            raise ValueError("配置文件中缺少 temperature 参数")
        try:
            model_temperature = float(temperature_value) if isinstance(temperature_value, str) else temperature_value
        except (ValueError, TypeError):
            raise ValueError(f"temperature 参数格式错误: {temperature_value}")

    if output_dir is None:
        output_dir = identity.get('output', '').strip()
        if not output_dir:
            raise ValueError("配置文件中缺少 output 参数")

    if log_file is None:
        log_file = identity.get('log', '').strip()
        if not log_file:
            raise ValueError("配置文件中缺少 log 参数")

    return model_name, model_temperature, model_max_tokens, output_dir, log_file


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


def format_ai_response(response, command):
    """格式化AI响应，使其更符合真实Linux命令的输出格式"""
    # 移除可能的多余提示符和命令前缀
    response = re.sub(r'\$\s*$', '', response)
    response = re.sub(r'^.*?\$\s*', '', response)  # 移除开头的提示符
    response = re.sub(r'^.*?\$\s*', '', response)  # 再次移除，以防有多层

    # 根据命令类型进行特殊处理
    command_lower = command.lower().strip()

    if command_lower == 'ls' or command_lower.startswith('ls '):
        # ls命令格式化
        lines = response.split('\n')
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('$') and not line.startswith(command_lower):
                # 确保ls输出格式正确
                if not re.match(r'^[d-][rwx-]{9}\s+\d+', line):
                    # 如果不是标准ls格式，尝试格式化
                    if os.path.basename(line):
                        formatted_lines.append(line)
                else:
                    formatted_lines.append(line)
        return '\n'.join(formatted_lines) if formatted_lines else response

    elif command_lower == 'pwd':
        # pwd命令应该只返回路径
        path_match = re.search(r'/([^/\s]+/?)*', response)
        if path_match:
            return path_match.group(0)
        return response.strip()

    elif command_lower == 'whoami':
        # whoami命令应该只返回用户名
        # 移除可能包含的命令本身
        cleaned_response = re.sub(r'^whoami\s*', '', response)
        username_match = re.search(r'\b\w+\b', cleaned_response)
        if username_match:
            return username_match.group(0)
        return cleaned_response.strip()

    elif command_lower.startswith('cat ') or command_lower.startswith('head ') or command_lower.startswith('tail '):
        # 文件内容命令，保持原格式但清理命令前缀
        return re.sub(r'^.*?\$\s*', '', response)

    elif command_lower in ['clear', 'reset']:
        # 清屏命令
        return '\033[2J\033[H'  # ANSI清屏序列

    else:
        # 其他命令，保持原格式但清理多余内容
        return response.strip()


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
        logs_dir = os.path.join(os.path.dirname(__file__), "..", "Log Manager", "logs")
        os.makedirs(logs_dir, exist_ok=True)  # 确保目录存在
        self.log_ssh_file = os.path.join(logs_dir, f"logSSH_{self.session_uuid}_{timestamp}.txt")
        self.history_ssh_file = os.path.join(logs_dir, f"historySSH_{self.session_uuid}_{timestamp}.txt")

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
            logs_dir = os.path.join(os.path.dirname(__file__), "..", "Log Manager", "logs")
            os.makedirs(logs_dir, exist_ok=True)  # 确保目录存在

            # 使用会话ID和时间戳作为文件名
            log_ssh_file = os.path.join(logs_dir, f"logSSH_{session_id}_{timestamp}.txt")

            # 生成符合ssh_module.py解析格式的登录记录
            # 格式: username terminal src_ip time_date_start
            # 例如: root pts/0 192.168.1.100 Mon Aug 15 08:44:32 2024
            login_record = f"{self.username} pts/0 {client_ip} {self.session_start_time.strftime('%a %b %d %H:%M:%S %Y')}\n"

            # 写入登录记录
            with open(log_ssh_file, 'w', encoding='utf-8') as f:
                f.write(login_record)

            print(f"[SSH蜜罐] 登录信息已记录到: {log_ssh_file}")

            # 创建命令历史文件
            history_ssh_file = os.path.join(logs_dir, f"historySSH_{session_id}_{timestamp}.txt")
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
        # 构建LLM交互环境
        personality = self.identity['prompt'] + self.identity['final_instr']
        fixed_identity = f"User is {self.username}@{self.hostname}. "
        initial_prompt = f"Your personality is: {fixed_identity}{personality}"
        messages = [{"role": "system", "content": initial_prompt}]

        # 初始化目录状态
        current_dir = f"/home/{self.username}"
        self.input_buffer = ""

        # 发送欢迎信息
        client_ip = self.channel.getpeername()[0] if self.channel else "unknown"
        welcome_msg = f"Last login: {today.strftime('%a %b %d %H:%M:%S %Y')} from {client_ip}\n"
        welcome_msg += "Welcome to Ubuntu 20.04.6 LTS (GNU/Linux 5.4.0-100-generic x86_64)\n\n"
        welcome_msg += " * Documentation:  https://help.ubuntu.com/\n"
        welcome_msg += " * Management:     https://landscape.canonical.com\n"
        welcome_msg += " * Support:        https://ubuntu.com/advantage\n\n"
        welcome_msg += "  System information as of " + today.strftime('%a %b %d %H:%M:%S %Y') + "\n\n"
        welcome_msg += "  System load:  0.52              Users logged in:       1\n"
        welcome_msg += "  Usage of /:   23.4% of 251.0GB  IPv4 address:         192.168.1.100\n"
        welcome_msg += "  Memory usage: 45%               System uptime:         2 days\n"
        welcome_msg += "  Swap usage:   0%\n\n"
        welcome_msg += "0 updates can be applied immediately.\n\n"
        welcome_msg += "The list of available updates is more than a week old.\n"
        welcome_msg += "To check for new updates run: sudo apt update\n\n"

        self.channel.send(welcome_msg)
        if self.debug: print("[SSH蜜罐] 欢迎信息已发送")

        # 构建命令提示符
        display_dir = current_dir
        if current_dir.startswith(f"/home/{self.username}"):
            display_dir = "~" + current_dir[len(f"/home/{self.username}"):]
        prompt = f"{self.username}@{self.hostname}:{display_dir}$ "
        self.channel.send(prompt)
        if self.debug: print(f"[SSH蜜罐] 已发送提示符: {prompt}")

        # 命令交互循环
        while self.running and self.channel is not None and self.channel.active:

            # 接收用户命令（事件驱动方式）
            command = self.read_until_newline()
            if not command:
                if self.debug: print("[SSH蜜罐] 收到空命令，继续循环")
                continue  # 连接关闭或出错

            print(f"[SSH蜜罐] 收到命令: {command}")

            # 处理cd命令
            current_dir = handle_cd_command(command, current_dir, self.username)

            # 退出命令处理
            if command.lower() in ("exit", "logout", "\q"):
                self.channel.send("logout\nConnection to 127.0.0.1 closed.\n")
                self.running = False
                if self.debug: print("[SSH蜜罐] 收到退出命令")
                break

            # 调用LLM生成响应
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

                # # 格式化AI响应，使其更逼真
                # formatted_response = format_ai_response(ai_response, command)
                #
                # if self.debug: print(f"[SSH蜜罐] 格式化后响应: {repr(formatted_response)}")

                # 发送响应给客户端
                self.channel.send(ai_response)
                messages.append({"role": "assistant", "content": ai_response})
                if self.debug: print(f"[SSH蜜罐] LLM响应已发送，长度: {len(ai_response)}")

                # 记录交互到historySSH文件
                try:
                    with open(self.history_ssh_file, "a", encoding="utf-8") as f:
                        f.write(f"{self.username}@{self.hostname}:{display_dir}$ {command}\n")
                        f.write(f"{ai_response}\n")
                    if self.debug: print(f"[SSH蜜罐] 交互已记录到: {self.history_ssh_file}")
                except Exception as e:
                    print(f"[SSH蜜罐] 记录交互历史失败: {e}")

            except Exception as e:
                error_msg = f"bash: {command}: command not found\n"
                self.channel.send(error_msg)
                print(f"[SSH蜜罐] LLM调用失败，发送默认错误消息: {e}")
                # 不要因为单个命令失败就结束会话，继续循环
                continue

        # 关闭连接
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
                    self.channel.send('\n')
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
                    self.channel.send('\n')
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


class HTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.openai_client = kwargs.pop('openai_client', None)
        self.identity = kwargs.pop('identity', None)
        self.model_name = kwargs.pop('model_name', None)
        self.temperature = kwargs.pop('temperature', None)
        self.max_tokens = kwargs.pop('max_tokens', None)
        self.output_dir = kwargs.pop('output_dir', None)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        try:
            # 记录请求
            client_ip = self.client_address[0]
            request_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 生成独立日志文件名
            logs_dir = os.path.join(os.path.dirname(__file__), "..", "Log Manager", "logs")
            os.makedirs(logs_dir, exist_ok=True)
            session_uuid = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_file = os.path.join(logs_dir, f"logHTTP_{session_uuid}_{timestamp}.txt")
            # 读取请求头
            headers = dict(self.headers)
            # 构建请求信息
            request_info = {
                "method": self.command,
                "path": self.path,
                "headers": headers,
                "client_ip": client_ip,
                "time": request_time
            }
            # 调用LLM生成响应
            messages = [
                {"role": "system", "content": self.identity['prompt']},
                {"role": "user", "content": json.dumps(request_info)}
            ]
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            # 解析LLM响应
            content = response.choices[0].message.content
            # 发送响应
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode())
            # 记录响应到独立日志文件
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"HTTP Request: {json.dumps(request_info)}\n")
                f.write(f"Response: {content}\n")
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Internal Server Error")


def start_http_server(openai_client, identity, model_name, temperature, max_tokens, output_dir, log_file):
    """启动HTTP服务器"""

    def handler(*args, **kwargs):
        return HTTPHandler(*args,
                           openai_client=openai_client,
                           identity=identity,
                           model_name=model_name,
                           temperature=temperature,
                           max_tokens=max_tokens,
                           output_dir=output_dir,
                           **kwargs)

    server = HTTPServer(('0.0.0.0', HTTP_PORT), handler)
    print(f"HTTP服务器启动在端口 {HTTP_PORT}")
    server.serve_forever()


def handle_ssh_connection(client_socket, openai_client, identity, model_name,
                          temperature, max_tokens, output_dir, log_file, username, hostname):
    try:
        # 生成或加载RSA密钥
        key_file = os.path.join(os.path.dirname(__file__), 'host_key')
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


def main():
    try:
        # 读取命令行参数
        # config_path, env_path, model_name, temperature, max_tokens, output_dir, log_file = read_arguments()
        env_path = '.env'
        # 读取各自配置文件
        with open(os.path.join(os.path.dirname(__file__), 'configSSH.yml'), 'r', encoding='utf-8') as f:
            ssh_identity = yaml.safe_load(f)['personality']
        with open(os.path.join(os.path.dirname(__file__), 'configHTTP.yml'), 'r', encoding='utf-8') as f:
            http_identity = yaml.safe_load(f)['personality']
        with open(os.path.join(os.path.dirname(__file__), 'configPOP3.yml'), 'r', encoding='utf-8') as f:
            pop3_identity = yaml.safe_load(f)['personality']
        with open(os.path.join(os.path.dirname(__file__), 'configMySQL.yml'), 'r', encoding='utf-8') as f:
            mysql_identity = yaml.safe_load(f)['personality']
        # 设置API密钥
        openai_client = set_key(env_path)
        # 设置各自参数
        ssh_model, ssh_temp, ssh_max_tokens, ssh_output, ssh_log = set_parameters(
            ssh_identity, None, None, None, None, None)
        http_model, http_temp, http_max_tokens, http_output, http_log = set_parameters(
            http_identity, None, None, None, None, None)
        pop3_model, pop3_temp, pop3_max_tokens, pop3_output, pop3_log = set_parameters(
            pop3_identity, None, None, None, None, None)
        mysql_model, mysql_temp, mysql_max_tokens, mysql_output, mysql_log = set_parameters(
            mysql_identity, None, None, None, None, None)
        # 启动SSH服务器
        ssh_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssh_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ssh_server.bind(('0.0.0.0', SSH_PORT))
        ssh_server.listen(100)
        print(f"SSH服务器启动在端口 {SSH_PORT}")
        # 启动HTTP服务器（在新线程中，传递http_identity和参数）
        http_thread = threading.Thread(
            target=start_http_server,
            args=(openai_client, http_identity, http_model, http_temp, http_max_tokens, http_output, http_log)
        )
        http_thread.daemon = True
        http_thread.start()

        # 启动POP3服务器（新线程，传递pop3_identity和参数）
        def start_pop3():
            import uuid
            import threading
            from datetime import datetime
            import socket
            logs_dir = os.path.join(os.path.dirname(__file__), "..", "Log Manager", "logs")
            os.makedirs(logs_dir, exist_ok=True)
            pop3_port = int(pop3_identity.get('port', 110))

            def handle_pop3_client(client_sock, client_addr):
                session_uuid = str(uuid.uuid4())
                session_start_time = datetime.now()
                timestamp = session_start_time.strftime("%Y-%m-%d_%H-%M-%S")
                log_file = os.path.join(logs_dir, f"logPOP3_{session_uuid}_{timestamp}.txt")
                history_file = os.path.join(logs_dir, f"historyPOP3_{session_uuid}_{timestamp}.txt")
                try:
                    with open(log_file, 'a', encoding='utf-8') as logf:
                        logf.write(f"POP3 session start: {session_start_time} from {client_addr[0]}:{client_addr[1]}\n")
                    with open(history_file, 'a', encoding='utf-8') as histf:
                        histf.write(f"Session started at: {session_start_time}\n")
                except Exception as e:
                    print(f"[POP3蜜罐] 日志文件创建失败: {e}")
                messages = [
                    {"role": "system", "content": pop3_identity['prompt'] + pop3_identity.get('final_instr', '')}
                ]
                banner = "Connected to pop.domain.ext.\r\nEscape character is '^]'.\r\n+OK ready\r\n> "
                try:
                    client_sock.sendall(banner.encode())
                    with open(log_file, 'a', encoding='utf-8') as logf:
                        logf.write(f"[BANNER] {banner}\n")
                except Exception as e:
                    print(f"[POP3蜜罐] 发送banner失败: {e}")
                    client_sock.close()
                    return
                while True:
                    try:
                        data = b''
                        while not data.endswith(b'\n') and not data.endswith(b'\r\n'):
                            chunk = client_sock.recv(1024)
                            if not chunk:
                                raise ConnectionError('客户端断开连接')
                            data += chunk
                        command = data.decode(errors='ignore').strip()
                        if not command:
                            continue
                        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        with open(log_file, 'a', encoding='utf-8') as logf:
                            logf.write(f"[{now}] [CMD] {command}\n")
                        with open(history_file, 'a', encoding='utf-8') as histf:
                            histf.write(f"> {command}\n")
                        messages.append({"role": "user", "content": command})
                        try:
                            response = openai_client.chat.completions.create(
                                model=pop3_model,
                                messages=messages,
                                temperature=pop3_temp,
                                max_tokens=pop3_max_tokens
                            )
                            ai_response = response.choices[0].message.content
                            print(f"[POP3蜜罐] 发送响应前: {ai_response}")
                            # 将所有 \n 替换为 \r\n
                            ai_response = ai_response.replace('\n', '\r\n')
                            # 确保响应以 \r\n> 结尾
                            if not ai_response.endswith('\r\n'):
                                ai_response += '\r\n>'
                            print(f"[POP3蜜罐] 发送响应后: {ai_response}")
                        except Exception as e:
                            ai_response = f"-ERR LLM服务异常: {e}\r\n> "
                        with open(log_file, 'a', encoding='utf-8') as logf:
                            logf.write(f"[{now}] [RESP] {ai_response}\n")
                        with open(history_file, 'a', encoding='utf-8') as histf:
                            histf.write(f"{ai_response}\n")
                        try:
                            client_sock.sendall(ai_response.encode())
                        except Exception as e:
                            print(f"[POP3蜜罐] 发送响应失败: {e}")
                            break
                        if command.lower() in ("quit", "exit", "logout"):
                            break
                    except Exception as e:
                        print(f"[POP3蜜罐] 处理命令异常: {e}")
                        break
                client_sock.close()
                with open(log_file, 'a', encoding='utf-8') as logf:
                    logf.write(f"POP3 session end: {datetime.now()}\n")

            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(('0.0.0.0', pop3_port))
            server_sock.listen(50)
            print(f"POP3蜜罐服务启动在端口 {pop3_port}")
            while True:
                try:
                    client_sock, client_addr = server_sock.accept()
                    print(f"[POP3蜜罐] 接受连接: {client_addr}")
                    t = threading.Thread(target=handle_pop3_client, args=(client_sock, client_addr))
                    t.daemon = True
                    t.start()
                except Exception as e:
                    print(f"[POP3蜜罐] 主循环异常: {e}")
                    continue

        threading.Thread(target=start_pop3, daemon=True).start()

        import time
        # 启动MySQL服务器（新线程，传递mysql_identity和参数）Add commentMore actions
        def start_mysql():
            import uuid
            import threading
            from datetime import datetime
            import socket
            import struct
            import time
            logs_dir = os.path.join(os.path.dirname(__file__), "..", "Log Manager", "logs")
            os.makedirs(logs_dir, exist_ok=True)
            mysql_port = int(mysql_identity.get('port', 3309))

            def handle_mysql_client(client_sock, client_addr):
                session_uuid = str(uuid.uuid4())
                session_start_time = datetime.now()
                timestamp = session_start_time.strftime("%Y-%m-%d_%H-%M-%S")
                log_file = os.path.join(logs_dir, f"logMySQL_{session_uuid}_{timestamp}.txt")
                history_file = os.path.join(logs_dir, f"historyMySQL_{session_uuid}_{timestamp}.txt")
                try:
                    with open(log_file, 'a', encoding='utf-8') as logf:
                        logf.write(
                            f"MySQL session start: {session_start_time} from {client_addr[0]}:{client_addr[1]}\n")
                    with open(history_file, 'a', encoding='utf-8') as histf:
                        histf.write(f"Session started at: {session_start_time}\n")
                except Exception as e:
                    print(f"[MySQL蜜罐] 日志文件创建失败: {e}")

                messages = [
                    {"role": "system", "content": mysql_identity['prompt'] + mysql_identity.get('final_instr', '')}
                ]

                try:
                    # 使用MySQL 5.7协议版本
                    protocol_version = 10
                    server_version = "5.7.42"  # 兼容版本
                    connection_id = 12345

                    # 能力标志（明确不支持SSL）
                    capability_flags = (
                            0x00000200 |  # CLIENT_PROTOCOL_41
                            0x00000008 |  # CLIENT_CONNECT_WITH_DB
                            0x00080000  # CLIENT_PLUGIN_AUTH
                    )

                    # 字符集和状态
                    charset = 33  # utf8mb4
                    status_flags = 2  # SERVER_STATUS_AUTOCOMMIT

                    # 构造握手包
                    handshake = bytearray()
                    handshake.append(protocol_version)
                    handshake.extend(server_version.encode() + b'\0')  # 服务器版本以NULL结尾
                    handshake.extend(struct.pack('<I', connection_id))

                    # 生成8字节随机盐值
                    salt = os.urandom(8)
                    handshake.extend(salt)
                    handshake.append(0)  # 填充字节
                    handshake.extend(struct.pack('<H', capability_flags & 0xFFFF))  # 低16位能力标志
                    handshake.append(charset)
                    handshake.extend(struct.pack('<H', status_flags))
                    handshake.extend(struct.pack('<H', (capability_flags >> 16) & 0xFFFF))  # 高16位能力标志
                    handshake.append(21)  # 认证数据长度
                    handshake.extend(b'\0' * 10)  # 保留10字节
                    handshake.extend(os.urandom(13))  # 剩余认证数据
                    handshake.extend(b"mysql_native_password\0")  # 认证插件名称

                    # 添加长度前缀和序列号
                    packet_len = len(handshake)
                    packet_header = struct.pack('<I', packet_len)[:3] + b'\x00'
                    full_packet = packet_header + handshake

                    # 发送握手包
                    client_sock.sendall(full_packet)
                    print(f"[MySQL蜜罐] 已发送握手包至 {client_addr}")

                    # 接收客户端响应
                    header = client_sock.recv(4)
                    if len(header) < 4:
                        raise ConnectionError("客户端响应不完整")

                    # 解析响应长度
                    packet_len = struct.unpack('<I', header[:3] + b'\x00')[0]
                    seq = header[3]

                    # 接收完整响应
                    data = b''
                    while len(data) < packet_len:
                        chunk = client_sock.recv(packet_len - len(data))
                        if not chunk:
                            raise ConnectionError("客户端断开连接")
                        data += chunk

                    print(f"[MySQL蜜罐] 收到客户端认证包，长度: {packet_len}")

                    # 解析客户端能力标志
                    if len(data) >= 4:
                        client_capability = struct.unpack('<I', data[:4])[0]
                        print(f"[MySQL蜜罐] 客户端能力标志: {hex(client_capability)}")

                    # 模拟认证成功 - 发送OK包
                    ok_packet = bytearray()
                    ok_packet.append(0)  # OK包标识
                    ok_packet.extend(b'\x00\x00')  # 影响行数
                    ok_packet.extend(b'\x00\x00')  # 最后插入ID
                    ok_packet.extend(struct.pack('<H', status_flags))  # 状态标志
                    ok_packet.extend(b'\x00\x00')  # 警告数

                    # 添加长度前缀和序列号
                    ok_packet_len = len(ok_packet)
                    full_ok_packet = struct.pack('<I', ok_packet_len)[:3] + struct.pack('B', seq + 1) + ok_packet
                    client_sock.sendall(full_ok_packet)
                    print("[MySQL蜜罐] 已发送认证成功响应")

                    # 发送欢迎消息
                    welcome_msg = "\n".join([
                        "Welcome to the MySQL monitor.  Commands end with ; or \\g.",
                        "Your MySQL connection id is 12345",
                        "Server version: 5.7.42 MySQL Community Server (GPL)",
                        "",
                        "Copyright (c) 2000, 2025, Oracle and/or its affiliates.",
                        "",
                        "Oracle is a registered trademark of Oracle Corporation and/or its",
                        "affiliates. Other names may be trademarks of their respective",
                        "owners.",
                        "",
                        "Type 'help;' or '\\h' for help. Type '\\c' to clear the current input statement.",
                        "",
                        "mysql> "
                    ]).encode('utf-8')

                    # 添加长度前缀和序列号
                    # welcome_packet_len = len(welcome_msg)
                    # welcome_header = struct.pack('<I', welcome_packet_len)+ struct.pack('B', seq + 2)
                    client_sock.send(welcome_msg)
                    print("[MySQL蜜罐] 已发送欢迎消息")

                    current_seq = seq + 3
                    while True:
                        try:
                            # 接收命令包头部 (修复点)
                            header = client_sock.recv(4)
                            if len(header) == 0:  # 客户端主动断开
                                print("[MySQL蜜罐] 客户端主动断开连接")
                                break
                            if len(header) < 4:
                                raise ConnectionError(f"命令包头部不完整，收到{len(header)}字节")

                            # 包长度解析和数据处理（保持原逻辑）
                            packet_len = struct.unpack('<I', header[:3] + b'\x00')[0]
                            seq_num = header[3]

                            data = b''
                            while len(data) < packet_len:
                                chunk = client_sock.recv(packet_len - len(data))
                                if not chunk:  # 接收中途断开
                                    raise ConnectionError("数据接收中客户端断开")
                                data += chunk

                            # 命令解析和处理（保持原逻辑）
                            if data:
                                command_type = data[0]
                                command_content = data[1:].decode('utf-8', errors='ignore').strip()
                            else:
                                command_content = ''

                            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            print(f"[MySQL蜜罐] 收到命令: {command_content}")

                            # 记录命令
                            with open(log_file, 'a', encoding='utf-8') as logf:
                                logf.write(f"[{now}] [CMD] {command_content}\n")
                            with open(history_file, 'a', encoding='utf-8') as histf:
                                histf.write(f"mysql> {command_content}\n")

                            # 处理QUIT命令
                            if command_content.lower() in ("quit", "exit", "\\q"):
                                # 发送再见消息
                                goodbye = "Bye\n".encode('utf-8')
                                goodbye_header = struct.pack('<I', len(goodbye))[:3] + struct.pack('B', current_seq)
                                client_sock.sendall(goodbye_header + goodbye)
                                break

                            # 调用LLM生成响应
                            messages.append({"role": "user", "content": command_content})
                            try:
                                response = openai_client.chat.completions.create(
                                    model=mysql_model,
                                    messages=messages,
                                    temperature=mysql_temp,
                                    max_tokens=mysql_max_tokens
                                )
                                ai_response = response.choices[0].message.content
                            except Exception as e:
                                ai_response = f"ERROR 2006 (HY000): MySQL server has gone away: {str(e)}"

                            # 确保响应以换行符结尾
                            if not ai_response.endswith('\n'):
                                ai_response += '\n'

                            # 添加mysql>提示符
                            ai_response += "mysql> "

                            # 记录响应
                            with open(log_file, 'a', encoding='utf-8') as logf:
                                logf.write(f"[{now}] [RESP] {ai_response}\n")
                            with open(history_file, 'a', encoding='utf-8') as histf:
                                histf.write(f"{ai_response}\n")

                            # 发送响应（添加长度前缀和序列号）
                            response_bytes = ai_response.encode('utf-8')
                            response_header = struct.pack('<I', len(response_bytes))[:3] + struct.pack('B', current_seq)
                            client_sock.sendall(response_header + response_bytes)
                            current_seq += 1

                        except socket.timeout:
                            print("[MySQL蜜罐] 命令接收超时，等待客户端输入...")
                            continue
                        except Exception as e:
                            print(f"[MySQL蜜罐] 命令处理错误: {e}")
                            break

                except ConnectionError as ce:
                    print(f"[MySQL蜜罐] 连接异常: {ce}")
                except Exception as e:
                    print(f"[MySQL蜜罐] 处理错误: {e}")
                finally:
                    client_sock.close()
                    print("[MySQL蜜罐] 客户端连接已关闭")
                    with open(log_file, 'a', encoding='utf-8') as logf:
                        logf.write(f"MySQL session end: {datetime.now()}\n")

            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(('0.0.0.0', mysql_port))
            server_sock.listen(50)
            print(f"MySQL蜜罐服务启动在端口 {mysql_port}")

            while True:
                try:
                    client_sock, client_addr = server_sock.accept()
                    client_sock.settimeout(30.0)  # 设置超时
                    print(f"[MySQL蜜罐] 接受连接: {client_addr}")
                    threading.Thread(
                        target=handle_mysql_client,
                        args=(client_sock, client_addr),
                        daemon=True
                    ).start()
                except Exception as e:
                    print(f"[MySQL蜜罐] 接受连接错误: {e}")

        threading.Thread(target=start_mysql, daemon=True).start()

        # 处理SSH连接
        while True:
            client_socket, addr = ssh_server.accept()
            print(f"接受SSH连接: {addr[0]}:{addr[1]}")
            ssh_thread = threading.Thread(
                target=handle_ssh_connection,
                args=(
                client_socket, openai_client, ssh_identity, ssh_model, ssh_temp, ssh_max_tokens, ssh_output, ssh_log,
                SSH_USER, "honeypot")
            )
            ssh_thread.daemon = True
            ssh_thread.start()
    except Exception as e:
        print(f"服务器错误: {e}")
        raise


if __name__ == "__main__":
    main()