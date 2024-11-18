import socket
import os

IP = socket.gethostbyname(socket.gethostname())
PORT = 4455
ADDR = (IP, PORT)
FORMAT = "utf-8"
SIZE = 1024
FOLDER = "data"  # Folder for client files
#uploads a file
def upload_file(client, filename):
    file_path = os.path.join(FOLDER, filename) #constructs filepath
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        file_ext = os.path.splitext(filename)[1].lower()
        #warn user about file constraints
        if file_ext == ".txt" and file_size > 25 * 1024 * 1024:
            print("[ERROR] Text files must be at least 25 MB.")
            return
        elif file_ext in [".mp3", ".wav"] and file_size > 1 * 1024 * 1024 * 1024:
            print("[ERROR] Audio files must be at least 1 GB.")
            return
        elif file_ext in [".mp4", ".mkv", ".avi"] and file_size > 2 * 1024 * 1024 * 1024:
            print("[ERROR] Video files must be at least 2 GB.")
            return

        #continue file upload
        client.send(f"UPLOAD:{filename}:{file_size}".encode(FORMAT)) #sends upload request with file size and name
        with open(file_path, "rb") as file:
            while chunk := file.read(SIZE): #sends file in chunks
                client.send(chunk)
        print(client.recv(SIZE).decode(FORMAT))
    else:
        print("[ERROR] File not found.")
#downloads a file
def download_file(client, filename):
    client.send(f"DOWNLOAD:{filename}".encode(FORMAT)) #sends download request with file name
    response = client.recv(SIZE).decode(FORMAT)
    if response.isdigit():
        file_size = int(response) #number response from server is the file size
        file_path = os.path.join(FOLDER, filename) #prepares file path
        if filename.lower().endswith(".txt"): #writes txt files using UTF-8
            with open(file_path, "w") as file:
                bytes_received = 0
                while bytes_received < file_size:
                    chunk = client.recv(SIZE)
                    file.write(chunk)  # writes the chunk of data into the file
                    bytes_received += len(chunk)
            print(f"[SUCCESS] {filename} downloaded.")
        else: #used for everything else but txt files, uses binary
            with open(file_path, "wb") as file:
                bytes_received = 0
                while bytes_received < file_size:
                    chunk = client.recv(SIZE)
                    file.write(chunk) #writes the chunk of data into the file
                    bytes_received += len(chunk)
            print(f"[SUCCESS] {filename} downloaded.")
    else:
        print(response)
#lists files in server
def list_files(client):
    client.send("LIST".encode(FORMAT)) #sends list command to server
    files = client.recv(SIZE).decode(FORMAT)
    print("[FILES ON SERVER]:")
    print(files)

def delete_file(client, filename):
    client.send(f"DELETE:{filename}".encode(FORMAT))#send delete request
    response = client.recv(SIZE).decode(FORMAT)
    print(response)

def subfolder(client):
    action = input("Enter command (CREATE OR DELETE): ").strip().upper()
    if action not in["CREATE", "DELETE"]:
        print("[ERROR] Invalid Action, Either CREATE or DELETE")
        return
    subfolder_name = input("Enter subfolder name: ").strip()
    client.send(f"SUBFOLDER:{action}:{subfolder_name}".encode(FORMAT))  # send subfolder creation request
    response = client.recv(SIZE).decode(FORMAT)
    print(response)

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #creates a socket
    client.connect(ADDR)

    while True:
        command = input("Enter command (UPLOAD, DOWNLOAD, DELETE, SUBFOLDER, LIST, QUIT): ").strip().upper()
        if command == "UPLOAD":
            filename = input("Enter filename to upload: ").strip()
            upload_file(client, filename)
        elif command == "DOWNLOAD":
            filename = input("Enter filename to download: ").strip()
            download_file(client, filename)
        elif command == "LIST":
            list_files(client)
        elif command == "DELETE":
            filename = input("Enter filename to delete: ").strip()
            delete_file(client, filename)
        elif command == "SUBFOLDER":
            subfolder(client)
        elif command == "QUIT": #terminates connection
            client.send("QUIT".encode(FORMAT))
            break
        else:
            print("[ERROR] Invalid command.")

    client.close()

if __name__ == "__main__":
    main()
