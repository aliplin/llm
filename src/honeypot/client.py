import argparse
import socket
import yaml

def read_arguments():
    parser = argparse.ArgumentParser(description='Your script description')
    parser.add_argument('-c', '--config', required=True, help='Path to config file (yaml)')
    args = parser.parse_args()
    return args.config

if __name__ == "__main__":
    config_path = read_arguments()
    # Read config file
    with open(config_path, 'r', encoding="utf-8") as file:
        identity = yaml.safe_load(file)
    identity = identity['personality']
    port = int(identity.get('port', 5656))

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('localhost', port))

    try:
        # 接收服务端的初始响应
        response = client.recv(16384)
        output = response.decode()
        print(output)

        while True:
            user_input = input()
            if user_input.lower() in ['exit', 'quit']:
                break
            client.send(user_input.encode())
            response = client.recv(16384)
            output = response.decode()
            print(output)
    except KeyboardInterrupt:
        print("Client closed by user.")
    finally:
        client.close()
    