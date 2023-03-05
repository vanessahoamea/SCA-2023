import sys
import socket
import cryptography
from customer_steps import customer_steps
from merchant_steps import merchant_steps
from payment_gateway_steps import payment_gateway_steps

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