# 跨平台MySQL蜜罐

一个支持Linux和Windows客户端连接的MySQL蜜罐服务器，包含文件反制功能和可选的LLM响应。

## 🚀 功能特性

- ✅ **跨平台兼容**: 支持Linux和Windows客户端连接
- ✅ **文件反制**: 对敏感文件返回伪造内容
- ✅ **协议模拟**: 完整的MySQL协议模拟
- ✅ **LLM响应**: 可选的AI智能响应
- ✅ **日志记录**: 详细的会话和操作日志
- ✅ **易于使用**: 简单的启动脚本和配置
- ✅ **权限处理**: 自动处理端口权限问题
- ✅ **配置文件**: 支持YAML配置文件

## 📋 系统要求

- Python 3.7+
- 可选: OpenAI API密钥（用于LLM响应）
- 可选: PyYAML（用于配置文件支持）

## 🛠️ 安装依赖

```bash
# 基本依赖
pip install asyncio

# 可选：LLM响应功能
pip install openai

# 可选：配置文件支持
pip install pyyaml
```

## 🎯 快速开始

### 方法1: 使用LLM增强启动脚本（推荐）

#### 基本启动
```bash
# 使用配置文件启动
python start_mysql_llm.py

# 指定OpenAI API密钥
python start_mysql_llm.py --openai_key YOUR_API_KEY

# 仅模拟模式（无LLM）
python start_mysql_llm.py --no-llm
```

#### 高级配置
```bash
# 自定义端口
python start_mysql_llm.py --port 3307

# 指定配置文件
python start_mysql_llm.py --config my_config.yml

# 命令行参数覆盖配置
python start_mysql_llm.py --port 3307 --model gpt-4 --temp 0.1
```

### 方法2: 使用快速启动脚本

#### Windows
```cmd
# 模拟响应模式
start_test.bat

# LLM响应模式
start_test.bat YOUR_API_KEY
```

#### Linux
```bash
# 给脚本执行权限
chmod +x quick_start.sh

# 模拟响应模式
./quick_start.sh

# LLM响应模式
./quick_start.sh YOUR_API_KEY
```

### 方法3: 手动启动

#### 1. 基本启动（模拟响应）

```bash
python start_cross_platform_mysql.py
```

#### 2. 启用LLM响应

```bash
python start_cross_platform_mysql.py --openai_key YOUR_API_KEY
```

#### 3. 自定义配置

```bash
# 自定义端口
python start_cross_platform_mysql.py --port 3307

# 指定监听地址
python start_cross_platform_mysql.py --host 127.0.0.1 --port 3306

# 完整配置
python start_cross_platform_mysql.py \
    --openai_key YOUR_API_KEY \
    --port 3307 \
    --host 0.0.0.0 \
    --model gpt-3.5-turbo \
    --temp 0.2 \
    --max_tokens 256
```

## 🤖 LLM功能详解

### LLM响应机制

蜜罐支持以下查询类型的LLM响应：

#### 1. 预定义响应
- `SHOW VARIABLES` - 返回模拟系统变量
- `SHOW DATABASES` - 返回模拟数据库列表
- `SHOW TABLES` - 返回模拟表列表
- `SELECT VERSION()` - 返回模拟版本信息
- `SELECT 1` - 返回简单查询结果

#### 2. LLM智能响应
对于未知查询，蜜罐会调用LLM生成响应：

```sql
-- 这些查询会由LLM处理
SHOW PROCESSLIST;
SELECT * FROM users;
CREATE TABLE test_table (id INT);
INSERT INTO users VALUES (1, 'admin');
DROP DATABASE test_db;
```

#### 3. 系统提示词
LLM使用专门的系统提示词来生成MySQL格式的响应：

```
你是一个MySQL数据库服务器，需要以MySQL的格式响应客户端查询。

重要规则：
1. 对于SHOW命令，返回适当的列定义和结果集
2. 对于SELECT查询，返回模拟的数据
3. 对于CREATE/DROP/ALTER等DDL命令，返回成功消息
4. 对于INSERT/UPDATE/DELETE等DML命令，返回影响的行数
5. 对于不支持的查询，返回适当的错误信息
6. 始终以MySQL协议格式响应
```

