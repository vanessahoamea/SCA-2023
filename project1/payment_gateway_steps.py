import json
import pickle
import cryptography

CCODE = "1234"

def payment_gateway_steps(keys, conn):
    while True:
        response = conn.recv(40).decode()
        if response == "Forwarding payment details":
            break
        elif response == "[ERROR] Couldn't complete transaction.":
            print(response)
            return
    
    #pasul 4: primim detaliile tranzactiei de la M
    data = pickle.loads(conn.recv(4096))
    
    merchant_payment_gateway_key = cryptography.decrypt_with_private_key(keys["payment_gateway_private_key"], data["merchant_payment_gateway_key"])
    if merchant_payment_gateway_key == None:
        conn.send(b"Exit")
        print("[ERROR] Couldn't complete transaction.")
        return
    else:
        keys["merchant_payment_gateway_key"] = merchant_payment_gateway_key
        conn.send(b"Success step 4.1")

    payment_message = pickle.loads(data["payment_message"])
    payment_information = payment_message["payment_information"]
    payment_information_signature = payment_message["payment_information_signature"]

    #extragem cheile necesare
    customer_payment_gateway_key = cryptography.decrypt_with_private_key(keys["payment_gateway_private_key"], payment_information["customer_payment_gateway_key"])
    customer_public_key_bytes = cryptography.decrypt_with_session_key(customer_payment_gateway_key, *payment_information["customer_public_key"])

    if customer_payment_gateway_key == None or customer_public_key_bytes == None:
        conn.send(b"Exit")
        print("[ERROR] Couldn't complete transaction.")
        return
    else:
        keys["customer_payment_gateway_key"] = customer_payment_gateway_key
        keys["customer_public_key_bytes"] = customer_public_key_bytes
        keys["customer_public_key"] = cryptography.load_one_asymmetric_key(customer_public_key_bytes)
        conn.send(b"Success step 4.2")

    #verificam informatiile din PM primite de la C
    credit_card_id = cryptography.decrypt_with_session_key(keys["customer_payment_gateway_key"], *payment_information["credit_card_id"])
    ccode = cryptography.decrypt_with_session_key(keys["customer_payment_gateway_key"], *payment_information["ccode"])
    sid_c = cryptography.decrypt_with_session_key(keys["customer_payment_gateway_key"], *payment_information["sid"])
    amount_c = cryptography.decrypt_with_session_key(keys["customer_payment_gateway_key"], *payment_information["amount"])
    nonce_c = cryptography.decrypt_with_session_key(keys["customer_payment_gateway_key"], *payment_information["nonce"])
    merchant_card_id = cryptography.decrypt_with_session_key(keys["customer_payment_gateway_key"], *payment_information["merchant_card_id"])

    if credit_card_id == None or ccode == None or sid_c == None or amount_c == None or nonce_c == None or merchant_card_id == None or ccode.decode() != CCODE:
        conn.send(b"Exit")
        print("[ERROR] Couldn't complete transaction.")
        return
    else:
        #verificam semnatura lui C
        payment_information_signature = cryptography.decrypt_with_session_key(keys["customer_payment_gateway_key"], *payment_information_signature)

        if not cryptography.check_signature(keys["customer_public_key"], pickle.dumps(payment_information), payment_information_signature):
            conn.send(b"Exit")
            print("[ERROR] Couldn't complete transaction.")
            return
        else:
            conn.send(b"Success step 4.3")
    
    #verificam semnatura lui M
    transaction_details = {
        "sid": sid_c,
        "amount": amount_c,
        "customer_public_key": keys["customer_public_key_bytes"]
    }
    transaction_signature = cryptography.decrypt_with_session_key(keys["merchant_payment_gateway_key"], *data["transaction_signature"])

    if transaction_signature == None:
        conn.send(b"Exit")
        print("[ERROR] Couldn't complete transaction.")
        return
    else:
        if not cryptography.check_signature(keys["merchant_public_key"], pickle.dumps(transaction_details), transaction_signature):
            conn.send(b"Exit")
            print("[ERROR] Couldn't complete transaction.")
            return
        else:
            conn.send(b"Success step 4")

    #pasul 5: trimitem lui M raspunsul final
    response = "ABORT"
    with open("data/cards.json", "r") as file:
        cards = json.load(file)
        for card in cards["customers"]:
            if card["id"] == int(credit_card_id):
                if card["amount"] >= int(amount_c):
                    response = "YES"

    transaction_data = {
        "response": response,
        "sid": sid_c.decode(),
        "amount": amount_c.decode(),
        "nonce": nonce_c.decode()
    }
    transaction_data_signature = cryptography.signature(keys["payment_gateway_private_key"], pickle.dumps(transaction_data))

    conn.send(pickle.dumps({
        "response": cryptography.encrypt_with_session_key(keys["merchant_payment_gateway_key"], response),
        "sid": cryptography.encrypt_with_session_key(keys["merchant_payment_gateway_key"], sid_c),
        "transaction_data_signature": cryptography.encrypt_with_session_key(keys["merchant_payment_gateway_key"],transaction_data_signature)
    }))

    #salvam rezultatul in baza de date, in caz de resolution
    history = None
    with open("data/history.json", "r") as file:
        history = json.load(file)
        history.append(transaction_data)
    
    with open("data/history.json", "w") as file:
        file.write(json.dumps(history, indent=4))

    #TODO: modificam banii de pe cartile de credit