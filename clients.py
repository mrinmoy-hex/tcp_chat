import socket
import threading
import os


HOST = "127.0.0.1"  # server address to connect to
PORT = 6555

nickname = input("Choose a nickname: ")
if nickname == 'admin':
    password = input("Enter password for admin: ")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))


stop_thread = False


def receive_messages() -> None:
    """
    Continuously listen for incoming data from the server: respond to the
    nickname handshake, and print any regular chat messages as they arrive.
    """
    while True:
        
        global stop_thread
        if stop_thread:
            break
        
        try:
            message = client.recv(1024).decode('ascii')
            if message == 'NICK':
                client.send(nickname.encode('ascii'))
                next_message = client.recv(1024).decode('ascii')
                if next_message == 'pwd':
                    client.send(password.encode('ascii'))
                    if client.recv(1024).decode('ascii') == 'REFUSE':
                        print("Connection refused. Wrong Password!")
                        stop_thread = True

                elif next_message == 'REFUSE':
                    print("Connection refused. You are banned from this server!")
                    client.close()
                    stop_thread = True  # 
                        
            else:
                print(message)
        except OSError:
            print("Connection to server lost.")
            client.close()
            break


def send_messages() -> None:
    """Continuously read user input and send it to the server as a chat message."""
    while True:
        if stop_thread:
            break
        
        message = f"{nickname}: {input('')}"
        if message[len(nickname)+2].startswith('/'):
            # username: /commands
            if nickname == 'admin':
                if message[len(nickname)+2].startswith('/kick'):
                    client.send(f"KICK {message[len(nickname)+2+6]}".encode('ascii'))
                
                elif message[len(nickname)+2].startswith('/ban'):
                    client.send(f"BAN {message[len(nickname)+2+5]}".encode('ascii'))
            else:
                print("Commands can only be executed by the admin!")
        
        else:       
            client.send(message.encode('ascii'))


if __name__ == "__main__":
    receive_thread = threading.Thread(target=receive_messages, daemon=True)
    receive_thread.start()

    write_thread = threading.Thread(target=send_messages, daemon=True)
    write_thread.start()

    try:
        write_thread.join()
    except KeyboardInterrupt:
        print("\nDisconnecting...")
        client.close()
        os._exit(0)