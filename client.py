import socket
import os

IP = socket.gethostbyname(socket.gethostname())
PORT = 4455
ADDR = (IP, PORT)
FORMAT = "utf-8"
SIZE = 1024
FOLDER = "data"  # Folder to send files from

def main():
    """ Start a TCP socket. """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        """ Connect to the server. """
        client.connect(ADDR)

        """ Get list of files in the folder. """
        files = os.listdir(FOLDER)

        for file_name in files:
            file_path = os.path.join(FOLDER, file_name)

            if os.path.isfile(file_path):  # Ensure it's a file
                """ Open and read the file data. """
                with open(file_path, "r") as file:
                    data = file.read()

                """ Send the filename and receive acknowledgment. """
                client.send(file_name.encode(FORMAT))
                msg = client.recv(SIZE).decode(FORMAT)
                print(f"[SERVER]: {msg}")

                """ Send the file data and receive acknowledgment. """
                client.send(data.encode(FORMAT))
                msg = client.recv(SIZE).decode(FORMAT)
                print(f"[SERVER]: {msg}")

        """ Notify the server that all files have been sent. """
        client.send("DONE".encode(FORMAT))

    except Exception as e:
        print(f"[ERROR]: {e}")

    finally:
        """ Close the connection. """
        client.close()

if __name__ == "__main__":
    main()
