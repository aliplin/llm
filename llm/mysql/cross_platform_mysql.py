#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台MySQL连接脚本
支持Windows和Linux系统
"""

import asyncio
import signal
import platform
import os
import uuid
from datetime import datetime
import re
import sys

# 导入MySQL协议模块
from protocol.base import OK, ERR, EOF
from protocol.handshake import HandshakeV10, HandshakeResponse41
from protocol.query import ColumnDefinition, ColumnDefinitionList, ResultSet
from protocol import _MysqlStreamSequence, MysqlStreamReader, MysqlStreamWriter

# 平台检测
IS_WINDOWS = platform.system().lower() == 'windows'
IS_LINUX = platform.system().lower() == 'linux'

def setup_signal_handlers():
    """设置信号处理器，跨平台兼容"""
    if IS_WINDOWS:
        # Windows下使用SIGINT
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    else:
        # Linux下使用SIGTERM和SIGINT
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)

def get_platform_info():
    """获取平台信息"""
    return {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor()
    }

def get_default_file_paths():
    """根据平台返回默认文件路径"""
    if IS_WINDOWS:
        return {
            'win_ini': r'C:\Windows\win.ini',
            'win_hosts': r'C:\Windows\System32\drivers\etc\hosts',
            'win_system': r'C:\Windows\System32',
            'win_sam': r'C:\Windows\System32\config\SAM',
            'win_system_reg': r'C:\Windows\System32\config\system',
            'win_users': r'C:\Users',
            'win_temp': os.environ.get('TEMP', r'C:\Windows\Temp')
        }
    else:
        return {
            'linux_passwd': '/etc/passwd',
            'linux_shadow': '/etc/shadow',
            'linux_hosts': '/etc/hosts',
            'linux_ssh_key': '/root/.ssh/id_rsa',
            'linux_bash_history': '/root/.bash_history',
            'linux_etc': '/etc',
            'linux_tmp': '/tmp'
        }

def create_event_loop():
    """创建适合当前平台的事件循环"""
    if IS_WINDOWS:
        # Windows下使用ProactorEventLoop
        try:
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
            print("使用Windows ProactorEventLoop")
        except Exception as e:
            print(f"ProactorEventLoop创建失败: {e}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    else:
        # Linux下使用默认事件循环
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            print("使用Linux默认事件循环")
        except Exception as e:
            print(f"事件循环创建失败: {e}")
            loop = asyncio.get_event_loop()
    
    return loop

class CrossPlatformMySQLHoneypot:
    def __init__(self, openai_client=None, mysql_model='gpt-3.5-turbo', mysql_temp=0.2, mysql_max_tokens=256):
        self.openai_client = openai_client
        self.mysql_model = mysql_model
        self.mysql_temp = mysql_temp
        self.mysql_max_tokens = mysql_max_tokens
        
        # 敏感文件配置
        self.SENSITIVE_FILES = [
            '/etc/passwd', '/root/.ssh/id_rsa', '/root/.bash_history', '/etc/shadow',
            'C:/Windows/System32/config/SAM', 'C:/Windows/System32/config/system',
            'id_rsa', 'id_dsa', 'authorized_keys', 'shadow', 'passwd', 'SAM', 'system',
            'C:/Windows/PFRO.log', 'C:/Windows/System32/config/RegBack/SAM'
        ]
        
        self.FAKE_CONTENT = {
            '/etc/passwd': 'root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000:user:/home/user:/bin/bash\n',
            '/etc/shadow': 'root:$6$fakehash:19000:0:99999:7:::\n',
            'C:/Windows/System32/config/SAM': 'FAKE_WINDOWS_SAM_CONTENT\n',
            'C:/Windows/PFRO.log': 'FAKE_WINDOWS_PFRO_LOG_CONTENT\n',
            'id_rsa': '-----BEGIN RSA PRIVATE KEY-----\nFAKEKEY\n-----END RSA PRIVATE KEY-----\n',
            'id_dsa': '-----BEGIN DSA PRIVATE KEY-----\nFAKEKEY\n-----END DSA PRIVATE KEY-----\n',
            'authorized_keys': 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDFAKEKEY== user@honeypot\n',
        }
        
        # 创建日志目录
        self.logs_dir = os.path.join(os.path.dirname(__file__), "..", "../Log Manager", "logs")
        os.makedirs(self.logs_dir, exist_ok=True)

    def mysql_get_file_content(self, filename, server_writer, capability, handshake_status, client_addr, log_file):
        """文件反制功能"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(log_file, 'a', encoding='utf-8') as logf:
            logf.write(f"[{now}] [FILE_READ] {client_addr} 尝试读取文件: {filename}\n")
        
        # 检查敏感文件
        for key in self.SENSITIVE_FILES:
            if key in filename:
                content = self.FAKE_CONTENT.get(key, 'FAKE_FILE_CONTENT\n')
                # 返回文件内容作为查询结果
                ColumnDefinitionList((ColumnDefinition('file_content'),)).write(server_writer)
                EOF(capability, handshake_status).write(server_writer)
                ResultSet((content,)).write(server_writer)
                return EOF(capability, handshake_status)
        
        # 普通文件，尝试读取
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(4096)
            ColumnDefinitionList((ColumnDefinition('file_content'),)).write(server_writer)
            EOF(capability, handshake_status).write(server_writer)
            ResultSet((content,)).write(server_writer)
            return EOF(capability, handshake_status)
        except Exception as e:
            # 返回错误
            error_msg = f"ERROR 1045 (28000): Access denied for file '{filename}'"
            return ERR(capability, 1045, "28000", error_msg)

    async def handle_server(self, server_reader, server_writer):
        """处理客户端连接的核心函数"""
        client_addr = server_writer.get_extra_info('peername')[:2]
        
        # 创建会话日志
        session_uuid = str(uuid.uuid4())
        session_start_time = datetime.now()
        timestamp = session_start_time.strftime("%Y-%m-%d_%H-%M-%S")
        log_file = os.path.join(self.logs_dir, f"logMySQL_{session_uuid}_{timestamp}.txt")
        history_file = os.path.join(self.logs_dir, f"historyMySQL_{session_uuid}_{timestamp}.txt")
        
        try:
            with open(log_file, 'a', encoding='utf-8') as logf:
                logf.write(f"MySQL session start: {session_start_time} from {client_addr[0]}:{client_addr[1]}\n")
            with open(history_file, 'a', encoding='utf-8') as histf:
                histf.write(f"Session started at: {session_start_time}\n")
        except Exception as e:
            print(f"[MySQL蜜罐] 日志文件创建失败: {e}")

        # 发送握手包
        handshake = HandshakeV10()
        handshake.write(server_writer)
        print(f"新连接: {client_addr}")
        await server_writer.drain()

        # 读取客户端响应
        handshake_response = await HandshakeResponse41.read(server_reader.packet(), handshake.capability)
        username = handshake_response.user
        print(f"登录用户名: {username.decode('ascii')}")

        # 发送认证成功响应
        capability = handshake_response.capability_effective
        result = OK(capability, handshake.status)
        result.write(server_writer)
        await server_writer.drain()

        # 主命令处理循环
        while True:
            server_writer.reset()
            packet = server_reader.packet()
            try:
                cmd = (await packet.read(1))[0]  # 读取命令字节
            except Exception:
                return  # 连接断开

            query = await packet.read()
            if query:
                query = query.decode('ascii')

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(log_file, 'a', encoding='utf-8') as logf:
                logf.write(f"[{now}] [CMD] {query}\n")
            with open(history_file, 'a', encoding='utf-8') as histf:
                histf.write(f"mysql> {query}\n")

            # 命令处理逻辑
            if cmd == 1:  # COM_QUIT
                print("客户端请求断开连接")
                return
            elif cmd == 3:  # COM_QUERY
                print(f"收到查询: {query}")

                # 检测文件读取命令
                if 'load_file' in query.lower() or 'into outfile' in query.lower():
                    m = re.search(r"load_file\s*\(\s*'([^']+)'\s*\)", query, re.I)
                    if m:
                        filename = m.group(1)
                    else:
                        m = re.search(r"into outfile\s*'([^']+)'", query, re.I)
                        filename = m.group(1) if m else ''
                    
                    if filename:
                        result = self.mysql_get_file_content(filename, server_writer, capability, handshake.status, client_addr, log_file)
                        result.write(server_writer)
                        await server_writer.drain()
                        continue

                # 处理其他查询 - 统一使用LLM处理
                if self.openai_client:
                    # 使用LLM响应所有查询
                    print(f"使用LLM处理查询: {query}")
                    try:
                        # 构建系统提示
                        system_prompt = """你是一个MySQL数据库服务器，需要以MySQL的格式响应客户端查询。

重要规则：
1. 对于SHOW DATABASES，返回标准的数据库列表（information_schema, mysql, performance_schema, sys, test等）
2. 对于SHOW TABLES，返回模拟的表列表
3. 对于SELECT查询，返回模拟的数据
4. 对于CREATE/DROP/ALTER等DDL命令，返回成功消息
5. 对于INSERT/UPDATE/DELETE等DML命令，返回影响的行数
6. 对于不支持的查询，返回适当的错误信息
7. 始终以MySQL协议格式响应

示例响应格式：
- SHOW DATABASES: 返回数据库列表
- SELECT 1: 返回数字1
- SELECT VERSION(): 返回版本信息
- 成功查询：返回结果集或OK消息
- 错误查询：返回ERROR消息
- 不支持：返回"ERROR 1064 (42000): You have an error in your SQL syntax"

请根据查询类型提供合适的MySQL响应。"""

                        messages = [
                            {"role": "system", "content": system_prompt}
                        ]
                        
                        # LLM生成响应
                        messages.append({"role": "user", "content": query})
                        try:
                            response = await asyncio.wait_for(
                                asyncio.to_thread(
                                    self.openai_client.chat.completions.create,
                                    model=self.mysql_model,
                                    messages=messages,
                                    temperature=self.mysql_temp,
                                    max_tokens=self.mysql_max_tokens
                                ),
                                timeout=10.0  # 10秒超时
                            )
                            ai_response = response.choices[0].message.content
                            print(f"LLM响应: {ai_response}")
                        except asyncio.TimeoutError:
                            print("LLM请求超时，使用默认响应")
                            ai_response = "Query OK, 0 rows affected"
                        except Exception as e:
                            print(f"LLM请求失败: {e}")
                            ai_response = f"ERROR 2006 (HY000): MySQL server has gone away: {str(e)}"

                        if not ai_response.endswith('\n'):
                            ai_response += '\n'

                        # 记录LLM响应
                        with open(log_file, 'a', encoding='utf-8') as logf:
                            logf.write(f"[{now}] [LLM_RESP] {ai_response}\n")
                        with open(history_file, 'a', encoding='utf-8') as histf:
                            histf.write(f"{ai_response}\n")

                        # 根据响应类型返回不同的结果
                        if ai_response.upper().startswith('ERROR'):
                            # 返回错误响应
                            error_msg = ai_response.replace('ERROR ', '').split(':', 1)
                            if len(error_msg) > 1:
                                error_code = error_msg[0].strip()
                                error_text = error_msg[1].strip()
                                try:
                                    error_code_int = int(error_code)
                                except ValueError:
                                    error_code_int = 1064
                                result = ERR(capability, error_code_int, "42000", error_text)
                            else:
                                result = ERR(capability, 1064, "42000", ai_response)
                        elif 'SELECT' in query.upper() or 'SHOW' in query.upper():
                            # 返回结果集
                            try:
                                # 发送列定义
                                ColumnDefinitionList((ColumnDefinition('result'),)).write(server_writer)
                                await server_writer.drain()
                                
                                # 发送EOF包
                                EOF(capability, handshake.status).write(server_writer)
                                await server_writer.drain()
                                
                                # 发送结果数据
                                ResultSet((ai_response.strip(),)).write(server_writer)
                                await server_writer.drain()
                                
                                # 发送最终EOF包
                                result = EOF(capability, handshake.status)
                            except Exception as e:
                                print(f"结果集发送失败: {e}")
                                result = ERR(capability, 1064, "42000", f"Error sending result set: {str(e)}")
                        else:
                            # 返回成功响应
                            result = OK(capability, handshake.status)
                            
                    except Exception as e:
                        print(f"LLM响应生成失败: {e}")
                        error_msg = f"ERROR 2006 (HY000): MySQL server has gone away: {str(e)}"
                        with open(log_file, 'a', encoding='utf-8') as logf:
                            logf.write(f"[{now}] [LLM_ERROR] {error_msg}\n")
                        
                        # 返回错误响应
                        result = ERR(capability, 2006, "HY000", f"MySQL server has gone away: {str(e)}")
                else:
                    # 没有LLM客户端时的默认响应
                    print(f"未知查询（无LLM）: {query}")
                    default_response = "Query OK, 0 rows affected"
                    with open(log_file, 'a', encoding='utf-8') as logf:
                        logf.write(f"[{now}] [DEFAULT_RESP] {default_response}\n")
                    result = OK(capability, handshake.status)
            else:
                # 未知命令返回错误
                result = ERR(capability)
                print(f"未知命令: {cmd}")

            # 发送响应
            result.write(server_writer)
            await server_writer.drain()

        # 记录会话结束
        with open(log_file, 'a', encoding='utf-8') as logf:
            logf.write(f"MySQL session end: {datetime.now()}\n")

    async def start_server(self, host='0.0.0.0', port=3306):
        """启动服务器"""
        async def handle_connection(reader, writer):
            seq = _MysqlStreamSequence()
            reader_m = MysqlStreamReader(reader, seq)
            writer_m = MysqlStreamWriter(writer, seq)
            await self.handle_server(reader_m, writer_m)
        
        if sys.platform == 'win32':
            # Windows平台
            server = await asyncio.start_server(
                handle_connection,
                host=host,
                port=port,
                reuse_address=True
            )
        else:
            # Linux平台
            server = await asyncio.start_server(
                handle_connection,
                host=host,
                port=port,
                reuse_address=True,
                reuse_port=True
            )
        return server

