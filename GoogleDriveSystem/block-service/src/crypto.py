from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os
import hashlib

# Use environment variable or generate a key (in production, use a secure key management system)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "0" * 32).encode()[:32]

def get_hash(data: bytes) -> str:
    """Calculate SHA256 hash of data"""
    return hashlib.sha256(data).hexdigest()

def encrypt_data(data: bytes) -> tuple[bytes, bytes]:
    """Encrypt data using AES-256 CBC mode"""
    # Generate random IV
    iv = os.urandom(16)
    
    # Pad data to multiple of 16 bytes
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()
    
    # Create cipher and encrypt
    cipher = Cipher(
        algorithms.AES(ENCRYPTION_KEY),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    
    return encrypted, iv

def decrypt_data(encrypted_data: bytes, iv: bytes) -> bytes:
    """Decrypt data using AES-256 CBC mode"""
    # Create cipher and decrypt
    cipher = Cipher(
        algorithms.AES(ENCRYPTION_KEY),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
    
    # Remove padding
    unpadder = padding.PKCS7(128).unpadder()
    decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
    
    return decrypted