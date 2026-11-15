"""Shared Cluster Orchestration Schemas (Feature 30: WireGuard mTLS Private Cluster).

Defines Pydantic v2 data models, enums, and request/response contracts
for multi-cloud cluster node registration, WireGuard configuration,
health heartbeat monitoring, and distributed task dispatch.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from shared.schemas.job_bundle import JobBundle
from shared.schemas.finding_result import FindingResult


class ClusterNodeRole(str, Enum):
    """Role of a node within the private cluster topology."""
    CONTROLLER = "CONTROLLER"
    WORKER = "WORKER"
    GATEWAY = "GATEWAY"
    LEADER = "LEADER"
    RELAY = "RELAY"


class ClusterNodeStatus(str, Enum):
    """Lifecycle and operational health status of a cluster node."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    ONLINE = "ONLINE"
    UNHEALTHY = "UNHEALTHY"
    DRAINED = "DRAINED"
    DRAINING = "DRAINING"
    BLOCKED = "BLOCKED"
    UNAUTHORIZED = "UNAUTHORIZED"
    OFFLINE = "OFFLINE"


class WireGuardPeerConfig(BaseModel):
    """WireGuard cryptokey routing peer configuration."""
    model_config = ConfigDict(extra="forbid")

    public_key: str = Field(..., description="Curve25519 base64 public key (44 chars)")
    allowed_ips: Union[str, List[str]] = Field(..., description="Routed CIDR range(s) for peer")
    endpoint: Optional[str] = Field(default=None, description="WAN hostname/IP:port if reachable")
    persistent_keepalive: int = Field(default=25, ge=0, le=3600, description="Keepalive interval in seconds")
    node_id: Optional[str] = Field(default=None, description="Cluster node identifier of peer")


class ClusterNode(BaseModel):
    """Registered cluster node entity with WireGuard identity and health telemetry."""
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., description="Unique cluster node ID")
    hostname: Optional[str] = Field(default=None, description="Node hostname or DNS name")
    wireguard_ip: str = Field(..., description="Internal WireGuard IP address (e.g. 10.42.0.2)")
    wireguard_public_key: str = Field(..., description="Base64-encoded Curve25519 public key")
    wireguard_private_key: Optional[str] = Field(default=None, description="Base64-encoded Curve25519 private key")
    endpoint: Optional[str] = Field(default=None, description="Public IP/hostname:port for WAN routing")
    allowed_ips: List[str] = Field(default_factory=list, description="Subnets routed to this node")
    listen_port: int = Field(default=51820, ge=1024, le=65535, description="WireGuard UDP listen port")
    role: ClusterNodeRole = Field(default=ClusterNodeRole.WORKER, description="Role in cluster")
    status: ClusterNodeStatus = Field(default=ClusterNodeStatus.ACTIVE, description="Node lifecycle status")
    cert_fingerprint: Optional[str] = Field(default=None, description="SHA-256 hex fingerprint of X.509 cert")
    certificate_pem: Optional[str] = Field(default=None, description="X.509 PEM certificate")
    registered_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Timestamp of admission",
    )
    last_heartbeat: Optional[datetime.datetime] = Field(default=None, description="Timestamp of last heartbeat")
    capacity: int = Field(default=4, ge=1, le=128, description="Maximum concurrent compute jobs")
    load_average: float = Field(default=0.0, ge=0.0, description="Reported system load average")
    active_tasks: int = Field(default=0, ge=0, description="Number of tasks currently executing")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary node metadata")

    @property
    def active_jobs(self) -> int:
        return self.active_tasks

    @active_jobs.setter
    def active_jobs(self, val: int) -> None:
        self.active_tasks = val

    @property
    def certificate_fingerprint(self) -> Optional[str]:
        return self.cert_fingerprint

    @certificate_fingerprint.setter
    def certificate_fingerprint(self, val: Optional[str]) -> None:
        self.cert_fingerprint = val


