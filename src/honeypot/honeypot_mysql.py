import os
import uuid
import threading
from datetime import datetime
import socket
import struct
from pathlib import Path

def send_mysql_packet(sock, payload, seq):
    length = len(payload)
    header = struct.pack('<I', length)[:3] + bytes([seq])
    sock.sendall(header + payload)

def send_mysql_text_result(sock, seq, text):
    # 1. 列数包
    col_count = 1
    col_count_packet = bytes([col_count])
    send_mysql_packet(sock, col_count_packet, seq)
    seq += 1
    # 2. 列定义包
    col_name = b"result"
    col_def_packet = (
        b"\x03def" + b"\x00" * 4 +  # catalog, db, table, org_table
        col_name + b"\x00" +        # name
        col_name + b"\x0c" +        # org_name, length of fixed fields
        b"\x3f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"  # type, flags, etc.
    )
    send_mysql_packet(sock, col_def_packet, seq)
    seq += 1
    # 3. EOF包
    send_mysql_packet(sock, b"\xfe\x00\x00\x02\x00\x00", seq)
    seq += 1
    # 4. 行数据包
    row_packet = bytes([len(text.encode())]) + text.encode()
    send_mysql_packet(sock, row_packet, seq)
    seq += 1
    # 5. EOF包
    send_mysql_packet(sock, b"\xfe\x00\x00\x02\x00\x00", seq)
    seq += 1
    return seq

