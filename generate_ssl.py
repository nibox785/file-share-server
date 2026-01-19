"""
Script tạo SSL certificates cho Windows (thay thế cho OpenSSL)
Chạy: python generate_ssl.py
"""

import os
import sys

def generate_ssl_certificates():
    """Tạo self-signed SSL certificate sử dụng Python cryptography library"""
    
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
    except ImportError:
        print("Đang cài đặt thư viện cryptography...")
        os.system(f"{sys.executable} -m pip install cryptography")
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime

    # Tạo thư mục ssl_certs nếu chưa có
    ssl_dir = "ssl_certs"
    if not os.path.exists(ssl_dir):
        os.makedirs(ssl_dir)
        print(f"✅ Đã tạo thư mục {ssl_dir}/")

    # Tạo private key (RSA 4096 bits)
    print("🔑 Đang tạo private key (RSA 4096 bits)...")
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )

    # Tạo self-signed certificate
    print("📜 Đang tạo self-signed certificate...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Ho Chi Minh"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Ho Chi Minh City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "File Share Server"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
        ]),
        critical=False,
    ).sign(key, hashes.SHA256(), default_backend())

    # Lưu private key
    key_path = os.path.join(ssl_dir, "server.key")
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"✅ Đã lưu private key: {key_path}")

    # Lưu certificate
    cert_path = os.path.join(ssl_dir, "server.crt")
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"✅ Đã lưu certificate: {cert_path}")

    print("\n🎉 Tạo SSL certificates thành công!")
    print(f"   - Private Key: {key_path}")
    print(f"   - Certificate: {cert_path}")
    print(f"   - Thời hạn: 365 ngày")

if __name__ == "__main__":
    generate_ssl_certificates()
