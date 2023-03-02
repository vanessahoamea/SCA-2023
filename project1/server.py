import sys
import socket
import pickle
import json
import cryptography
from threading import Thread

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

    #resolution sub-protocol
    resolution(customer, merchant, payment_gateway)

    #inchidem conexiunile
    close_connections(customer, merchant, payment_gateway)

def setup(customer, merchant, payment_gateway):
    #incepem protocolul
    customer.send(b"Start")

    #cumparatorul alege produsul pe care vrea sa-l cumpere
    while True:
        product_id = customer.recv(10).decode()

        exists = False
        with open("data/products.json", "r") as file:
            products_list = json.load(file)
            for product in products_list["products"]:
                try:
                    if product["id"] == int(product_id):
                        exists = True
                except:
                    pass

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
            close_connections(customer, merchant, payment_gateway)
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
            close_connections(customer, merchant, payment_gateway)
            sys.exit()
        if status == "Success step 2.2":
            break

def exchange(customer, merchant, payment_gateway):
    #pasul 3: carte de credit si produs
    while True:
        credit_card_id = customer.recv(10).decode()
        exists = False
        with open("data/cards.json", "r") as file:
            cards_list = json.load(file)
            for card in cards_list["customers"]:
                try:
                    if card["id"] == int(credit_card_id):
                        exists = True
                except:
                    pass

        if not exists:
            customer.send(b"Credit card does not exist")
        else:
            customer.send(b"Credit card exists")
            break

    data = customer.recv(4098)
    print(data)

def resolution(customer, merchant, payment_gateway):
    pass

def close_connections(customer, merchant, payment_gateway):
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