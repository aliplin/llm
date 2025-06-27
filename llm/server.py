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
import select
import uuid
from paramiko import ServerInterface, Transport
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import struct

from honeypot_ssh import handle_ssh_connection, SSH_USER,SSH_PASS,SSH_PORT
from honeypot_http import start_http_server,HTTP_PORT
from honeypot_pop3 import start_pop3
from honeypot_mysql import start_mysql

# 设置 Kimi API 的基础 URL
OpenAI.api_base = "https://api.moonshot.cn/v1"
today = datetime.now()

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

def main():
    try:
        env_path = '.env'
        with open(os.path.join(os.path.dirname(__file__), 'configSSH.yml'), 'r', encoding='utf-8') as f:
            ssh_identity = yaml.safe_load(f)['personality']
        with open(os.path.join(os.path.dirname(__file__), 'configHTTP.yml'), 'r', encoding='utf-8') as f:
            http_identity = yaml.safe_load(f)['personality']
        with open(os.path.join(os.path.dirname(__file__), 'configPOP3.yml'), 'r', encoding='utf-8') as f:
            pop3_identity = yaml.safe_load(f)['personality']
        with open(os.path.join(os.path.dirname(__file__), 'configMySQL.yml'), 'r', encoding='utf-8') as f:
            mysql_identity = yaml.safe_load(f)['personality']
        openai_client = set_key(env_path)
        ssh_model, ssh_temp, ssh_max_tokens, ssh_output, ssh_log = set_parameters(
            ssh_identity, None, None, None, None, None)
        http_model, http_temp, http_max_tokens, http_output, http_log = set_parameters(
            http_identity, None, None, None, None, None)
        pop3_model, pop3_temp, pop3_max_tokens, pop3_output, pop3_log = set_parameters(
            pop3_identity, None, None, None, None, None)
        mysql_model, mysql_temp, mysql_max_tokens, mysql_output, mysql_log = set_parameters(
            mysql_identity, None, None, None, None, None)
        # 启动HTTP服务
        http_thread = threading.Thread(
            target=start_http_server,
            args=(openai_client, http_identity, http_model, http_temp, http_max_tokens, http_output, http_log)
        )
        http_thread.daemon = True
        http_thread.start()
        # 启动POP3服务
        threading.Thread(target=start_pop3, args=(openai_client, pop3_identity, pop3_model, pop3_temp, pop3_max_tokens), daemon=True).start()
        # 启动MySQL服务
        threading.Thread(target=start_mysql, args=(openai_client, mysql_identity, mysql_model, mysql_temp, mysql_max_tokens), daemon=True).start()
        # 启动SSH服务
        ssh_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssh_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ssh_server.bind(('0.0.0.0', SSH_PORT))
        ssh_server.listen(100)
        print(f"SSH服务器启动在端口 {SSH_PORT}")
        while True:
            client_socket, addr = ssh_server.accept()
            print(f"接受SSH连接: {addr[0]}:{addr[1]}")
            ssh_thread = threading.Thread(
                target=handle_ssh_connection,
                args=(client_socket, openai_client, ssh_identity, ssh_model, ssh_temp, ssh_max_tokens, ssh_output, ssh_log, SSH_USER, "honeypot")
            )
            ssh_thread.daemon = True
            ssh_thread.start()
    except Exception as e:
        print(f"服务器错误: {e}")
        raise


if __name__ == "__main__":
    main()