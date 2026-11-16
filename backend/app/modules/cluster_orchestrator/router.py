"""Cluster Orchestrator REST API Router (Feature 30).

Provides FastAPI endpoints for node admission (/nodes/join), health heartbeats (/nodes/heartbeat),
WireGuard configuration retrieval (/nodes/{node_id}/config), node inventory (/nodes),
workload dispatch (/dispatch), and lifecycle administration (block, drain, unblock).
"""

from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.core.config import settings
from app.modules.cluster_orchestrator.dispatcher import ClusterTaskDispatcher
from app.modules.cluster_orchestrator.registry import ClusterNodeRegistry
from app.modules.cluster_orchestrator.wireguard import build_wireguard_config
from shared.schemas.cluster import (
    ClusterNode,
    ClusterNodeRole,
    ClusterNodeStatus,
    ClusterTaskDispatchResponse,
    HeartbeatPayload,
    HeartbeatResponse,
    NodeJoinRequest,
    NodeJoinResponse,
    WireGuardConfigResponse,
    WireGuardPeerConfig,
)
from shared.schemas.job_bundle import JobBundle

router = APIRouter(prefix="/cluster", tags=["cluster-orchestrator"])

# Global singleton registry and dispatcher instances
_cluster_registry: Optional[ClusterNodeRegistry] = None
_cluster_dispatcher: Optional[ClusterTaskDispatcher] = None


def get_cluster_registry() -> ClusterNodeRegistry:
    """Dependency provider for ClusterNodeRegistry singleton."""
    global _cluster_registry
    if _cluster_registry is None:
        _cluster_registry = ClusterNodeRegistry(cluster_secret=settings.cluster_join_token)
    return _cluster_registry


def require_cluster_admin(
    token: Optional[str] = Header(None, alias="X-Cluster-Admin-Token"),
) -> None:
    """Protect cluster control-plane operations with a separately configured secret."""
    configured_token = settings.cluster_admin_token
    if not configured_token or len(configured_token.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cluster control plane is not configured",
        )
    if not token or not secrets.compare_digest(token, configured_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid cluster admin token required",
            headers={"WWW-Authenticate": "Cluster"},
        )


def get_cluster_dispatcher() -> ClusterTaskDispatcher:
    """Dependency provider for ClusterTaskDispatcher singleton."""
    global _cluster_dispatcher
    if _cluster_dispatcher is None:
        registry = get_cluster_registry()
        _cluster_dispatcher = ClusterTaskDispatcher(registry=registry)
    return _cluster_dispatcher


def reset_cluster_state(
    registry: Optional[ClusterNodeRegistry] = None,
    dispatcher: Optional[ClusterTaskDispatcher] = None,
) -> None:
    """Resets or overrides the global cluster state for testing."""
    global _cluster_registry, _cluster_dispatcher
    _cluster_registry = registry
    _cluster_dispatcher = dispatcher


