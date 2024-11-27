import socket
import os
import threading
from cryptography.fernet import Fernet
import json

IP = socket.gethostbyname(socket.gethostname())
PORT = 4455
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
FOLDER = "server_data"  # Folder to store files
USER_DB = "user_db.json"


def load_user_DB():
    if os.path.exists(USER_DB):
        try:
            with open(USER_DB, "r") as file:
                return json.load(file)
        except json.JSONDecodeError:
            print("[ERROR] Malformed user database. Initializing a new one.")
            return {}
    return {}


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

# Validate username and password
user_lock = threading.Lock()


def validate_user(username, password):
    with user_lock:
        if username in user_DB:
            stored_encrypted_password = user_DB[username]
            try:
                decrypted_password = cipher.decrypt(stored_encrypted_password.encode()).decode()
                return password == decrypted_password
            except Exception:
                return False
        elif username not in user_DB:
            # Handle account creation request
            conn.send("[ERROR] Username not found. Do you want to create an account? (yes/no): ".encode(FORMAT))
            response = conn.recv(SIZE).decode(FORMAT).strip().lower()

            if response == "yes":
                conn.send("[INFO] Enter a new password: ".encode(FORMAT))
                new_password = conn.recv(SIZE).decode(FORMAT)
                # Add user to the database if possible
                if add_user(username, new_password):
                    conn.send("[SUCCESS] Account created successfully. Please re-login.".encode(FORMAT))
                else:
                    conn.send("[ERROR] Username already exists. Connection closing.".encode(FORMAT))
                    return
            else:
                conn.send("[ERROR] Connection closing.".encode(FORMAT))
                return

    return False


# Add a new user
def add_user(username, password):
    if username in user_DB:
        return False
    encrypted_password = cipher.encrypt(password.encode()).decode()
    user_DB[username] = encrypted_password
    save_user_DB(user_DB)
    return True


# Save username to database
def save_user_DB(user_DB):
    with open(USER_DB, "w") as file:
        json.dump(user_DB, file)


user_DB = load_user_DB()

server_password = "passkey"  # Hardcoded server password
stored_password = cipher.encrypt(server_password.encode())