def main():
    """主函数"""
    print("=" * 50)
    print("跨平台MySQL模拟服务器")
    print("=" * 50)
    
    # 显示平台信息
    platform_info = get_platform_info()
    print(f"操作系统: {platform_info['system']} {platform_info['release']}")
    print(f"架构: {platform_info['machine']}")
    print(f"处理器: {platform_info['processor']}")
    
    # 设置信号处理器
    setup_signal_handlers()
    
    # 创建事件循环
    loop = create_event_loop()
    
    # 启动服务器
    port = 3306
    print(f"启动MySQL模拟服务器 (端口: {port})...")
    print(f"监听地址: 0.0.0.0:{port}")
    
    try:
        # 初始化OpenAI客户端（如果提供了API密钥）
        openai_client = None
        if sys.argv[1:]:
            try:
                import openai
                openai_client = openai.OpenAI(api_key=sys.argv[1])
                print("已启用LLM响应功能")
            except ImportError:
                print("警告: 未安装openai库，将使用模拟响应")
            except Exception as e:
                print(f"警告: OpenAI客户端初始化失败: {e}")

        # 创建蜜罐实例
        honeypot = CrossPlatformMySQLHoneypot(openai_client)

        # 启动服务器
        server = loop.run_until_complete(
            honeypot.start_server(host='0.0.0.0', port=port)
        )

        print(f"服务器已在 {server.sockets[0].getsockname()} 启动")
        loop.run_forever()
        
    except KeyboardInterrupt:
        print("\n收到停止信号，正在关闭服务器...")
    except Exception as e:
        print(f"服务器运行错误: {e}")
    finally:
        try:
            # 清理资源
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # 等待所有任务完成
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            loop.close()
            print("服务器已停止")
        except Exception as e:
            print(f"关闭服务器时发生错误: {e}")

if __name__ == "__main__":
    main() 