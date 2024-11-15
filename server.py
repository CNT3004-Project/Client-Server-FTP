import socket
import os

IP = socket.gethostbyname(socket.gethostname())
PORT = 4455
ADDR = (IP, PORT)
SIZE = 1024  # Make sure this matches the client-side SIZE
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
            """ Receive the metadata (filename and size). """
            metadata = conn.recv(SIZE).decode(FORMAT)
            if metadata == "DONE":
                print("[DONE] All files received.")
                break

            filename, file_size = metadata.split(":")
            file_size = int(file_size)
            print(f"[RECV] Receiving the file: {filename} ({file_size} bytes)")

            file_path = os.path.join(FOLDER, filename)

            """ Receive the file data in chunks. """
            with open(file_path, "wb") as file:
                bytes_received = 0
                while bytes_received < file_size:
                    chunk = conn.recv(SIZE)
                    if not chunk:
                        break
                    file.write(chunk)
                    bytes_received += len(chunk)
                    print(f"[DEBUG] Received {bytes_received}/{file_size} bytes")

                    # Calculate and display progress
                    progress = (bytes_received / file_size) * 100
                    print(f"[PROGRESS] {filename}: {progress:.2f}% received", end="\r")

            print(f"\n[COMPLETE] {filename} received successfully.")
            conn.send(f"{filename} received.".encode(FORMAT))

        """ Close the connection with the client. """
        conn.close()
        print(f"[DISCONNECTED] {addr} disconnected.")

if __name__ == "__main__":
    main()
