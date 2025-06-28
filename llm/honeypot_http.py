import os
import json
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

HTTP_PORT = 8080

<<<<<<< HEAD
class HTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.openai_client = kwargs.pop('openai_client', None)
        self.identity = kwargs.pop('identity', None)
        self.model_name = kwargs.pop('model_name', None)
        self.temperature = kwargs.pop('temperature', None)
        self.max_tokens = kwargs.pop('max_tokens', None)
        self.output_dir = kwargs.pop('output_dir', None)
=======
# 预定义模板
HTML_TEMPLATES = {
    "home": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name} - {model_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; margin: 0; padding: 0; }}
        header {{ background-color: #0056b3; color: white; padding: 10px 0; text-align: center; }}
        nav {{ background-color: #333; color: white; padding: 10px 0; text-align: center; }}
        nav a {{ color: white; text-decoration: none; padding: 10px 15px; margin: 0 5px; }}
        nav a:hover {{ background: #555; }}
        .container {{ width: 80%; margin: auto; padding: 20px; }}
        .main-content {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        h1, h2 {{ color: #0056b3; }}
        .features {{ background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .features ul {{ padding-left: 20px; }}
        .features li {{ margin: 8px 0; }}
        footer {{ background: #333; color: white; text-align: center; padding: 10px 0; position: fixed; bottom: 0; width: 100%; }}
    </style>
</head>
<body>
    <header>
        <h1><a href="/" style="color: white; text-decoration: none;">{company_name} - {model_name}</a></h1>
    </header>
    <nav>
        <a href="/">Home</a>
        <a href="/documentation">Documentation</a>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
    </nav>
    <div class="container">
        <div class="main-content">
            <h2>Welcome to {company_name}</h2>
            <p>{welcome_text}</p>
            <div class="features">
                <h3>Key Features:</h3>
                <ul>
                    {features_list}
                </ul>
            </div>
            <p>{description_text}</p>
        </div>
    </div>
    <footer>
        <p>&copy; 2025 {company_name}. All rights reserved.</p>
    </footer>
</body>
</html>""",

    "documentation": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name} - Documentation</title>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; margin: 0; padding: 0; }}
        header {{ background-color: #0056b3; color: white; padding: 10px 0; text-align: center; }}
        nav {{ background-color: #333; color: white; padding: 10px 0; text-align: center; }}
        nav a {{ color: white; text-decoration: none; padding: 10px 15px; margin: 0 5px; }}
        nav a:hover {{ background: #555; }}
        .container {{ width: 80%; margin: auto; padding: 20px; }}
        .doc-content {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        h1, h2, h3 {{ color: #0056b3; }}
        .section {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 5px; }}
        code {{ background-color: #eee; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background-color: #eee; padding: 10px; border-radius: 3px; overflow-x: auto; }}
        footer {{ background: #333; color: white; text-align: center; padding: 10px 0; position: fixed; bottom: 0; width: 100%; }}
    </style>
</head>
<body>
    <header>
        <h1><a href="/" style="color: white; text-decoration: none;">{company_name} - {model_name}</a></h1>
    </header>
    <nav>
        <a href="/">Home</a>
        <a href="/documentation">Documentation</a>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
    </nav>
    <div class="container">
        <div class="doc-content">
            <h2>Documentation</h2>
            {doc_content}
        </div>
    </div>
    <footer>
        <p>&copy; 2025 {company_name}. All rights reserved.</p>
    </footer>
</body>
</html>""",

    "error_400": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>400 Bad Request</title>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; text-align: center; padding: 50px; }}
        .error-container {{ background: white; padding: 40px; border-radius: 10px; max-width: 500px; margin: auto; }}
        h1 {{ color: #d32f2f; font-size: 48px; margin: 0; }}
        h2 {{ color: #333; margin: 20px 0; }}
        p {{ color: #666; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>400</h1>
        <h2>Bad Request</h2>
        <p>The server cannot process the request due to a client error.</p>
        <p>Please check your request and try again.</p>
    </div>
</body>
</html>""",

    "css": """/* Main styles for {company_name} {model_name} */
body {{
    font-family: Arial, sans-serif;
    background-color: #f4f4f4;
    color: #333;
    margin: 0;
    padding: 0;
}}

header {{
    background-color: #0056b3;
    color: white;
    padding: 10px 0;
    text-align: center;
}}

nav {{
    background-color: #333;
    color: white;
    padding: 10px 0;
    text-align: center;
}}

nav a {{
    color: white;
    text-decoration: none;
    padding: 10px 15px;
    margin: 0 5px;
}}

nav a:hover {{
    background: #555;
}}

.container {{
    width: 80%;
    margin: auto;
    padding: 20px;
}}

.main-content {{
    background: white;
    padding: 20px;
    border-radius: 5px;
    margin: 20px 0;
}}

h1, h2, h3 {{
    color: #0056b3;
}}

footer {{
    background: #333;
    color: white;
    text-align: center;
    padding: 10px 0;
    position: fixed;
    bottom: 0;
    width: 100%;
}}"""
}

class HTTPSession:
    """HTTP会话管理类，维护AI对话历史和内容缓存"""
    
    def __init__(self, openai_client, identity, model_name, temperature, max_tokens):
        self.openai_client = openai_client
        self.identity = identity
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # 初始化AI对话历史
        self.conversation_history = [
            {"role": "system", "content": self.identity['prompt']}
        ]
        
        # 内容缓存 - 确保同一页面内容一致
        self.content_cache = {}
        
        # 初始化网站内容（只生成一次）
        self._initialize_website_content()
    
    def _initialize_website_content(self):
        """初始化网站内容，确保整个网站的一致性"""
        try:
            # 生成网站基础信息
            prompt = f"""你是一个{self.identity['prompt']}的打印机公司。请生成以下信息（只返回JSON格式）：
1. company_name: 公司名称（简短有创意）
2. model_name: 打印机型号（包含数字）
3. welcome_text: 欢迎文字（50字以内）
4. features_list: 5个主要特性（HTML格式的li标签）
5. description_text: 产品描述（100字以内）

只返回JSON，不要其他内容。"""
            
            messages = [
                {"role": "system", "content": "你是一个打印机公司的AI助手，只返回JSON格式的数据。"},
                {"role": "user", "content": prompt}
            ]
            
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # 解析JSON响应
            try:
                data = json.loads(content)
                self.website_info = {
                    "company_name": data.get("company_name", "Tech Soulutions"),
                    "model_name": data.get("model_name", "TechPrint 2000"),
                    "welcome_text": data.get("welcome_text", "Welcome to our printer solutions."),
                    "features_list": data.get("features_list", "<li>High-speed printing</li><li>Wireless connectivity</li><li>Duplex printing</li><li>High resolution</li><li>Eco-friendly</li>"),
                    "description_text": data.get("description_text", "Our flagship printer offers advanced features for modern businesses.")
                }
            except:
                # 如果JSON解析失败，使用默认值
                self.website_info = {
                    "company_name": "Tech Soulutions",
                    "model_name": "TechPrint 2000",
                    "welcome_text": "Welcome to Tech Soulutions, leading manufacturer of high-quality printing solutions.",
                    "features_list": "<li>High-speed printing up to 30 ppm</li><li>1200 dpi resolution</li><li>Wireless and Ethernet connectivity</li><li>Duplex printing</li><li>Touchscreen display</li>",
                    "description_text": "The TechPrint 2000 is designed to meet the demands of modern businesses with its robust performance and user-friendly interface."
                }
            
            # 生成文档内容
            self._generate_documentation_content()
            
        except Exception as e:
            print(f"初始化网站内容失败: {e}")
            # 使用默认内容
            self.website_info = {
                "company_name": "Tech Soulutions",
                "model_name": "TechPrint 2000",
                "welcome_text": "Welcome to Tech Soulutions, leading manufacturer of high-quality printing solutions.",
                "features_list": "<li>High-speed printing up to 30 ppm</li><li>1200 dpi resolution</li><li>Wireless and Ethernet connectivity</li><li>Duplex printing</li><li>Touchscreen display</li>",
                "description_text": "The TechPrint 2000 is designed to meet the demands of modern businesses with its robust performance and user-friendly interface."
            }
            self._generate_documentation_content()
    
    def _generate_documentation_content(self):
        """生成文档内容并缓存"""
        try:
            prompt = f"""你是一个{self.identity['prompt']}的打印机公司。请生成技术文档内容（只返回HTML格式的div内容，包含多个section）：
- 安装指南
- 使用说明
- 故障排除
- 技术规格

每个section包含h3标题和详细内容。只返回HTML内容，不要完整的HTML文档。"""
            
            messages = [
                {"role": "system", "content": "你是一个打印机公司的技术文档生成器，只返回HTML格式的文档内容。"},
                {"role": "user", "content": prompt}
            ]
            
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=800
            )
            
            self.doc_content = response.choices[0].message.content
            
        except Exception as e:
            print(f"生成文档内容失败: {e}")
            # 使用默认文档内容
            self.doc_content = """
            <div class="section">
                <h3>Installation Guide</h3>
                <p>Follow these steps to install your TechPrint 2000 printer:</p>
                <ol>
                    <li>Unpack the printer and remove all packaging materials</li>
                    <li>Connect the power cable to the printer and electrical outlet</li>
                    <li>Install the ink cartridges as shown in the quick start guide</li>
                    <li>Load paper into the input tray</li>
                    <li>Turn on the printer and follow the on-screen setup wizard</li>
                </ol>
            </div>
            <div class="section">
                <h3>Usage Instructions</h3>
                <p>The TechPrint 2000 features an intuitive touchscreen interface for easy operation. Use the navigation buttons to access different functions and settings.</p>
            </div>
            <div class="section">
                <h3>Troubleshooting</h3>
                <p>If you experience any issues with your printer, refer to the troubleshooting section in the user manual or contact our technical support team.</p>
            </div>
            <div class="section">
                <h3>Technical Specifications</h3>
                <ul>
                    <li>Print Resolution: Up to 1200 dpi</li>
                    <li>Print Speed: Up to 30 pages per minute</li>
                    <li>Connectivity: USB, Ethernet, Wi-Fi</li>
                    <li>Paper Capacity: 250 sheets</li>
                </ul>
            </div>
            """
    
    def get_home_page(self):
        """获取首页内容（使用缓存）"""
        if "home" not in self.content_cache:
            self.content_cache["home"] = HTML_TEMPLATES["home"].format(
                company_name=self.website_info["company_name"],
                model_name=self.website_info["model_name"],
                welcome_text=self.website_info["welcome_text"],
                features_list=self.website_info["features_list"],
                description_text=self.website_info["description_text"]
            )
        return self.content_cache["home"]
    
    def get_documentation_page(self):
        """获取文档页面内容（使用缓存）"""
        if "documentation" not in self.content_cache:
            self.content_cache["documentation"] = HTML_TEMPLATES["documentation"].format(
                company_name=self.website_info["company_name"],
                model_name=self.website_info["model_name"],
                doc_content=self.doc_content
            )
        return self.content_cache["documentation"]
    
    def get_css(self):
        """获取CSS内容（使用缓存）"""
        if "css" not in self.content_cache:
            self.content_cache["css"] = HTML_TEMPLATES["css"].format(
                company_name=self.website_info["company_name"],
                model_name=self.website_info["model_name"]
            )
        return self.content_cache["css"]
    
    def get_error_page(self):
        """获取错误页面内容（使用缓存）"""
        if "error_400" not in self.content_cache:
            self.content_cache["error_400"] = HTML_TEMPLATES["error_400"]
        return self.content_cache["error_400"]
    
    def get_other_page(self):
        """获取其他页面内容（使用缓存）"""
        if "other" not in self.content_cache:
            self.content_cache["other"] = HTML_TEMPLATES["home"].format(
                company_name=self.website_info["company_name"],
                model_name=self.website_info["model_name"],
                welcome_text=self.website_info["welcome_text"],
                features_list=self.website_info["features_list"],
                description_text=self.website_info["description_text"]
            )
        return self.content_cache["other"]

class HTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
>>>>>>> 3114dd187db48eb9aad93eaf1fe470dc1f067429
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
<<<<<<< HEAD
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
=======

            # 根据路径选择响应策略（使用会话缓存）
            if self.path == "/":
                response_content = self.session.get_home_page()
            elif self.path == "/documentation":
                response_content = self.session.get_documentation_page()
            elif self.path == "/styles.css":
                response_content = self.session.get_css()
                self.send_header('Content-type', 'text/css')
            elif self.path.startswith("/") and len(self.path) > 1:
                # 其他页面使用默认模板
                response_content = self.session.get_other_page()
            else:
                response_content = self.session.get_error_page()

            self.send_response(200)
            if self.path != "/styles.css":
                self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(response_content.encode())

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"HTTP Request: {json.dumps(request_info)}\n")
                f.write(f"Response: {response_content}\n")

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.wfile.write(b"Internal Server Error")

def start_http_server(openai_client, identity, model_name, temperature, max_tokens, output_dir, log_file):
    # 创建HTTP会话（只创建一次）
    session = HTTPSession(openai_client, identity, model_name, temperature, max_tokens)
    
    def handler(*args, **kwargs):
        return HTTPHandler(*args, session=session, **kwargs)
    
    server = HTTPServer(('0.0.0.0', HTTP_PORT), handler)
    print(f"HTTP服务器启动在端口 {HTTP_PORT}")
    print(f"网站信息: {session.website_info['company_name']} - {session.website_info['model_name']}")
>>>>>>> 3114dd187db48eb9aad93eaf1fe470dc1f067429
    server.serve_forever() 