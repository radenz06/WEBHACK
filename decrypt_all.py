#!/usr/bin/env python3
"""WEBHACK v4.0.1 - Decrypt All Files"""
import sys, os, base64, hashlib, zlib
from pathlib import Path

password = sys.argv[1] if len(sys.argv) > 1 else "inccessaden"

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
    root = Path(__file__).parent
    for enc_file in sorted(root.glob("*.enc")):
        try:
            data = decrypt_file(enc_file, password)
            out_name = enc_file.name.replace(".enc", "")
            Path(out_name).write_bytes(data)
            print(f"  Decrypted: {enc_file.name} -> {out_name}")
        except Exception as e:
            print(f"  ERROR: {enc_file.name}: {e}")
    print("Done! Run: python3 scan2.py | python3 xweb.py | python3 osint.py")

if __name__ == "__main__":
    main()