### LLM配置选项

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--openai_key` | 无 | OpenAI API密钥 |
| `--model` | gpt-3.5-turbo | LLM模型 |
| `--temp` | 0.2 | LLM温度参数 |
| `--max_tokens` | 256 | LLM最大token数 |
| `--no-llm` | False | 禁用LLM功能 |

### 配置文件示例

```yaml
mysql_honeypot:
  server:
    host: "0.0.0.0"
    port: 3306
    auto_port: true
    
  llm:
    enabled: true
    model: "gpt-3.5-turbo"
    temperature: 0.2
    max_tokens: 256
    system_prompt: |
      你是一个MySQL数据库服务器...
```

## 🔧 配置选项

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--openai_key` | 无 | OpenAI API密钥（可选） |
| `--port` | 3306 | 监听端口 |
| `--host` | 0.0.0.0 | 监听地址 |
| `--model` | gpt-3.5-turbo | LLM模型 |
| `--temp` | 0.2 | LLM温度参数 |
| `--max_tokens` | 256 | LLM最大token数 |
| `--config` | config_mysql_llm.yml | 配置文件路径 |
| `--no-llm` | False | 禁用LLM功能 |

## 🧪 连接测试

### 测试蜜罐是否运行
```bash
# 自动检测可用端口
python test_connection.py

# 测试特定端口
python test_connection.py 3307
```

### 客户端连接测试

#### 使用MySQL命令行客户端
```bash
# 连接蜜罐（替换PORT为实际端口）
mysql -h localhost -P PORT -u root -p

# 示例：如果蜜罐运行在3307端口
mysql -h localhost -P 3307 -u root -p
```

#### 测试LLM功能
```sql
-- 连接后测试以下查询
SHOW DATABASES;
SHOW TABLES;
SELECT VERSION();
SELECT * FROM users;
CREATE TABLE test (id INT);
INSERT INTO test VALUES (1);
```

#### 使用Python连接
```python
import mysql.connector

# 连接蜜罐
conn = mysql.connector.connect(
    host='localhost',
    port=3307,  # 替换为实际端口
    user='root',
    password='password'
)

cursor = conn.cursor()
cursor.execute("SHOW DATABASES")
result = cursor.fetchall()
print(result)
```

## ⚠️ 权限问题解决方案

### 问题描述
在Windows/Linux上启动时可能遇到权限错误：
```
❌ 启动失败: [Errno 13] error while attempting to bind on address ('0.0.0.0', 3306): 权限被拒绝
```

### 解决方案

#### 1. 使用快速启动脚本（推荐）
脚本会自动检测权限并选择合适的端口：
- 管理员权限 → 使用3306端口
- 普通权限 → 使用3307端口

#### 2. 手动指定高端口
```bash
python start_mysql_llm.py --port 3307
```

#### 3. 以管理员身份运行

**Windows:**
```cmd
# 右键点击命令提示符，选择"以管理员身份运行"
python start_mysql_llm.py
```

**Linux:**
```bash
sudo python start_mysql_llm.py
```

#### 4. 自动端口选择
启动脚本会自动尝试以下端口：3306, 3307, 3308, 3309, 13306, 23306

## 📁 文件反制功能

蜜罐会自动检测并反制以下敏感文件的访问：

### Linux敏感文件
- `/etc/passwd`
- `/etc/shadow`
- `/root/.ssh/id_rsa`
- `/root/.bash_history`

### Windows敏感文件
- `C:/Windows/System32/config/SAM`
- `C:/Windows/System32/config/system`
- `C:/Windows/PFRO.log`

### 通用敏感文件
- `id_rsa`
- `id_dsa`
- `authorized_keys`

## 📝 日志记录

所有会话和操作都会记录到以下位置：

```
../Log Manager/logs/
├── logMySQL_[UUID]_[TIMESTAMP].txt    # 详细操作日志
└── historyMySQL_[UUID]_[TIMESTAMP].txt # 会话历史记录
```

### 日志类型

| 日志类型 | 说明 | 示例 |
|---------|------|------|
| `[CMD]` | 客户端命令 | `mysql> SHOW DATABASES;` |
| `[LLM_RESP]` | LLM响应 | `Query OK, 1 row affected` |
| `[LLM_ERROR]` | LLM错误 | `ERROR 2006: Connection failed` |
| `[FILE_READ]` | 文件读取尝试 | `尝试读取文件: /etc/passwd` |
| `[DEFAULT_RESP]` | 默认响应 | `Query OK, 0 rows affected` |

