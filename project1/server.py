import socket
import pickle
import cryptography

def setup(customer, merchant):
    pass

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

    #permitem unui singur cumparator/vanzator/PG sa se conecteze la un moment dat
    customer_socket.listen(1)
    merchant_socket.listen(1)
    payment_gateway_socket.listen(1)

    #acceptam conexiunile
    customer_conn, customer_addr = customer_socket.accept()
    print("Customer connected:", customer_addr)

    merchant_conn, merchant_addr = merchant_socket.accept()
    print("Merchant connected:", merchant_addr)

    payment_gateway_conn, payment_gateway_addr = payment_gateway_socket.accept()
    print("Payment gateway connected:", payment_gateway_addr)

    #faza de pregatire: trimitem cheile necesare partilor
    customer_public_key, customer_private_key = cryptography.generate_asymmetric_keys()
    merchant_public_key, merchant_private_key = cryptography.generate_asymmetric_keys()
    payment_gateway_public_key, payment_gateway_private_key = cryptography.generate_asymmetric_keys()

    customer_conn.sendall(pickle.dumps({
        "customer_public_key": customer_public_key,
        "customer_private_key": customer_private_key,
        "merchant_public_key": merchant_public_key,
        "payment_gateway_public_key": payment_gateway_public_key
    }))

    merchant_conn.send(pickle.dumps({
        "merchant_public_key": merchant_public_key,
        "merchant_private_key": merchant_private_key,
        "payment_gateway_public_key": payment_gateway_public_key
    }))

    payment_gateway_conn.send(pickle.dumps({
        "payment_gateway_public_key": payment_gateway_public_key,
        "payment_gateway_private_key": payment_gateway_private_key,
        "merchant_public_key": merchant_public_key
    }))

    #setup sub-protocol
    setup(customer_conn, merchant_conn)

    #exchange sub-protocol
    exchange(customer_conn, merchant_conn, payment_gateway_conn)

    #resolution sub-protocol
    resolution(customer_conn, payment_gateway_conn)

    #inchidem conexiunile
    customer_conn.close()
    merchant_conn.close()
    payment_gateway_conn.close()