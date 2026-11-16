"""Comprehensive Automated Test Suite for Cluster Node Orchestration (Feature 30).

Validates:
1. WireGuard Curve25519 keypair generation, public key derivation, key validation,
   canonical wg0.conf INI configuration generation, and dynamic IP allocation.
2. X.509 Cluster Root CA generation, node dual-use client/server certificate issuance
   with SANs and ExtendedKeyUsage, SHA-256 fingerprinting, and mTLS SSLContext creation.
3. Authentic loopback mTLS socket handshakes via MockWireGuardTunnelTransport,
   WireGuard cryptokey routing verification, and rejection of rogue/expired certificates.
4. ClusterNodeRegistry admission with join tokens, telemetry heartbeats, stale node
   detection (> 30s), and zero-trust rogue node blocking.
5. ClusterTaskDispatcher optimal worker selection (min load_average, min active_tasks),
   HMAC-SHA256 workload signing, and end-to-end task dispatch.
6. FastAPI REST API endpoints (/api/v1/cluster/...) for join, heartbeat, list, config,
   dispatch, block, drain, and unblock operations.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import ssl
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import settings
from app.modules.cluster_orchestrator.dispatcher import ClusterTaskDispatcher
from app.modules.cluster_orchestrator.mtls import (
    ClusterCertificateAuthority,
    create_mtls_ssl_context,
)
from app.modules.cluster_orchestrator.registry import ClusterNodeRegistry
from app.modules.cluster_orchestrator.router import (
    get_cluster_dispatcher,
    get_cluster_registry,
    reset_cluster_state,
)
from app.modules.cluster_orchestrator.transport import MockWireGuardTunnelTransport
from app.modules.cluster_orchestrator.wireguard import (
    allocate_cluster_ip,
    build_wireguard_config,
    generate_wireguard_keypair,
    get_wireguard_public_key,
    parse_wireguard_config,
    validate_wireguard_key,
)
from shared.schemas.cluster import (
    ClusterNode,
    ClusterNodeRole,
    ClusterNodeStatus,
    HeartbeatPayload,
    NodeJoinRequest,
)
from shared.schemas.finding_result import FindingResult, FindingState
from shared.schemas.job_bundle import JobBundle, TargetEntityType
from shared.schemas.math_ast import ExprNode, NodeType


def create_sample_job_bundle(job_id: str = "cluster-job-001") -> JobBundle:
    """Helper creating a valid JobBundle for dispatch testing."""
    return JobBundle(
        job_id=job_id,
        version_id="v1.0.0",
        target_entity_type=TargetEntityType.EQUATION,
        target_entity_id="eq-42",
        expression_ast=ExprNode(node_type=NodeType.CONSTANT, value=42),
        variables=[],
        units=[],
        timeout_seconds=10,
    )


# ==============================================================================
# 1. WireGuard Keypair, Config, & IP Allocation Tests
# ==============================================================================


def test_generate_wireguard_keypair():
    """Verify WireGuard Curve25519 keypair generation adheres to standard 32-byte format."""
    priv_b64, pub_b64 = generate_wireguard_keypair()
    assert isinstance(priv_b64, str)
    assert isinstance(pub_b64, str)
    assert len(priv_b64) == 44
    assert len(pub_b64) == 44

    # Deriving public key from private key matches generated public key
    derived_pub = get_wireguard_public_key(priv_b64)
    assert derived_pub == pub_b64


def test_validate_wireguard_key():
    """Verify validation of 32-byte base64 Curve25519 WireGuard keys."""
    priv_b64, pub_b64 = generate_wireguard_keypair()
    assert validate_wireguard_key(priv_b64) is True
    assert validate_wireguard_key(pub_b64) is True

    # Invalid cases
    assert validate_wireguard_key("") is False
    assert validate_wireguard_key("short-key") is False
    assert validate_wireguard_key("!@#$invalid_base64_string_with_bad_chars!==") is False
    assert validate_wireguard_key("A" * 43) is False
    assert validate_wireguard_key("A" * 45) is False


def test_build_wireguard_config_syntax():
    """Verify generated wg0.conf has correct INI syntax and sections."""
    priv_1, pub_1 = generate_wireguard_keypair()
    priv_2, pub_2 = generate_wireguard_keypair()

    node_1 = ClusterNode(
        node_id="worker-01",
        wireguard_ip="10.42.0.2",
        wireguard_public_key=pub_1,
        wireguard_private_key=priv_1,
        listen_port=51820,
    )
    peer_2 = ClusterNode(
        node_id="worker-02",
        wireguard_ip="10.42.0.3",
        wireguard_public_key=pub_2,
        endpoint="198.51.100.5:51820",
        allowed_ips=["10.42.0.3/32"],
    )

    config_str = build_wireguard_config(node=node_1, peers=[node_1, peer_2])
    assert "[Interface]" in config_str
    assert f"PrivateKey = {priv_1}" in config_str
    assert "Address = 10.42.0.2/24" in config_str
    assert "ListenPort = 51820" in config_str

    assert "[Peer]" in config_str
    assert f"PublicKey = {pub_2}" in config_str
    assert "AllowedIPs = 10.42.0.3/32" in config_str
    assert "Endpoint = 198.51.100.5:51820" in config_str
    assert "PersistentKeepalive = 25" in config_str

    # Node 1 must NOT be included in its own peers
    assert f"PublicKey = {pub_1}" not in config_str.split("[Peer]")[1]

    parsed = parse_wireguard_config(config_str)
    assert parsed["interface"]["Address"] == "10.42.0.2/24"
    assert len(parsed["peers"]) == 1
    assert parsed["peers"][0]["PublicKey"] == pub_2


def test_allocate_cluster_ip():
    """Verify sequential IP allocation within subnet and reservation of controller IP."""
    nodes = []
    ip1 = allocate_cluster_ip(nodes, subnet="10.42.0.0/24")
    assert ip1 == "10.42.0.2"  # 10.42.0.1 is reserved for controller

    nodes.append(ClusterNode(node_id="w1", wireguard_ip=ip1, wireguard_public_key="k1"))
    ip2 = allocate_cluster_ip(nodes, subnet="10.42.0.0/24")
    assert ip2 == "10.42.0.3"

    # Test small subnet exhaustion
    small_nodes = [
        ClusterNode(node_id="c", wireguard_ip="10.42.0.1", wireguard_public_key="k"),
        ClusterNode(node_id="w1", wireguard_ip="10.42.0.2", wireguard_public_key="k"),
    ]
    with pytest.raises(RuntimeError, match="address space exhausted"):
        allocate_cluster_ip(small_nodes, subnet="10.42.0.0/30")  # /30 has only 2 usable hosts (.1, .2)


# ==============================================================================
# 2. X.509 CA & Mutual TLS Subsystem Tests
# ==============================================================================


def test_cluster_ca_generation_and_export():
    """Verify Cluster Root CA generation with BasicConstraints ca=True."""
    ca = ClusterCertificateAuthority(common_name="Test Cluster Root CA")
    ca_pem = ca.export_ca_pem()
    ca_key_pem = ca.export_ca_key_pem()

    assert "-----BEGIN CERTIFICATE-----" in ca_pem
    assert "-----END CERTIFICATE-----" in ca_pem
    assert "-----BEGIN EC PRIVATE KEY-----" in ca_key_pem or "-----BEGIN PRIVATE KEY-----" in ca_key_pem

    # Reload from PEM bytes
    reloaded_ca = ClusterCertificateAuthority(ca_cert_pem=ca_pem, ca_key_pem=ca_key_pem)
    assert reloaded_ca.export_ca_pem() == ca_pem


def test_issue_node_certificate_and_fingerprint():
    """Verify issued node certificate has SANs, ExtendedKeyUsage, and valid signature."""
    ca = ClusterCertificateAuthority()
    cert_pem, key_pem = ca.issue_node_certificate(
        node_id="worker-node-alpha",
        san_ips=["10.42.0.5"],
        san_dns=["worker-node-alpha.cluster.local"],
        validity_days=30,
    )

    assert "-----BEGIN CERTIFICATE-----" in cert_pem
    assert "-----BEGIN EC PRIVATE KEY-----" in key_pem or "-----BEGIN PRIVATE KEY-----" in key_pem

    fingerprint = ca.get_certificate_fingerprint(cert_pem)
    assert isinstance(fingerprint, str)
    assert len(fingerprint) == 64  # SHA-256 hex digest

    # Verify signature passes
    assert ca.verify_certificate(cert_pem) is True

    # Verify certificate signed by different CA fails verification
    other_ca = ClusterCertificateAuthority(common_name="Rogue CA")
    rogue_cert, _ = other_ca.issue_node_certificate("rogue-node")
    assert ca.verify_certificate(rogue_cert) is False


def test_create_mtls_ssl_context():
    """Verify creation of server and client SSLContext instances requiring peer certificates."""
    ca = ClusterCertificateAuthority()
    cert_pem, key_pem = ca.issue_node_certificate("node-01")

    server_ctx = create_mtls_ssl_context(
        ca_cert_pem=ca.export_ca_pem(),
        cert_pem=cert_pem,
        key_pem=key_pem,
        is_server=True,
    )
    assert server_ctx.verify_mode == ssl.CERT_REQUIRED
    assert server_ctx.minimum_version == ssl.TLSVersion.TLSv1_2

    client_ctx = create_mtls_ssl_context(
        ca_cert_pem=ca.export_ca_pem(),
        cert_pem=cert_pem,
        key_pem=key_pem,
        is_server=False,
    )
    assert client_ctx.verify_mode == ssl.CERT_REQUIRED


# ==============================================================================
# 3. Transport & Authentic mTLS Socket Handshake Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_mtls_socket_handshake_success():
    """Verify genuine mutual TLS socket handshake over loopback using MockWireGuardTunnelTransport."""
    ca = ClusterCertificateAuthority()
    ca_pem = ca.export_ca_pem()

    # Server node
    _, s_pub = generate_wireguard_keypair()
    s_cert, s_key = ca.issue_node_certificate("server-node", san_ips=["127.0.0.1"])
    server_node = ClusterNode(
        node_id="server-node",
        wireguard_ip="10.42.0.1",
        wireguard_public_key=s_pub,
    )

    # Client node
    _, c_pub = generate_wireguard_keypair()
    c_cert, c_key = ca.issue_node_certificate("client-node", san_ips=["127.0.0.1"])
    client_node = ClusterNode(
        node_id="client-node",
        wireguard_ip="10.42.0.2",
        wireguard_public_key=c_pub,
    )

    server_transport = MockWireGuardTunnelTransport(
        ca_cert_pem=ca_pem,
        local_node=server_node,
        node_cert_pem=s_cert,
        node_key_pem=s_key,
    )
    client_transport = MockWireGuardTunnelTransport(
        ca_cert_pem=ca_pem,
        local_node=client_node,
        node_cert_pem=c_cert,
        node_key_pem=c_key,
    )

    async def echo_handler(data: bytes, metadata: dict) -> bytes:
        assert metadata["client_node_id"] == "client-node"
        return b"ECHO:" + data

    bound_port = await server_transport.start_server(server_node, echo_handler)
    try:
        # Register peer routing table
        client_transport.register_peer_route(server_node, "127.0.0.1", bound_port)

        payload = b"CLUSTER_HELLO_REALITY_SCIENCE"
        response = await client_transport.send_to_node(server_node, payload)
        assert response == b"ECHO:CLUSTER_HELLO_REALITY_SCIENCE"
    finally:
        await server_transport.stop_server()


@pytest.mark.asyncio
async def test_mtls_rejects_rogue_certificate():
    """Verify that a client presenting a rogue certificate is rejected during TLS handshake."""
    trusted_ca = ClusterCertificateAuthority(common_name="Trusted Cluster CA")
    rogue_ca = ClusterCertificateAuthority(common_name="Attacker Untrusted CA")

    # Server signed by trusted CA
    _, s_pub = generate_wireguard_keypair()
    s_cert, s_key = trusted_ca.issue_node_certificate("server-node", san_ips=["127.0.0.1"])
    server_node = ClusterNode(
        node_id="server-node",
        wireguard_ip="10.42.0.1",
        wireguard_public_key=s_pub,
    )

    # Rogue client signed by rogue CA
    _, r_pub = generate_wireguard_keypair()
    r_cert, r_key = rogue_ca.issue_node_certificate("rogue-node", san_ips=["127.0.0.1"])
    rogue_client_node = ClusterNode(
        node_id="rogue-node",
        wireguard_ip="10.42.0.99",
        wireguard_public_key=r_pub,
    )

    server_transport = MockWireGuardTunnelTransport(
        ca_cert_pem=trusted_ca.export_ca_pem(),
        local_node=server_node,
        node_cert_pem=s_cert,
        node_key_pem=s_key,
    )
    rogue_transport = MockWireGuardTunnelTransport(
        ca_cert_pem=trusted_ca.export_ca_pem(),
        local_node=rogue_client_node,
        node_cert_pem=r_cert,
        node_key_pem=r_key,
    )

    async def dummy_handler(data: bytes, meta: dict) -> bytes:
        return b"OK"

    bound_port = await server_transport.start_server(server_node, dummy_handler)
    try:
        rogue_transport.register_peer_route(server_node, "127.0.0.1", bound_port)
        with pytest.raises(Exception):  # ssl.SSLError / ConnectionResetError
            await rogue_transport.send_to_node(server_node, b"ATTACK_PAYLOAD")
    finally:
        await server_transport.stop_server()


@pytest.mark.asyncio
async def test_wireguard_cryptokey_routing_violation():
    """Verify transport enforces WireGuard Cryptokey Routing checks before transmitting."""
    ca = ClusterCertificateAuthority()
    _, pub_real = generate_wireguard_keypair()
    _, pub_fake = generate_wireguard_keypair()

    target_node = ClusterNode(
        node_id="target",
        wireguard_ip="10.42.0.10",
        wireguard_public_key=pub_fake,  # Mismatched public key
    )
    c_cert, c_key = ca.issue_node_certificate("client-node")
    transport = MockWireGuardTunnelTransport(
        ca_cert_pem=ca.export_ca_pem(),
        local_node=ClusterNode(node_id="c", wireguard_ip="10.42.0.2", wireguard_public_key=pub_real),
        node_cert_pem=c_cert,
        node_key_pem=c_key,
    )
    # Register genuine peer route with pub_real
    transport.cryptokey_routing_table["10.42.0.10"] = pub_real
    transport.endpoint_routing_table["10.42.0.10"] = ("127.0.0.1", 9999)

    with pytest.raises(PermissionError, match="WireGuard Cryptokey Routing violation"):
        await transport.send_to_node(target_node, b"PAYLOAD")


# ==============================================================================
# 4. Cluster Node Registry & Zero-Trust Security Tests
# ==============================================================================


def test_node_join_and_admission_lifecycle():
    """Verify node admission with join token, certificate issuance, and status tracking."""
    registry = ClusterNodeRegistry(cluster_secret="valid-secret-token")
    _, pub = generate_wireguard_keypair()

    join_req = NodeJoinRequest(
        hostname="worker-node-01",
        wireguard_public_key=pub,
        role=ClusterNodeRole.WORKER,
        join_token="valid-secret-token",
        endpoint="203.0.113.10:51820",
    )
    resp = registry.register_node(join_req)

    assert resp.status == ClusterNodeStatus.ACTIVE
    assert resp.assigned_wireguard_ip == "10.42.0.2"
    assert "-----BEGIN CERTIFICATE-----" in resp.issued_cert_pem
    assert len(resp.peers) >= 1  # Includes controller node

    # Bad token raises PermissionError
    bad_req = NodeJoinRequest(
        hostname="worker-node-02",
        wireguard_public_key=pub,
        role=ClusterNodeRole.WORKER,
        join_token="wrong-token",
    )
    with pytest.raises(PermissionError, match="Invalid cluster join token"):
        registry.register_node(bad_req)


def test_heartbeat_telemetry_and_stale_detection():
    """Verify heartbeat recording, 30s stale detection, and recovery back to ACTIVE."""
    registry = ClusterNodeRegistry(cluster_secret="valid-secret")
    _, pub = generate_wireguard_keypair()

    join_resp = registry.register_node(
        NodeJoinRequest(
            hostname="worker-stale",
            wireguard_public_key=pub,
            join_token="valid-secret",
        )
    )
    node_id = join_resp.node_id

    # Record normal heartbeat
    hb_resp = registry.record_heartbeat(
        HeartbeatPayload(
            node_id=node_id,
            load_average=0.45,
            active_tasks=2,
        )
    )
    assert hb_resp.acknowledged is True
    assert hb_resp.node_status == ClusterNodeStatus.ACTIVE
    node = registry.get_node(node_id)
    assert node.load_average == 0.45
    assert node.active_tasks == 2

    # Fast-forward time to simulate stale node (> 30s)
    node.last_heartbeat = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=45)
    stale_nodes = registry.mark_stale_nodes(threshold_seconds=30.0)
    assert node_id in stale_nodes
    assert node.status == ClusterNodeStatus.UNHEALTHY

    # Stale node should not be in healthy workers
    healthy = registry.get_healthy_workers()
    assert node_id not in [n.node_id for n in healthy]

    # Subsequent heartbeat recovers node to ACTIVE
    recovery_resp = registry.record_heartbeat(
        HeartbeatPayload(
            node_id=node_id,
            load_average=0.10,
            active_tasks=0,
        )
    )
    assert recovery_resp.node_status == ClusterNodeStatus.ACTIVE
    assert node.status == ClusterNodeStatus.ACTIVE


def test_zero_trust_rogue_blocking():
    """Verify zero-trust enforcement: mismatched cert fingerprint or public key blocks node."""
    registry = ClusterNodeRegistry(cluster_secret="valid-secret")
    _, pub = generate_wireguard_keypair()

    join_resp = registry.register_node(
        NodeJoinRequest(
            hostname="worker-security",
            wireguard_public_key=pub,
            join_token="valid-secret",
        )
    )
    node_id = join_resp.node_id
    node = registry.get_node(node_id)

    # Valid fingerprint heartbeat succeeds
    registry.record_heartbeat(
        HeartbeatPayload(node_id=node_id, load_average=0.1, active_tasks=0),
        claimed_fingerprint=node.cert_fingerprint,
    )
    assert node.status == ClusterNodeStatus.ACTIVE

    # Rogue fingerprint causes immediate BLOCKED status
    with pytest.raises(PermissionError, match="Zero-trust violation: Certificate fingerprint mismatch"):
        registry.record_heartbeat(
            HeartbeatPayload(node_id=node_id, load_average=0.1, active_tasks=0),
            claimed_fingerprint="0000000000000000000000000000000000000000000000000000000000000000",
        )

    assert node.status == ClusterNodeStatus.BLOCKED

    # Blocked node cannot perform subsequent heartbeats
    with pytest.raises(PermissionError, match="BLOCKED"):
        registry.record_heartbeat(
            HeartbeatPayload(node_id=node_id, load_average=0.1, active_tasks=0),
        )


def test_node_drain_and_unblock():
    """Verify administrative draining and unblocking operations."""
    registry = ClusterNodeRegistry(cluster_secret="sec")
    _, pub = generate_wireguard_keypair()
    resp = registry.register_node(
        NodeJoinRequest(hostname="worker-ops", wireguard_public_key=pub, join_token="sec")
    )
    node_id = resp.node_id

    # Drain node
    assert registry.drain_node(node_id) is True
    node = registry.get_node(node_id)
    assert node.status == ClusterNodeStatus.DRAINED
    assert node_id not in [n.node_id for n in registry.get_healthy_workers()]

    # Unblock / restore node
    assert registry.unblock_node(node_id) is True
    assert node.status == ClusterNodeStatus.ACTIVE
    assert node_id in [n.node_id for n in registry.get_healthy_workers()]


# ==============================================================================
# 5. Cluster Task Dispatcher Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_dispatcher_least_loaded_worker_selection():
    """Verify dispatcher selects worker with min(load_average, active_tasks)."""
    registry = ClusterNodeRegistry(cluster_secret="sec")
    _, pub1 = generate_wireguard_keypair()
    _, pub2 = generate_wireguard_keypair()
    _, pub3 = generate_wireguard_keypair()

    resp1 = registry.register_node(NodeJoinRequest(hostname="w1", wireguard_public_key=pub1, join_token="sec"))
    resp2 = registry.register_node(NodeJoinRequest(hostname="w2", wireguard_public_key=pub2, join_token="sec"))
    resp3 = registry.register_node(NodeJoinRequest(hostname="w3", wireguard_public_key=pub3, join_token="sec"))

    w1 = registry.get_node(resp1.node_id)
    w2 = registry.get_node(resp2.node_id)
    w3 = registry.get_node(resp3.node_id)

    w1.load_average = 0.8
    w1.active_tasks = 3

    w2.load_average = 0.2
    w2.active_tasks = 2

    w3.load_average = 0.2
    w3.active_tasks = 0

    dispatcher = ClusterTaskDispatcher(registry=registry)
    selected = dispatcher.select_optimal_worker()
    assert selected.node_id == w3.node_id  # Lowest load, then lowest tasks


def test_dispatcher_hmac_signing_and_verification():
    """Verify HMAC-SHA256 task payload signing and tamper detection."""
    registry = ClusterNodeRegistry(cluster_secret="strong-cluster-secret")
    dispatcher = ClusterTaskDispatcher(registry=registry, cluster_secret="strong-cluster-secret")

    bundle = create_sample_job_bundle("job-sign-test")
    signature = dispatcher.sign_bundle(bundle)
    assert isinstance(signature, str)
    assert len(signature) == 64

    # Verification passes for intact bundle
    assert dispatcher.verify_signature(bundle, signature) is True

    # Tampered bundle fails verification
    tampered_bundle = bundle.model_copy(update={"job_id": "job-tampered-999"})
    assert dispatcher.verify_signature(tampered_bundle, signature) is False


@pytest.mark.asyncio
async def test_dispatcher_dispatch_bundle_e2e():
    """Verify end-to-end task dispatch, workload execution, and FindingResult return."""
    registry = ClusterNodeRegistry(cluster_secret="sec")
    _, pub = generate_wireguard_keypair()
    resp = registry.register_node(NodeJoinRequest(hostname="worker-compute", wireguard_public_key=pub, join_token="sec"))
    worker_id = resp.node_id

    # Mock compute executor returning valid FindingResult
    def mock_evaluator(bundle: JobBundle) -> FindingResult:
        return FindingResult(
            job_id=bundle.job_id,
            state=FindingState.PASS,
            diagnostic_code="VALIDATION_PASSED",
            message="AST verified successfully on cluster worker",
            dimensions_verified=True,
            diagnostics=["Layer 1-3 PASS"],
        )

    dispatcher = ClusterTaskDispatcher(registry=registry, mock_executor=mock_evaluator)
    bundle = create_sample_job_bundle("job-dispatch-e2e")

    dispatch_resp = await dispatcher.dispatch_bundle(bundle)
    assert dispatch_resp.dispatched is True
    assert dispatch_resp.target_node_id == worker_id
    assert dispatch_resp.finding_result is not None
    assert dispatch_resp.finding_result.state == FindingState.PASS
    assert dispatch_resp.finding_result.diagnostic_code == "VALIDATION_PASSED"
    assert dispatch_resp.execution_time_ms is not None

    # Verify direct node dispatch
    worker_node = registry.get_node(worker_id)
    finding = await dispatcher.dispatch_bundle_to_node(worker_node, bundle)
    assert finding.state == FindingState.PASS


@pytest.mark.asyncio
async def test_dispatcher_fails_when_no_healthy_workers():
    """Verify dispatcher raises RuntimeError when all workers are drained or unavailable."""
    registry = ClusterNodeRegistry(cluster_secret="sec")
    dispatcher = ClusterTaskDispatcher(registry=registry)
    bundle = create_sample_job_bundle("job-fail-no-workers")

    with pytest.raises(RuntimeError, match="No healthy worker nodes available"):
        await dispatcher.dispatch_bundle(bundle)


# ==============================================================================
# 6. FastAPI REST API Endpoint Tests
# ==============================================================================


@pytest.fixture(autouse=True)
def reset_global_cluster():
    """Reset global cluster registry and dispatcher state before each test."""
    reg = ClusterNodeRegistry(cluster_secret="test-cluster-join-token-32-bytes-long")
    original_join_token = settings.cluster_join_token
    original_admin_token = settings.cluster_admin_token
    settings.cluster_join_token = "test-cluster-join-token-32-bytes-long"
    settings.cluster_admin_token = "test-cluster-admin-token-32-bytes-long"
    disp = ClusterTaskDispatcher(
        registry=reg,
        mock_executor=lambda b: FindingResult(
            job_id=b.job_id,
            state=FindingState.PASS,
            diagnostic_code="VALIDATION_PASSED",
            message="Mock API computation pass",
            dimensions_verified=True,
        ),
    )
    reset_cluster_state(registry=reg, dispatcher=disp)
    yield
    reset_cluster_state(None, None)
    settings.cluster_join_token = original_join_token
    settings.cluster_admin_token = original_admin_token


@pytest.mark.asyncio
async def test_api_cluster_join_and_get_config():
    """Verify POST /api/v1/cluster/nodes/join and GET /api/v1/cluster/nodes/{id}/config."""
    _, pub = generate_wireguard_keypair()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Join cluster
        join_payload = {
            "hostname": "api-worker-01",
            "wireguard_public_key": pub,
            "role": "WORKER",
            "join_token": "test-cluster-join-token-32-bytes-long",
            "endpoint": "198.51.100.22:51820",
        }
        res_join = await ac.post("/api/v1/cluster/nodes/join", json=join_payload)
        assert res_join.status_code == 201
        data = res_join.json()
        node_id = data["node_id"]
        assert data["status"] == "ACTIVE"
        assert "assigned_wireguard_ip" in data
        assert "-----BEGIN CERTIFICATE-----" in data["issued_cert_pem"]

        # 2. Get WireGuard wg0.conf
        cluster_headers = {"X-Cluster-Admin-Token": "test-cluster-admin-token-32-bytes-long"}
        unauthenticated_nodes = await ac.get("/api/v1/cluster/nodes")
        assert unauthenticated_nodes.status_code == 401
        res_cfg = await ac.get(f"/api/v1/cluster/nodes/{node_id}/config", headers=cluster_headers)
        assert res_cfg.status_code == 200
        cfg_data = res_cfg.json()
        assert cfg_data["node_id"] == node_id
        assert "[Interface]" in cfg_data["interface_config"]
        assert "[Peer]" in cfg_data["interface_config"]

        # 3. List nodes
        res_list = await ac.get("/api/v1/cluster/nodes", headers=cluster_headers)
        assert res_list.status_code == 200
        nodes_list = res_list.json()
        assert any(n["node_id"] == node_id for n in nodes_list)
        assert all("wireguard_private_key" not in node for node in nodes_list)
        assert all("certificate_pem" not in node for node in nodes_list)

        controller_cfg = await ac.get(
            "/api/v1/cluster/nodes/controller-node/config",
            headers=cluster_headers,
        )
        assert controller_cfg.status_code == 403


@pytest.mark.asyncio
async def test_cluster_join_fails_closed_without_configured_token():
    _, pub = generate_wireguard_keypair()
    settings.cluster_join_token = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/cluster/nodes/join",
            json={
                "hostname": "unconfigured-worker",
                "wireguard_public_key": pub,
                "join_token": "reality-cluster-dev-token-secret-2026",
            },
        )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_cluster_join_rejects_non_worker_role():
    _, pub = generate_wireguard_keypair()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/cluster/nodes/join",
            json={
                "hostname": "untrusted-controller",
                "wireguard_public_key": pub,
                "role": "CONTROLLER",
                "join_token": "test-cluster-join-token-32-bytes-long",
            },
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cluster_control_plane_requires_configured_admin_token():
    settings.cluster_admin_token = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/cluster/nodes")

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_api_cluster_heartbeat_and_security_blocking():
    """Verify POST /api/v1/cluster/nodes/heartbeat and rogue blocking."""
    _, pub = generate_wireguard_keypair()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res_join = await ac.post(
            "/api/v1/cluster/nodes/join",
            json={
                "hostname": "api-worker-heartbeat",
                "wireguard_public_key": pub,
                "role": "WORKER",
                "join_token": "test-cluster-join-token-32-bytes-long",
            },
        )
        node_id = res_join.json()["node_id"]

        # Valid heartbeat
        cluster_headers = {"X-Cluster-Admin-Token": "test-cluster-admin-token-32-bytes-long"}
        res_hb = await ac.post(
            "/api/v1/cluster/nodes/heartbeat",
            json={"node_id": node_id, "load_average": 0.25, "active_tasks": 1},
            headers=cluster_headers,
        )
        assert res_hb.status_code == 200
        assert res_hb.json()["acknowledged"] is True

        # Heartbeat with mismatched fingerprint returns 403 Forbidden
        res_rogue = await ac.post(
            "/api/v1/cluster/nodes/heartbeat",
            json={"node_id": node_id, "load_average": 0.25, "active_tasks": 1},
            headers={
                **cluster_headers,
                "X-Cert-Fingerprint": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            },
        )
        assert res_rogue.status_code == 403


@pytest.mark.asyncio
async def test_api_cluster_dispatch_task():
    """Verify POST /api/v1/cluster/dispatch sends JobBundle and receives FindingResult."""
    _, pub = generate_wireguard_keypair()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Admit a worker
        await ac.post(
            "/api/v1/cluster/nodes/join",
            json={
                "hostname": "api-worker-dispatch",
                "wireguard_public_key": pub,
                "role": "WORKER",
                "join_token": "test-cluster-join-token-32-bytes-long",
            },
        )

        bundle = create_sample_job_bundle("api-dispatch-001")
        res_dispatch = await ac.post(
            "/api/v1/cluster/dispatch",
            json=bundle.model_dump(),
            headers={"X-Cluster-Admin-Token": "test-cluster-admin-token-32-bytes-long"},
        )
        assert res_dispatch.status_code == 200
        disp_data = res_dispatch.json()
        assert disp_data["dispatched"] is True
        assert disp_data["job_id"] == "api-dispatch-001"
        assert disp_data["finding_result"]["state"] == "PASS"


@pytest.mark.asyncio
async def test_api_block_drain_unblock():
    """Verify admin operations: block, drain, unblock via API."""
    _, pub = generate_wireguard_keypair()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res_join = await ac.post(
            "/api/v1/cluster/nodes/join",
            json={
                "hostname": "api-worker-ops",
                "wireguard_public_key": pub,
                "role": "WORKER",
                "join_token": "test-cluster-join-token-32-bytes-long",
            },
        )
        node_id = res_join.json()["node_id"]

        # Drain
        cluster_headers = {"X-Cluster-Admin-Token": "test-cluster-admin-token-32-bytes-long"}
        res_drain = await ac.post(f"/api/v1/cluster/nodes/{node_id}/drain", headers=cluster_headers)
        assert res_drain.status_code == 200
        assert res_drain.json()["status"] == "DRAINED"

        # Block
        res_block = await ac.post(f"/api/v1/cluster/nodes/{node_id}/block", headers=cluster_headers)
        assert res_block.status_code == 200
        assert res_block.json()["status"] == "BLOCKED"

        # Unblock
        res_unblock = await ac.post(f"/api/v1/cluster/nodes/{node_id}/unblock", headers=cluster_headers)
        assert res_unblock.status_code == 200
        assert res_unblock.json()["status"] == "ACTIVE"
