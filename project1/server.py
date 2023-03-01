import socket
import pickle
import cryptography
import json
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

    # file = open("keys.PEM", "wb")
    # file.write(customer_public_key)
    # file.write(customer_private_key)
    # file.write(merchant_public_key)
    # file.write(merchant_private_key)
    # file.write(payment_gateway_public_key)
    # file.write(payment_gateway_private_key)
    # file.close()


    customer.send(pickle.dumps({
        "customer_public_key": customer_public_key,
        "customer_private_key": customer_private_key,
        "merchant_public_key": merchant_public_key,
        "payment_gateway_public_key": payment_gateway_public_key
    }))

    merchant.send(pickle.dumps({
        "merchant_public_key": merchant_public_key,
        "merchant_private_key": merchant_private_key,
        "payment_gateway_public_key": payment_gateway_public_key
    }))

    payment_gateway.send(pickle.dumps({
        "payment_gateway_public_key": payment_gateway_public_key,
        "payment_gateway_private_key": payment_gateway_private_key,
        "merchant_public_key": merchant_public_key
    }))

    #setup sub-protocol
    setup(customer, merchant)

    #exchange sub-protocol
    exchange(customer, merchant, payment_gateway)

    #resolution sub-protocol
    resolution(customer, payment_gateway)

    #inchidem conexiunile
    customer.close()
    merchant.close()
    payment_gateway.close()

    print("Transaction ended.")

def setup(customer, merchant):
        while True:
            id = customer.recv(10).decode()
            # print(id)
            fileName = open("products.json", "r")
            file = json.load(fileName)
            #print(file["products"])
            exists = False
            for products in file["products"]:

                if products["id"] == int(id):
                    exists = True
            fileName.close()
            if not exists:
                customer.send(b"Product does not exists")
            else:
                customer.send(b"Product exists")
                break
        data = pickle.loads(customer.recv(4000))
        print(data)

def exchange(customer, merchant, payment_gateway):
    pass

def resolution(customer, payment_gateway):
    pass

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