#!/usr/bin/env python3
"""
简单的SSH客户端测试脚本
用于测试SSH蜜罐的功能
"""

import paramiko
import time

def test_ssh_connection():
    """测试SSH连接"""
    print("=== SSH客户端测试 ===")
    
    # SSH连接参数
    hostname = 'localhost'
    port = 5656
    username = 'root'
    password = '123456'
    
    try:
        # 创建SSH客户端
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"正在连接到 {hostname}:{port}...")
        
        # 连接到SSH服务器
        client.connect(hostname, port, username, password, timeout=10)
        print("✓ SSH连接成功")
        
        # 获取shell通道
        channel = client.invoke_shell()
        print("✓ Shell通道已建立")
        
        # 等待欢迎信息
        time.sleep(1)
        
        # 读取欢迎信息
        if channel.recv_ready():
            welcome = channel.recv(4096).decode('utf-8')
            print(f"欢迎信息:\n{welcome}")
        
        # 测试命令
        test_commands = ['ls', 'pwd', 'whoami', 'echo "Hello World"']
        
        for command in test_commands:
            print(f"\n--- 测试命令: {command} ---")
            
            # 发送命令
            channel.send(command + '\n')
            time.sleep(0.5)
            
            # 读取响应
            if channel.recv_ready():
                response = channel.recv(4096).decode('utf-8')
                print(f"响应:\n{response}")
            else:
                print("没有收到响应")
        
        # 发送退出命令
        print("\n--- 退出 ---")
        channel.send('exit\n')
        time.sleep(0.5)
        
        # 关闭连接
        client.close()
        print("✓ SSH连接已关闭")
        
    except Exception as e:
        print(f"✗ SSH连接失败: {e}")

def test_ssh_interactive():
    """测试交互式SSH会话"""
    print("\n=== 交互式SSH测试 ===")
    
    # SSH连接参数
    hostname = 'localhost'
    port = 5656
    username = 'root'
    password = '123456'
    
    try:
        # 创建SSH客户端
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"正在连接到 {hostname}:{port}...")
        
        # 连接到SSH服务器
        client.connect(hostname, port, username, password, timeout=10)
        print("✓ SSH连接成功")
        
        # 获取shell通道
        channel = client.invoke_shell()
        print("✓ Shell通道已建立")
        
        # 等待欢迎信息
        time.sleep(1)
        
        # 读取欢迎信息
        if channel.recv_ready():
            welcome = channel.recv(4096).decode('utf-8')
            print(f"欢迎信息:\n{welcome}")
        
        # 交互式测试
        print("\n开始交互式测试...")
        print("输入 'quit' 退出")
        
        while True:
            # 检查是否有数据可读
            if channel.recv_ready():
                data = channel.recv(4096).decode('utf-8')
                print(data, end='')
            
            # 检查是否有输入
            import select
            import sys
            
            if select.select([sys.stdin], [], [], 0.1)[0]:
                user_input = input()
                if user_input.lower() == 'quit':
                    break
                channel.send(user_input + '\n')
        
        # 关闭连接
        client.close()
        print("✓ SSH连接已关闭")
        
    except Exception as e:
        print(f"✗ SSH连接失败: {e}")

if __name__ == "__main__":
    # 运行测试
    test_ssh_connection()
    
    # 询问是否进行交互式测试
    response = input("\n是否进行交互式测试? (y/n): ")
    if response.lower() == 'y':
        test_ssh_interactive()
    
    print("\n=== 测试完成 ===") 