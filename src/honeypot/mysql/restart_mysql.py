#!/usr/bin/env python3
"""
快速重启MySQL蜜罐脚本
"""

import os
import sys
import subprocess
import time

def main():
    """主函数"""
    print("=" * 50)
    print("MySQL蜜罐快速重启")
    print("=" * 50)
    
    # 获取API密钥
    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        api_key = input("请输入OpenAI API密钥 (或直接回车跳过): ").strip()
        if not api_key:
            api_key = None
    
    print("\n🛑 请手动停止当前运行的MySQL蜜罐 (Ctrl+C)")
    print("等待3秒后启动新进程...")
    time.sleep(3)
    
    # 启动新进程
    print("\n🚀 启动MySQL蜜罐...")
    
    # 构建命令
    cmd = [sys.executable, 'start_cross_platform_mysql.py']
    if api_key:
        cmd.append(api_key)
    
    try:
        print(f"执行命令: {' '.join(cmd)}")
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n⏹️  用户中断")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 