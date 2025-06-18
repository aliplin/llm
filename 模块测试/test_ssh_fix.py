#!/usr/bin/env python3
"""
测试SSH蜜罐修复
"""

import os
import uuid
from datetime import datetime

def test_log_file_paths():
    """测试日志文件路径创建"""
    print("=== 测试日志文件路径创建 ===")
    
    # 模拟SSH蜜罐的路径创建逻辑
    session_uuid = str(uuid.uuid4())
    session_start_time = datetime.now()
    timestamp = session_start_time.strftime("%Y-%m-%d_%H-%M-%S")
    
    # 创建日志文件路径
    logs_dir = os.path.join("Log Manager", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    log_ssh_file = os.path.join(logs_dir, f"logSSH_{session_uuid}_{timestamp}.txt")
    history_ssh_file = os.path.join(logs_dir, f"historySSH_{session_uuid}_{timestamp}.txt")
    
    print(f"日志目录: {logs_dir}")
    print(f"登录日志文件: {log_ssh_file}")
    print(f"交互历史文件: {history_ssh_file}")
    
    # 测试文件创建
    try:
        # 创建登录日志
        with open(log_ssh_file, 'w', encoding='utf-8') as f:
            f.write(f"root pts/0 192.168.1.100 {session_start_time.strftime('%a %b %d %H:%M:%S %Y')}\n")
        print(f"✓ 登录日志文件创建成功")
        
        # 创建交互历史
        with open(history_ssh_file, 'w', encoding='utf-8') as f:
            f.write("root@honeypot:~$ ls\n")
            f.write("total 40\ndrwxr-xr-x 2 root root 4.0K Mar 22 13:45 media\n")
        print(f"✓ 交互历史文件创建成功")
        
        # 验证文件存在
        if os.path.exists(log_ssh_file):
            print(f"✓ 登录日志文件存在: {os.path.getsize(log_ssh_file)} bytes")
        else:
            print(f"✗ 登录日志文件不存在")
            
        if os.path.exists(history_ssh_file):
            print(f"✓ 交互历史文件存在: {os.path.getsize(history_ssh_file)} bytes")
        else:
            print(f"✗ 交互历史文件不存在")
        
        # 清理测试文件
        os.remove(log_ssh_file)
        os.remove(history_ssh_file)
        print("✓ 测试文件已清理")
        
    except Exception as e:
        print(f"✗ 文件创建失败: {e}")

def test_input_processing():
    """测试输入处理逻辑"""
    print("\n=== 测试输入处理逻辑 ===")
    
    # 模拟字符处理逻辑
    def process_char(char, buffer):
        if char == '\r':
            return buffer, "忽略回车"
        elif char == '\n':
            return buffer, "发送换行并返回命令"
        elif char == '\x7f':  # Backspace
            if buffer:
                return buffer[:-1], "退格"
            return buffer, "退格（缓冲区为空）"
        elif ord(char) >= 32:
            return buffer + char, "添加字符"
        else:
            return buffer, "忽略控制字符"
    
    # 测试用例
    test_cases = [
        ('a', "", "a"),
        ('b', "a", "ab"),
        ('\x7f', "ab", "a"),  # Backspace
        ('\n', "a", "a"),     # Enter
    ]
    
    buffer = ""
    for char, expected_buffer, expected_action in test_cases:
        new_buffer, action = process_char(char, buffer)
        buffer = new_buffer
        print(f"字符: {repr(char)}, 缓冲区: {repr(buffer)}, 动作: {action}")

def test_response_formatting():
    """测试响应格式化"""
    print("\n=== 测试响应格式化功能 ===")
    
    def format_ai_response(response, command):
        import re
        # 移除可能的多余提示符和命令前缀
        response = re.sub(r'\$\s*$', '', response)
        response = re.sub(r'^.*?\$\s*', '', response)  # 移除开头的提示符
        response = re.sub(r'^.*?\$\s*', '', response)  # 再次移除，以防有多层
        
        command_lower = command.lower().strip()
        
        if command_lower == 'ls':
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
        
        else:
            return response.strip()
    
    # 测试用例
    test_cases = [
        ("ls", "root@honeypot:~$ ls\ntotal 40\ndrwxr-xr-x 2 root root 4.0K Mar 22 13:45 media", "total 40\ndrwxr-xr-x 2 root root 4.0K Mar 22 13:45 media"),
        ("pwd", "root@honeypot:~$ pwd\n/home/root", "/home/root"),
        ("whoami", "root@honeypot:~$ whoami\nroot", "root"),
        ("ls", "ls\ntotal 40\ndrwxr-xr-x 2 root root 4.0K Mar 22 13:45 media", "total 40\ndrwxr-xr-x 2 root root 4.0K Mar 22 13:45 media"),
        ("whoami", "whoami\nroot", "root")
    ]
    
    for command, raw_response, expected in test_cases:
        formatted = format_ai_response(raw_response, command)
        print(f"命令: {command}")
        print(f"原始: {repr(raw_response)}")
        print(f"格式化: {repr(formatted)}")
        print(f"期望: {repr(expected)}")
        print(f"结果: {'✓' if formatted == expected else '✗'}")
        print()

if __name__ == "__main__":
    test_log_file_paths()
    test_input_processing()
    test_response_formatting()
    print("\n=== 测试完成 ===") 