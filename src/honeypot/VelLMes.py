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

# 设置 Kimi API 的基础 URL
OpenAI.api_base = "https://api.moonshot.cn/v1"

today = datetime.now()


def read_arguments():
    parser = argparse.ArgumentParser(description='Your script description')

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

    # Access the arguments
    config_path = args.config
    env_path = args.env
    model_name = args.model
    temperature = args.temperature
    max_tokens = args.max_tokens
    output_dir = args.output
    log_file = args.log

    return config_path, env_path, model_name, temperature, max_tokens, output_dir, log_file


def set_key(env_path):
    env = dotenv_values(env_path)
    if "KIMI_API_KEY" not in env:
        raise ValueError("未找到 API 密钥")
    # 使用新版 SDK 的 client 初始化
    return OpenAI(
        api_key=env["KIMI_API_KEY"],
        base_url="https://api.moonshot.cn/v1",
        timeout=60  # 设置全局超时
    )


def read_history(identity, output_dir, reset_prompt):
    history = open(output_dir, "a+", encoding="utf-8")
    TOKEN_COUNT = 0

    if os.stat(output_dir).st_size != 0:
        history.write(reset_prompt)
        history.seek(0)
        prompt = history.read()

        # 使用通用编码方案
        encoding = tiktoken.get_encoding("cl100k_base")
        TOKEN_COUNT = len(encoding.encode(prompt))

    if TOKEN_COUNT > 15100 or os.stat(output_dir).st_size == 0:
        prompt = identity['prompt']
        history.truncate(0)

    history.close()
    return prompt


def setParameters(identity, model_name, model_temperature, model_max_tokens, output_dir, log_file):
    # 改进参数设置逻辑，处理不同数据类型并增加错误检查

    if model_name is None:
        model_name = identity.get('model', '').strip()
        if not model_name:
            raise ValueError("配置文件中缺少 model 参数")

    if model_max_tokens is None:
        max_tokens_value = identity.get('max_tokens')
        if max_tokens_value is None:
            raise ValueError("配置文件中缺少 max_tokens 参数")

        # 处理可能是字符串或整数的情况
        try:
            model_max_tokens = int(max_tokens_value) if isinstance(max_tokens_value, str) else max_tokens_value
        except (ValueError, TypeError):
            raise ValueError(f"max_tokens 参数格式错误: {max_tokens_value}")

    if model_temperature is None:
        temperature_value = identity.get('temperature')
        if temperature_value is None:
            raise ValueError("配置文件中缺少 temperature 参数")

        # 处理可能是字符串或浮点数的情况
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


def ping(message, messages, logs, username, hostname):
    # 提取LLM响应内容并去除多余的提示符
    content = message["content"]

    # 移除可能包含的多余提示符
    unwanted_prompt = "charlie@ubuntu:~\\$"
    content = re.sub(unwanted_prompt, '', content)

    lines = content.split("\n")

    # 只打印非空行
    for line in lines:
        if line.strip():
            print(line)
            sleep(random.uniform(0.05, 0.1))  # 减小延迟，提高响应速度

    # 获取当前时间并格式化为所需的字符串格式
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 构建命令提示符
    prompt = f"[{current_time}] {username}@{hostname}:~> "

    # 获取用户输入
    user_input = input(prompt)

    # 将完整的命令行写入日志
    full_command_line = f"{prompt}{user_input}\t<{datetime.now()}>"
    messages.append({"role": "user", "content": full_command_line})
    logs.write(full_command_line + "\n")


def getUserInput(messages, logs, username, hostname):
    # 获取当前时间并格式化为所需的字符串格式
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 构建命令提示符
    prompt = f"[{current_time}] {username}@{hostname}:~> "

    # 打印提示符并获取用户输入
    user_input = input(prompt)

    # 将完整的命令行写入日志
    full_command_line = f"{prompt}{user_input}\t<{datetime.now()}>"
    messages.append({"role": "user", "content": full_command_line})
    logs.write(full_command_line + "\n")

    return user_input


