import socket
import os

IP = socket.gethostbyname(socket.gethostname())
PORT = 4455
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
FOLDER = "server_data"  # Folder to store files

#manages communication with the connected client
def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    #infinite loop to handle client requests until client disconnects
    while True:
        # Receive client request
        request = conn.recv(SIZE).decode(FORMAT)
        if not request:
            break

        print(f"[REQUEST] {addr}: {request}")
        command, *args = request.split(":")
        #reads incoming file and then writes the indcoming chunks of data to a file in server_data
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
        #sends requested file to client
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
        #lists all files in server_data
        elif command == "LIST":
            files = os.listdir(FOLDER)
            conn.send("\n".join(files).encode(FORMAT))
        #breaks the loop
        elif command == "QUIT":
            break

    conn.close()
    print(f"[DISCONNECTED] {addr} disconnected.")


def main():
    print("[STARTING] Server is starting.")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    #makes server_data if it doesnt exist
    if not os.path.exists(FOLDER):
        os.makedirs(FOLDER)

    server.listen() #listens for client connections
    print("[LISTENING] Server is listening.")

    while True:
        conn, addr = server.accept() #accepts connections
        handle_client(conn, addr)


if __name__ == "__main__":
    main()