@router.post(
    "/nodes/join",
    response_model=NodeJoinResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admit a new node to the private cluster network",
)
async def join_cluster(
    request: NodeJoinRequest,
    registry: ClusterNodeRegistry = Depends(get_cluster_registry),
) -> NodeJoinResponse:
    """Validates cluster join token, assigns WireGuard IP, issues mTLS cert, and registers node."""
    configured_token = settings.cluster_join_token
    if not configured_token or len(configured_token.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cluster node admission is not configured",
        )
    if request.role != ClusterNodeRole.WORKER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only worker nodes may use the public admission endpoint",
        )
    try:
        response = registry.register_node(request)
        return response
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post(
    "/nodes/heartbeat",
    response_model=HeartbeatResponse,
    status_code=status.HTTP_200_OK,
    summary="Record node telemetry and verify zero-trust liveness",
)
async def record_node_heartbeat(
    payload: HeartbeatPayload,
    x_cert_fingerprint: Optional[str] = Header(None, alias="X-Cert-Fingerprint"),
    x_wireguard_pubkey: Optional[str] = Header(None, alias="X-WireGuard-Pubkey"),
    registry: ClusterNodeRegistry = Depends(get_cluster_registry),
    _: None = Depends(require_cluster_admin),
) -> HeartbeatResponse:
    """Processes node heartbeat ping, updates load metrics, and verifies client certificates."""
    try:
        return registry.record_heartbeat(
            payload=payload,
            claimed_fingerprint=x_cert_fingerprint,
            claimed_pubkey=x_wireguard_pubkey,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get(
    "/nodes",
    response_model=List[ClusterNode],
    response_model_exclude={"__all__": {"wireguard_private_key", "certificate_pem"}},
    status_code=status.HTTP_200_OK,
    summary="List registered cluster nodes with optional filtering",
)
async def list_cluster_nodes(
    role: Optional[ClusterNodeRole] = Query(None, description="Filter by node role"),
    node_status: Optional[ClusterNodeStatus] = Query(None, alias="status", description="Filter by node status"),
    registry: ClusterNodeRegistry = Depends(get_cluster_registry),
    _: None = Depends(require_cluster_admin),
) -> List[ClusterNode]:
    """Returns active, pending, or drained nodes in the cluster network."""
    return registry.list_nodes(role=role, status=node_status)


@router.get(
    "/nodes/{node_id}/config",
    response_model=WireGuardConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve generated wg0.conf INI configuration for a node",
)
async def get_node_wireguard_config(
    node_id: str,
    registry: ClusterNodeRegistry = Depends(get_cluster_registry),
    _: None = Depends(require_cluster_admin),
) -> WireGuardConfigResponse:
    """Generates a complete wg0.conf configuration file including all registered peers."""
    node = registry.get_node(node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found")
    if node.role == ClusterNodeRole.CONTROLLER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Controller private configuration is unavailable through the API",
        )

    all_nodes = registry.list_nodes()
    config_ini = build_wireguard_config(node=node, peers=all_nodes)

    peers: List[WireGuardPeerConfig] = []
    for p in all_nodes:
        if p.node_id == node_id:
            continue
        peer_allowed = p.allowed_ips or [f"{p.wireguard_ip}/32"]
        peers.append(
            WireGuardPeerConfig(
                public_key=p.wireguard_public_key,
                allowed_ips=peer_allowed,
                endpoint=p.endpoint,
                node_id=p.node_id,
            )
        )

    return WireGuardConfigResponse(
        node_id=node_id,
        interface_config=config_ini,
        peers=peers,
    )


@router.post(
    "/dispatch",
    response_model=ClusterTaskDispatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Dispatch a JobBundle workload to an optimal cluster worker",
)
async def dispatch_cluster_task(
    bundle: JobBundle,
    target_node_id: Optional[str] = Query(None, description="Optional target worker node ID"),
    dispatcher: ClusterTaskDispatcher = Depends(get_cluster_dispatcher),
    _: None = Depends(require_cluster_admin),
) -> ClusterTaskDispatchResponse:
    """Selects least-loaded healthy worker, signs task, and dispatches workload."""
    try:
        return await dispatcher.dispatch_bundle(bundle=bundle, target_node_id=target_node_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post(
    "/nodes/{node_id}/block",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Block a compromised or rogue cluster node",
)
async def block_node_endpoint(
    node_id: str,
    registry: ClusterNodeRegistry = Depends(get_cluster_registry),
    _: None = Depends(require_cluster_admin),
) -> Dict[str, str]:
    """Marks node status as BLOCKED and denies further communication."""
    node = registry.get_node(node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found")
    registry.block_node(node_id)
    return {"node_id": node_id, "status": "BLOCKED"}


@router.post(
    "/nodes/{node_id}/drain",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Drain a node for graceful maintenance",
)
async def drain_node_endpoint(
    node_id: str,
    registry: ClusterNodeRegistry = Depends(get_cluster_registry),
    _: None = Depends(require_cluster_admin),
) -> Dict[str, str]:
    """Marks node as DRAINED to stop receiving new workloads."""
    node = registry.get_node(node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found")
    registry.drain_node(node_id)
    return {"node_id": node_id, "status": "DRAINED"}


@router.post(
    "/drain",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Drain a node by node_id query param",
)
async def drain_node_query(
    node_id: str = Query(..., description="Node ID to drain"),
    registry: ClusterNodeRegistry = Depends(get_cluster_registry),
    _: None = Depends(require_cluster_admin),
) -> Dict[str, str]:
    return await drain_node_endpoint(node_id=node_id, registry=registry)


@router.post(
    "/nodes/{node_id}/unblock",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Unblock and restore a cluster node",
)
async def unblock_node_endpoint(
    node_id: str,
    registry: ClusterNodeRegistry = Depends(get_cluster_registry),
    _: None = Depends(require_cluster_admin),
) -> Dict[str, str]:
    """Restores node status to ACTIVE."""
    node = registry.get_node(node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found")
    registry.unblock_node(node_id)
    return {"node_id": node_id, "status": "ACTIVE"}


@router.post(
    "/unblock",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Unblock a node by node_id query param",
)
async def unblock_node_query(
    node_id: str = Query(..., description="Node ID to unblock"),
    registry: ClusterNodeRegistry = Depends(get_cluster_registry),
    _: None = Depends(require_cluster_admin),
) -> Dict[str, str]:
    return await unblock_node_endpoint(node_id=node_id, registry=registry)
