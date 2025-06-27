import os
import json
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

HTTP_PORT = 8080

class HTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.openai_client = kwargs.pop('openai_client', None)
        self.identity = kwargs.pop('identity', None)
        self.model_name = kwargs.pop('model_name', None)
        self.temperature = kwargs.pop('temperature', None)
        self.max_tokens = kwargs.pop('max_tokens', None)
        self.output_dir = kwargs.pop('output_dir', None)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        try:
            client_ip = self.client_address[0]
            request_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logs_dir = os.path.join(os.path.dirname(__file__), "..", "Log Manager", "logs")
            os.makedirs(logs_dir, exist_ok=True)
            session_uuid = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_file = os.path.join(logs_dir, f"logHTTP_{session_uuid}_{timestamp}.txt")
            headers = dict(self.headers)
            request_info = {
                "method": self.command,
                "path": self.path,
                "headers": headers,
                "client_ip": client_ip,
                "time": request_time
            }
            messages = [
                {"role": "system", "content": self.identity['prompt']},
                {"role": "user", "content": json.dumps(request_info)}
            ]
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            content = response.choices[0].message.content
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode())
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"HTTP Request: {json.dumps(request_info)}\n")
                f.write(f"Response: {content}\n")
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.welcome_msg()
            self.wfile.write(b"Internal Server Error")

def start_http_server(openai_client, identity, model_name, temperature, max_tokens, output_dir, log_file):
    def handler(*args, **kwargs):
        return HTTPHandler(*args,
                         openai_client=openai_client,
                         identity=identity,
                         model_name=model_name,
                         temperature=temperature,
                         max_tokens=max_tokens,
                         output_dir=output_dir,
                         **kwargs)
    HTTP_PORT = 8080
    server = HTTPServer(('0.0.0.0', HTTP_PORT), handler)
    print(f"HTTP服务器启动在端口 {HTTP_PORT}")
    server.serve_forever() 