def start_mysql(openai_client, mysql_identity, mysql_model, mysql_temp, mysql_max_tokens):
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent
    logs_dir = project_root / "src" / "log_manager" / "logs"
    logs_dir.mkdir(exist_ok=True)
    mysql_port = int(mysql_identity.get('port', 3309))

    def handle_mysql_client(client_sock, client_addr):
        session_uuid = str(uuid.uuid4())
        session_start_time = datetime.now()
        timestamp = session_start_time.strftime("%Y-%m-%d_%H-%M-%S")
        log_file = logs_dir / f"logMySQL_{session_uuid}_{timestamp}.txt"
        history_file = logs_dir / f"historyMySQL_{session_uuid}_{timestamp}.txt"
        try:
            with open(log_file, 'a', encoding='utf-8') as logf:
                logf.write(f"MySQL session start: {session_start_time} from {client_addr[0]}:{client_addr[1]}\n")
            with open(history_file, 'a', encoding='utf-8') as histf:
                histf.write(f"Session started at: {session_start_time}\n")
        except Exception as e:
            print(f"[MySQL蜜罐] 日志文件创建失败: {e}")
        messages = [
            {"role": "system", "content": mysql_identity['prompt'] + mysql_identity.get('final_instr', '')}
        ]
        try:
            protocol_version = 10
            server_version = "5.7.42"
            connection_id = 12345
            capability_flags = (
                    0x00000200 |  # CLIENT_PROTOCOL_41
                    0x00000008 |  # CLIENT_CONNECT_WITH_DB
                    0x00080000  # CLIENT_PLUGIN_AUTH
            )
            charset = 33
            status_flags = 2
            handshake = bytearray()
            handshake.append(protocol_version)
            handshake.extend(server_version.encode() + b'\0')
            handshake.extend(struct.pack('<I', connection_id))
            salt = os.urandom(8)
            handshake.extend(salt)
            handshake.append(0)
            handshake.extend(struct.pack('<H', capability_flags & 0xFFFF))
            handshake.append(charset)
            handshake.extend(struct.pack('<H', status_flags))
            handshake.extend(struct.pack('<H', (capability_flags >> 16) & 0xFFFF))
            handshake.append(21)
            handshake.extend(b'\0' * 10)
            handshake.extend(os.urandom(13))
            handshake.extend(b"mysql_native_password\0")
            packet_len = len(handshake)
            packet_header = struct.pack('<I', packet_len)[:3] + b'\x00'
            full_packet = packet_header + handshake
            client_sock.sendall(full_packet)
            print(f"[MySQL蜜罐] 已发送握手包至 {client_addr}")
            header = client_sock.recv(4)
            if len(header) < 4:
                raise ConnectionError("客户端响应不完整")
            packet_len = struct.unpack('<I', header[:3] + b'\x00')[0]
            seq = header[3]
            data = b''
            while len(data) < packet_len:
                chunk = client_sock.recv(packet_len - len(data))
                if not chunk:
                    raise ConnectionError("客户端断开连接")
                data += chunk
            print(f"[MySQL蜜罐] 收到客户端认证包，长度: {packet_len}")
            if len(data) >= 4:
                client_capability = struct.unpack('<I', data[:4])[0]
                print(f"[MySQL蜜罐] 客户端能力标志: {hex(client_capability)}")
            ok_packet = bytearray()
            ok_packet.append(0)
            ok_packet.extend(b'\x00\x00')
            ok_packet.extend(b'\x00\x00')
            ok_packet.extend(struct.pack('<H', status_flags))
            ok_packet.extend(b'\x00\x00')
            ok_packet_len = len(ok_packet)
            full_ok_packet = struct.pack('<I', ok_packet_len)[:3] + struct.pack('B', seq + 1) + ok_packet
            client_sock.sendall(full_ok_packet)
            print("[MySQL蜜罐] 已发送认证成功响应")
            welcome_msg = "Welcome to the MySQL honeypot. Type SQL or any command."
            seq = seq + 2
            send_mysql_text_result(client_sock, seq, welcome_msg)
            seq += 5
            while True:
                try:
                    header = client_sock.recv(4)
                    if len(header) == 0:
                        print("[MySQL蜜罐] 客户端主动断开连接")
                        break
                    if len(header) < 4:
                        raise ConnectionError(f"命令包头部不完整，收到{len(header)}字节")
                    packet_len = struct.unpack('<I', header[:3] + b'\x00')[0]
                    seq_num = header[3]
                    data = b''
                    while len(data) < packet_len:
                        chunk = client_sock.recv(packet_len - len(data))
                        if not chunk:
                            raise ConnectionError("数据接收中客户端断开")
                        data += chunk
                    if data:
                        command_type = data[0]
                        command_content = data[1:].decode('utf-8', errors='ignore').strip()
                    else:
                        command_content = ''
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    print(f"[MySQL蜜罐] 收到命令: {command_content}")
                    with open(log_file, 'a', encoding='utf-8') as logf:
                        logf.write(f"[{now}] [CMD] {command_content}\n")
                    with open(history_file, 'a', encoding='utf-8') as histf:
                        histf.write(f"mysql> {command_content}\n")
                    if command_content.lower() in ("quit", "exit", "\\q"):
                        goodbye = "Bye"
                        send_mysql_text_result(client_sock, seq_num + 1, goodbye)
                        break
                    messages.append({"role": "user", "content": command_content})
                    try:
                        response = openai_client.chat.completions.create(
                            model=mysql_model,
                            messages=messages,
                            temperature=mysql_temp,
                            max_tokens=mysql_max_tokens
                        )
                        ai_response = response.choices[0].message.content
                    except Exception as e:
                        ai_response = f"ERROR 2006 (HY000): MySQL server has gone away: {str(e)}"
                    if not ai_response.endswith('\n'):
                        ai_response += '\n'
                    with open(log_file, 'a', encoding='utf-8') as logf:
                        logf.write(f"[{now}] [RESP] {ai_response}\n")
                    with open(history_file, 'a', encoding='utf-8') as histf:
                        histf.write(f"{ai_response}\n")
                    send_mysql_text_result(client_sock, seq_num + 1, ai_response)
                except socket.timeout:
                    print("[MySQL蜜罐] 命令接收超时，等待客户端输入...")
                    continue
                except Exception as e:
                    print(f"[MySQL蜜罐] 命令处理错误: {e}")
                    break
        except ConnectionError as ce:
            print(f"[MySQL蜜罐] 连接异常: {ce}")
        except Exception as e:
            print(f"[MySQL蜜罐] 处理错误: {e}")
        finally:
            client_sock.close()
            print("[MySQL蜜罐] 客户端连接已关闭")
            with open(log_file, 'a', encoding='utf-8') as logf:
                logf.write(f"MySQL session end: {datetime.now()}\n")

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', mysql_port))
    server_sock.listen(50)
    print(f"MySQL蜜罐服务启动在端口 {mysql_port}")
    while True:
        try:
            client_sock, client_addr = server_sock.accept()
            client_sock.settimeout(30.0)
            print(f"[MySQL蜜罐] 接受连接: {client_addr}")
            threading.Thread(
                target=handle_mysql_client,
                args=(client_sock, client_addr),
                daemon=True
            ).start()
        except Exception as e:
            print(f"[MySQL蜜罐] 接受连接错误: {e}")

    pass 