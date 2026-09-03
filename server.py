import threading
import socket
import os
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


HOST = "127.0.0.1"      # local host — bind address for the server
PORT = 6555             # arbitrary unused port for the chat server

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

# maps each connected client socket to its chosen nickname.
# pattern is: {client_socket: nickname}
clients: dict[socket.socket, str] = {}


def broadcast(message: bytes) -> None:
    """Send `message` to every currently connected client."""
    for client in clients:
        client.send(message)


def handle_client(client: socket.socket) -> None:
    """
    Continuously relay messages from one connected client to everyone else.
    Runs in its own thread per client. Exits the loop when the client
    disconnects (recv/send raises, since the socket becomes unusable).
    """
    while True:
        try:
            # debug this
            # msg = message = client.recv(1024)
            message = client.recv(1024)
            
            if message.decode('ascii').startswith('KICK'):

                # check for admin privileges
                if clients.get(client) == 'admin':
                    name_to_kick = message.decode('ascii')[5:]
                    kick_user(name_to_kick)
                else:
                    client.send('You are not the admin!'.encode('ascii'))
                
            elif message.decode('ascii').startswith('BAN'):
                name_to_ban = message.decode('ascii')[4:]
                kick_user(name_to_ban)
                
                with open('bans.txt', 'a') as f:
                    f.write(f"{name_to_ban}\n")
                
                print(f"{name_to_ban} was banned.")
                
            else:
                broadcast(message)
                
        except OSError:
            # Client disconnected (abruptly closed, network drop, etc.)
            nickname = clients.pop(client)
            client.close()
            broadcast(f"{nickname} left the chat!".encode('ascii'))
            break


def accept_connections() -> None:
    """
    Continuously accept new client connections, register their nickname,
    and spin up a dedicated thread to handle each one.
    """
    while True:
        client, address = server.accept()
        logger.info(f"Connected with {address}")

        client.send('NICK'.encode('ascii'))
        nickname = client.recv(1024).decode('ascii')

        # check if the bans.txt file exists, if not create it
        if not os.path.exists('bans.txt'):
            open('bans.txt', 'a').close()

        with open('bans.txt', 'r', encoding='utf-8') as f:
            bans = [line.strip() for line in f if line.strip()]

        # check if the user is banned
        if nickname in bans:
            client.send('REFUSE'.encode('ascii'))
            client.close()
            continue
        
        # check for admin
        if nickname == 'admin':
            client.send('pwd'.encode('ascii'))
            password = client.recv(1024).decode('ascii')
            
            # need to work on it to make it more secure
            if password != 'adminpass':
                client.send('REFUSE'.encode('ascii'))
                client.close()
                continue
        

        clients[client] = nickname

        logger.info(f"Nickname of the client is {nickname}")
        broadcast(f"{nickname} joined the chat!".encode('ascii'))
        client.send("Connected to the server!".encode('ascii'))

        client_thread = threading.Thread(target=handle_client, args=(client,), daemon=True)
        client_thread.start()


def kick_user(name):
    """Kick a user from the chat by their nickname."""
    if name in clients.values():
        for client, nicknames in clients.items():
            if nicknames == name:
                clients.pop(client)
                client.send('You have been kicked by the admin!'.encode('ascii'))
                client.close()
                broadcast(f"{name} was kicked by the admin!".encode('ascii'))
                break



if __name__ == "__main__":
    try:
        accept_connections()

    except KeyboardInterrupt:
        logger.error("\nShutting down server...")
        server.close()
        os._exit(0)