import asyncio
import signal
from llm.mysql.protocol import start_mysql_server
from llm.mysql.protocol import OK, ERR, EOF
from llm.mysql.protocol import HandshakeV10, HandshakeResponse41
from llm.mysql.protocol.query import ColumnDefinition, ColumnDefinitionList, ResultSet

# 处理SIGINT信号
signal.signal(signal.SIGINT, signal.SIG_DFL)


async def handle_server(server_reader, server_writer):
    """处理客户端连接的核心函数"""
    # 发送握手包
    handshake = HandshakeV10()
    handshake.write(server_writer)
    print(f"新连接: {server_writer.get_extra_info('peername')[:2]}")
    await server_writer.drain()

    # 读取客户端响应
    handshake_response = await HandshakeResponse41.read(server_reader.packet(), handshake.capability)
    username = handshake_response.user
    print(f"登录用户名: {username.decode('ascii')}")

    # 发送认证成功响应
    capability = handshake_response.capability_effective
    result = OK(capability, handshake.status)
    result.write(server_writer)
    await server_writer.drain()

    # 主命令处理循环
    while True:
        server_writer.reset()
        packet = server_reader.packet()
        try:
            cmd = (await packet.read(1))[0]  # 读取命令字节
        except Exception:
            return  # 连接断开

        query = await packet.read()
        if query:
            query = query.decode('ascii')

        # 命令处理逻辑
        if cmd == 1:  # COM_QUIT
            print("客户端请求断开连接")
            return
        elif cmd == 3:  # COM_QUERY
            print(f"收到查询: {query}")

            if 'SHOW VARIABLES' in query.upper():
                # 处理SHOW VARIABLES查询
                print("返回模拟系统变量")
                ColumnDefinitionList((ColumnDefinition('Variable_name'), ColumnDefinition('Value'))).write(
                    server_writer)
                EOF(capability, handshake.status).write(server_writer)
                ResultSet(("version", "8.0.0-mysqlfake")).write(server_writer)
                ResultSet(("max_allowed_packet", "67108864")).write(server_writer)
                result = EOF(capability, handshake.status)
            elif 'SELECT' in query.upper():
                # 处理SELECT查询
                print("返回模拟查询结果")
                ColumnDefinitionList((ColumnDefinition('id'), ColumnDefinition('name'))).write(server_writer)
                EOF(capability, handshake.status).write(server_writer)
                ResultSet(("1", "test_record")).write(server_writer)
                result = EOF(capability, handshake.status)
            else:
                # 其他查询返回成功
                result = OK(capability, handshake.status)
        else:
            # 未知命令返回错误
            result = ERR(capability)
            print(f"未知命令: {cmd}")

        # 发送响应
        result.write(server_writer)
        await server_writer.drain()


if __name__ == "__main__":
    # 创建Windows专用事件循环
    loop = asyncio.ProactorEventLoop()  # 关键修改：适配Windows
    asyncio.set_event_loop(loop)

    print("启动MySQL模拟服务器 (端口: 3306)...")
    server = start_mysql_server(handle_server, host='0.0.0.0', port=3306)
    loop.create_task(server)

    try:
        loop.run_forever()  # 使用ProactorEventLoop运行
    except KeyboardInterrupt:
        print("服务器已停止")
    finally:
        loop.close()