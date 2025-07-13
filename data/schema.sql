-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建规则表
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    pattern TEXT NOT NULL,
    severity TEXT NOT NULL,
    category TEXT,
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建事件表
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT,
    request_path TEXT,
    request_method TEXT,
    request_data TEXT,
    severity TEXT,
    status TEXT,
    event_type TEXT,
    FOREIGN KEY (rule_id) REFERENCES rules (id)
);

-- 创建系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建设置表
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认设置
INSERT OR IGNORE INTO settings (name, value, description) VALUES
('log_level', 'INFO', '系统日志级别'),
('alert_email', '', '告警邮件接收地址'),
('block_duration', '3600', 'IP封禁时长(秒)'),
('max_events', '10000', '数据库中保留的最大事件数');


-- 插入默认规则
INSERT INTO rules (name, description, pattern, severity, category) VALUES
('SQL注入检测', '检测常见SQL注入模式', '\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|OR|AND)\s+.*\b(SELECT|FROM|WHERE|INTO|VALUES|UPDATE|DELETE|DROP|UNION)\b', 'high', 'injection'),
('XSS攻击检测', '检测跨站脚本攻击', '<script[^>]*>.*?</script>|<[^>]*on\w+\s*=\s*[^>]*>', 'high', 'xss'),
('命令注入检测', '检测命令注入尝试', '\b(wget|curl|nc|netcat|bash|sh|python|perl|ruby)\b.*?\$|\$\(.*?\)', 'high', 'injection'),
('目录遍历检测', '检测目录遍历攻击', '\.\./|\.\.\\|/etc/passwd|/etc/shadow|/proc/self/environ', 'high', 'traversal'),
('敏感文件访问', '检测对敏感文件的访问', '\.env|\.htaccess|\.git/|\.gitignore|config\.php|database\.php', 'medium', 'sensitive'),
('常见Web漏洞扫描', '检测常见的Web漏洞扫描工具', 'nikto|sqlmap|w3af|dirb|dirbuster|metasploit', 'medium', 'scanning'),
('可疑User-Agent', '检测可疑的User-Agent字符串', 'python-requests|curl|wget|nmap|masscan|zmap', 'low', 'scanning'),

-- 新增规则：更全面的SQL注入检测
('SQL注入-UNION查询', '检测UNION查询注入', 'UNION\s+(ALL\s+)?SELECT|UNION\s+(ALL\s+)?SELECT\s+.*?FROM', 'high', 'injection'),
('SQL注入-布尔盲注', '检测布尔盲注攻击', 'AND\s+\d+\s*=\s*\d+|OR\s+\d+\s*=\s*\d+|AND\s+TRUE|OR\s+FALSE', 'high', 'injection'),
('SQL注入-时间盲注', '检测时间盲注攻击', 'SLEEP\(\d+\)|BENCHMARK\(\d+,.*\)|WAIT\s+FOR\s+DELAY', 'high', 'injection'),
('SQL注入-堆叠查询', '检测堆叠查询注入', ';\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)', 'high', 'injection'),

-- 新增规则：更全面的XSS检测
('XSS-事件处理器', '检测事件处理器XSS', 'on\w+\s*=\s*["\']?[^"\'>]*["\']?', 'high', 'xss'),
('XSS-JavaScript协议', '检测JavaScript协议XSS', 'javascript:|vbscript:|data:text/html', 'high', 'xss'),
('XSS-编码绕过', '检测编码绕过的XSS', '&#x?[0-9a-fA-F]+;|%[0-9a-fA-F]{2}|\\x[0-9a-fA-F]{2}', 'medium', 'xss'),
('XSS-SVG标签', '检测SVG标签XSS', '<svg[^>]*>|<foreignObject[^>]*>|<animate[^>]*>', 'high', 'xss'),

-- 新增规则：命令注入扩展
('命令注入-管道操作', '检测管道命令注入', '\|\s*\w+|\|\s*[;&]|\|\s*`.*`', 'high', 'injection'),
('命令注入-反引号', '检测反引号命令执行', '`.*`|\$\(.*\)', 'high', 'injection'),
('命令注入-分号分隔', '检测分号分隔的命令', ';\s*\w+.*?;|;\s*[&\|]', 'high', 'injection'),
('命令注入-环境变量', '检测环境变量利用', '\$\{[^}]+\}|\$[A-Z_]+', 'medium', 'injection'),

-- 新增规则：文件包含漏洞
('本地文件包含', '检测本地文件包含攻击', '\.\./|\.\.\\|/etc/|/proc/|/sys/|/dev/', 'high', 'lfi'),
('远程文件包含', '检测远程文件包含攻击', 'http://|https://|ftp://|file://|php://|data://', 'high', 'rfi'),
('文件包含-编码绕过', '检测编码绕过的文件包含', '%2e%2e%2f|%2e%2e%5c|%252e%252e%252f', 'medium', 'lfi'),