## 🧪 测试功能

运行兼容性测试：

```bash
python test_cross_platform.py
```

测试内容包括：
- Linux客户端连接测试
- Windows客户端连接测试
- 文件反制功能测试
- 协议兼容性测试

## 🔌 客户端连接示例

### Linux客户端

```bash
# 使用mysql命令行客户端
mysql -h 127.0.0.1 -P 3307 -u root -p

# 使用Python连接
import mysql.connector
conn = mysql.connector.connect(
    host='127.0.0.1',
    port=3307,  # 注意端口号
    user='root',
    password='password'
)
```

### Windows客户端

```cmd
# 使用mysql命令行客户端
mysql -h 127.0.0.1 -P 3307 -u root -p

# 使用MySQL Workbench或其他GUI客户端
# 连接参数：
# Host: 127.0.0.1
# Port: 3307 (或实际运行端口)
# Username: root
# Password: password
```

## 🎭 支持的查询类型

### 基本查询
- `SHOW VARIABLES` - 返回模拟系统变量
- `SHOW DATABASES` - 返回模拟数据库列表
- `SHOW TABLES` - 返回模拟表列表
- `SELECT VERSION()` - 返回模拟版本信息
- `SELECT 1` - 返回测试数据

### 文件读取查询
- `SELECT LOAD_FILE('/etc/passwd')` - 返回伪造的passwd内容
- `SELECT LOAD_FILE('C:/Windows/System32/config/SAM')` - 返回伪造的SAM内容

### LLM响应查询
当启用LLM时，所有其他查询都会通过AI生成响应：
- `SHOW PROCESSLIST` - LLM生成进程列表
- `SELECT * FROM users` - LLM生成用户数据
- `CREATE TABLE test` - LLM生成创建响应
- `INSERT INTO table` - LLM生成插入响应

## 🐛 故障排除

### 端口被占用
```bash
# 使用其他端口
python start_mysql_llm.py --port 3307
```

### 权限被拒绝
```bash
# 使用快速启动脚本（自动处理）
./quick_start.sh

# 或手动指定高端口
python start_mysql_llm.py --port 3307
```

### 连接被拒绝
```bash
# 检查防火墙设置
# 确保监听地址正确
python start_mysql_llm.py --host 0.0.0.0
```

### 客户端连接无响应
```bash
# 1. 检查蜜罐是否正在运行
python test_connection.py

# 2. 确认连接端口
# 查看启动时的端口信息

# 3. 使用正确的端口连接
mysql -h localhost -P 3307 -u root -p
```

### LLM功能异常
```bash
# 检查API密钥
# 安装openai库
pip install openai

# 检查网络连接
# 确认API密钥有效
```

### 常见错误及解决方案

| 错误信息 | 原因 | 解决方案 |
|---------|------|----------|
| `端口被占用` | 3306端口已被其他服务使用 | 使用 `--port 3307` 或 `start_test.bat` |
| `权限被拒绝` | 需要管理员权限绑定低端口 | 使用高端口或管理员权限运行 |
| `连接被拒绝` | 蜜罐未启动或端口错误 | 检查蜜罐状态，确认端口号 |
| `没有反应` | 客户端连接端口错误 | 使用 `test_connection.py` 检测正确端口 |
| `CharacterSet错误` | 客户端发送未知字符集值 | 已自动处理，使用默认utf8字符集 |
| `StreamReader错误` | 协议处理异常 | 检查MySQL协议兼容性 |
| `LLM响应失败` | API密钥无效或网络问题 | 检查API密钥和网络连接 |

### 字符集问题
如果遇到 `ValueError: X is not a valid CharacterSet` 错误，这是正常的。蜜罐会自动处理未知字符集值并使用默认的utf8字符集。这不会影响功能。

### 协议兼容性
蜜罐支持大多数MySQL客户端，包括：
- MySQL命令行客户端
- MySQL Workbench
- Navicat
- HeidiSQL
- Python mysql-connector
- 其他标准MySQL客户端

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

---

**注意**: 此蜜罐仅用于安全研究和教育目的，请勿用于非法活动。 