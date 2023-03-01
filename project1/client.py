import sys
import socket
import pickle
import cryptography

CCODE = "1234" #challenge code pentru cumparator si PG

def customer_steps(keys):
    sessionKey = cryptography.generate_session_key()

    while True:
        id = input("Enter product id: ")
        client_socket.send(id.encode())
        if client_socket.recv(30) == b"Product exists":
            break
    merchant_public_key, merchant_private_key = cryptography.load_asymmetric_keys(keys["merchant_public_key"], keys["customer_private_key"])
    customer_public_key, customer_private_key = cryptography.load_asymmetric_keys(keys["customer_public_key"],
                                                                                  keys["customer_private_key"])
    k = cryptography.encrypt_with_public_key(merchant_public_key, sessionKey)
    dict = {"customer_merchant_key": k,
        "customer_public_key": cryptography.encrypt_with_session_key(k, customer_public_key) }

    client_socket.send(pickle.dumps(dict))

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
    # file = open("keys.PEM", "rb")
    # customer_public_key = file.read()
    # customer_private_key = file.read()
    # merchant_public_key = file.read()
    # merchant_private_key = file.read()
    # payment_gateway_public_key = file.read()
    # payment_gateway_private_key = file.read()
    # file.close()

    # customer_public_key, customer_private_key = cryptography.load_asymmetric_keys(customer_public_key,customer_private_key)
    # merchant_public_key, merchant_private_key = cryptography.load_asymmetric_keys(merchant_public_key,merchant_private_key)
    # payment_gateway_public_key, payment_gateway_private_key = cryptography.load_asymmetric_keys(payment_gateway_public_key,
    #                                                                               payment_gateway_private_key)

    #executam pasii protocolului
    match port:
        case 7000:
            customer_steps(keys)
        case 8000:
            merchant_steps(keys)
        case 9000:
            payment_gateway_steps(keys)

    client_socket.close()