import sys
import socket
import pickle
import json
import time
import cryptography
from threading import Thread

TIME_LIMIT = 10

def existsInDatabase(file_name, section, item_id):
    exists = False
    with open(file_name, "r") as file:
        items_list = json.load(file)
        for item in items_list[section]:
            try:
                if item["id"] == item_id:
                    exists = True
            except:
                pass
    
    return exists

def accept_clients(customer_socket, merchant_socket, payment_gateway_socket):
    #acceptam conexiunile
    customer_conn, customer_addr = customer_socket.accept()
    print("Customer connected:", customer_addr)

    merchant_conn, merchant_addr = merchant_socket.accept()
    print("Merchant connected:", merchant_addr)

    payment_gateway_conn, payment_gateway_addr = payment_gateway_socket.accept()
    print("Payment gateway connected:", payment_gateway_addr)

    transaction(customer_conn, merchant_conn, payment_gateway_conn)

def transaction(customer, merchant, payment_gateway):
    print("Transaction started...")

    #faza de pregatire: trimitem cheile necesare partilor
    customer_public_key, customer_private_key = cryptography.generate_asymmetric_keys()
    merchant_public_key, merchant_private_key = cryptography.generate_asymmetric_keys()
    payment_gateway_public_key, payment_gateway_private_key = cryptography.generate_asymmetric_keys()

    with open("keys/customer_public_key.pem", "wb") as file:
        file.write(customer_public_key)
    with open("keys/customer_private_key.pem", "wb") as file:
        file.write(customer_private_key)
    with open("keys/merchant_public_key.pem", "wb") as file:
        file.write(merchant_public_key)
    with open("keys/merchant_private_key.pem", "wb") as file:
        file.write(merchant_private_key)
    with open("keys/payment_gateway_public_key.pem", "wb") as file:
        file.write(payment_gateway_public_key)
    with open("keys/payment_gateway_private_key.pem", "wb") as file:
        file.write(payment_gateway_private_key)

    #setup sub-protocol
    setup(customer, merchant, payment_gateway)

    #exchange sub-protocol
    exchange(customer, merchant, payment_gateway)

    #inchidem conexiunile
    close_connections(customer, merchant, payment_gateway)

def setup(customer, merchant, payment_gateway):
    #incepem protocolul
    customer.send(b"Start")

    #cumparatorul alege produsul pe care vrea sa-l cumpere
    while True:
        product_id = customer.recv(10).decode()

        exists = existsInDatabase("data/products.json", "products", int(product_id))
        if not exists:
            customer.send(b"Product does not exist")
        else:
            customer.send(b"Product exists")
            break
    
    #pasul 1: C trimite lui M cheia sa publica
    data = customer.recv(4096)
    merchant.send(b"Generated client-merchant key")
    merchant.send(data)

    while True:
        status = merchant.recv(30).decode()

        if status == "Exit":
            close_connections(customer, merchant, payment_gateway, True)
            sys.exit()
        if status == "Success step 1.2":
            break

    #pasul 2: M trimite lui C id-ul tranzactiei
    data = merchant.recv(4096)
    customer.send(b"Generated SID")
    customer.send(data)

    while True:
        status = customer.recv(30).decode()
        
        if status == "Exit":
            close_connections(customer, merchant, payment_gateway, True)
            sys.exit()
        if status == "Success step 2":
            break