def getHTTPCommands(message, messages, logs):
    command = 0

    # 提取LLM响应内容并去除多余的提示符
    content = message["content"]

    # 移除可能包含的多余提示符
    unwanted_prompt = "charlie@ubuntu:~\\$"
    content = re.sub(unwanted_prompt, '', content)

    # 打印处理后的响应
    if content.strip():
        print(content)

    while True:
        user_input = input()
        messages.append({"role": "user", "content": f" {user_input}\n"})
        logs.write(f" {user_input}\t<{datetime.now()}>\n")

        if user_input != "":
            command = 1
        elif user_input == "" and command == 1:
            break

    return user_input


def main():
    try:
        # 导入正则表达式模块用于处理字符串
        import re

        # 读取命令行参数
        config_path, env_path, model_name, model_temperature, model_max_tokens, output_dir, log_file = read_arguments()

        # 设置API密钥
        client = set_key(env_path)

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
        log_file = identity['log'].strip()

        # 新增：从配置文件获取username和hostname，或设置默认值
        username = identity.get('username', 'root')  # 默认使用root
        hostname = identity.get('hostname', 'honeypot')  # 默认使用honeypot

        # 读取历史记录
        prompt = read_history(identity, output_dir, reset_prompt)

        # 设置模型参数
        model_name, model_temperature, model_max_tokens, output_dir, log_file = setParameters(
            identity, model_name, model_temperature, model_max_tokens, output_dir, log_file
        )

        # 构建包含固定用户名的 system prompt
        login_date = today.strftime("%Y-%m-%d %H:%M:%S")
        personality = prompt + final_instruction + f"\n对于最后登录日期使用 {login_date}\n"
        # 新增：强制注入用户名和主机名到 prompt 中
        fixed_identity = f"User is {username}@{hostname}. "  # 格式：用户名@主机名
        initial_prompt = f"Your personality is: {fixed_identity}{personality}"
        messages = [{"role": "system", "content": initial_prompt}]

        # 写入历史文件
        history = open(output_dir, "a+", encoding="utf-8")
        if os.stat(output_dir).st_size == 0:
            for msg in messages:
                history.write(msg["content"])
        else:
            history.write("The session continues in following lines.\n\n")
        history.close()

        # 主循环
        run = 1
        while run == 1:
            logs = open(output_dir, "a+", encoding="utf-8")
            try:
                # 获取模型响应
                res = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=model_temperature,
                    max_tokens=model_max_tokens,
                )
                msg = res.choices[0].message.content
                message = {"content": msg, "role": 'assistant'}

                # 移除LLM响应中可能包含的多余提示符
                unwanted_prompt = r"charlie@ubuntu:~\$"
                clean_msg = re.sub(unwanted_prompt, '', msg)

                # 打印处理后的响应
                print(clean_msg)

                # 写入工作内存
                messages.append(message)
                last = messages[len(messages) - 1]["content"]

                # 写入历史记录
                logs.write(last)
                logs.close()

                # 重新打开日志文件
                logs = open(output_dir, "a+", encoding="utf-8")

                # 检查退出条件
                if "will be reported" in last or "logout" in last and not "_logout" in last:
                    print(last)
                    run = 0
                    break

                # 协议特定处理
                if protocol == "SSH" and "PING" in message["content"]:
                    ping(message, messages, logs, username, hostname)

                elif protocol == "HTTP":
                    user_input = getHTTPCommands(message, messages, logs)

                else:
                    user_input = getUserInput(messages, logs, username, hostname)

                    # 检查MySQL退出命令
                    if protocol == "MySQL" and ("\q" == user_input or "exit" == user_input):
                        run = 0

            except KeyboardInterrupt:
                # Do not end conversation on ^C. Just print it in the new line and add to working memory.
                messages.append({"role": "user", "content": "^C\n"})
                print("")

            except EOFError:
                print("")
                break

            except Exception as e:
                logfile = open(log_file, "a+", encoding="utf-8")
                logfile.write("\n")
                logfile.write(str(datetime.now()))
                logfile.write("\nError generating response!")
                logfile.write(str(e))
                logfile.close()
                print(f"发生错误: {e}")
                break

            logs.close()

    except Exception as e:
        print(f"程序初始化失败: {e}")
        return


if __name__ == '__main__':
    main()