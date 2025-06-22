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
    FOREIGN KEY (rule_id) REFERENCES rules (id)
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
('可疑User-Agent', '检测可疑的User-Agent字符串', 'python-requests|curl|wget|nmap|masscan|zmap', 'low', 'scanning');
