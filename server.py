import socket
import os

IP = socket.gethostbyname(socket.gethostname())
PORT = 4455
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
FOLDER = "server_data"  # Folder to save files


def main():
    """ Start a TCP socket. """
    print("[STARTING] Server is starting.")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    """ Bind the IP and PORT to the server. """
    server.bind(ADDR)

    """ Create folder if it doesn't exist. """
    if not os.path.exists(FOLDER):
        os.makedirs(FOLDER)

    """ Server is listening. """
    server.listen()
    print("[LISTENING] Server is listening.")

    while True:
        """ Accept a connection from the client. """
        conn, addr = server.accept()
        print(f"[NEW CONNECTION] {addr} connected.")

        while True:
            """ Receive the filename. """
            filename = conn.recv(SIZE).decode(FORMAT)

            if filename == "DONE":
                print("[DONE] All files received.")
                break

            print(f"[RECV] Receiving the file: {filename}")
            file_path = os.path.join(FOLDER, filename)

            """ Receive the file data. """
            with open(file_path, "w") as file:
                data = conn.recv(SIZE).decode(FORMAT)
                file.write(data)

            conn.send("File received.".encode(FORMAT))

        """ Close the connection with the client. """
        conn.close()
        print(f"[DISCONNECTED] {addr} disconnected.")


if __name__ == "__main__":
    main()
