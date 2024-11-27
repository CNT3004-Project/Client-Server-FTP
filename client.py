import socket
import os

IP = socket.gethostbyname(socket.gethostname())
PORT = 4455
ADDR = (IP, PORT)
FORMAT = "utf-8"
SIZE = 1024
FOLDER = "data"

def upload_file(client, filename):
    file_path = os.path.join(FOLDER, filename)
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext == ".txt" and file_size > 25 * 1024 * 1024:
            print("[ERROR] Text files must be at most 25MB.")
            return
        elif file_ext in [".mp3", ".wav"] and file_size > 1 * 1024 * 1024 * 1024:
            print("[ERROR] Audio files must be at most 1GB.")
            return
        elif file_ext in [".mp4", ".mkv", ".avi"] and file_size > 2 * 1024 * 1024 * 1024:
            print("[ERROR] Video files must be at most 2GB.")
            return

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
        if filename.lower().endswith(".txt"):
            with open(file_path, "w") as file:
                bytes_received = 0
                while bytes_received < file_size:
                    chunk = client.recv(SIZE)
                    file.write(chunk)
                    bytes_received += len(chunk)
            print(f"[SUCCESS] {filename} downloaded.")
        else:
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

def delete_file(client, filename):
    client.send(f"DELETE:{filename}".encode(FORMAT))
    response = client.recv(SIZE).decode(FORMAT)
    print(response)

def subfolder(client):
    action = input("Enter command (CREATE OR DELETE): ").strip().upper()
    if action not in ["CREATE", "DELETE"]:
        print("[ERROR] Invalid Action, Either CREATE or DELETE")
        return
    subfolder_name = input("Enter subfolder name: ").strip()
    client.send(f"SUBFOLDER:{action}:{subfolder_name}".encode(FORMAT))
    response = client.recv(SIZE).decode(FORMAT)
    print(response)

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)

    if not os.path.exists(FOLDER):
        os.makedirs(FOLDER)

    try:
        # Receive server prompt for username
        server_response = client.recv(SIZE).decode(FORMAT)
        print(server_response)
        username = input("Enter your username: ").strip()
        client.send(username.encode(FORMAT))

        # Process server response
        response = client.recv(SIZE).decode(FORMAT)
        print(f"[SERVER]: {response}")

        # Handle server's response
        if response.startswith("[INFO] LOGIN:"):
            password = input("Enter your password: ").strip()
            client.send(password.encode(FORMAT))
            login_response = client.recv(SIZE).decode(FORMAT)

            if login_response.startswith("[SUCCESS]"):
                print(login_response)
            else:
                print(f"[ERROR] {login_response}")
                return  # Stop execution if login fails

        elif response.startswith("[ERROR] Username not found"):
            choice = input("Do you want to create an account? (yes/no): ").strip().lower()
            client.send(choice.encode(FORMAT))

            # Handle account creation process
            if choice == "yes":
                new_password_prompt = client.recv(SIZE).decode(FORMAT)
                print(new_password_prompt)  # Server asks for the new password
                new_password = input("Enter a new password: ").strip()
                client.send(new_password.encode(FORMAT))

                # Receive account creation confirmation
                account_creation_response = client.recv(SIZE).decode(FORMAT)
                print(account_creation_response)
                if account_creation_response.startswith("[SUCCESS]"):
                    print("Please restart the program to log in with your new account.")
                    return  # End execution after account creation
                else:
                    print(f"[ERROR] {account_creation_response}")
                    return
            else:
                print("[INFO] Exiting...")
                return

        # Command loop
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
            elif command == "QUIT":
                client.send("QUIT".encode(FORMAT))
                break
            else:
                print("[ERROR] Invalid command.")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