def exchange(customer, merchant, payment_gateway):
    timeout = False
    #cumparatorul isi alege o carte de credit pentru a efectua plata
    credit_card_id = -1
    while True:
        credit_card_id = customer.recv(10).decode()

        exists = existsInDatabase("data/cards.json", "customers", int(credit_card_id))
        if not exists:
            customer.send(b"Credit card does not exist")
        else:
            customer.send(b"Credit card exists")
            break

    #pasul 3: C trimite lui M detaliile de plata
    data = customer.recv(4096)
    merchant.send(b"Received payment details")
    merchant.send(data)

    #incepem sa numaram secundele de la trimiterea detaliilor de plata
    start = time.perf_counter()

    while True:
        status = merchant.recv(30).decode()
        
        if status == "Exit":
            close_connections(customer, merchant, payment_gateway, True)
            sys.exit()
        if status == "Success step 3":
            break
    
    #pasul 4: M trimite mai departe detaliile de plata catre PG
    data = merchant.recv(4096)
    payment_gateway.send(b"Forwarding payment details")
    payment_gateway.send(data)

    while True:
        status = payment_gateway.recv(30).decode()
        
        if status == "Exit":
            close_connections(customer, merchant, payment_gateway, True)
            sys.exit()
        if status == "Success step 4":
            break

    #pasul 5: PG trimite lui M raspunsul
    data = payment_gateway.recv(4096)
    merchant.send(b"Sending transaction response")
    merchant.send(data)

    while True:
        status = merchant.recv(30).decode()
        if status == "Exit":
            close_connections(customer, merchant, payment_gateway, True)
            sys.exit()
        if status == "Success step 5":
            break

    #verificam daca procesarea datelor dureaza mai mult decat limita
    end = time.perf_counter()
    if end - start > TIME_LIMIT:
        timeout = True

    if timeout:
        #resolution sub-protocol
        customer.send(b"Resolution")
        merchant.send(b"Resolution")
        payment_gateway.send(b"Resolution")
        resolution(customer, merchant, payment_gateway)
        return
    else:
        merchant.send(b"Forwarding response to customer")

    #pasul 6: M transmite raspunsul catre C
    data = merchant.recv(4096)
    customer.send(b"Received response")
    customer.send(data)

    while True:
        status = customer.recv(30).decode()
        if status == "Exit":
            close_connections(customer, merchant, payment_gateway, True)
            sys.exit()
        if status == "Success step 6":
            payment_gateway.send(b"Complete payment")
            break

    customer.send(b"Success")
    merchant.send(b"Success")
    payment_gateway.send(b"Success")
    
def resolution(customer, merchant, payment_gateway):
    print("Started resolution protocol.")

    #pasul 7: C incepe protocolul de rezolutie cu PG
    data = customer.recv(4096)
    payment_gateway.send(b"Received resolution data")
    payment_gateway.send(data)

    while True:
        status = payment_gateway.recv(30).decode()
        if status == "Exit":
            close_connections(customer, merchant, payment_gateway, True)
            sys.exit()
        if status == "Success step 7":
            break

    #pasul 8: PG trimite din nou raspunsul catre C
    data = payment_gateway.recv(4096)
    customer.send(b"Resolution response")
    customer.send(data)

    while True:
        status = customer.recv(30).decode()
        if status == "Exit":
            close_connections(customer, merchant, payment_gateway, True)
            sys.exit()
        if status == "Success step 8":
            payment_gateway.send(b"Complete payment")
            break
    
    customer.send(b"Success")
    merchant.send(b"Success")
    payment_gateway.send(b"Success")

def close_connections(customer, merchant, payment_gateway, error = False):
    if error:
        customer.send(b"[ERROR] Couldn't complete transaction.")
        merchant.send(b"[ERROR] Couldn't complete transaction.")
        payment_gateway.send(b"[ERROR] Couldn't complete transaction.")

    customer.close()
    merchant.close()
    payment_gateway.close()

    print("Transaction ended.")

if __name__ == "__main__":
    host = "127.0.0.1"
    customer_port = 7000
    merchant_port = 8000
    payment_gateway_port = 9000

    #cream un socket pentru fiecare participant
    customer_socket = socket.socket()
    customer_socket.bind((host, customer_port))

    merchant_socket = socket.socket()
    merchant_socket.bind((host, merchant_port))

    payment_gateway_socket = socket.socket()
    payment_gateway_socket.bind((host, payment_gateway_port))

    #serverul se poate ocupa de cel mult 10 tranzactii in acelasi timp
    customer_socket.listen(10)
    merchant_socket.listen(10)
    payment_gateway_socket.listen(10)

    for i in range(0, 10):
        Thread(target=accept_clients, args=(customer_socket, merchant_socket, payment_gateway_socket)).start()