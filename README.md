# 混合威胁检测与蜜罐系统——整合说明文档

---

## 一、项目概述

本系统融合了基于大语言模型（LLM）的智能入侵检测、SSH蜜罐与日志管理三大模块，旨在模拟真实服务器环境，吸引并分析潜在攻击者行为，实现自动化威胁检测、响应与可视化监控。

- **蜜罐系统**：模拟SSH等服务，诱捕攻击者并记录行为。
- **入侵检测系统（IDS）**：实时监听HTTP/SSH流量，利用LLM智能分析威胁。
- **日志系统**：集中管理、分析和可视化各类安全日志。

---

## 二、项目结构

- `llm/`：蜜罐与相关配置、脚本
- `IDS/IDS_Project/`：入侵检测系统（含Web管理界面、LLM分析、数据库等）
- `Log Manager/`：日志管理与分析
- `requirements.txt`：依赖列表
- `install_dependencies.bat/.sh`：一键安装脚本

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

### 1. 检查网络接口（可选）
  ```bash
  cd IDS/IDS_Project
  python check_network.py
  ```

### 2. 运行系统测试（可选）
  ```bash
  python test_system.py
  ```

### 3. 启动IDS系统（推荐一键启动）
  ```bash
  python start_ids.py
  ```
  - 启动Web管理界面与LLM分析模块
  - 需管理员权限（Windows请用"以管理员身份运行"命令行，Linux/Mac用sudo）

#### 或分别启动：
  ```bash
  python app.py          # 启动Web界面
  python ids_llm.py      # 启动LLM分析
  ```

### 4. 启动蜜罐系统
  ```bash
  cd llm
  python server.py -e .env -c configSSH.yml
  # 或
  python llm/server.py -e llm/.env -c llm/configSSH.yml
  ```

### 5. 启动日志系统
  ```bash
  cd 'Log Manager'
  python log_manager.py
  ```

### 6. 访问Web管理界面
- 浏览器访问：http://localhost:5001
- 默认账号：admin  密码：admin123

### 7. 模拟攻击（可选）
  ```bash
  ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa root@127.0.0.1 -p 5656
  # ssh root@127.0.0.1 -p 5656
  ```

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
- 编辑 `IDS/IDS_Project/ids_llm.py`：
  ```python
  KIMI_API_KEY = "你的Kimi API密钥"
  ```

### 2. 网络接口配置
- 系统自动检测，如需手动指定，编辑 `ids_llm.py`：
  ```python
  #PVM_IP_ADDRESS, interface_name = get_interface_ip('你的接口名称')
  ```

### 3. Token限制
- 编辑 `ids_llm.py`：
  ```python
  #self.token_limit = 1000000  # 每日Token限制
  ```

---

## 七、常见问题与故障排查

### 1. 权限错误
- Windows：以管理员身份运行命令行
- Linux/Mac：使用sudo

### 2. 网络接口检测失败
- 运行 `python check_network.py` 检查接口
- 编辑 `ids_llm.py` 手动指定接口

### 3. 依赖缺失
- 重新运行依赖安装脚本或 `pip install -r requirements.txt`

### 4. API调用失败
- 检查网络连接与API密钥

### 5. Token用完
- 等待次日自动重置，或调整Token限制

### 6. 日志与数据库
- `ids.log`：系统运行日志
- `ids.db`：事件数据库
- `pending_reviews.json`：待审核事件

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
  python -u ids_llm.py
  ```
- 运行系统测试：
  ```bash
  python test_system.py
  ```

---

## 十、注意事项

- 本系统仅供学习与研究使用，禁止用于生产环境！
- 如有问题或建议，请联系开发团队。 