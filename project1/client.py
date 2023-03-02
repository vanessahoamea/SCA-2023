import sys
import socket
import pickle
import secrets
import string
import cryptography

CCODE = "1234" #challenge code pentru C si PG

def customer_steps(keys, conn):
    #asteptam ca tranzactia sa porneasca
    conn.recv(10)

    #cumparatorul alege produsul pe care vrea sa-l cumpere
    product_id = -1
    while True:
        product_id = input("Enter product id: ")
        conn.send(product_id.encode())

        response = conn.recv(30).decode()
        if response == "Product exists":
            break
        else:
            print(response)

    #generam o cheie de sesiune intre C si M
    customer_merchant_key = cryptography.generate_session_key()
    keys["customer_merchant_key"] = customer_merchant_key

    #pasul 1: trimitem lui M cheia publica a lui C si cheia de sesiune
    conn.send(pickle.dumps({
        "customer_public_key": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], keys["customer_public_key_bytes"]),
        "customer_merchant_key": cryptography.encrypt_with_public_key(keys["merchant_public_key"], keys["customer_merchant_key"])
    }))

    while True:
        response = conn.recv(30).decode()
        if response == "Generated SID":
            break
    
    #pasul 2: primim id-ul sesiunii de la M
    data = pickle.loads(conn.recv(4096))

    sid = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["sid"])
    if sid == None:
        conn.send(b"Exit")
    else:
        conn.send(b"Success step 2.1")

    #verificam semnatura lui M peste sid
    sid_signature = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["sid_signature"])
    if sid_signature == None:
        conn.send(b"Exit")
    else:
        if not cryptography.check_signature(keys["merchant_public_key"], sid, sid_signature):
            conn.send(b"Exit")
        else:
            conn.send(b"Success step 2.2")

def merchant_steps(keys, conn):
    while True:
        response = conn.recv(30).decode()
        if response == "Generated client-merchant key":
            break
    
    #pasul 1: primim datele de la C
    data = pickle.loads(conn.recv(4096))

    customer_merchant_key = cryptography.decrypt_with_private_key(keys["merchant_private_key"], data["customer_merchant_key"])
    if customer_merchant_key == None:
        conn.send(b"Exit")
    else:
        keys["customer_merchant_key"] = customer_merchant_key
        conn.send(b"Success step 1.1")

    customer_public_key_bytes = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["customer_public_key"])
    if customer_public_key_bytes == None:
        conn.send(b"Exit")
    else:
        keys["customer_public_key"] = cryptography.load_one_asymmetric_key(customer_public_key_bytes)
        conn.send(b"Success step 1.2")
    
    #pasul 2: trimitem lui C id-ul tranzactiei si semnatura
    sid = "".join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(10))
    signature = cryptography.signature(keys["merchant_private_key"], sid)

    #ambele parti cunosc cheia de sesiune, deci putem cripta mesajele direct cu aceasta
    conn.send(pickle.dumps({
        "sid": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], sid),
        "sid_signature": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], signature)
    }))

def payment_gateway_steps(keys, conn):
    pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide a port.")
        sys.exit()
    
    if sys.argv[1] != "7000" and sys.argv[1] != "8000" and sys.argv[1] != "9000":
        print("Allowed ports: 7000 (customer), 8000 (merchant), 9000 (payment gateway).")
        sys.exit()
    
    host = "127.0.0.1"
    port = int(sys.argv[1])

    client_socket = socket.socket() 
    client_socket.connect((host, port))

    #faza de pregatire: primim cheile necesare de la server
    with open("keys/customer_public_key.pem", "rb") as file:
        customer_public_key_bytes = file.read()
    with open("keys/customer_private_key.pem", "rb") as file:
        customer_private_key_bytes = file.read()
    customer_public_key, customer_private_key = cryptography.load_asymmetric_keys(customer_public_key_bytes, customer_private_key_bytes)

    with open("keys/merchant_public_key.pem", "rb") as file:
        merchant_public_key_bytes = file.read()
    with open("keys/merchant_private_key.pem", "rb") as file:
        merchant_private_key_bytes = file.read()
    merchant_public_key, merchant_private_key = cryptography.load_asymmetric_keys(merchant_public_key_bytes, merchant_private_key_bytes)

    with open("keys/payment_gateway_public_key.pem", "rb") as file:
        payment_gateway_public_key_bytes = file.read()
    with open("keys/payment_gateway_private_key.pem", "rb") as file:
        payment_gateway_private_key_bytes = file.read()
    payment_gateway_public_key, payment_gateway_private_key = cryptography.load_asymmetric_keys(payment_gateway_public_key_bytes, payment_gateway_private_key_bytes)

    #executam pasii protocolului
    match port:
        case 7000:
            keys = {
                "customer_public_key_bytes": customer_public_key_bytes,
                "payment_gateway_public_key_bytes": payment_gateway_public_key_bytes,
                "customer_public_key": customer_public_key,
                "customer_private_key": customer_private_key,
                "merchant_public_key": merchant_public_key,
                "payment_gateway_public_key": payment_gateway_public_key,
            }
            customer_steps(keys, client_socket)
        case 8000:
            keys = {
                "merchant_public_key_bytes": merchant_public_key_bytes,
                "merchant_private_key_bytes": merchant_private_key_bytes,
                "merchant_public_key": merchant_public_key,
                "merchant_private_key": merchant_private_key,
                "payment_gateway_public_key": payment_gateway_public_key
            }
            merchant_steps(keys, client_socket)
        case 9000:
            keys = {
                "payment_gateway_public_key_bytes": payment_gateway_public_key_bytes,
                "payment_gateway_private_key_bytes": payment_gateway_private_key_bytes,
                "payment_gateway_public_key": payment_gateway_public_key,
                "payment_gateway_private_key": payment_gateway_private_key,
                "merchant_public_key": merchant_public_key
            }
            payment_gateway_steps(keys, client_socket)

    client_socket.close()