import pickle
import secrets
import string
import cryptography

def merchant_steps(keys, conn):
    while True:
        response = conn.recv(40).decode()
        if response == "Generated client-merchant key":
            break
        elif response == "[ERROR] Couldn't complete transaction.":
            print(response)
            return
    
    #pasul 1: primim cheile de la C
    data = pickle.loads(conn.recv(4096))

    customer_merchant_key = cryptography.decrypt_with_private_key(keys["merchant_private_key"], data["customer_merchant_key"])
    if customer_merchant_key == None:
        conn.send(b"Exit")
        print("[ERROR] Couldn't complete transaction.")
        return
    else:
        keys["customer_merchant_key"] = customer_merchant_key
        conn.send(b"Success step 1.1")

    customer_public_key_bytes = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["customer_public_key"])
    if customer_public_key_bytes == None:
        conn.send(b"Exit")
        print("[ERROR] Couldn't complete transaction.")
        return
    else:
        keys["customer_public_key_bytes"] = customer_public_key_bytes
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

    while True:
        response = conn.recv(40).decode()
        if response == "Received payment details":
            break
        elif response == "[ERROR] Couldn't complete transaction.":
            print(response)
            return

    #pasul 3: primim datele despre produs si cartea de credit
    data = pickle.loads(conn.recv(4096))

    payment_message = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["payment_message"])
    order_details = data["order_details"]
    order_details_signature = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *data["order_details_signature"])
    if(payment_message == None or order_details_signature == None):
        conn.send(b"Exit")
        print("[ERROR] Couldn't complete transaction.")
        return
    else:
        product_id = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *order_details["product_id"])
        sid_c = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *order_details["sid"])
        amount = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *order_details["amount"])
        nonce = cryptography.decrypt_with_session_key(keys["customer_merchant_key"], *order_details["nonce"])
        order_details_signature = cryptography.check_signature(keys["customer_public_key"], pickle.dumps(order_details), order_details_signature)

        if(product_id == None or sid_c == None or amount == None or nonce == None or order_details_signature == None or sid_c != sid.encode()):
            conn.send(b"Exit")
            print("[ERROR] Couldn't complete transaction.")
            return
        else:
            conn.send(b"Success step 3")
    
    #generam o cheie de sesiune intre M si PG
    keys["merchant_payment_gateway_key"] = cryptography.generate_session_key()

    #pasul 4: trimitem lui PG detaliile tranzactiei
    transaction_details = {
        "sid": sid.encode(),
        "amount": amount,
        "customer_public_key": keys["customer_public_key_bytes"]
    }
    transaction_signature = cryptography.signature(keys["merchant_private_key"], pickle.dumps(transaction_details))

    conn.send(pickle.dumps({
        "payment_message": payment_message,
        "transaction_signature": cryptography.encrypt_with_session_key(keys["merchant_payment_gateway_key"], transaction_signature),
        "merchant_payment_gateway_key": cryptography.encrypt_with_public_key(keys["payment_gateway_public_key"], keys["merchant_payment_gateway_key"])
    }))

    #pasul 5:

    while True:
        response = conn.recv(40).decode()
        if response == "Forwarding response":
            break
    data = pickle.loads(conn.recv(4096))



    transaction_data = {
        "response": cryptography.decrypt_with_session_key(keys["merchant_payment_gateway_key"], *data["response"]).decode(),
        "Sid": sid,
        "Amount": amount.decode(),
        "Nonce": nonce.decode()
    }

    transaction_data_signature = cryptography.decrypt_with_session_key(keys["merchant_payment_gateway_key"], *data["transaction_data_signature"])
    sid_pg = cryptography.decrypt_with_session_key(keys["merchant_payment_gateway_key"], *data["Sid"])

    if sid_pg == None or transaction_data_signature == None:
        conn.send(b"Exit")
        print("[ERROR] Couldn't complete transaction.")
        return
    else:
        if not cryptography.check_signature(keys["payment_gateway_public_key"], pickle.dumps(transaction_data), transaction_data_signature):
            conn.send(b"Exit")
            print("[ERROR] Couldn't complete transaction.")
            return
        else:
            conn.send(b"Success step 5")

    while True:
        resp = conn.recv(40).decode()
        if resp == "Send response to customer":
            break
        elif resp == "resolution":
            return

    transaction_data = {
        "response": cryptography.decrypt_with_session_key(keys["merchant_payment_gateway_key"], *data["response"]).decode(),
        "Sid": sid,
        "Amount": amount.decode(),
        "Nonce": nonce.decode()
    }
    transaction_data_signature = cryptography.signature(keys["merchant_private_key"], pickle.dumps(transaction_data))
    data = { "response": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], response),
             "Sid": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], sid),
             "transaction_data_signature": cryptography.encrypt_with_session_key(keys["customer_merchant_key"], transaction_data_signature)
    }
    conn.send(pickle.dumps(data))