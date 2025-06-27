#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDS系统启动脚本
同时启动Flask Web界面和LLM分析程序
"""

import os
import sys
import time
import threading
import subprocess
from pathlib import Path

def check_dependencies():
    """检查必要的依赖是否已安装"""
    required_packages = [
        'flask', 'flask_login', 'flask_socketio', 'scapy', 'scapy_http', 
        'netifaces', 'requests', 'pytz'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("✅ 所有依赖包已安装")
    return True

def check_permissions():
    """检查是否有足够的权限运行网络监听"""
    try:
        # 尝试创建一个测试socket
        import socket
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        test_socket.close()
        print("✅ 网络权限检查通过")
        return True
    except PermissionError:
        print("❌ 需要管理员权限来监听网络流量")
        print("请使用 sudo python start_ids.py 运行")
        return False
    except Exception as e:
        print(f"⚠️  网络权限检查警告: {e}")
        return True

def start_flask_app():
    """启动Flask Web应用"""
    try:
        print("🚀 启动Flask Web应用...")
        # 切换到IDS项目目录
        os.chdir(Path(__file__).parent)
        
        # 启动Flask应用
        from app import app, socketio
        socketio.run(app, debug=False, port=5001, allow_unsafe_werkzeug=True, host='0.0.0.0')
    except Exception as e:
        print(f"❌ Flask应用启动失败: {e}")

def start_llm_analysis():
    """启动LLM分析程序"""
    try:
        print("🧠 启动LLM分析程序...")
        # 切换到IDS项目目录
        os.chdir(Path(__file__).parent)
        
        # 导入并运行LLM分析
        import ids_llm
        
        # 这里会启动网络监听和LLM分析
        print("LLM分析程序已启动，开始监听网络流量...")
        
    except Exception as e:
        print(f"❌ LLM分析程序启动失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("🔒 混合分析威胁检测Agent启动器")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查权限
    if not check_permissions():
        sys.exit(1)
    
    print("\n📋 系统信息:")
    print(f"   - 工作目录: {Path(__file__).parent}")
    print(f"   - Python版本: {sys.version}")
    print(f"   - 操作系统: {os.name}")
    
    print("\n🔄 启动服务...")
    
    # 创建线程来运行Flask应用
    flask_thread = threading.Thread(target=start_flask_app, daemon=True)
    flask_thread.start()
    
    # 等待Flask应用启动
    time.sleep(3)
    
    # 启动LLM分析程序（在主线程中运行）
    try:
        start_llm_analysis()
    except KeyboardInterrupt:
        print("\n\n🛑 收到中断信号，正在关闭系统...")
        print("✅ 系统已安全关闭")
    except Exception as e:
        print(f"\n❌ 系统运行出错: {e}")

if __name__ == "__main__":
    main() 