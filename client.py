import socket
import os

IP = socket.gethostbyname(socket.gethostname())
PORT = 4455
ADDR = (IP, PORT)
FORMAT = "utf-8"
SIZE = 1024  # Make sure this matches the server-side SIZE
FOLDER = "data"  # Folder to send files from

# File type size limits (in bytes)
SIZE_LIMITS = {
    "text": 25 * 1024 * 1024,  # 25 MB
    "audio": 1 * 1024 * 1024 * 1024,  # 1 GB
    "video": 2 * 1024 * 1024 * 1024,  # 2 GB
}

# Mapping of extensions to file types
FILE_TYPES = {
    ".txt": "text",
    ".mp3": "audio",
    ".wav": "audio",
    ".mp4": "video",
    ".mkv": "video",
    ".avi": "video",
}


def get_file_type(file_name):
    """Determine file type based on extension."""
    ext = os.path.splitext(file_name)[1].lower()
    return FILE_TYPES.get(ext, None)


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
                file_type = get_file_type(file_name)

                if not file_type:
                    print(f"[SKIPPED] {file_name}: Unsupported file type.")
                    continue

                """ Get the file size automatically. """
                file_size = os.path.getsize(file_path)

                """ Check file size against limits. """
                if file_size > SIZE_LIMITS[file_type]:
                    print(f"[SKIPPED] {file_name}: File size exceeds {SIZE_LIMITS[file_type]} bytes for {file_type} files.")
                    continue

                """ Send the metadata (filename and size). """
                metadata = f"{file_name}:{file_size}"
                client.send(metadata.encode(FORMAT))

                """ Wait for server acknowledgment. """
                msg = client.recv(SIZE).decode(FORMAT)
                print(f"[SERVER]: {msg}")

                """ Send the file data in chunks. """
                with open(file_path, "rb") as file:
                    while chunk := file.read(SIZE):
                        print(f"[DEBUG] Sending chunk of size {len(chunk)}")
                        client.send(chunk)
                    print("[DEBUG] Finished sending file data.")

                """ Wait for server acknowledgment. """
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
