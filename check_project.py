#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目状态检查脚本
检查项目结构、依赖、配置等
"""

import os
import sys
import importlib
from pathlib import Path

def check_project_structure():
    """检查项目结构"""
    print("=== 检查项目结构 ===")
    
    required_dirs = [
        "src",
        "src/honeypot", 
        "src/ids",
        "src/log_manager",
        "src/utils",
        "src/tests",
        "config",
        "docs",
        "logs",
        "data"
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)
            print(f"❌ 缺少目录: {dir_path}")
        else:
            print(f"✅ 目录存在: {dir_path}")
    
    if missing_dirs:
        print(f"\n需要创建 {len(missing_dirs)} 个目录")
        for dir_path in missing_dirs:
            os.makedirs(dir_path, exist_ok=True)
            print(f"✅ 已创建: {dir_path}")
    
    return len(missing_dirs) == 0

def check_required_files():
    """检查必需文件"""
    print("\n=== 检查必需文件 ===")
    
    required_files = [
        "requirements.txt",
        "README.md",
        "start_all.py",
        "start_honeypot.py", 
        "start_ids.py",
        "start_log_manager.py",
        "config/project_config.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
            print(f"❌ 缺少文件: {file_path}")
        else:
            print(f"✅ 文件存在: {file_path}")
    
    return len(missing_files) == 0

def check_dependencies():
    """检查Python依赖"""
    print("\n=== 检查Python依赖 ===")
    
    required_packages = [
        "flask",
        "requests", 
        "yaml",
        "sqlite3",
        "threading",
        "socket",
        "paramiko"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ 依赖已安装: {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ 缺少依赖: {package}")
    
    if missing_packages:
        print(f"\n需要安装 {len(missing_packages)} 个依赖包")
        print("请运行: pip install -r requirements.txt")
    
    return len(missing_packages) == 0

def check_config_files():
    """检查配置文件"""
    print("\n=== 检查配置文件 ===")
    
    config_files = [
        "config/configSSH.yml",
        "config/configHTTP.yml", 
        "config/configMySQL.yml",
        "config/configPOP3.yml",
        "config/host_key"
    ]
    
    missing_configs = []
    for config_file in config_files:
        if not os.path.exists(config_file):
            missing_configs.append(config_file)
            print(f"❌ 缺少配置: {config_file}")
        else:
            print(f"✅ 配置存在: {config_file}")
    
    return len(missing_configs) == 0

def check_ports():
    """检查端口占用"""
    print("\n=== 检查端口占用 ===")
    
    import socket
    
    ports_to_check = [5000, 5001, 5656, 8080]
    
    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            print(f"⚠️  端口 {port} 已被占用")
        else:
            print(f"✅ 端口 {port} 可用")

def main():
    """主函数"""
    print("混合威胁检测与蜜罐系统 - 项目状态检查")
    print("=" * 50)
    
    # 检查项目结构
    structure_ok = check_project_structure()
    
    # 检查必需文件
    files_ok = check_required_files()
    
    # 检查依赖
    deps_ok = check_dependencies()
    
    # 检查配置文件
    config_ok = check_config_files()
    
    # 检查端口
    check_ports()
    
    print("\n" + "=" * 50)
    print("检查结果汇总:")
    print(f"项目结构: {'✅ 正常' if structure_ok else '❌ 需要修复'}")
    print(f"必需文件: {'✅ 正常' if files_ok else '❌ 需要修复'}")
    print(f"Python依赖: {'✅ 正常' if deps_ok else '❌ 需要安装'}")
    print(f"配置文件: {'✅ 正常' if config_ok else '❌ 需要修复'}")
    
    if all([structure_ok, files_ok, deps_ok, config_ok]):
        print("\n🎉 项目状态正常，可以启动服务！")
        print("运行 'python start_all.py' 启动所有服务")
    else:
        print("\n⚠️  项目存在问题，请先修复上述问题")

if __name__ == "__main__":
    main() 