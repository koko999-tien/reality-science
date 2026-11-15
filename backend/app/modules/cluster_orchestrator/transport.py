"""Cluster Communication Transport Abstractions (Feature 30).

Provides abstract transport interface and a rootless, user-space
MockWireGuardTunnelTransport that validates WireGuard Cryptokey Routing
rules while executing authentic Python mutual TLS (mTLS) socket handshakes
over loopback in unprivileged CI/CD environments.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, Union

from app.modules.cluster_orchestrator.mtls import create_mtls_ssl_context
from shared.schemas.cluster import ClusterNode


class ClusterTransport(ABC):
    """Abstract cluster communication transport for inter-node dispatch and messaging."""

    @abstractmethod
    async def send_to_node(self, target_node: ClusterNode, message: bytes) -> bytes:
        """Sends an encrypted message to a target node and awaits the response."""
        raise NotImplementedError

    @abstractmethod
    async def start_server(
        self,
        node: ClusterNode,
        handler: Callable[[bytes, Dict[str, Any]], Awaitable[bytes]],
    ) -> int:
        """Starts a listening server for incoming cluster messages.

        Returns:
            int: Bound TCP/TLS port.
        """
        raise NotImplementedError

    @abstractmethod
    async def stop_server(self) -> None:
        """Stops the listening server and releases bound resources."""
        raise NotImplementedError


class MockWireGuardTunnelTransport(ClusterTransport):
    """Rootless user-space transport simulating WireGuard Cryptokey Routing and mTLS.

    Enforces:
    1. WireGuard Cryptokey Routing: Peer public keys and internal WireGuard IPs must match.
    2. Strict Mutual TLS: Validates X.509 certificates against the Cluster CA (verify_mode = ssl.CERT_REQUIRED).
    3. Zero Root Privileges: Runs over unprivileged local TCP sockets in CI/CD without kernel TUN devices.
    """

    def __init__(
        self,
        ca_cert_pem: Union[str, bytes],
        local_node: ClusterNode,
        node_cert_pem: Union[str, bytes],
        node_key_pem: Union[str, bytes],
    ) -> None:
        self.ca_cert_pem = ca_cert_pem
        self.local_node = local_node
        self.node_cert_pem = node_cert_pem
        self.node_key_pem = node_key_pem
        self.server: Optional[asyncio.Server] = None
        self.port: Optional[int] = None
        self.cryptokey_routing_table: Dict[str, str] = {}  # clean_ip -> wg_public_key
        self.endpoint_routing_table: Dict[str, Tuple[str, int]] = {}  # clean_ip -> (host, port)

    def register_peer_route(self, peer: ClusterNode, host: str, port: int) -> None:
        """Registers a routing table entry simulating the WireGuard peer cryptokey routing table.

        Args:
            peer: Peer cluster node.
            host: Physical/loopback IP address.
            port: Bound mTLS port.
        """
        clean_ip = peer.wireguard_ip.split("/")[0].strip()
        self.cryptokey_routing_table[clean_ip] = peer.wireguard_public_key
        self.endpoint_routing_table[clean_ip] = (host, port)

    async def start_server(
        self,
        node: ClusterNode,
        handler: Callable[[bytes, Dict[str, Any]], Awaitable[bytes]],
    ) -> int:
        """Starts an authentic mTLS socket server on 127.0.0.1 requiring client certificates."""
        server_ctx = create_mtls_ssl_context(
            ca_cert_pem=self.ca_cert_pem,
            cert_pem=self.node_cert_pem,
            key_pem=self.node_key_pem,
            is_server=True,
            check_hostname=False,
        )

        async def _client_connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                peercert = writer.get_extra_info("peercert") or {}
                client_subject = dict(x[0] for x in peercert.get("subject", []))
                client_node_id = client_subject.get("commonName", "unknown")

                # Read 4-byte length prefix
                raw_len = await reader.readexactly(4)
                msg_len = int.from_bytes(raw_len, byteorder="big")
                data = await reader.readexactly(msg_len)

                metadata: Dict[str, Any] = {
                    "client_node_id": client_node_id,
                    "peercert": peercert,
                }
                resp = await handler(data, metadata)

                # Write 4-byte length prefix + response
                writer.write(len(resp).to_bytes(4, byteorder="big") + resp)
                await writer.drain()
            except Exception:
                pass
            finally:
                writer.close()
                await writer.wait_closed()

        self.server = await asyncio.start_server(_client_connected, "127.0.0.1", 0, ssl=server_ctx)
        self.port = self.server.sockets[0].getsockname()[1]
        return self.port

    async def stop_server(self) -> None:
        """Stops the listening server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            self.port = None

    async def send_to_node(self, target_node: ClusterNode, message: bytes) -> bytes:
        """Sends payload to target node over mTLS after verifying WireGuard cryptokey routing."""
        clean_ip = target_node.wireguard_ip.split("/")[0].strip()

        # Enforce WireGuard Cryptokey Routing check
        expected_pubkey = self.cryptokey_routing_table.get(clean_ip)
        if expected_pubkey and expected_pubkey != target_node.wireguard_public_key:
            raise PermissionError(
                f"WireGuard Cryptokey Routing violation for node '{target_node.node_id}': "
                f"key mismatch on IP {clean_ip}"
            )

        endpoint = self.endpoint_routing_table.get(clean_ip)
        if not endpoint:
            if target_node.endpoint and ":" in target_node.endpoint:
                h, p = target_node.endpoint.split(":")
                endpoint = (h, int(p))
            else:
                raise ConnectionError(f"No routable endpoint registered for WireGuard IP {clean_ip}")

        client_ctx = create_mtls_ssl_context(
            ca_cert_pem=self.ca_cert_pem,
            cert_pem=self.node_cert_pem,
            key_pem=self.node_key_pem,
            is_server=False,
            check_hostname=False,
        )

        reader, writer = await asyncio.open_connection(endpoint[0], endpoint[1], ssl=client_ctx)
        try:
            # Write 4-byte length-prefixed payload
            writer.write(len(message).to_bytes(4, byteorder="big") + message)
            await writer.drain()

            # Read 4-byte length-prefixed response
            raw_len = await reader.readexactly(4)
            resp_len = int.from_bytes(raw_len, byteorder="big")
            resp = await reader.readexactly(resp_len)
            return resp
        finally:
            writer.close()
            await writer.wait_closed()
