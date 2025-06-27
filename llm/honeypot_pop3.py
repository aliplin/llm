import os
import uuid
import threading
from datetime import datetime
import socket

def start_pop3(openai_client, pop3_identity, pop3_model, pop3_temp, pop3_max_tokens):
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "Log Manager", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    pop3_port = int(pop3_identity.get('port', 110))

    def handle_pop3_client(client_sock, client_addr):
        session_uuid = str(uuid.uuid4())
        session_start_time = datetime.now()
        timestamp = session_start_time.strftime("%Y-%m-%d_%H-%M-%S")
        log_file = os.path.join(logs_dir, f"logPOP3_{session_uuid}_{timestamp}.txt")
        history_file = os.path.join(logs_dir, f"historyPOP3_{session_uuid}_{timestamp}.txt")
        try:
            with open(log_file, 'a', encoding='utf-8') as logf:
                logf.write(f"POP3 session start: {session_start_time} from {client_addr[0]}:{client_addr[1]}\n")
            with open(history_file, 'a', encoding='utf-8') as histf:
                histf.write(f"Session started at: {session_start_time}\n")
        except Exception as e:
            print(f"[POP3蜜罐] 日志文件创建失败: {e}")
        messages = [
            {"role": "system", "content": pop3_identity['prompt'] + pop3_identity.get('final_instr', '')}
        ]
        banner = "Connected to pop.domain.ext.\r\nEscape character is '^]'.\r\n+OK ready\r\n> "
        try:
            client_sock.sendall(banner.encode())
            with open(log_file, 'a', encoding='utf-8') as logf:
                logf.write(f"[BANNER] {banner}\n")
        except Exception as e:
            print(f"[POP3蜜罐] 发送banner失败: {e}")
            client_sock.close()
            return
        while True:
            try:
                data = b''
                while not data.endswith(b'\n') and not data.endswith(b'\r\n'):
                    chunk = client_sock.recv(1024)
                    if not chunk:
                        raise ConnectionError('客户端断开连接')
                    data += chunk
                command = data.decode(errors='ignore').strip()
                if not command:
                    continue
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with open(log_file, 'a', encoding='utf-8') as logf:
                    logf.write(f"[{now}] [CMD] {command}\n")
                with open(history_file, 'a', encoding='utf-8') as histf:
                    histf.write(f"> {command}\n")
                messages.append({"role": "user", "content": command})
                try:
                    response = openai_client.chat.completions.create(
                        model=pop3_model,
                        messages=messages,
                        temperature=pop3_temp,
                        max_tokens=pop3_max_tokens
                    )
                    ai_response = response.choices[0].message.content
                    ai_response = ai_response.replace('\n', '\r\n')
                    if not ai_response.endswith('\r\n'):
                        ai_response += '\r\n>'
                except Exception as e:
                    ai_response = f"-ERR LLM服务异常: {e}\r\n> "
                with open(log_file, 'a', encoding='utf-8') as logf:
                    logf.write(f"[{now}] [RESP] {ai_response}\n")
                with open(history_file, 'a', encoding='utf-8') as histf:
                    histf.write(f"{ai_response}\n")
                try:
                    client_sock.sendall(ai_response.encode())
                except Exception as e:
                    print(f"[POP3蜜罐] 发送响应失败: {e}")
                    break
                if command.lower() in ("quit", "exit", "logout"):
                    break
            except Exception as e:
                print(f"[POP3蜜罐] 处理命令异常: {e}")
                break
        client_sock.close()
        with open(log_file, 'a', encoding='utf-8') as logf:
            logf.write(f"POP3 session end: {datetime.now()}\n")

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', pop3_port))
    server_sock.listen(50)
    print(f"POP3蜜罐服务启动在端口 {pop3_port}")
    while True:
        try:
            client_sock, client_addr = server_sock.accept()
            print(f"[POP3蜜罐] 接受连接: {client_addr}")
            t = threading.Thread(target=handle_pop3_client, args=(client_sock, client_addr))
            t.daemon = True
            t.start()
        except Exception as e:
            print(f"[POP3蜜罐] 主循环异常: {e}")
            continue 