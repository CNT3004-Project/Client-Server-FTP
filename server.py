import socket
import os

IP = socket.gethostbyname(socket.gethostname())
PORT = 4455
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
FOLDER = "server_data"  # Folder to store files


def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")

    while True:
        # Receive client request
        request = conn.recv(SIZE).decode(FORMAT)
        if not request:
            break

        print(f"[REQUEST] {addr}: {request}")
        command, *args = request.split(":")

        if command == "UPLOAD":
            filename, file_size = args
            file_size = int(file_size)
            file_path = os.path.join(FOLDER, filename)

            with open(file_path, "wb") as file:
                bytes_received = 0
                while bytes_received < file_size:
                    chunk = conn.recv(SIZE)
                    if not chunk:
                        break
                    file.write(chunk)
                    bytes_received += len(chunk)

            conn.send(f"[SUCCESS] {filename} uploaded.".encode(FORMAT))

        elif command == "DOWNLOAD":
            filename = args[0]
            file_path = os.path.join(FOLDER, filename)

            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                conn.send(f"{file_size}".encode(FORMAT))
                with open(file_path, "rb") as file:
                    while chunk := file.read(SIZE):
                        conn.send(chunk)
            else:
                conn.send("[ERROR] File not found.".encode(FORMAT))

        elif command == "LIST":
            files = os.listdir(FOLDER)
            conn.send("\n".join(files).encode(FORMAT))

        elif command == "QUIT":
            break

    conn.close()
    print(f"[DISCONNECTED] {addr} disconnected.")


def main():
    print("[STARTING] Server is starting.")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)

    if not os.path.exists(FOLDER):
        os.makedirs(FOLDER)

    server.listen()
    print("[LISTENING] Server is listening.")

    while True:
        conn, addr = server.accept()
        handle_client(conn, addr)


if __name__ == "__main__":
    main()