-- 新增规则：SSRF攻击检测
('SSRF-内网探测', '检测SSRF内网探测', '127\.0\.0\.1|localhost|0\.0\.0\.0|10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.', 'high', 'ssrf'),
('SSRF-云服务元数据', '检测云服务元数据访问', '169\.254\.169\.254|metadata\.googleapis\.com|169\.254\.170\.2', 'high', 'ssrf'),

-- 新增规则：反序列化攻击
('反序列化-危险类', '检测危险的反序列化类', 'O:|a:\d+:|s:\d+:|i:\d+:|b:\d+:|N;', 'high', 'deserialization'),
('反序列化-PHP对象', '检测PHP对象反序列化', 'O:\d+:"[^"]+":\d+:', 'high', 'deserialization'),

-- 新增规则：模板注入
('模板注入-Jinja2', '检测Jinja2模板注入', '\{\{.*\}\}|\{%.*%\}|\{#.*#\}', 'high', 'template_injection'),
('模板注入-PHP', '检测PHP模板注入', '<\?php.*\?>|<\?=.*\?>', 'high', 'template_injection'),

-- 新增规则：认证绕过
('认证绕过-空密码', '检测空密码尝试', 'password=|passwd=|pwd=|admin=|root=', 'medium', 'auth_bypass'),
('认证绕过-SQL注入', '检测认证SQL注入', 'admin.*OR.*1=1|admin.*OR.*1=1--|admin.*OR.*1=1#', 'high', 'auth_bypass'),
('认证绕过-弱密码', '检测常见弱密码', 'admin|password|123456|qwerty|letmein|welcome', 'low', 'auth_bypass'),

-- 新增规则：暴力破解检测
('暴力破解-登录尝试', '检测登录暴力破解', 'login|signin|auth|authenticate', 'medium', 'brute_force'),
('暴力破解-参数爆破', '检测参数爆破攻击', 'id=\d+|user=\w+|page=\d+', 'low', 'brute_force'),

-- 新增规则：信息泄露
('信息泄露-错误信息', '检测详细的错误信息泄露', 'error|exception|stack trace|debug|warning', 'medium', 'info_disclosure'),
('信息泄露-版本信息', '检测版本信息泄露', 'version|build|release|v\d+\.\d+', 'low', 'info_disclosure'),
('信息泄露-路径泄露', '检测路径信息泄露', '/var/www/|/home/|/usr/local/|C:\\', 'medium', 'info_disclosure'),

-- 新增规则：恶意文件上传
('文件上传-危险扩展', '检测危险文件上传', '\.php|\.jsp|\.asp|\.aspx|\.exe|\.bat|\.sh|\.pl|\.py', 'high', 'file_upload'),
('文件上传-双扩展名', '检测双扩展名绕过', '\.(php|jsp|asp|aspx|exe|bat|sh|pl|py)\.[a-zA-Z]+$', 'high', 'file_upload'),
('文件上传-空字节', '检测空字节绕过', '%00|\\x00|\\0', 'high', 'file_upload'),

-- 新增规则：HTTP请求走私
('HTTP走私-头部注入', '检测HTTP请求走私', 'Content-Length.*Content-Length|Transfer-Encoding.*Content-Length', 'high', 'http_smuggling'),
('HTTP走私-分块编码', '检测分块编码走私', 'Transfer-Encoding:\s*chunked', 'medium', 'http_smuggling'),

-- 新增规则：缓存投毒
('缓存投毒-头部操作', '检测缓存投毒攻击', 'X-Forwarded-Host|X-Forwarded-Proto|X-Original-URL', 'medium', 'cache_poisoning'),
('缓存投毒-参数污染', '检测参数污染攻击', 'X-Forwarded-For|X-Real-IP|X-Client-IP', 'low', 'cache_poisoning'),

-- 新增规则：业务逻辑漏洞
('业务逻辑-水平越权', '检测水平越权访问', 'user_id=|account_id=|order_id=|id=\d+', 'medium', 'business_logic'),
('业务逻辑-垂直越权', '检测垂直越权访问', 'admin|manager|superuser|root', 'high', 'business_logic'),
('业务逻辑-条件竞争', '检测条件竞争攻击', 'concurrent|race|condition', 'medium', 'business_logic'),

-- 新增规则：API滥用
('API滥用-速率限制', '检测API速率限制绕过', 'api/|rest/|graphql/', 'low', 'api_abuse'),
('API滥用-参数篡改', '检测API参数篡改', 'price=|amount=|quantity=|discount=', 'medium', 'api_abuse'),

