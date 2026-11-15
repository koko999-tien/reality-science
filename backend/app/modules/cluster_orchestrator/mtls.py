"""Mutual TLS (mTLS) Authentication Subsystem for Cluster Nodes (Feature 30).

Provides X.509 Cluster Root Certificate Authority (CA) generation,
node client/server certificate issuance with Subject Alternative Names (SANs)
and ExtendedKeyUsage, SHA-256 fingerprint generation, certificate verification,
and configuration of mutual TLS SSLContext instances enforcing `ssl.CERT_REQUIRED`.
"""

from __future__ import annotations

import datetime
import ipaddress
import os
import ssl
import tempfile
from typing import List, Optional, Tuple, Union

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


class ClusterCertificateAuthority:
    """X.509 Cluster Certificate Authority managing mutual TLS identity and trust."""

    def __init__(
        self,
        ca_cert_pem: Optional[Union[str, bytes]] = None,
        ca_key_pem: Optional[Union[str, bytes]] = None,
        common_name: str = "Reality Science Cluster Root CA",
        organization: str = "Reality Science",
        validity_days: int = 3650,
    ) -> None:
        """Initializes or loads the Cluster Certificate Authority.

        Args:
            ca_cert_pem: Optional existing CA certificate in PEM format.
            ca_key_pem: Optional existing CA private key in PEM format.
            common_name: Subject Common Name for self-signed CA.
            organization: Organization name for CA subject.
            validity_days: Validity duration in days (default 10 years).
        """
        if ca_cert_pem and ca_key_pem:
            cert_bytes = ca_cert_pem.encode("utf-8") if isinstance(ca_cert_pem, str) else ca_cert_pem
            key_bytes = ca_key_pem.encode("utf-8") if isinstance(ca_key_pem, str) else ca_key_pem
            self.ca_cert = x509.load_pem_x509_certificate(cert_bytes)
            self.ca_key = serialization.load_pem_private_key(key_bytes, password=None)
        else:
            self.ca_key = ec.generate_private_key(ec.SECP256R1())
            ca_name = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Cluster Security Mesh"),
            ])
            now = datetime.datetime.now(datetime.timezone.utc)
            self.ca_cert = (
                x509.CertificateBuilder()
                .subject_name(ca_name)
                .issuer_name(ca_name)
                .public_key(self.ca_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - datetime.timedelta(minutes=5))
                .not_valid_after(now + datetime.timedelta(days=validity_days))
                .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .add_extension(
                    x509.KeyUsage(
                        digital_signature=True,
                        content_commitment=False,
                        key_encipherment=False,
                        data_encipherment=False,
                        key_agreement=False,
                        key_cert_sign=True,
                        crl_sign=True,
                        encipher_only=False,
                        decipher_only=False,
                    ),
                    critical=True,
                )
                .add_extension(
                    x509.SubjectKeyIdentifier.from_public_key(self.ca_key.public_key()),
                    critical=False,
                )
                .sign(self.ca_key, hashes.SHA256())
            )

    def export_ca_pem(self) -> str:
        """Exports the Root CA certificate in PEM string format."""
        return self.ca_cert.public_bytes(serialization.Encoding.PEM).decode("ascii")

    def export_ca_key_pem(self) -> str:
        """Exports the Root CA private key in PEM string format."""
        return self.ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")

    def get_ca_cert_pem(self) -> str:
        """Alias for export_ca_pem."""
        return self.export_ca_pem()

    def issue_node_certificate(
        self,
        node_id: str,
        san_ips: Optional[List[str]] = None,
        san_dns: Optional[List[str]] = None,
        validity_days: int = 365,
    ) -> Tuple[str, str]:
        """Issues an X.509 dual-use client/server certificate for a cluster node.

        Configures:
        - BasicConstraints(ca=False)
        - ExtendedKeyUsage([SERVER_AUTH, CLIENT_AUTH])
        - SubjectAlternativeName for provided IP addresses and DNS hostnames
        - AuthorityKeyIdentifier and SubjectKeyIdentifier

        Args:
            node_id: Unique cluster node identifier (used as Common Name).
            san_ips: List of IP addresses to include in SAN (e.g. WireGuard IP, 127.0.0.1).
            san_dns: List of DNS hostnames to include in SAN.
            validity_days: Certificate validity in days.

        Returns:
            Tuple[str, str]: (node_cert_pem, node_key_pem) as strings.
        """
        node_key = ec.generate_private_key(ec.SECP256R1())
        subject_name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, node_id),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Reality Science Cluster Node"),
        ])

        san_general_names: list[x509.GeneralName] = []

        # Add DNS SANs
        dns_names = set(san_dns or [])
        dns_names.add(node_id)
        dns_names.add("localhost")
        for d in sorted(dns_names):
            san_general_names.append(x509.DNSName(d))

        # Add IP SANs
        ip_addresses = set(san_ips or [])
        ip_addresses.add("127.0.0.1")
        for raw_ip in sorted(ip_addresses):
            clean_ip = raw_ip.split("/")[0].strip()
            try:
                san_general_names.append(x509.IPAddress(ipaddress.ip_address(clean_ip)))
            except ValueError:
                # If not a valid IP, add as DNS
                san_general_names.append(x509.DNSName(clean_ip))

        now = datetime.datetime.now(datetime.timezone.utc)
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject_name)
            .issuer_name(self.ca_cert.subject)
            .public_key(node_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=5))
            .not_valid_after(now + datetime.timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=True,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([
                    ExtendedKeyUsageOID.SERVER_AUTH,
                    ExtendedKeyUsageOID.CLIENT_AUTH,
                ]),
                critical=False,
            )
            .add_extension(x509.SubjectAlternativeName(san_general_names), critical=False)
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(node_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(self.ca_key.public_key()),
                critical=False,
            )
        )

        node_cert = cert_builder.sign(self.ca_key, hashes.SHA256())

        cert_pem = node_cert.public_bytes(serialization.Encoding.PEM).decode("ascii")
        key_pem = node_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        return cert_pem, key_pem

    def get_certificate_fingerprint(self, cert_pem: Union[str, bytes]) -> str:
        """Returns the SHA-256 lowercase hex fingerprint of a PEM certificate.

        Args:
            cert_pem: Certificate in PEM format (str or bytes).

        Returns:
            str: 64-character lowercase hexadecimal SHA-256 digest.
        """
        raw = cert_pem.encode("utf-8") if isinstance(cert_pem, str) else cert_pem
        cert = x509.load_pem_x509_certificate(raw)
        return cert.fingerprint(hashes.SHA256()).hex().lower()

    def verify_certificate(self, cert_pem: Union[str, bytes]) -> bool:
        """Cryptographically verifies that a certificate is signed by this CA and is valid.

        Args:
            cert_pem: Candidate node certificate in PEM format.

        Returns:
            bool: True if signature is valid and current time is within validity window.
        """
        try:
            raw = cert_pem.encode("utf-8") if isinstance(cert_pem, str) else cert_pem
            cert = x509.load_pem_x509_certificate(raw)

            # Verify signature against CA public key
            ca_pubkey = self.ca_key.public_key()
            if isinstance(ca_pubkey, ec.EllipticCurvePublicKey):
                ca_pubkey.verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    ec.ECDSA(cert.signature_hash_algorithm),
                )
            else:
                return False

            # Verify validity dates
            now = datetime.datetime.now(datetime.timezone.utc)
            if now < cert.not_valid_before_utc or now > cert.not_valid_after_utc:
                return False

            return True
        except Exception:
            return False