class NodeJoinRequest(BaseModel):
    """Payload sent by a node requesting admission into the private cluster."""
    model_config = ConfigDict(extra="forbid")

    hostname: str = Field(..., description="Hostname of joining node")
    wireguard_public_key: str = Field(..., description="Curve25519 base64 public key (44 chars)")
    role: ClusterNodeRole = Field(default=ClusterNodeRole.WORKER, description="Requested role")
    join_token: str = Field(..., description="Secret cluster admission token")
    requested_ip: Optional[str] = Field(default=None, description="Optional requested WireGuard IP")
    endpoint: Optional[str] = Field(default=None, description="Optional public endpoint host:port")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional node attributes")


class NodeJoinResponse(BaseModel):
    """Admission response returned by cluster controller with networking & credentials."""
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., description="Assigned cluster node ID")
    status: ClusterNodeStatus = Field(..., description="Initial admission status")
    assigned_wireguard_ip: str = Field(..., description="Allocated WireGuard internal IP")
    issued_cert_pem: str = Field(..., description="Issued X.509 client/server certificate PEM")
    ca_cert_pem: str = Field(..., description="Cluster Root CA certificate PEM")
    peers: List[WireGuardPeerConfig] = Field(default_factory=list, description="Active cluster peer configurations")
    controller_endpoint: str = Field(..., description="Controller address for mTLS control plane")
    message: str = Field(..., description="Human-readable admission outcome")


class HeartbeatPayload(BaseModel):
    """Periodic telemetry report sent by worker nodes to controller."""
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., description="Cluster node ID reporting heartbeat")
    load_average: float = Field(default=0.0, ge=0.0, description="Current CPU/system load average")
    active_tasks: int = Field(default=0, ge=0, description="Active task count")
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Node-side report timestamp",
    )
    status: Optional[ClusterNodeStatus] = Field(default=None, description="Node operational status")

    @property
    def active_jobs(self) -> int:
        return self.active_tasks

    @active_jobs.setter
    def active_jobs(self, val: int) -> None:
        self.active_tasks = val


class HeartbeatResponse(BaseModel):
    """Controller acknowledgment returned to worker node."""
    model_config = ConfigDict(extra="forbid")

    acknowledged: bool = Field(default=True, description="Whether heartbeat was successfully recorded")
    node_status: ClusterNodeStatus = Field(..., description="Current status according to controller")
    server_time: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Controller UTC server time",
    )
    action_required: str = Field(default="NONE", description="Directive: NONE, DRAIN, RECONFIG, BLOCKED")


class ClusterTaskDispatchPayload(BaseModel):
    """Task dispatch envelope transmitted over mTLS channel."""
    model_config = ConfigDict(extra="forbid")

    target_node_id: str = Field(..., description="Destination worker node ID")
    bundle: JobBundle = Field(..., description="Computation JobBundle workload")
    signature: Optional[str] = Field(default=None, description="HMAC-SHA256 signature for authenticity")
    dispatch_timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Dispatch initiation timestamp",
    )


class ClusterTaskDispatchResponse(BaseModel):
    """Dispatch and execution outcome from remote worker."""
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(..., description="Job identifier")
    target_node_id: str = Field(..., description="Node where job was executed")
    dispatched: bool = Field(..., description="Whether task was successfully dispatched and received")
    finding_result: Optional[FindingResult] = Field(default=None, description="Engine verification result")
    execution_time_ms: Optional[float] = Field(default=None, ge=0.0, description="Elapsed execution time")
    message: str = Field(..., description="Dispatch outcome description")


class WireGuardConfigResponse(BaseModel):
    """Generated wg0.conf INI configuration response."""
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., description="Node identifier for which config was built")
    interface_config: str = Field(..., description="wg0.conf formatted INI string")
    peers: List[WireGuardPeerConfig] = Field(default_factory=list, description="Peer configuration list")
