import socket
import threading
import sys

def handle_client(client_socket, target_host, target_port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.connect((target_host, target_port))
    except Exception as e:
        client_socket.close()
        return

    def forward(src, dst):
        try:
            while True:
                data = src.recv(4096)
                if len(data) == 0:
                    break
                dst.send(data)
        except:
            pass
        finally:
            src.close()
            dst.close()

    threading.Thread(target=forward, args=(client_socket, server_socket)).start()
    threading.Thread(target=forward, args=(server_socket, client_socket)).start()

def main():
    listen_host = "0.0.0.0"
    listen_port = 6379
    target_host = "127.0.0.1"
    target_port = 6379

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((listen_host, listen_port))
    except Exception as e:
        print("Failed to bind:", e)
        sys.exit(1)
        
    server.listen(5)
    print(f"Proxying {listen_host}:{listen_port} to {target_host}:{target_port}")

    while True:
        try:
            client_socket, addr = server.accept()
            threading.Thread(target=handle_client, args=(client_socket, target_host, target_port)).start()
        except KeyboardInterrupt:
            break

if __name__ == '__main__':
    main()