# Manages communication with the connected client
def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")

    try:
        # User login or signup
        conn.send("[INFO] LOGIN: Enter your username: ".encode(FORMAT))
        username = conn.recv(SIZE).decode(FORMAT).strip()
        print(f"[REQUEST] {addr}: {username}")  # Changed to print the username instead of request

        # Checking if username exists
        if username in user_DB:
            conn.send("[INFO] LOGIN: Enter your password: ".encode(FORMAT))
            password = conn.recv(SIZE).decode(FORMAT)
            if validate_user(username, password):
                conn.send("[SUCCESS] Login successful.".encode(FORMAT))
            else:
                conn.send("[ERROR] Incorrect password. Connection closing.".encode(FORMAT))
                return
        else:
            # Handle Account Creation
            conn.send("[ERROR] Username not found. Do you want to create an account? (yes/no): ".encode(FORMAT))
            response = conn.recv(SIZE).decode(FORMAT).strip().lower()

            if response == "yes":
                conn.send("[INFO] Enter a new password: ".encode(FORMAT))
                new_password = conn.recv(SIZE).decode(FORMAT)
                if add_user(username, new_password):
                    conn.send("[SUCCESS] Account created successfully. Please re-login.".encode(FORMAT))
                    return  # Immediately close connection after account creation
                else:
                    conn.send("[ERROR] Username already exists. Connection closing.".encode(FORMAT))
                    return
            else:
                conn.send("[ERROR] Connection closing.".encode(FORMAT))
                return

        # Now, after login or account creation, proceed with file commands
        while True:
            request = conn.recv(SIZE).decode(FORMAT).strip()
            if not request:
                break

            print(f"[REQUEST] {addr}: {request}")
            command, *args = request.split(":")

            # Handle file uploads
            if command == "UPLOAD":
                filename, file_size = args
                file_size = int(file_size)
                file_ext = os.path.splitext(filename)[1].lower()
                file_path = os.path.join(FOLDER, filename)

                # Check file size constraints
                if file_ext == ".txt" and file_size > 25 * 1024 * 1024:
                    conn.send("[ERROR] Text files must be at most 25MB.".encode(FORMAT))
                elif file_ext in [".mp3", ".wav"] and file_size > 1 * 1024 * 1024 * 1024:
                    conn.send("[ERROR] Audio files must be at most 1GB.".encode(FORMAT))
                elif file_ext in [".mp4", ".mkv", ".avi"] and file_size > 2 * 1024 * 1024 * 1024:
                    conn.send("[ERROR] Video files must be at most 2GB.".encode(FORMAT))
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
                        conn.send(f"[SUCCESS] {filename} uploaded.".encode(FORMAT))
                    else:
                        conn.send("[ERROR] File upload failed.".encode(FORMAT))

            elif command == "QUIT":
                break

            # Handle other commands (LIST, DELETE, SUBFOLDER, etc.)
            elif command == "LIST":
                response = []
                for root, dirs, files in os.walk(FOLDER):
                    for subfolder in dirs:
                        response.append(f"[DIR] {os.path.relpath(os.path.join(root, subfolder), FOLDER)}")
                    for file in files:
                        response.append(f"[FILE] {os.path.relpath(os.path.join(root, file), FOLDER)}")
                conn.send("\n".join(response).encode(FORMAT))

            elif command == "DELETE":
                filename = args[0]
                file_path = os.path.join(FOLDER, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    conn.send(f"[SUCCESS] {filename} deleted.".encode(FORMAT))
                else:
                    conn.send("[ERROR] File not found.".encode(FORMAT))

            elif command == "SUBFOLDER":
                action, subfolder_name = args
                subfolder_path = os.path.join(FOLDER, subfolder_name)

                if action == "CREATE":
                    if not os.path.exists(subfolder_path):
                        os.makedirs(subfolder_path)
                        conn.send(f"[SUCCESS] Subfolder '{subfolder_name}' created.".encode(FORMAT))
                    else:
                        conn.send(f"[ERROR] Subfolder '{subfolder_name}' already exists".encode(FORMAT))

                elif action == "DELETE":
                    if os.path.exists(subfolder_path) and os.path.isdir(subfolder_path):
                        try:
                            os.rmdir(subfolder_path)
                            conn.send(f"[SUCCESS] Subfolder '{subfolder_name}' deleted.".encode(FORMAT))
                        except OSError:
                            conn.send(f"[ERROR] '{subfolder_name}' is not empty".encode(FORMAT))
                    else:
                        conn.send(f"[ERROR] Subfolder '{subfolder_name}' does not exist.".encode(FORMAT))

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        conn.close()
        print(f"[DISCONNECTED] {addr} disconnected")


def main():
    print("[STARTING] Server is starting.")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #server.bind(ADDR)

    # Try to bind the server to the address and port
    try:
        server.bind(ADDR)
        print(f"[INFO] Server bound to {ADDR}")
    except Exception as e:
        print(f"[ERROR] Failed to bind server: {e}")
        return

    # Ensure the server folder exists
    if not os.path.exists(FOLDER):
        os.makedirs(FOLDER)
        print(f"[INFO] Created folder: {FOLDER}")

    try:
        server.listen()
        print(f"[LISTENING] Server is listening on {IP}:{PORT}")
    except Exception as e:
        print(f"[ERROR] Failed to listen on port {PORT}: {e}")
        return

    while True:
        try:
            conn, addr = server.accept()
            print(f"[NEW CONNECTION] {addr} connected.")
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
        except KeyboardInterrupt:
            print("\n[SHUTTING DOWN] Server is shutting down.")
            server.close()  # Ensure server is closed when interrupted
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            server.close()  # Close the server in case of an unexpected error
            break


if __name__ == "__main__":
    main()