import socket
import os

IP = socket.gethostbyname(socket.gethostname())
PORT = 4455
ADDR = (IP, PORT)
FORMAT = "utf-8"
SIZE = 1024
FOLDER = "data"  # Folder for client files

def upload_file(client, filename):
    file_path = os.path.join(FOLDER, filename)
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        client.send(f"UPLOAD:{filename}:{file_size}".encode(FORMAT))
        with open(file_path, "rb") as file:
            while chunk := file.read(SIZE):
                client.send(chunk)
        print(client.recv(SIZE).decode(FORMAT))
    else:
        print("[ERROR] File not found.")

def download_file(client, filename):
    client.send(f"DOWNLOAD:{filename}".encode(FORMAT))
    response = client.recv(SIZE).decode(FORMAT)
    if response.isdigit():
        file_size = int(response)
        file_path = os.path.join(FOLDER, filename)
        with open(file_path, "wb") as file:
            bytes_received = 0
            while bytes_received < file_size:
                chunk = client.recv(SIZE)
                file.write(chunk)
                bytes_received += len(chunk)
        print(f"[SUCCESS] {filename} downloaded.")
    else:
        print(response)

def list_files(client):
    client.send("LIST".encode(FORMAT))
    files = client.recv(SIZE).decode(FORMAT)
    print("[FILES ON SERVER]:")
    print(files)

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)

    while True:
        command = input("Enter command (UPLOAD, DOWNLOAD, LIST, QUIT): ").strip().upper()
        if command == "UPLOAD":
            filename = input("Enter filename to upload: ").strip()
            upload_file(client, filename)
        elif command == "DOWNLOAD":
            filename = input("Enter filename to download: ").strip()
            download_file(client, filename)
        elif command == "LIST":
            list_files(client)
        elif command == "QUIT":
            client.send("QUIT".encode(FORMAT))
            break
        else:
            print("[ERROR] Invalid command.")

    client.close()

if __name__ == "__main__":
    main()