def create_mtls_ssl_context(
    ca_cert_pem: Union[str, bytes],
    cert_pem: Union[str, bytes],
    key_pem: Union[str, bytes],
    is_server: bool = True,
    check_hostname: bool = False,
) -> ssl.SSLContext:
    """Creates a mutual TLS SSLContext with mandatory peer certificate verification.

    Args:
        ca_cert_pem: CA certificate in PEM format.
        cert_pem: Node certificate in PEM format.
        key_pem: Node private key in PEM format.
        is_server: True for server context (CLIENT_AUTH), False for client (SERVER_AUTH).
        check_hostname: Whether to enforce hostname verification against certificate SAN.

    Returns:
        ssl.SSLContext: Configured SSL context with verify_mode = ssl.CERT_REQUIRED.
    """
    ca_str = ca_cert_pem.decode("ascii") if isinstance(ca_cert_pem, bytes) else str(ca_cert_pem)
    cert_str = cert_pem.decode("ascii") if isinstance(cert_pem, bytes) else str(cert_pem)
    key_str = key_pem.decode("ascii") if isinstance(key_pem, bytes) else str(key_pem)

    if is_server:
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.verify_mode = ssl.CERT_REQUIRED
    else:
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.check_hostname = check_hostname

    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_verify_locations(cadata=ca_str)

    # Securely load certificate and private key via temporary files
    cf_fd, cf_path = tempfile.mkstemp(suffix=".crt")
    kf_fd, kf_path = tempfile.mkstemp(suffix=".key")
    try:
        with open(cf_fd, "w", encoding="utf-8") as f:
            f.write(cert_str)
        with open(kf_fd, "w", encoding="utf-8") as f:
            f.write(key_str)
        ctx.load_cert_chain(certfile=cf_path, keyfile=kf_path)
    finally:
        if os.path.exists(cf_path):
            os.unlink(cf_path)
        if os.path.exists(kf_path):
            os.unlink(kf_path)

    return ctx
