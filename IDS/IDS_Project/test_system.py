#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDS系统功能测试脚本
"""

import os
import sys
import time
import requests
import json
from pathlib import Path

def test_kimi_api():
    """测试Kimi API连接"""
    print("🧪 测试Kimi API连接...")
    
    try:
        from ids_llm import call_kimi_api
        
        # 测试简单的API调用
        messages = [{"role": "user", "content": "Hello, this is a test message."}]
        response = call_kimi_api(messages)
        
        if response and 'choices' in response:
            print("✅ Kimi API连接成功")
            return True
        else:
            print("❌ Kimi API连接失败")
            return False
            
    except Exception as e:
        print(f"❌ Kimi API测试出错: {e}")
        return False

def test_token_monitor():
    """测试Token监控功能"""
    print("🧪 测试Token监控功能...")
    
    try:
        from ids_llm import token_monitor
        
        # 获取初始状态
        initial_status = token_monitor.get_token_status()
        print(f"   初始状态: {initial_status}")
        
        # 模拟添加tokens
        token_monitor.add_tokens(1000)
        updated_status = token_monitor.get_token_status()
        print(f"   添加1000 tokens后: {updated_status}")
        
        # 检查是否正常工作
        if updated_status['daily_tokens_used'] == initial_status['daily_tokens_used'] + 1000:
            print("✅ Token监控功能正常")
            return True
        else:
            print("❌ Token监控功能异常")
            return False
            
    except Exception as e:
        print(f"❌ Token监控测试出错: {e}")
        return False

def test_flask_app():
    """测试Flask应用"""
    print("🧪 测试Flask应用...")
    
    try:
        # 检查Flask应用是否可以导入
        from app import app
        
        # 创建测试客户端
        with app.test_client() as client:
            # 测试登录页面
            response = client.get('/login')
            if response.status_code == 200:
                print("✅ Flask应用启动正常")
                return True
            else:
                print(f"❌ Flask应用响应异常: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Flask应用测试出错: {e}")
        return False

def test_database():
    """测试数据库连接"""
    print("🧪 测试数据库连接...")
    
    try:
        import sqlite3
        
        # 检查数据库文件是否存在
        db_path = Path('ids.db')
        if not db_path.exists():
            print("⚠️  数据库文件不存在，将创建新数据库")
        
        # 测试数据库连接
        conn = sqlite3.connect('ids.db')
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"   数据库表: {[table[0] for table in tables]}")
        
        conn.close()
        print("✅ 数据库连接正常")
        return True
        
    except Exception as e:
        print(f"❌ 数据库测试出错: {e}")
        return False

def test_network_interface():
    """测试网络接口"""
    print("🧪 测试网络接口...")
    
    try:
        import netifaces
        from ids_llm import get_interface_ip
        
        # 获取网络接口列表
        interfaces = netifaces.interfaces()
        print(f"   可用网络接口: {interfaces}")
        
        # 测试自动检测功能
        ip, interface_name = get_interface_ip()
        
        if ip and interface_name:
            print(f"   自动检测到接口: {interface_name}, IP: {ip}")
            print("✅ 网络接口配置正常")
            return True
        else:
            print("⚠️  自动检测失败，尝试手动指定接口")
            
            # 尝试找到第一个可用的接口
            for iface in interfaces:
                if not iface.startswith('{') and iface != 'lo':
                    try:
                        ip, interface_name = get_interface_ip(iface)
                        if ip:
                            print(f"   使用接口: {interface_name}, IP: {ip}")
                            print("✅ 网络接口配置正常")
                            return True
                    except:
                        continue
            
            print("❌ 未找到可用的网络接口")
            return False
            
    except Exception as e:
        print(f"❌ 网络接口测试出错: {e}")
        return False

def test_dependencies():
    """测试依赖包"""
    print("🧪 测试依赖包...")
    
    required_packages = [
        'flask', 'flask_login', 'flask_socketio', 'scapy', 'scapy_http', 
        'netifaces', 'requests', 'pytz', 'sqlite3'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'sqlite3':
                import sqlite3
            else:
                __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    else:
        print("✅ 所有依赖包已安装")
        return True

def main():
    """主测试函数"""
    print("=" * 60)
    print("🔒 IDS系统功能测试")
    print("=" * 60)
    
    tests = [
        ("依赖包", test_dependencies),
        ("数据库", test_database),
        ("网络接口", test_network_interface),
        ("Flask应用", test_flask_app),
        ("Token监控", test_token_monitor),
        ("Kimi API", test_kimi_api),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}测试:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:15} {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统可以正常运行。")
        print("\n启动命令:")
        print("  python start_ids.py")
    else:
        print("⚠️  部分测试失败，请检查配置后重试。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 