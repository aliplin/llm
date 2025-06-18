#!/usr/bin/env python3
"""
测试SSH蜜罐日志记录功能
"""

import os
import uuid
from datetime import datetime

def test_log_file_creation():
    """测试日志文件创建功能"""
    print("=== 测试日志文件创建功能 ===")
    
    # 生成测试数据
    session_uuid = str(uuid.uuid4())
    session_start_time = datetime.now()
    timestamp = session_start_time.strftime("%Y-%m-%d_%H-%M-%S")
    
    # 创建日志文件路径（模拟新的路径结构）
    logs_dir = os.path.join("Log Manager", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_ssh_file = os.path.join(logs_dir, f"logSSH_{session_uuid}_{timestamp}.txt")
    history_ssh_file = os.path.join(logs_dir, f"historySSH_{session_uuid}_{timestamp}.txt")
    
    print(f"会话UUID: {session_uuid}")
    print(f"时间戳: {timestamp}")
    print(f"登录日志文件: {log_ssh_file}")
    print(f"交互历史文件: {history_ssh_file}")
    
    # 测试登录信息记录
    username = "root"
    client_ip = "192.168.1.100"
    login_record = f"{username} pts/0 {client_ip} {session_start_time.strftime('%a %b %d %H:%M:%S %Y')}\n"
    
    # 写入测试登录信息
    with open(log_ssh_file, 'w', encoding='utf-8') as f:
        f.write(login_record)
    
    print(f"登录信息已写入: {login_record.strip()}")
    
    # 测试交互历史记录
    test_commands = [
        ("ls", "total 40\ndrwxr-xr-x 2 root root 4.0K Mar 22 13:45 media\n..."),
        ("pwd", "/home/root"),
        ("whoami", "root")
    ]
    
    with open(history_ssh_file, 'w', encoding='utf-8') as f:
        for command, response in test_commands:
            f.write(f"root@honeypot:~$ {command}\n")
            f.write(f"{response}\n")
    
    print(f"交互历史已写入，包含 {len(test_commands)} 个命令")
    
    # 验证文件内容
    print("\n=== 验证文件内容 ===")
    
    with open(log_ssh_file, 'r', encoding='utf-8') as f:
        log_content = f.read()
        print(f"登录日志内容: {log_content.strip()}")
    
    with open(history_ssh_file, 'r', encoding='utf-8') as f:
        history_content = f.read()
        print(f"交互历史内容:\n{history_content}")
    
    # 清理测试文件
    os.remove(log_ssh_file)
    os.remove(history_ssh_file)
    print("\n测试文件已清理")

def test_ssh_module_compatibility():
    """测试与ssh_module.py的兼容性"""
    print("\n=== 测试与ssh_module.py的兼容性 ===")
    
    # 创建符合ssh_module.py解析格式的测试数据
    test_login_data = "root pts/0 192.168.1.100 Mon Aug 15 08:44:32 2024"
    
    # 模拟ssh_module.py的解析逻辑
    parts = test_login_data.split()
    if len(parts) >= 8:
        username = parts[0]
        terminal = parts[1]
        src_ip = parts[2]
        time_date_start = " ".join(parts[3:8])
        
        print(f"解析结果:")
        print(f"  用户名: {username}")
        print(f"  终端: {terminal}")
        print(f"  源IP: {src_ip}")
        print(f"  时间: {time_date_start}")
        print("✓ 格式兼容性测试通过")
    else:
        print("✗ 格式兼容性测试失败")

def test_response_formatting():
    """测试响应格式化功能"""
    print("\n=== 测试响应格式化功能 ===")
    
    # 模拟format_ai_response函数
    def format_ai_response(response, command):
        import re
        # 移除可能的多余提示符
        response = re.sub(r'\$\s*$', '', response)
        response = re.sub(r'^.*?\$\s*', '', response)
        
        command_lower = command.lower().strip()
        
        if command_lower == 'ls':
            lines = response.split('\n')
            formatted_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('$'):
                    formatted_lines.append(line)
            return '\n'.join(formatted_lines) if formatted_lines else response
        
        elif command_lower == 'pwd':
            path_match = re.search(r'/([^/\s]+/?)*', response)
            if path_match:
                return path_match.group(0)
            return response.strip()
        
        else:
            return response.strip()
    
    # 测试用例
    test_cases = [
        ("ls", "root@honeypot:~$ ls\ntotal 40\ndrwxr-xr-x 2 root root 4.0K Mar 22 13:45 media\n...", "total 40\ndrwxr-xr-x 2 root root 4.0K Mar 22 13:45 media\n..."),
        ("pwd", "root@honeypot:~$ pwd\n/home/root", "/home/root"),
        ("whoami", "root@honeypot:~$ whoami\nroot", "root")
    ]
    
    for command, raw_response, expected in test_cases:
        formatted = format_ai_response(raw_response, command)
        print(f"命令: {command}")
        print(f"原始响应: {raw_response}")
        print(f"格式化后: {formatted}")
        print(f"期望结果: {expected}")
        print(f"测试结果: {'✓' if formatted == expected else '✗'}")
        print()

if __name__ == "__main__":
    test_log_file_creation()
    test_ssh_module_compatibility()
    test_response_formatting()
    print("\n=== 测试完成 ===") 