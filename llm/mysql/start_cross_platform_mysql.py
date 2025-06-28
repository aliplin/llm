#!/usr/bin/env python3
"""
跨平台MySQL蜜罐启动脚本
支持Linux和Windows客户端连接
包含文件反制功能和可选的LLM响应
"""

import sys
import os
import socket
import yaml

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cross_platform_mysql import CrossPlatformMySQLHoneypot
import asyncio

def load_config(config_file=None):
    """加载配置文件"""
    if config_file is None:
        config_file = 'configMySQL.yml'
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 提取API密钥和personality配置
        api_key = config.get('api_key', '')
        personality = config.get('personality', {})
        
        return {
            'api_key': api_key,
            'personality': personality
        }
    except FileNotFoundError:
        print(f"⚠️  配置文件 {config_file} 未找到，使用默认配置")
        return {'api_key': '', 'personality': {}}
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return {'api_key': '', 'personality': {}}

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='跨平台MySQL蜜罐服务器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本启动（模拟响应）
  python start_cross_platform_mysql.py
  
  # 启用LLM响应
  python start_cross_platform_mysql.py --openai_key YOUR_API_KEY
  
  # 自定义端口
  python start_cross_platform_mysql.py --port 3307
  
  # 指定监听地址
  python start_cross_platform_mysql.py --host 127.0.0.1 --port 3306
        """
    )
    
    parser.add_argument('--openai_key', type=str, help='OpenAI API密钥（可选）')
    parser.add_argument('--port', type=int, default=3306, help='监听端口（默认: 3306）')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址（默认: 0.0.0.0）')
    parser.add_argument('--model', type=str, default='gpt-3.5-turbo', help='LLM模型（默认: gpt-3.5-turbo）')
    parser.add_argument('--temp', type=float, default=0.2, help='LLM温度参数（默认: 0.2）')
    parser.add_argument('--max_tokens', type=int, default=256, help='LLM最大token数（默认: 256）')
    parser.add_argument('--config', type=str, help='配置文件路径（可选）')
    parser.add_argument('--no_llm', action='store_true', help='禁用LLM响应')
    
    args = parser.parse_args()

    # 加载配置文件
    config = load_config(args.config)
    
    # 合并配置和命令行参数
    port = args.port or int(config['personality'].get('port', 3306))
    host = args.host or '0.0.0.0'
    
    # LLM配置
    llm_enabled = not args.no_llm
    openai_key = args.openai_key or config['api_key'] or os.environ.get('OPENAI_API_KEY')
    model = args.model or config['personality'].get('model', 'gpt-3.5-turbo')
    temp = args.temp or float(config['personality'].get('temperature', 0.2))
    max_tokens = args.max_tokens or int(config['personality'].get('max_tokens', 256))

    # 初始化OpenAI客户端（如果提供了API密钥）
    openai_client = None
    if openai_key:
        try:
            import openai
            openai_client = openai.OpenAI(api_key=openai_key)
            print("✅ 已启用LLM响应功能")
        except ImportError:
            print("⚠️  警告: 未安装openai库，将使用模拟响应")
            print("   安装命令: pip install openai")
        except Exception as e:
            print(f"⚠️  警告: OpenAI客户端初始化失败: {e}")
            print("   将使用模拟响应")

    # 创建蜜罐实例
    honeypot = CrossPlatformMySQLHoneypot(
        openai_client=openai_client,
        mysql_model=model,
        mysql_temp=temp,
        mysql_max_tokens=max_tokens
    )

    # 设置事件循环
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        print("🪟 Windows平台检测，使用ProactorEventLoop")
    else:
        loop = asyncio.get_event_loop()
        print("🐧 Linux平台检测，使用默认事件循环")

    print(f"�� 启动跨平台MySQL蜜罐服务器 ({host}:{port})...")
    print("📋 功能特性:")
    print("   • 支持Linux和Windows客户端连接")
    print("   • 文件反制功能（敏感文件返回伪造内容）")
    print("   • 完整的MySQL协议模拟")
    print("   • 详细的会话日志记录")
    if openai_client:
        print("   • LLM智能响应")
    else:
        print("   • 模拟响应模式")

    # 启动服务器
    try:
        # 检查端口权限和可用性
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            test_socket.bind((host, port))
            test_socket.close()
            print(f"✅ 端口 {port} 可用")
        except OSError as e:
            if "权限" in str(e) or "permission" in str(e).lower():
                print(f"⚠️  端口 {port} 需要管理员权限")
                print("💡 建议使用以下解决方案之一：")
                print("   1. 使用更高端口号: --port 3307")
                print("   2. 以管理员身份运行")
                print("   3. 使用其他端口")
                
                # 自动尝试其他端口
                alternative_ports = [3307, 3308, 3309, 13306, 23306]
                for alt_port in alternative_ports:
                    try:
                        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        test_socket.bind((host, alt_port))
                        test_socket.close()
                        print(f"🔄 自动切换到端口 {alt_port}")
                        port = alt_port
                        break
                    except OSError:
                        continue
                else:
                    print("❌ 无法找到可用端口，请手动指定")
                    return 1
            elif "Address already in use" in str(e) or "端口" in str(e):
                print(f"⚠️  端口 {port} 被占用，尝试其他端口...")
                
                # 自动尝试其他端口
                alternative_ports = [3307, 3308, 3309, 13306, 23306]
                for alt_port in alternative_ports:
                    try:
                        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        test_socket.bind((host, alt_port))
                        test_socket.close()
                        print(f"🔄 自动切换到端口 {alt_port}")
                        port = alt_port
                        break
                    except OSError:
                        continue
                else:
                    print("❌ 无法找到可用端口，请手动指定")
                    return 1
            else:
                print(f"❌ 端口 {port} 错误: {e}")
                return 1
        
        server = loop.run_until_complete(
            honeypot.start_server(host=host, port=port)
        )
        
        print(f"✅ 服务器已在 {server.sockets[0].getsockname()} 启动")
        print("📝 日志文件保存在: ../../Log Manager/logs/")
        print("⏹️  按 Ctrl+C 停止服务器")
        print("-" * 50)
        
        loop.run_forever()
        
    except KeyboardInterrupt:
        print("\n⏹️  收到停止信号，正在关闭服务器...")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ 错误: 端口 {port} 已被占用")
            print(f"   请尝试使用其他端口: --port {port + 1}")
        else:
            print(f"❌ 启动失败: {e}")
    except Exception as e:
        print(f"❌ 未知错误: {e}")
    finally:
        try:
            server.close()
            loop.run_until_complete(server.wait_closed())
        except:
            pass
        loop.close()
        print("✅ 服务器已完全关闭")

if __name__ == "__main__":
    main() 