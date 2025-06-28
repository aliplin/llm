#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import threading
import time

def test_mysql_connection():
    """测试MySQL连接"""
    try:
        # 连接到MySQL服务器
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 3309))
        print("成功连接到MySQL服务器")
        
        # 接收服务器响应
        data = sock.recv(4096)
        print(f"服务器响应: {data.decode()}")
        
        # 发送测试命令
        test_commands = [
            "SHOW DATABASES;",
            "SELECT VERSION();",
            "SELECT USER();",
            "quit"
        ]
        
        for cmd in test_commands:
            print(f"\n发送命令: {cmd}")
            sock.sendall((cmd + '\n').encode())
            
            # 接收响应
            response = sock.recv(4096)
            print(f"响应: {response.decode()}")
            
            time.sleep(1)
        
        sock.close()
        print("连接已关闭")
        
    except Exception as e:
        print(f"连接失败: {e}")

def interactive_mysql_client():
    """交互式MySQL客户端"""
    try:
        # 连接到MySQL服务器
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 3309))
        print("成功连接到MySQL服务器")
        
        # 接收服务器响应
        data = sock.recv(4096)
        print(f"服务器响应: {data.decode()}")
        
        # 交互式命令输入
        while True:
            try:
                command = input("mysql> ")
                if command.lower() in ['quit', 'exit', '\\q']:
                    break
                
                sock.sendall((command + '\n').encode())
                
                # 接收响应
                response = sock.recv(4096)
                print(response.decode())
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"错误: {e}")
                break
        
        sock.close()
        print("连接已关闭")
        
    except Exception as e:
        print(f"连接失败: {e}")

if __name__ == "__main__":
    print("=== MySQL客户端测试 ===")
    print("1. 自动测试")
    print("2. 交互式测试")
    
    choice = input("请选择测试模式 (1/2): ")
    
    if choice == "1":
        test_mysql_connection()
    elif choice == "2":
        interactive_mysql_client()
    else:
        print("无效选择") 