"""WireGuard Interface Manager for Private Cluster Network (Feature 30).

Provides Curve25519 (X25519) key generation, public key derivation, key validation,
canonical wg0.conf INI configuration generation, and dynamic cluster IP allocation.
"""

from __future__ import annotations

import base64
import ipaddress
from typing import Any, Dict, Iterable, List, Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519

from shared.schemas.cluster import ClusterNode, WireGuardPeerConfig


def generate_wireguard_keypair() -> Tuple[str, str]:
    """Generates a WireGuard Curve25519 (X25519) keypair.

    Returns:
        Tuple[str, str]: (private_key_b64, public_key_b64)
        Each key is a raw 32-byte Curve25519 key base64-encoded to 44 characters,
        matching standard WireGuard `wg genkey` and `wg pubkey`.
    """
    priv_key = x25519.X25519PrivateKey.generate()
    pub_key = priv_key.public_key()

    raw_priv = priv_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    raw_pub = pub_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    b64_priv = base64.b64encode(raw_priv).decode("ascii")
    b64_pub = base64.b64encode(raw_pub).decode("ascii")
    return b64_priv, b64_pub


def get_wireguard_public_key(private_key_b64: str) -> str:
    """Derives the Curve25519 public key from a base64-encoded WireGuard private key.

    Args:
        private_key_b64: 44-character base64-encoded private key.

    Returns:
        str: 44-character base64-encoded public key.

    Raises:
        ValueError: If key is not valid base64 or not 32 raw bytes.
    """
    try:
        raw_priv = base64.b64decode(private_key_b64, validate=True)
    except Exception as exc:
        raise ValueError(f"Invalid base64 encoding for private key: {exc}") from exc

    if len(raw_priv) != 32:
        raise ValueError(f"Invalid WireGuard private key length: {len(raw_priv)} bytes (expected 32)")

    priv_key = x25519.X25519PrivateKey.from_private_bytes(raw_priv)
    raw_pub = priv_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw_pub).decode("ascii")


def validate_wireguard_key(key_b64: str) -> bool:
    """Validates whether a string is a valid 32-byte base64-encoded Curve25519 key.

    Args:
        key_b64: String candidate key.

    Returns:
        bool: True if valid 32-byte base64 key, False otherwise.
    """
    if not isinstance(key_b64, str) or len(key_b64.strip()) != 44:
        return False
    try:
        decoded = base64.b64decode(key_b64.strip(), validate=True)
        return len(decoded) == 32
    except Exception:
        return False


def allocate_cluster_ip(
    existing_nodes: Iterable[ClusterNode],
    subnet: str = "10.42.0.0/24",
) -> str:
    """Allocates the next available private IPv4 address within the cluster subnet.

    Reserves host 1 (e.g. 10.42.0.1) for the controller / coordinator node.
    Worker nodes are sequentially allocated from host 2 upwards.

    Args:
        existing_nodes: Collection of currently registered nodes.
        subnet: CIDR notation of cluster VPN subnet.

    Returns:
        str: Available IPv4 address string (e.g. "10.42.0.2").

    Raises:
        RuntimeError: If all addresses in the subnet pool are exhausted.
    """
    network = ipaddress.ip_network(subnet, strict=False)
    allocated: set[str] = set()

    for node in existing_nodes:
        if node.wireguard_ip:
            clean_ip = node.wireguard_ip.split("/")[0].strip()
            allocated.add(clean_ip)

    # Controller is 10.42.0.1
    controller_ip = str(network.network_address + 1)
    allocated.add(controller_ip)

    for host in network.hosts():
        ip_str = str(host)
        if ip_str not in allocated:
            return ip_str

    raise RuntimeError(f"Subnet {subnet} address space exhausted (all IPs allocated)")


def build_wireguard_config(
    node: ClusterNode,
    peers: List[ClusterNode],
    private_key: Optional[str] = None,
    listen_port: Optional[int] = None,
) -> str:
    """Generates canonical wg0.conf INI configuration for a node.

    Args:
        node: The local ClusterNode generating this interface configuration.
        peers: List of peer ClusterNode instances.
        private_key: Explicit private key override (defaults to node.wireguard_private_key
            or redacted placeholder).
        listen_port: Optional port override (defaults to node.listen_port).

    Returns:
        str: wg0.conf formatted INI configuration string.
    """
    priv_key = private_key or node.wireguard_private_key or "<REDACTED_NODE_PRIVATE_KEY>"
    port = listen_port or node.listen_port or 51820

    # Ensure Address has CIDR prefix
    address = node.wireguard_ip if "/" in node.wireguard_ip else f"{node.wireguard_ip}/24"

    lines = [
        "[Interface]",
        f"PrivateKey = {priv_key}",
        f"Address = {address}",
        f"ListenPort = {port}",
        "",
    ]

    for peer in peers:
        # Never add self as a peer
        if peer.node_id == node.node_id:
            continue

        if peer.allowed_ips:
            if isinstance(peer.allowed_ips, list):
                peer_allowed = ", ".join(peer.allowed_ips)
            else:
                peer_allowed = str(peer.allowed_ips)
        else:
            clean_peer_ip = peer.wireguard_ip.split("/")[0]
            peer_allowed = f"{clean_peer_ip}/32"

        lines.append("[Peer]")
        lines.append(f"# Node: {peer.node_id}")
        lines.append(f"PublicKey = {peer.wireguard_public_key}")
        lines.append(f"AllowedIPs = {peer_allowed}")
        if peer.endpoint:
            lines.append(f"Endpoint = {peer.endpoint}")
        lines.append("PersistentKeepalive = 25")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def parse_wireguard_config(config_text: str) -> Dict[str, Any]:
    """Parses a WireGuard configuration string into structured dictionary."""
    result: Dict[str, Any] = {"interface": {}, "peers": []}
    current_section: Optional[str] = None
    current_peer: Dict[str, Any] = {}

    for raw_line in config_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            sec = line[1:-1].strip()
            if sec == "Interface":
                current_section = "Interface"
            elif sec == "Peer":
                current_section = "Peer"
                current_peer = {}
                result["peers"].append(current_peer)
            continue
        if "=" in line:
            key, val = [x.strip() for x in line.split("=", 1)]
            if current_section == "Interface":
                result["interface"][key] = val
            elif current_section == "Peer":
                current_peer[key] = val

    return result
