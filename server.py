import socket
import os
import threading
from cryptography.fernet import Fernet
import json
import time
from globalvars import SIZE, FORMAT, PORT, SERVER_FOLDER, SERVER_STATS_FILE, MAX_STATS, USER_DB

IP = socket.gethostbyname(socket.gethostname())
ADDR = (IP, PORT)
def write_server_stats(operation, filename, filesize, time_taken, rate):
    try:
        with open(SERVER_STATS_FILE, "a") as stats_file:
            stats_file.write(
                f"{operation}: {filename}, Size: {filesize} bytes, Time: {time_taken:.2f}s, Rate: {rate:.2f} bytes/s\n")

        # Keep only the latest MAX_STATS records
        with open(SERVER_STATS_FILE, "r") as stats_file:
            lines = stats_file.readlines()

        if len(lines) > MAX_STATS:
            with open(SERVER_STATS_FILE, "w") as stats_file:
                stats_file.writelines(lines[-MAX_STATS:])
    except Exception as e:
        print(f"[ERROR] Failed to write server stats: {e}")

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
    try:
        if not os.path.exists(file_path):
            key = Fernet.generate_key()
            with open(file_path, "wb") as key_file:
                key_file.write(key)
        else:
            with open(file_path, "rb") as key_file:
                key = key_file.read()
        return key
    except Exception as e:
        print(f"[ERROR] Failed to load/create encryption key: {e}")
        return None


# Load the encryption key
key = load_create_key()
if key is None:
    exit(1)  # Exit if key generation/loading failed
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

    try:
        print(f"[NEW CONNECTION] {addr} connected.")
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
                file_path = os.path.join(SERVER_FOLDER, filename)

                # Check file size constraints
                if file_ext == ".txt" and file_size > 25 * 1024 * 1024:
                    conn.send("[ERROR] Text files must be at most 25MB.".encode(FORMAT))
                elif file_ext in [".mp3", ".wav"] and file_size > 1 * 1024 * 1024 * 1024:
                    conn.send("[ERROR] Audio files must be at most 1GB.".encode(FORMAT))
                elif file_ext in [".mp4", ".mkv", ".avi"] and file_size > 2 * 1024 * 1024 * 1024:
                    conn.send("[ERROR] Video files must be at most 2GB.".encode(FORMAT))
                else:
                    start_time = time.time()  # Start tracking time
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

                    end_time = time.time()  # End tracking time
                    time_taken = end_time - start_time
                    rate = file_size / time_taken if time_taken > 0 else 0

                    if bytes_received == file_size:
                        conn.send(f"[SUCCESS] {filename} uploaded.".encode(FORMAT))
                        print(f"[INFO] {filename} uploaded in {time_taken:.2f}s at {rate:.2f} bytes/s.")

                        # Save statistics to the server log file
                        write_server_stats("UPLOAD", filename, file_size, time_taken, rate)
                    else:
                        conn.send("[ERROR] File upload failed.".encode(FORMAT))

            elif command == "QUIT":
                break

            # Handle other commands (LIST, DELETE, SUBFOLDER, etc.)
            elif command == "LIST":
                response = []
                for root, dirs, files in os.walk(SERVER_FOLDER):
                    for subfolder in dirs:
                        response.append(f"[DIR] {os.path.relpath(os.path.join(root, subfolder), SERVER_FOLDER)}")
                    for file in files:
                        response.append(f"[FILE] {os.path.relpath(os.path.join(root, file), SERVER_FOLDER)}")
                conn.send("\n".join(response).encode(FORMAT))

            elif command == "DELETE":
                filename = args[0]
                file_path = os.path.join(SERVER_FOLDER, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    conn.send(f"[SUCCESS] {filename} deleted.".encode(FORMAT))
                else:
                    conn.send("[ERROR] File not found.".encode(FORMAT))

            elif command == "SUBFOLDER":
                action, subfolder_name = args
                subfolder_path = os.path.join(SERVER_FOLDER, subfolder_name)

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
    if not os.path.exists(SERVER_FOLDER):
        os.makedirs(SERVER_FOLDER)
        print(f"[INFO] Created folder: {SERVER_FOLDER}")

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
