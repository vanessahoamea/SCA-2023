import pickle
import json
import cryptography

CCODE = "1234"
NONCE = "BJMVOYaqV5RHNA1"

def customer_steps(keys, conn):
    #asteptam ca tranzactia sa porneasca
    conn.recv(10)

    #cumparatorul alege produsul pe care vrea sa-l cumpere
    product_id = -1
    while True:
        product_id = input("Enter product ID: ")
        conn.send(product_id.encode())

        response = conn.recv(40).decode()
        if response == "Product exists":
            break
        elif response == "[ERROR] Couldn't complete transaction.":
            print(response)
            return
        else:
            print(response)

    #generam o cheie de sesiune intre C si M
    keys["customer_merchant_key"] = cryptography.generate_session_key()

    #pasul 1: trimitem lui M cheia publica a lui C si cheia de sesiune
    conn.send(pickle.dumps({
        "customer_public_key": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], keys["customer_public_key_bytes"]),
        "customer_merchant_key": cryptography.encrypt_with_public_key(keys["merchant_public_key"], keys["customer_merchant_key"])
    }))

    while True:
        response = conn.recv(40).decode()
        if response == "Generated SID":
            break
        elif response == "[ERROR] Couldn't complete transaction.":
            print(response)
            return
    
    #pasul 2: primim id-ul sesiunii de la M
    data = pickle.loads(conn.recv(4096))

    sid = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["sid"])
    sid_signature = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["sid_signature"])
    if sid == None or sid_signature == None:
        conn.send(b"Exit")
        print("[ERROR] Couldn't complete transaction.")
        return
    else:
        if not cryptography.check_signature(keys["merchant_public_key"], sid, sid_signature):
            conn.send(b"Exit")
            print("[ERROR] Couldn't complete transaction.")
            return
        else:
            conn.send(b"Success step 2")
    
    #cumparatorul introduce detaliile de plata
    credit_card_id = -1
    while True:
        credit_card_id = input("Enter credit card ID: ")
        conn.send(credit_card_id.encode())

        response = conn.recv(40).decode()
        if response == "Credit card exists":
            break
        elif response == "[ERROR] Couldn't complete transaction.":
            print(response)
            return
        else:
            print(response)
    
    amount = 0
    merchant_card_id = -1
    with open("data/products.json", "r") as file:
        products_list = json.load(file)
        for product in products_list["products"]:
            if product["id"] == int(product_id):
                amount = str(product["price"])
                merchant_card_id = str(product["merchant_card_id"])
                break

    #generam o cheie de sesiune intre C si PG
    keys["customer_payment_gateway_key"] = cryptography.generate_session_key()

    #pasul 3: trimitem lui M detaliile tranzactiei
    payment_information = {
        "credit_card_id": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], credit_card_id),
        "ccode": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], CCODE),
        "sid": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], sid),
        "amount": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], amount),
        "customer_public_key": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], keys["customer_public_key_bytes"]),
        "nonce": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], NONCE),
        "merchant_card_id": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], merchant_card_id),
        "customer_payment_gateway_key": cryptography.encrypt_with_public_key(keys["payment_gateway_public_key"], keys["customer_payment_gateway_key"])
    }
    payment_information_signature = cryptography.signature(keys["customer_private_key"], pickle.dumps(payment_information))
    payment_information_signature = cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], payment_information_signature)

    payment_message = pickle.dumps({
        "payment_information": payment_information,
        "payment_information_signature": payment_information_signature
    })

    order_details = {
        "product_id": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], product_id),
        "sid": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], sid),
        "amount": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], amount),
        "nonce": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], NONCE)
    }
    order_details_signature = cryptography.signature(keys["customer_private_key"], pickle.dumps(order_details))
    order_details_signature = cryptography.encrypt_with_session_key(keys["customer_merchant_key"], order_details_signature)

    conn.send(pickle.dumps({
        #payment message - pentru PG
        "payment_message": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], payment_message),
        #purchase order - pentru M
        "order_details": order_details,
        "order_details_signature": order_details_signature
    }))

    while True:
        response = conn.recv(40).decode()
        if response == "Received response":
            break
        elif response == "Resolution":
            resolution(keys, conn, sid, amount)
            return
        elif response == "[ERROR] Couldn't complete transaction.":
            print(response)
            return

    #pasul 6: primim raspunsul dat de PG
    data = pickle.loads(conn.recv(4096))

    final_response = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["response"])
    sid_pg = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["sid"])
    transaction_data = {
        "response": cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["response"]).decode(),
        "sid": sid.decode(),
        "amount": amount,
        "nonce": NONCE
    }
    transaction_data_signature = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["transaction_data_signature"])

    if final_response == None or sid_pg == None or transaction_data_signature == None or final_response.decode() not in ["YES", "ABORT"] or sid_pg != sid:
        conn.send(b"Exit")
        print("[ERROR] Couldn't complete transaction.")
        return
    else:
        if not cryptography.check_signature(keys["payment_gateway_public_key"], pickle.dumps(transaction_data), transaction_data_signature):
            conn.send(b"Exit")
            print("[ERROR] Couldn't complete transaction.")
            return
        else:
            conn.send(b"Success step 6")

    #astemptam rezultatul tranzactiei
    while True:
        response = conn.recv(40).decode()
        if response == "Success":
            print("Transaction completed succesfully.")
            break
        elif response == "[ERROR] Couldn't complete transaction.":
            print(response)
            break

