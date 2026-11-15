"""Cluster Orchestration Module (Feature 30).

Provides WireGuard interface generation, mutual TLS (mTLS) authentication,
cluster node registry with health tracking, and distributed task dispatching.
"""

from app.modules.cluster_orchestrator.dispatcher import ClusterTaskDispatcher
from app.modules.cluster_orchestrator.mtls import (
    ClusterCertificateAuthority,
    create_mtls_ssl_context,
)
from app.modules.cluster_orchestrator.registry import ClusterNodeRegistry
from app.modules.cluster_orchestrator.router import router as cluster_router
from app.modules.cluster_orchestrator.transport import (
    ClusterTransport,
    MockWireGuardTunnelTransport,
)
from app.modules.cluster_orchestrator.wireguard import (
    allocate_cluster_ip,
    build_wireguard_config,
    generate_wireguard_keypair,
    get_wireguard_public_key,
    parse_wireguard_config,
    validate_wireguard_key,
)

__all__ = [
    "ClusterCertificateAuthority",
    "create_mtls_ssl_context",
    "generate_wireguard_keypair",
    "get_wireguard_public_key",
    "validate_wireguard_key",
    "build_wireguard_config",
    "allocate_cluster_ip",
    "parse_wireguard_config",
    "ClusterTransport",
    "MockWireGuardTunnelTransport",
    "ClusterNodeRegistry",
    "ClusterTaskDispatcher",
    "cluster_router",
]
