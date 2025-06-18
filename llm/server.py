import argparse
import os
import random
import re
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
from paramiko import ServerInterface, Transport

# 设置 Kimi API 的基础 URL
OpenAI.api_base = "https://api.moonshot.cn/v1"
today = datetime.now()

# SSH服务配置
SSH_PORT = 5656
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

    def check_auth_password(self, username, password):
        # 记录登录尝试
        with open(self.log_file, 'a') as f:
            f.write(f"[{datetime.now()}] 登录尝试 - 用户: {username}, 密码: {password}\n")
        # 验证用户名密码
        if username == SSH_USER and password == SSH_PASS:
            print(f"[SSH蜜罐] {username} 登录成功")
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
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
        # 创建新线程处理Shell会话
        threading.Thread(target=self.handle_shell, daemon=True).start()
        return True

    def get_allowed_auths(self, username):
        return 'password'

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
        welcome_msg = f"Last login: {today.strftime('%Y-%m-%d %H:%M:%S')} from {self.channel.getpeername()[0]}\n"
        welcome_msg += "Welcome to Ubuntu 20.04 LTS (GNU/Linux 5.4.0-100-generic x86_64)\n"
        self.channel.send(welcome_msg)
        if self.debug: print("[SSH蜜罐] 欢迎信息已发送")

        # 命令交互循环
        while self.running and self.channel is not None and self.channel.active:
            # 构建命令提示符
            display_dir = current_dir
            if current_dir.startswith(f"/home/{self.username}"):
                display_dir = "~" + current_dir[len(f"/home/{self.username}"):]
            prompt = f"{self.username}@{self.hostname}:{display_dir}$ "
            self.channel.send(prompt)
            if self.debug: print(f"[SSH蜜罐] 已发送提示符: {prompt}")

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
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                ai_response = response.choices[0].message.content
                # 移除可能包含的多余提示符
                ai_response = re.sub(r'\$\s*$', '', ai_response)
                self.channel.send(ai_response)
                messages.append({"role": "assistant", "content": ai_response})
                if self.debug: print(f"[SSH蜜罐] LLM响应已发送，长度: {len(ai_response)}")

                # 记录输出
                with open(self.output_dir, "a", encoding="utf-8") as f:
                    f.write(f"用户: {command}\n")
                    f.write(f"系统: {ai_response}\n")

            except Exception as e:
                error_msg = f"[错误]: {e}\n"
                self.channel.send(error_msg)
                print(error_msg)
                self.running = False
                break

        # 关闭连接
        if self.channel is not None:
            self.channel.close()
        print(f"[SSH蜜罐] 连接已关闭")

    def read_until_newline(self):
        """使用select监听数据，兼容多种换行符格式"""
        buffer = self.input_buffer
        self.input_buffer = ""  # 重用现有缓冲区

        while self.running and self.channel is not None and self.channel.active:
            # 使用select监听通道可读事件
            try:
                readable, _, _ = select.select([self.channel], [], [], 1.0)  # 1秒超时
                if not readable:
                    if self.debug: print("[SSH蜜罐] 读取超时，继续循环")
                    continue  # 超时继续循环

                data = self.channel.recv(1024)
                if not data:
                    if self.debug: print("[SSH蜜罐] 收到空数据，连接可能已关闭")
                    break

                received = data.decode('utf-8', errors='ignore')
                buffer += received
                if self.debug: print(f"[SSH蜜罐] 接收到数据: {received!r}，当前缓冲区: {buffer!r}")

                # 检查多种换行符格式
                if '\n' in buffer:
                    # 处理 Unix 换行符 \n
                    command, self.input_buffer = buffer.split('\n', 1)
                    if self.debug: print(f"[SSH蜜罐] 解析到命令(Unix): {command!r}，剩余缓冲区: {self.input_buffer!r}")
                    return command.strip()
                elif '\r\n' in buffer:
                    # 处理 Windows 换行符 \r\n
                    command, self.input_buffer = buffer.split('\r\n', 1)
                    if self.debug: print(
                        f"[SSH蜜罐] 解析到命令(Windows): {command!r}，剩余缓冲区: {self.input_buffer!r}")
                    return command.strip()
                elif '\r' in buffer:
                    # 处理旧 Mac 换行符 \r
                    command, self.input_buffer = buffer.split('\r', 1)
                    if self.debug: print(f"[SSH蜜罐] 解析到命令(Mac): {command!r}，剩余缓冲区: {self.input_buffer!r}")
                    return command.strip()

            except Exception as e:
                print(f"[SSH蜜罐] 读取错误: {e}")
                break

        # 保存未解析的缓冲区
        self.input_buffer = buffer
        if self.debug and buffer:
            print(f"[SSH蜜罐] 返回剩余缓冲区命令: {buffer!r}")
        return buffer.strip()


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
        transport.start_server(server=server)

        # 等待连接关闭
        transport.join()

    except Exception as e:
        error_msg = f"[SSH蜜罐错误]: {e}\n"
        print(error_msg)
        if 'transport' in locals():
            transport.close()


def main():
    try:
        # 读取命令行参数
        config_path, env_path, model_name, temperature, max_tokens, output_dir, log_file = read_arguments()

        # 设置API密钥
        openai_client = set_key(env_path)

        # 读取配置文件
        with open(config_path, 'r', encoding="utf-8") as file:
            identity = yaml.safe_load(file)
        identity = identity['personality']

        # 设置输出目录和日志文件
        if not output_dir:
            output_dir = identity['output'].strip()
        reset_prompt = identity['reset_prompt']
        final_instruction = identity['final_instr']
        protocol = identity['type'].strip()
        if not log_file:
            log_file = identity['log'].strip()

        # 从配置文件获取username和hostname，设置默认值
        username = identity.get('username', 'root')
        hostname = identity.get('hostname', 'honeypot')

        # 读取历史记录
        prompt = read_history(identity, output_dir, reset_prompt)

        # 设置模型参数
        model_name, temperature, max_tokens, output_dir, log_file = set_parameters(
            identity, model_name, temperature, max_tokens, output_dir, log_file
        )

        # 初始化SSH服务器 socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', SSH_PORT))
        server.listen(5)
        print(f"[SSH蜜罐] 正在监听端口 {SSH_PORT}...")

        # 处理客户端连接
        while True:
            client_socket, addr = server.accept()
            print(f"[SSH蜜罐] 接收到来自 {addr} 的连接")
            # 为每个连接创建新线程处理
            client_thread = threading.Thread(
                target=handle_ssh_connection,
                args=(client_socket, openai_client, identity, model_name, temperature,
                      max_tokens, output_dir, log_file, username, hostname)
            )
            client_thread.daemon = True
            client_thread.start()

    except Exception as e:
        print(f"程序初始化失败: {e}")
        if 'server' in locals():
            server.close()
        return


if __name__ == '__main__':
    main()