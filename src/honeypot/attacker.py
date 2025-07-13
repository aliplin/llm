import socket

from dotenv import dotenv_values
import argparse
from datetime import datetime
import yaml
from time import sleep
import random
import os
import tiktoken
from openai import OpenAI
from pathlib import Path

# 设置 Kimi API 的基础 URL
OpenAI.api_base = "https://api.moonshot.cn/v1"

today = datetime.now()

# 创建 socket 客户端连接
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 54320))


def read_arguments():
    parser = argparse.ArgumentParser(description='LLM-based honeypot client')

    # Mandatory arguments
    parser.add_argument('-e', '--env', required=True, help='Path to environment file (.env)')
    parser.add_argument('-c', '--config', required=True, help='Path to config file (yaml)')

    # Optional arguments
    parser.add_argument('-m', '--model', help='Model name')
    parser.add_argument('-t', '--temperature', type=float, help='Temperature')
    parser.add_argument('-mt', '--max_tokens', type=int, help='Max tokens')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('-l', '--log', help='Log file')

    args = parser.parse_args()

    return args.config, args.env, args.model, args.temperature, args.max_tokens, args.output, args.log


def set_key(env_path):
    env = dotenv_values(env_path)
    if "KIMI_API_KEY" not in env:
        raise ValueError("未找到 KIMI_API_KEY 环境变量")

    return OpenAI(
        api_key=env["KIMI_API_KEY"],
        base_url="https://api.moonshot.cn/v1",
        timeout=60  # 设置超时时间为 60 秒
    )


def read_history(identity, output_dir, reset_prompt):
    """读取历史记录或初始化新会话"""
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_path = logs_dir / os.path.basename(output_dir)
    history = open(log_path, "a+", encoding="utf-8")
    history.seek(0)
    content = history.read()

    # 计算历史记录的 token 数量
    TOKEN_COUNT = 0
    if content:
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        TOKEN_COUNT = len(encoding.encode(content))

    # 如果历史记录为空或超过 token 限制，重置会话
    if TOKEN_COUNT > 15100 or not content:
        prompt = identity['prompt']
        history.truncate(0)
        history.write(prompt)
    else:
        prompt = content

    history.close()
    return prompt


def setParameters(identity, model_name, model_temperature, model_max_tokens, output_dir, log_file):
    """设置和验证参数"""
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    if model_name is None:
        model_name = identity.get('model', '').strip()
        if not model_name:
            raise ValueError("配置文件中缺少 model 参数")

    if model_max_tokens is None:
        max_tokens_value = identity.get('max_tokens')
        if max_tokens_value is None:
            raise ValueError("配置文件中缺少 max_tokens 参数")
        try:
            model_max_tokens = int(max_tokens_value)
        except (ValueError, TypeError):
            raise ValueError(f"max_tokens 参数格式错误: {max_tokens_value}")

    if model_temperature is None:
        temperature_value = identity.get('temperature')
        if temperature_value is None:
            raise ValueError("配置文件中缺少 temperature 参数")
        try:
            model_temperature = float(temperature_value)
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
    log_file = str(logs_dir / os.path.basename(log_file))

    return model_name, model_temperature, model_max_tokens, output_dir, log_file


def ping(message, messages, logs):
    """处理 SSH PING 命令的特殊逻辑"""
    lines = message["content"].split("\n")
    print(lines[0])

    for i in range(1, len(lines) - 5):
        print(lines[i])
        sleep(random.uniform(0.1, 0.5))

    for i in range(len(lines) - 4, len(lines) - 1):
        print(lines[i])

    # 获取用户输入并记录到日志
    user_input = input(f'{lines[len(lines) - 1]}'.strip() + " ")
    messages.append({"role": "user", "content": user_input + f"\t<{datetime.now()}>\n"})
    logs.write(" " + user_input + f"\t<{datetime.now()}>\n")
    return user_input


def getUserInput(messages, logs):
    """获取标准用户输入"""
    user_input = input(f'\n{messages[len(messages) - 1]["content"]}'.strip() + " ")
    messages.append({"role": "user", "content": " " + user_input + f"\t<{datetime.now()}>\n"})
    logs.write(" " + user_input + f"\t<{datetime.now()}>\n")
    return user_input


def getHTTPCommands(message, messages, logs):
    """处理 HTTP 协议命令"""
    command = 0
    user_input = ""

    while True:
        if message["content"] != '':
            user_input = input(f'\n{messages[len(messages) - 1]["content"]}'.strip() + "\n\n")
            messages.append({"role": "user", "content": " " + user_input + f"\n"})
            logs.write(" " + user_input + f"\t<{datetime.now()}>\n")
            message["content"] = ''
            if user_input != "":
                command = 1
        else:
            user_input = input("")
            messages.append({"role": "user", "content": " " + user_input + f"\n"})
            logs.write(" " + user_input + f"\t<{datetime.now()}>\n")

            if user_input != "":
                command = 1
            elif user_input == "" and command == 1:
                break

    return user_input


