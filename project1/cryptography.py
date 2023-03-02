from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import AES, PKCS1_OAEP
from Cryptodome.Hash import SHA256
from Cryptodome.Signature import pkcs1_15
from os import urandom

def generate_asymmetric_keys():
    key = RSA.generate(1024)

    private_key_bytes = key.export_key()
    public_key_bytes = key.publickey().export_key()

    return (public_key_bytes, private_key_bytes)

def load_asymmetric_keys(public_key_bytes, private_key_bytes):
    public_key = RSA.import_key(public_key_bytes)
    private_key = RSA.import_key(private_key_bytes)

    return (public_key, private_key)

def load_one_asymmetric_key(bytes_key):
    return RSA.import_key(bytes_key)

def encrypt_with_public_key(public_key, message):
    if(isinstance(message, str)):
        message = message.encode() #string to bytes

    cipher = PKCS1_OAEP.new(public_key)
    encrypted_message = cipher.encrypt(message)

    return encrypted_message

def decrypt_with_private_key(private_key, message):
    cipher = PKCS1_OAEP.new(private_key)

    try:
        decrypted_message = cipher.decrypt(message)
        return decrypted_message
    except ValueError:
        return None

def generate_session_key():
    session_key = urandom(16)

    return session_key

def encrypt_with_session_key(session_key, message):
    if(isinstance(message, str)):
        message = message.encode() #string to bytes

    cipher = AES.new(session_key, AES.MODE_EAX)
    nonce = cipher.nonce
    ciphertext, tag = cipher.encrypt_and_digest(message)

    return (ciphertext, tag, nonce)

def decrypt_with_session_key(session_key, ciphertext, tag, nonce):
    cipher = AES.new(session_key, AES.MODE_EAX, nonce=nonce)
    plaintext = cipher.decrypt(ciphertext)

    try:
        cipher.verify(tag)
        return plaintext
    except ValueError:
        return None

def signature(private_key, message):
    if(isinstance(message, str)):
        message = message.encode() #string to bytes

    h = SHA256.new(message)
    signature = pkcs1_15.new(private_key).sign(h)

    return signature

def check_signature(public_key, message, signature):
    h = SHA256.new(message)

    try:
        pkcs1_15.new(public_key).verify(h, signature)
        return True
    except (ValueError, TypeError):
        return False