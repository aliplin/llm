# llm

## 项目概况

这是一个基于大语言模型（LLM）的SSH蜜罐系统，模拟真实服务器环境，吸引潜在攻击者并记录其行为。系统通过TikToken计算Token，使用Kimi API（兼容OpenAI API）生成响应，通过Paramiko实现SSH服务。

## 项目结构说明

- `requirements.txt`: 项目依赖列表
- `install_dependencies.bat`: Windows一键安装脚本
- `install_dependencies.sh`: Linux/Mac一键安装脚本



## 配置

### Windows用户

1. 双击运行 `install_dependencies.bat` 文件
2. 脚本会自动检查Python环境并安装所有依赖

### Linux/Mac用户

1. 给脚本添加执行权限：

   ```bash
   chmod +x install_dependencies.sh
   ```

2. 运行安装脚本：

   ```bash
   ./install_dependencies.sh
   ```

### 手动安装方法

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

## 项目启动

### 终端1

**启动蜜罐**

```bash
python llm/server.py -e .env -c configSSH.yml
```

### 终端2

**启动日志记录脚本**

```bash
python Log Manager/log_manager.py
```

### 终端3

```bash
python Log Manager/ssh_module.py
```

### 终端4

**登录ssh，模拟攻击者**

```bash
# ssh root@127.0.0.1 -p 5656 由于服务器只支持老旧的SSH-RSA 因此这个指令会报错
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa root@127.0.0.1 -p 5656
```