def rec():
    """接收并打印 socket 响应"""
    try:
        response = client.recv(16384)
        output = response.decode()
        if output:
            print(output)
        return output
    except Exception as e:
        print(f"接收响应出错: {e}")
        return ""


def main():
    try:
        # 读取命令行参数
        config_path, env_path, model_name, model_temperature, model_max_tokens, output_dir, log_file = read_arguments()

        # 初始化 Kimi API 客户端
        client_api = set_key(env_path)

        # 读取配置文件
        with open(config_path, 'r', encoding="utf-8") as file:
            identity = yaml.safe_load(file)

        identity = identity['personality']
        if not output_dir:
            output_dir = identity['output'].strip()
        reset_prompt = identity['reset_prompt']
        final_instruction = identity['final_instr']
        protocol = identity['type'].strip()
        log_file = identity['log'].strip()

        # 设置并验证参数
        model_name, model_temperature, model_max_tokens, output_dir, log_file = setParameters(
            identity, model_name, model_temperature, model_max_tokens, output_dir, log_file
        )

        # 读取历史记录或初始化新会话
        prompt = read_history(identity, output_dir, reset_prompt)

        # 构建初始提示
        personality = prompt + final_instruction + f"\nFor the last login date use {today}\n"
        initial_prompt = f"Your personality is: {personality}"
        messages = [{"role": "system", "content": initial_prompt}]

        # 接收初始响应
        output = rec()
        if output:
            messages.append({"role": "user", "content": output})

        # 初始化历史文件
        logs_dir = Path(__file__).parent.parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        log_path = logs_dir / os.path.basename(output_dir)
        history = open(log_path, "a+", encoding="utf-8")
        if os.stat(log_path).st_size == 0:
            for msg in messages:
                history.write(msg["content"] + "\n")
        else:
            history.write("The session continues in following lines.\n\n")
        history.close()

        # 主循环
        run = 1
        while run == 1:
            logs_dir = Path(__file__).parent.parent.parent / "logs"
            logs_dir.mkdir(exist_ok=True)
            log_path = logs_dir / os.path.basename(output_dir)
            logs = open(log_path, "a+", encoding="utf-8")

            try:
                # 调用 Kimi API 生成响应
                res = client_api.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=model_temperature,
                    max_tokens=model_max_tokens,
                )

                # 处理 API 响应
                msg = res.choices[0].message.content
                message = {"content": msg, "role": 'assistant'}
                print(message["content"])

                # 发送响应到 socket 服务端
                client.send(message["content"].encode())

                # 记录到工作内存和历史文件
                messages.append(message)
                logs.write(message["content"] + "\n")
                logs.close()

                # 检查是否需要终止会话
                last_response = message["content"]
                if "will be reported" in last_response or "logout" in last_response and not "_logout" in last_response:
                    run = 0
                    break

                if protocol == "POP3" and "Connection closed" in last_response:
                    run = 0
                    break

                if protocol == "HTTP" and (
                        "Bad Request" in last_response or "Connection closed by foreign host." in last_response):
                    run = 0
                    break

                # 根据协议类型处理用户输入
                if protocol == "SSH" and "PING" in message["content"]:
                    user_input = ping(message, messages, logs)
                elif protocol == "HTTP":
                    user_input = getHTTPCommands(message, messages, logs)
                else:
                    user_input = getUserInput(messages, logs)
                    if protocol == "MySQL" and ("\q" == user_input or "exit" == user_input):
                        run = 0

            except KeyboardInterrupt:
                # 处理 Ctrl+C 中断
                messages.append({"role": "user", "content": "^C\n"})
                print("")
            except EOFError:
                print("")
                break
            except Exception as e:
                # 记录错误到日志文件
                logs_dir = Path(__file__).parent.parent.parent / "logs"
                logs_dir.mkdir(exist_ok=True)
                log_path = logs_dir / os.path.basename(log_file)
                logfile = open(log_path, "a+", encoding="utf-8")
                logfile.write(f"\n{datetime.now()}\nError generating response: {str(e)}\n")
                logfile.close()
                print(f"发生错误: {e}")
                break
            finally:
                logs.close()

    except Exception as e:
        print(f"程序初始化失败: {e}")
        return
    finally:
        # 关闭 socket 连接
        client.close()


if __name__ == '__main__':
    main()