-- 新增规则：WebShell检测
('WebShell-常见特征', '检测WebShell特征', 'eval\(|exec\(|system\(|shell_exec\(|passthru\(', 'high', 'webshell'),
('WebShell-文件操作', '检测WebShell文件操作', 'file_get_contents\(|file_put_contents\(|fopen\(|fwrite\(', 'medium', 'webshell'),
('WebShell-网络连接', '检测WebShell网络连接', 'fsockopen\(|curl_exec\(|file_get_contents\(http', 'high', 'webshell'),

-- 新增规则：加密货币挖矿
('挖矿-常见矿池', '检测加密货币挖矿', 'pool\.|stratum\+tcp://|xmr\.|monero|ethereum', 'high', 'mining'),
('挖矿-挖矿脚本', '检测挖矿脚本', 'miner\.js|coinhive|cryptoloot|minero', 'high', 'mining'),

-- 新增规则：恶意重定向
('重定向-开放重定向', '检测开放重定向漏洞', 'redirect=|url=|next=|target=|goto=|return=', 'medium', 'redirect'),
('重定向-钓鱼链接', '检测钓鱼重定向', 'login\.|signin\.|verify\.|confirm\.', 'high', 'phishing'),

-- 新增规则：会话管理
('会话-会话固定', '检测会话固定攻击', 'session=|sid=|token=', 'medium', 'session'),
('会话-会话劫持', '检测会话劫持', 'PHPSESSID|JSESSIONID|ASP\.NET_SessionId', 'low', 'session'),

-- 新增规则：输入验证绕过
('输入验证-编码绕过', '检测编码绕过', 'urlencode|urldecode|base64|hex|rot13', 'medium', 'bypass'),
('输入验证-大小写绕过', '检测大小写绕过', '[Ss][Ee][Ll][Ee][Cc][Tt]|[Uu][Nn][Ii][Oo][Nn]', 'low', 'bypass'),
('输入验证-注释绕过', '检测注释绕过', '--|#|/\*|\*/|<!--|-->', 'medium', 'bypass'),

-- 新增规则：DoS攻击检测
('DoS-慢速攻击', '检测慢速DoS攻击', 'slow|timeout|delay|sleep', 'medium', 'dos'),
('DoS-大量请求', '检测大量请求攻击', 'burst|flood|spam|mass', 'high', 'dos'),

-- 新增规则：恶意爬虫
('爬虫-恶意爬虫', '检测恶意爬虫', 'bot|crawler|spider|scraper', 'low', 'crawler'),
('爬虫-搜索引擎', '检测搜索引擎爬虫', 'googlebot|bingbot|baiduspider|yandex', 'low', 'crawler'),

-- 新增规则：移动端攻击
('移动端-恶意应用', '检测移动端恶意应用', 'android|ios|mobile|app', 'low', 'mobile'),
('移动端-设备指纹', '检测设备指纹收集', 'device|fingerprint|imei|mac', 'low', 'mobile'),

-- 新增规则：IoT设备攻击
('IoT-默认凭据', '检测IoT默认凭据', 'admin:admin|root:root|user:user', 'medium', 'iot'),
('IoT-设备发现', '检测IoT设备发现', 'upnp|ssdp|mdns|bonjour', 'low', 'iot'),

-- 新增规则：区块链相关
('区块链-智能合约', '检测智能合约攻击', 'solidity|ethereum|smart contract', 'medium', 'blockchain'),
('区块链-钱包攻击', '检测钱包攻击', 'wallet|private key|seed phrase', 'high', 'blockchain'),

-- 新增规则：AI/ML攻击
('AI-模型投毒', '检测AI模型投毒', 'training|model|ml|ai|neural', 'medium', 'ai_attack'),
('AI-对抗样本', '检测对抗样本攻击', 'adversarial|perturbation|noise', 'medium', 'ai_attack'),

-- 新增规则：容器安全
('容器-逃逸攻击', '检测容器逃逸', 'docker|container|kubernetes|pod', 'high', 'container'),
('容器-镜像投毒', '检测容器镜像投毒', 'registry|image|pull|push', 'medium', 'container'),

-- 新增规则：云安全
('云-配置错误', '检测云配置错误', 'aws|azure|gcp|cloud', 'medium', 'cloud'),
('云-权限提升', '检测云权限提升', 'iam|role|policy|permission', 'high', 'cloud'),

-- 新增规则：零日漏洞
('零日-未知攻击', '检测未知攻击模式', 'unknown|zero-day|exploit', 'high', 'zero_day'),
('零日-异常行为', '检测异常行为模式', 'anomaly|unusual|suspicious', 'medium', 'zero_day');
