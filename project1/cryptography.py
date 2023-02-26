import rsa

def generate_asymmetric_keys():
    (public_key, private_key) = rsa.newkeys(512)

    public_key_bytes = public_key.save_pkcs1()
    private_key_bytes = private_key.save_pkcs1()

    return (public_key_bytes, private_key_bytes)

def load_asymmetric_keys():
    public_key = rsa.PublicKey.load_pkcs1(public_key_bytes)
    private_key = rsa.PrivateKey.load_pkcs1(private_key_bytes)

    return (public_key, private_key)

def generate_session_key():
    pass