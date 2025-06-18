#!/usr/bin/env python3
"""
简化的SSH测试客户端
用于调试SSH蜜罐的输入输出问题
"""

import socket
import time

def test_simple_ssh():
    """简单的SSH连接测试"""
    print("=== 简单SSH测试 ===")
    
    try:
        # 创建socket连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 5656))
        print("✓ Socket连接成功")
        
        # 发送SSH协议版本
        ssh_version = "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5\r\n"
        sock.send(ssh_version.encode())
        print(f"发送SSH版本: {ssh_version.strip()}")
        
        # 接收服务器响应
        time.sleep(0.1)
        if sock.recv(1024):
            print("收到服务器响应")
        
        # 发送一些测试数据
        test_data = b"ls\n"
        sock.send(test_data)
        print(f"发送测试数据: {test_data}")
        
        # 等待响应
        time.sleep(1)
        response = sock.recv(4096)
        if response:
            print(f"收到响应: {response}")
        else:
            print("没有收到响应")
        
        sock.close()
        print("✓ 连接已关闭")
        
    except Exception as e:
        print(f"✗ 连接失败: {e}")

def test_paramiko_simple():
    """使用paramiko的简单测试"""
    print("\n=== Paramiko简单测试 ===")
    
    try:
        import paramiko
        
        # 创建SSH客户端
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print("正在连接...")
        client.connect('localhost', 5656, 'root', '123456', timeout=5)
        print("✓ 连接成功")
        
        # 获取shell
        channel = client.invoke_shell()
        print("✓ Shell已建立")
        
        # 等待欢迎信息
        time.sleep(1)
        
        # 读取欢迎信息
        if channel.recv_ready():
            welcome = channel.recv(4096).decode('utf-8')
            print(f"欢迎信息:\n{welcome}")
        
        # 发送单个命令
        print("\n发送命令: ls")
        channel.send('ls\n')
        
        # 等待响应
        time.sleep(2)
        
        # 读取响应
        if channel.recv_ready():
            response = channel.recv(4096).decode('utf-8')
            print(f"响应:\n{repr(response)}")
        else:
            print("没有响应")
        
        # 关闭连接
        client.close()
        print("✓ 连接已关闭")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    test_simple_ssh()
    test_paramiko_simple()
    print("\n=== 测试完成 ===") 