#!/usr/bin/env python3
"""WEBHACK v4.0.1 - Decrypt and Run osint.py"""
import sys, os, base64, hashlib, zlib
from pathlib import Path

def decrypt_file(enc_path, password):
    enc = enc_path.read_bytes()
    rev = enc.decode()[::-1]
    b64_1 = base64.b64decode(rev).decode()
    xor_data = base64.b64decode(b64_1)
    pwd_hash = hashlib.sha256(password.encode()).digest()
    xor_stream = (pwd_hash * (len(xor_data) // 32 + 1))[:len(xor_data)]
    compressed = bytes(a ^ b for a, b in zip(xor_data, xor_stream))
    data = zlib.decompress(compressed)
    return data

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_osint.py <password>")
        sys.exit(1)
    password = sys.argv[1]
    enc_file = Path(__file__).parent / "osint.py.enc"
    if not enc_file.exists():
        print(f"Error: {enc_file} not found")
        sys.exit(1)
    try:
        data = decrypt_file(enc_file, password)
        exec(data.decode())
    except Exception as e:
        print(f"Decryption failed: {e}")
        print("Wrong password?")
        sys.exit(1)

if __name__ == "__main__":
    main()