def resolution(keys, conn, sid, amount):
    #pasul 7: trimitem datele pentru rezolutie catre PG
    resolution_data = {
        "sid": sid.decode(),
        "amount": amount,
        "nonce": NONCE,
        "customer_public_key": keys["customer_public_key_bytes"]
    }
    resolution_data_signature = cryptography.signature(keys["customer_private_key"], pickle.dumps(resolution_data))

    conn.send(pickle.dumps({
        "sid": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], sid.decode()),
        "amount": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], amount),
        "nonce": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], NONCE),
        "customer_public_key": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], keys["customer_public_key_bytes"]),
        "resolution_data_signature": cryptography.encrypt_with_session_key(keys["customer_payment_gateway_key"], resolution_data_signature)
    }))

    while True:
            response = conn.recv(40).decode()
            if response == "Resolution response":
                break
            elif response == "[ERROR] Couldn't complete transaction.":
                print(response)
                return

    #pasul 8: primim raspunsul de la PG, finalizam tranzactia
    data = pickle.loads(conn.recv(4096))

    final_response = cryptography.decrypt_with_session_key(keys["customer_payment_gateway_key"], *data["response"])
    sid_pg = cryptography.decrypt_with_session_key(keys["customer_payment_gateway_key"], *data["sid"])
    transaction_data = {
        "response": cryptography.decrypt_with_session_key(keys["customer_payment_gateway_key"], *data["response"]).decode(),
        "sid": sid.decode(),
        "amount": amount,
        "nonce": NONCE
    }
    transaction_data_signature = cryptography.decrypt_with_session_key(keys["customer_payment_gateway_key"], *data["transaction_data_signature"])

    if final_response == None or sid_pg == None or transaction_data_signature == None or final_response.decode() not in ["YES", "ABORT"] or sid_pg != sid:
        conn.send(b"Exit")
        print("[ERROR] Couldn't complete transaction.")
        return
    else:
        if not cryptography.check_signature(keys["payment_gateway_public_key"], pickle.dumps(transaction_data), transaction_data_signature):
            conn.send(b"Exit")
            print("[ERROR] Couldn't complete transaction.")
            return
        else:
            conn.send(b"Success step 8")

    #astemptam rezultatul tranzactiei
    while True:
        response = conn.recv(40).decode()
        if response == "Success":
            print("Transaction completed succesfully.")
            break
        elif response == "[ERROR] Couldn't complete transaction.":
            print(response)
            break