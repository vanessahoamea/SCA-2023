import sys
import socket
import pickle
import cryptography

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide a port.")
        sys.exit()
    
    if(sys.argv[1] != "7000" and sys.argv[1] != "8000" and sys.argv[1] != "9000"):
        print("Allowed ports: 7000 (customer), 8000 (merchant), 9000 (payment gateway).")
        sys.exit()
    
    host = "127.0.0.1"
    port = int(sys.argv[1])

    client_socket = socket.socket() 
    client_socket.connect((host, port))

    #faza de pregatire: primim cheile necesare de la server
    keys = pickle.loads(client_socket.recv(4096))
    print(keys)

    match port:
        case 7000:
            pass
        case 8000:
            pass
        case 9000:
            pass

    client_socket.close()