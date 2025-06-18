#!/usr/bin/env python3
"""
调试用SSH客户端
专门用于调试SSH蜜罐的输入输出问题
"""

import paramiko
import time
import sys

def debug_ssh_connection():
    """调试SSH连接"""
    print("=== SSH蜜罐调试客户端 ===")
    
    try:
        # 创建SSH客户端
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print("正在连接到 localhost:5656...")
        client.connect('localhost', 5656, 'root', '123456', timeout=10)
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
        
        # 交互式调试
        print("\n=== 开始交互式调试 ===")
        print("输入命令进行测试，输入 'quit' 退出")
        
        while True:
            # 检查是否有数据可读
            if channel.recv_ready():
                data = channel.recv(4096).decode('utf-8')
                print(f"收到数据: {repr(data)}")
                print(f"数据显示: {data}")
            
            # 获取用户输入
            try:
                user_input = input("> ")
                if user_input.lower() == 'quit':
                    break
                
                print(f"发送命令: {repr(user_input)}")
                channel.send(user_input + '\n')
                
                # 等待响应
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\n收到Ctrl+C，退出")
                break
            except EOFError:
                print("\n收到EOF，退出")
                break
        
        # 关闭连接
        client.close()
        print("✓ SSH连接已关闭")
        
    except Exception as e:
        print(f"✗ SSH连接失败: {e}")
        import traceback
        traceback.print_exc()

def test_single_command():
    """测试单个命令"""
    print("=== 单命令测试 ===")
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print("正在连接...")
        client.connect('localhost', 5656, 'root', '123456', timeout=5)
        print("✓ 连接成功")
        
        channel = client.invoke_shell()
        print("✓ Shell已建立")
        
        # 等待欢迎信息
        time.sleep(1)
        if channel.recv_ready():
            welcome = channel.recv(4096).decode('utf-8')
            print(f"欢迎信息:\n{welcome}")
        
        # 测试单个命令
        test_command = "ls"
        print(f"\n测试命令: {test_command}")
        channel.send(test_command + '\n')
        
        # 等待响应
        time.sleep(2)
        
        # 读取所有可用数据
        all_data = ""
        while channel.recv_ready():
            data = channel.recv(4096).decode('utf-8')
            all_data += data
        
        print(f"完整响应:\n{repr(all_data)}")
        print(f"响应内容:\n{all_data}")
        
        client.close()
        print("✓ 连接已关闭")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "single":
        test_single_command()
    else:
        debug_ssh_connection()
    
    print("\n=== 调试完成 ===") 