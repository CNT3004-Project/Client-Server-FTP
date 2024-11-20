import socket
import os
import threading
from cryptography.fernet import Fernet

IP = socket.gethostbyname(socket.gethostname())
PORT = 4455
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
FOLDER = "server_data"  # Folder to store files

# Generate and save a key if it doesn't exist
def load_create_key(file_path="server_key.key"):
    if not os.path.exists(file_path):
        key = Fernet.generate_key()
        with open(file_path, "wb") as key_file:
            key_file.write(key)
    else:
        with open(file_path, "rb") as key_file:
            key = key_file.read()
    return key

# Load the encryption key
key = load_create_key()
cipher = Fernet(key)

# Validate a password
server_password = "passkey"  # Hardcoded server password
stored_password = cipher.encrypt(server_password.encode())

def validate_password(input_password):
    try:
        decrypted_password = cipher.decrypt(stored_password).decode()
        return input_password == decrypted_password
    except Exception:
        return False

#manages communication with the connected client
def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    #Validate the passcode
    conn.send("PASSCODE: Enter the passcode: ".encode(FORMAT))
    passcode = conn.recv(SIZE).decode(FORMAT)
    if not validate_password(passcode):
        conn.send("[ERROR] Invalid passcode. Connection closing.".encode(FORMAT))
        conn.close()
        return

    conn.send("[SUCCESS] Passcode validated.".encode(FORMAT))

    #infinite loop to handle client requests until client disconnects
    while True:
        # Receive client request
        request = conn.recv(SIZE).decode(FORMAT)
        if not request:
            break

        print(f"[REQUEST] {addr}: {request}")
        command, *args = request.split(":")

        #Handles client upload
        if command == "UPLOAD":
            filename, file_size = args
            file_size = int(file_size)
            file_ext = os.path.splitext(filename)[1].lower()
            file_path = os.path.join(FOLDER, filename)

            #check file size constrants
            if file_ext == ".txt" and file_size > 25*1024*1024:
                conn.send("[ERROR] Text files must be at most 25MB, please split the text files up".encode(FORMAT))
            elif file_ext in [".mp3", ".wav"] and file_size > 1*1024*1024*1024:
                conn.send("[ERROR] Audio files must be at most 1GB, please split the audio files up".encode(FORMAT))
            elif file_ext in [".mp4", ".mkv", ".avi"] and file_size > 2*1024*1024*1024:
                conn.send("[ERROR] Video files must be at most 2GB, please split the video files up".encode(FORMAT))
            else:
                print(f"[INFO] Starting file upload: {filename} with size {file_size} bytes.")
                with open(file_path, "wb") as file:
                    bytes_received = 0
                    while bytes_received < file_size:
                        chunk = conn.recv(SIZE)
                        if not chunk:
                            print("[ERROR] No chunk received.")
                            break
                        file.write(chunk)
                        bytes_received += len(chunk)
                        print(f"[INFO] Received {bytes_received}/{file_size} bytes.")

                if bytes_received == file_size:
                    print(f"[INFO] File {filename} uploaded successfully.")
                    conn.send(f"[SUCCESS] {filename} uploaded.".encode(FORMAT))  # Confirm successful upload
                else:
                    print("[ERROR] File upload incomplete.")
                    conn.send("[ERROR] File upload failed.".encode(FORMAT))

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
            response = []
            for root, dirs, files in os.walk(FOLDER):
                #add subfolder to response
                for subfolder in dirs:
                    response.append(f"[DIR] {os.path.relpath(os.path.join(root, subfolder), FOLDER)}")
                # Add files to the response
                for file in files:
                    response.append(f"[FILE] {os.path.relpath(os.path.join(root, file), FOLDER)}")
            conn.send("\n".join(files).encode(FORMAT))
        #Deletes a file from server_data
        elif command == "DELETE":
            filename = args[0]
            file_path = os.path.join(FOLDER, filename)

            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"[INFO] {filename} was deleted from server.")
                conn.send(f"[SUCCESS] {filename} deleted.".encode(FORMAT))
            else:
                conn.send("[ERROR] file not found.".encode(FORMAT))
        #creates a subfolder in server_data
        elif command == "SUBFOLDER":
            action, subfolder_name = args
            subfolder_path = os.path.join(FOLDER, subfolder_name)

            if action =="CREATE":
                if not os.path.exists(subfolder_path):
                    os.makedirs(subfolder_path)#creates subfolder
                    conn.send(f"[SUCCESS] Subfolder '{subfolder_name}' created.".encode(FORMAT))
                else:
                    conn.send(f"[ERROR] Subfolder '{subfolder_name}' already exists".encode(FORMAT))
            if action == "DELETE":
                if os.path.exists(subfolder_path) and os.path.isdir(subfolder_path):
                    try:
                        os.rmdir(subfolder_path)
                        conn.send(f"[SUCCESS] Subfolder '{subfolder_name} deleted'".encode(FORMAT))
                    except OSError:
                        conn.send(f"[ERROR] '{subfolder_name}' is not empty".encode(FORMAT))
                else:
                    conn.send(f"[ERROR] Subfolder '{subfolder_name} does not exist'".encode(FORMAT))
            else:
                conn.send("[ERROR] invalid subfolder action".encode(FORMAT))

        #breaks the loop
        elif command == "QUIT":
            break

    conn.close()
    print(f"[DISCONNECTED] {addr} disconnected.")

def load_password():
    # Load encrypted password
    password_file = "password.txt"

    if os.path.exists(password_file):
        with open(password_file, "rb") as file:
            encrypted_password = file.read()
        return encrypted_password
    else:
        print("[INFO] No password exists.")
        return None

def store_password(password):
    #Encrypt and store the new pasword.
    encrypted_password = cipher.encrypt(password.encode())
    with open("password.txt", "wb") as file:
        file.write(encrypted_password)
        print("[INFO] Password has been stored and encrypted successfully.")
        return encrypted_password

def main():
    print("[STARTING] Server is starting.")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)

    global stored_password
    stored_password = load_password()
    if not stored_password:
        action = input("No password was found... Would you like to create a password? (yes/no): ").strip().lower()
        if action == "yes":
            new_password = input("Enter your new password: ").strip()
            stored_password = store_password(new_password)
        else:
            print("[ERROR] Password is required.\n[SYSTEM] Exiting.")
    else:
        print("[INFO] Existing password loaded successfully.")

    #makes server_data if it doesnt exist
    if not os.path.exists(FOLDER):
        os.makedirs(FOLDER)

    server.listen() #listens for client connections
    print("[LISTENING] Server is listening.")

    while True:
        conn, addr = server.accept() #accepts connections
        client_thread = threading.Thread(target=handle_client, args=(conn,addr)) #creates a thread to handle client
        client_thread.start()


if __name__ == "__main__":
    main()
