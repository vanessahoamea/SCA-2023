from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.Cipher import AES
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

def encrypt_with_public_key(public_key, message):
    message = message.encode() #string to bytes

    cipher = PKCS1_OAEP.new(public_key)
    encrypted_message = cipher.encrypt(message)

    return encrypted_message

def decrypt_with_private_key(private_key, message):
    cipher = PKCS1_OAEP.new(private_key)
    decrypted_message = cipher.decrypt(message)

    decrypted_message = decrypted_message.decode() #bytes to string

    return decrypted_message

def generate_session_key():
    session_key = urandom(16)

    return session_key

def encrypt_with_session_key(session_key, message):
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
        plaintext = plaintext.decode() #bytes to string
        return plaintext
    except ValueError:
        return None