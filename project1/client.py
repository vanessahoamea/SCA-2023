import sys
import socket
import pickle
import cryptography

CCODE = "1234" #challenge code pentru cumparator si PG

def customer_steps(keys):
    pass

def merchant_steps(keys):
    pass

def payment_gateway_steps(keys):
    pass

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
    keys = pickle.loads(client_socket.recv(2048))

    #executam pasii protocolului
    match port:
        case 7000:
            customer_steps(keys)
        case 8000:
            merchant_steps(keys)
        case 9000:
            payment_gateway_steps(keys)

    client_socket.close()