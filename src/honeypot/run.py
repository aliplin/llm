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
from pathlib import Path

from .ssh.honeypot_ssh import handle_ssh_connection, SSH_USER,SSH_PASS,SSH_PORT
from .http.honeypot_http import start_http_server,HTTP_PORT
from .pop3.honeypot_pop3 import start_pop3
from .mysql.honeypot_mysql import start_mysql

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



def main():
    try:
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent
        env_path = project_root / "config" / ".env"
        # 读取配置文件
        with open(project_root / "config" / "configSSH.yml", 'r', encoding='utf-8') as f:
            ssh_identity = yaml.safe_load(f)['personality']
        with open(project_root / "config" / "configHTTP.yml", 'r', encoding='utf-8') as f:
            http_identity = yaml.safe_load(f)['personality']
        with open(project_root / "config" / "configPOP3.yml", 'r', encoding='utf-8') as f:
            pop3_identity = yaml.safe_load(f)['personality']
        with open(project_root / "config" / "configMySQL.yml", 'r', encoding='utf-8') as f:
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