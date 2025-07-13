# 混合威胁检测与蜜罐系统

---

## 一、项目概述

本系统融合了基于大语言模型（LLM）的智能入侵检测、SSH蜜罐与日志管理三大模块，旨在模拟真实服务器环境，吸引并分析潜在攻击者行为，实现自动化威胁检测、响应与可视化监控。

- **蜜罐系统**：模拟SSH等服务，诱捕攻击者并记录行为。
- **入侵检测系统（IDS）**：实时监听HTTP/SSH流量，利用LLM智能分析威胁。
- **日志系统**：集中管理、分析和可视化各类安全日志。

---

## 二、项目结构

```
llm/
├── src/                    # 源代码目录
│   ├── honeypot/          # 蜜罐模块
│   │   ├── honeypot_ssh.py
│   │   ├── honeypot_http.py
│   │   ├── honeypot_mysql.py
│   │   ├── honeypot_pop3.py
│   │   ├── server.py
│   │   └── mysql/         # MySQL蜜罐子模块
│   ├── ids/               # 入侵检测系统
│   │   ├── app/           # Web应用
│   │   ├── templates/     # 网页模板
│   │   ├── data/          # 数据文件
│   │   └── run.py         # 启动脚本
│   ├── log_manager/       # 日志管理
│   │   ├── log_manager.py
│   │   ├── log_parser.py
│   │   ├── templates/     # 网页模板
│   │   ├── static/        # 静态文件
│   │   └── logs/          # 日志文件
│   ├── utils/             # 工具模块
│   │   └── 可视化.py
│   └── tests/             # 测试模块
├── config/                 # 配置文件
│   ├── configSSH.yml
│   ├── configHTTP.yml
│   ├── configMySQL.yml
│   ├── configPOP3.yml
│   ├── host_key
│   └── db_credentials.env
├── docs/                   # 文档
├── requirements.txt         # 依赖列表
├── install_dependencies.bat # Windows安装脚本
├── install_dependencies.sh  # Linux/Mac安装脚本
```

---

## 三、环境准备与依赖安装

### 1. Windows用户
- 双击 `install_dependencies.bat` 自动安装依赖

### 2. Linux/Mac用户
- 赋予脚本执行权限并运行：
  ```bash
  chmod +x install_dependencies.sh
  ./install_dependencies.sh
  ```

### 3. 手动安装
  ```bash
  pip install -r requirements.txt
  ```

---

## 四、快速启动

### 分别启动

#### 1. 启动IDS系统
```bash
python src/ids/run.py
```

#### 2. 启动蜜罐系统
```bash
python src/honeypot/server.py
```

### 访问地址
- **Web管理界面**: http://localhost:5000
- **默认账号**: admin / admin123

---

## 五、主要功能

### 1. 实时监控与可视化
- 仪表盘：系统状态总览
- 事件日志：检测到的安全事件
- 实时流量监控
- Token使用与LLM分析状态

### 2. LLM智能分析
- HTTP威胁检测（SQL注入、XSS等）
- SSH暴力破解检测
- 自动封禁恶意IP
- Token用量监控与自动流控

### 3. 日志管理
- 集中存储与分析蜜罐、IDS等日志
- 支持多种数据库（如SQLite）
- Web界面可视化查询

---

## 六、配置说明

### 1. API密钥配置
- 编辑 `src/ids/app/api/auth.py`：
  ```python
  KIMI_API_KEY = "你的Kimi API密钥"
  ```

### 2. 网络接口配置
- 系统自动检测，如需手动指定，编辑相关配置文件

### 3. Token限制
- 编辑相关配置文件调整Token限制

---

## 七、常见问题与故障排查

### 1. 权限错误
- Windows：以管理员身份运行命令行
- Linux/Mac：使用sudo

### 2. 网络接口检测失败
- 检查网络配置
- 编辑相关配置文件手动指定接口

### 3. 依赖缺失
- 重新运行依赖安装脚本或 `pip install -r requirements.txt`

### 4. API调用失败
- 检查网络连接与API密钥

### 5. Token用完
- 等待次日自动重置，或调整Token限制

---

## 八、安全建议

1. 定期更换API密钥，避免泄露
2. 监控Token用量，防止超额
3. 定期检查系统日志，及时处理威胁
4. 仅在受信任网络环境中运行
5. 限制数据库与日志文件访问权限

---

## 九、调试与测试

- 启用详细日志：
  ```bash
  python -u start_ids.py
  ```

---

## 十、注意事项

- 本系统仅供学习与研究使用，禁止用于生产环境！
- 如有问题或建议，请联系开发团队。 