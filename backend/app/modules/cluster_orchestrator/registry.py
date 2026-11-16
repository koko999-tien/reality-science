"""Cluster Node Registry and Health Monitoring Subsystem (Feature 30).

Maintains authorized worker node inventory, coordinates node admission with join tokens,
allocates WireGuard IPs, issues mTLS certificates, monitors heartbeat health telemetry,
detects stale nodes (> 30s threshold), and enforces zero-trust rogue node blocking.
"""

from __future__ import annotations

import datetime
import hmac
import threading
import uuid
from typing import Dict, Iterable, List, Optional

from app.modules.cluster_orchestrator.mtls import ClusterCertificateAuthority
from app.modules.cluster_orchestrator.wireguard import (
    allocate_cluster_ip,
    generate_wireguard_keypair,
    validate_wireguard_key,
)
from shared.schemas.cluster import (
    ClusterNode,
    ClusterNodeRole,
    ClusterNodeStatus,
    HeartbeatPayload,
    HeartbeatResponse,
    NodeJoinRequest,
    NodeJoinResponse,
    WireGuardPeerConfig,
)


class ClusterNodeRegistry:
    """Zero-trust node registry maintaining authorized cluster workers."""

    def __init__(
        self,
        ca: Optional[ClusterCertificateAuthority] = None,
        cluster_secret: Optional[str] = None,
        controller_ip: str = "10.42.0.1",
        controller_endpoint: str = "127.0.0.1:8443",
        subnet: str = "10.42.0.0/24",
    ) -> None:
        self.ca = ca or ClusterCertificateAuthority()
        self.cluster_secret = cluster_secret
        self.controller_ip = controller_ip
        self.controller_endpoint = controller_endpoint
        self.subnet = subnet
        self._lock = threading.Lock()
        self._nodes: Dict[str, ClusterNode] = {}

        # Pre-register Controller Node
        ctrl_priv, ctrl_pub = generate_wireguard_keypair()
        ctrl_cert, ctrl_key = self.ca.issue_node_certificate(
            node_id="controller-node",
            san_ips=[controller_ip, "127.0.0.1"],
            san_dns=["controller-node", "localhost"],
        )
        ctrl_fingerprint = self.ca.get_certificate_fingerprint(ctrl_cert)

        self.controller_node = ClusterNode(
            node_id="controller-node",
            hostname="controller-node",
            wireguard_ip=controller_ip,
            wireguard_public_key=ctrl_pub,
            wireguard_private_key=ctrl_priv,
            endpoint=controller_endpoint,
            role=ClusterNodeRole.CONTROLLER,
            status=ClusterNodeStatus.ACTIVE,
            cert_fingerprint=ctrl_fingerprint,
            certificate_pem=ctrl_cert,
            allowed_ips=[subnet],
            capacity=128,
            registered_at=datetime.datetime.now(datetime.timezone.utc),
            last_heartbeat=datetime.datetime.now(datetime.timezone.utc),
        )
        self.controller_key_pem = ctrl_key
        self._nodes[self.controller_node.node_id] = self.controller_node

    def register_node(self, request: NodeJoinRequest) -> NodeJoinResponse:
        """Admits a new node to the cluster after validating join token and WireGuard key.

        Args:
            request: Node admission request payload.

        Returns:
            NodeJoinResponse: Cluster credentials, assigned IP, mTLS certificates, and peer list.

        Raises:
            PermissionError: If join token is invalid or existing node is blocked.
            ValueError: If WireGuard public key is invalid or duplicate identity conflict.
        """
        with self._lock:
            # 1. Validate join token
            if not self.cluster_secret or not hmac.compare_digest(request.join_token, self.cluster_secret):
                raise PermissionError("Invalid cluster join token: access denied")

            # 2. Validate WireGuard public key
            if not validate_wireguard_key(request.wireguard_public_key):
                raise ValueError("Invalid WireGuard Curve25519 public key (must be 32 bytes base64)")

            # 3. Determine unique node_id
            node_id = f"node-{request.hostname}-{uuid.uuid4().hex[:6]}"

            # Check for existing node with identical hostname or public key
            for existing in self._nodes.values():
                if existing.hostname == request.hostname and existing.role != ClusterNodeRole.CONTROLLER:
                    if existing.status == ClusterNodeStatus.BLOCKED:
                        raise PermissionError(f"Node with hostname '{request.hostname}' is blocked by cluster security policy")
                    if existing.wireguard_public_key != request.wireguard_public_key:
                        existing.status = ClusterNodeStatus.BLOCKED
                        raise PermissionError(f"Zero-trust violation: public key mismatch for hostname '{request.hostname}'. Node blocked.")

            # 4. Allocate WireGuard IP
            if request.requested_ip:
                clean_req_ip = request.requested_ip.split("/")[0].strip()
                existing_ips = {n.wireguard_ip.split("/")[0].strip() for n in self._nodes.values()}
                if clean_req_ip not in existing_ips:
                    assigned_ip = clean_req_ip
                else:
                    assigned_ip = allocate_cluster_ip(self._nodes.values(), subnet=self.subnet)
            else:
                assigned_ip = allocate_cluster_ip(self._nodes.values(), subnet=self.subnet)

            # 5. Issue X.509 dual-use mTLS certificate
            cert_pem, key_pem = self.ca.issue_node_certificate(
                node_id=node_id,
                san_ips=[assigned_ip],
                san_dns=[request.hostname, node_id],
            )
            cert_fingerprint = self.ca.get_certificate_fingerprint(cert_pem)

            # 6. Build peer configuration list for the joining node
            peers: List[WireGuardPeerConfig] = []
            for peer in self._nodes.values():
                peer_allowed = peer.allowed_ips or [f"{peer.wireguard_ip}/32"]
                peers.append(
                    WireGuardPeerConfig(
                        public_key=peer.wireguard_public_key,
                        allowed_ips=peer_allowed,
                        endpoint=peer.endpoint,
                        node_id=peer.node_id,
                    )
                )

            # 7. Record node in registry
            new_node = ClusterNode(
                node_id=node_id,
                hostname=request.hostname,
                wireguard_ip=assigned_ip,
                wireguard_public_key=request.wireguard_public_key,
                endpoint=request.endpoint,
                allowed_ips=[f"{assigned_ip}/32"],
                role=request.role,
                status=ClusterNodeStatus.ACTIVE,
                cert_fingerprint=cert_fingerprint,
                certificate_pem=cert_pem,
                registered_at=datetime.datetime.now(datetime.timezone.utc),
                last_heartbeat=datetime.datetime.now(datetime.timezone.utc),
                metadata=request.metadata,
            )
            self._nodes[node_id] = new_node

            return NodeJoinResponse(
                node_id=node_id,
                status=new_node.status,
                assigned_wireguard_ip=assigned_ip,
                issued_cert_pem=cert_pem,
                ca_cert_pem=self.ca.export_ca_pem(),
                peers=peers,
                controller_endpoint=self.controller_endpoint,
                message=f"Node '{node_id}' successfully admitted to private cluster network.",
            )

    def record_heartbeat(
        self,
        payload: HeartbeatPayload,
        claimed_fingerprint: Optional[str] = None,
        claimed_pubkey: Optional[str] = None,
    ) -> HeartbeatResponse:
        """Records node telemetry and checks for zero-trust anomalies.

        Args:
            payload: Heartbeat metrics (load average, active tasks).
            claimed_fingerprint: Optional client certificate fingerprint.
            claimed_pubkey: Optional WireGuard public key from connection.

        Returns:
            HeartbeatResponse: Status and action directive.

        Raises:
            KeyError: If node_id is not found in registry.
            PermissionError: If node is blocked or zero-trust violation detected.
        """
        with self._lock:
            node = self._nodes.get(payload.node_id)
            if not node:
                raise KeyError(f"Node '{payload.node_id}' is not registered in cluster")

            # Check if already blocked
            if node.status in (ClusterNodeStatus.BLOCKED, ClusterNodeStatus.UNAUTHORIZED):
                raise PermissionError(f"Node '{payload.node_id}' is BLOCKED by cluster security policy")

            # Zero-trust verification: check claimed fingerprint
            if claimed_fingerprint and node.cert_fingerprint:
                if claimed_fingerprint.lower() != node.cert_fingerprint.lower():
                    node.status = ClusterNodeStatus.BLOCKED
                    raise PermissionError(
                        f"Zero-trust violation: Certificate fingerprint mismatch for node '{payload.node_id}'. Node BLOCKED."
                    )

            # Zero-trust verification: check claimed public key
            if claimed_pubkey and claimed_pubkey != node.wireguard_public_key:
                node.status = ClusterNodeStatus.BLOCKED
                raise PermissionError(
                    f"Zero-trust violation: WireGuard public key mismatch for node '{payload.node_id}'. Node BLOCKED."
                )

            # Update telemetry
            node.last_heartbeat = datetime.datetime.now(datetime.timezone.utc)
            node.load_average = payload.load_average
            node.active_tasks = payload.active_tasks

            # If node was UNHEALTHY, restore to ACTIVE upon valid heartbeat
            if node.status == ClusterNodeStatus.UNHEALTHY:
                node.status = ClusterNodeStatus.ACTIVE

            action = "DRAIN" if node.status in (ClusterNodeStatus.DRAINED, ClusterNodeStatus.DRAINING) else "NONE"

            return HeartbeatResponse(
                acknowledged=True,
                node_status=node.status,
                server_time=datetime.datetime.now(datetime.timezone.utc),
                action_required=action,
            )

    def mark_stale_nodes(self, threshold_seconds: float = 30.0) -> List[str]:
        """Detects nodes with stale heartbeats and transitions them to UNHEALTHY.

        Args:
            threshold_seconds: Seconds of silence before marking unhealthy (default 30.0).

        Returns:
            List[str]: Node IDs marked UNHEALTHY.
        """
        with self._lock:
            now = datetime.datetime.now(datetime.timezone.utc)
            stale: List[str] = []
            for node in self._nodes.values():
                if node.role == ClusterNodeRole.CONTROLLER:
                    continue
                if node.status in (ClusterNodeStatus.ACTIVE, ClusterNodeStatus.ONLINE):
                    if node.last_heartbeat is None or (now - node.last_heartbeat).total_seconds() > threshold_seconds:
                        node.status = ClusterNodeStatus.UNHEALTHY
                        stale.append(node.node_id)
            return stale

    def get_healthy_workers(self) -> List[ClusterNode]:
        """Returns active, healthy compute workers eligible for job dispatch."""
        self.mark_stale_nodes(threshold_seconds=30.0)
        with self._lock:
            return [
                node
                for node in self._nodes.values()
                if node.role == ClusterNodeRole.WORKER
                and node.status in (ClusterNodeStatus.ACTIVE, ClusterNodeStatus.ONLINE)
            ]

    def verify_node(self, node_id: str, wg_public_key: str, cert_fingerprint: str) -> bool:
        """Verifies that a node is registered, healthy, and matches its cryptographic identity."""
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return False
            if node.status not in (ClusterNodeStatus.ACTIVE, ClusterNodeStatus.ONLINE):
                return False
            if node.wireguard_public_key != wg_public_key:
                node.status = ClusterNodeStatus.BLOCKED
                return False
            if node.cert_fingerprint and cert_fingerprint:
                if node.cert_fingerprint.lower() != cert_fingerprint.lower():
                    node.status = ClusterNodeStatus.BLOCKED
                    return False
            return True

    def block_node(self, node_id: str) -> bool:
        """Immediately blocks a node from receiving or sending cluster traffic."""
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return False
            node.status = ClusterNodeStatus.BLOCKED
            return True

    def drain_node(self, node_id: str) -> bool:
        """Marks a node as DRAINED so no new tasks are dispatched to it."""
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return False
            node.status = ClusterNodeStatus.DRAINED
            return True

    def unblock_node(self, node_id: str) -> bool:
        """Restores a blocked or drained node to ACTIVE status."""
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return False
            node.status = ClusterNodeStatus.ACTIVE
            return True

    def get_node(self, node_id: str) -> Optional[ClusterNode]:
        """Retrieves a node by node_id."""
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(
        self,
        role: Optional[ClusterNodeRole] = None,
        status: Optional[ClusterNodeStatus] = None,
    ) -> List[ClusterNode]:
        """Lists nodes with optional role and status filters."""
        with self._lock:
            nodes = list(self._nodes.values())
            if role:
                nodes = [n for n in nodes if n.role == role]
            if status:
                nodes = [n for n in nodes if n.status == status]
            return nodes
