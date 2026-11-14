"""
REALITY SCIENCE — Local Development & Multi-Zone Verification Script
Supports dual-mode execution:
1. Docker daemon available -> delegates to Docker Compose orchestration
2. Docker daemon absent -> static validation + native local process orchestration
"""

import sys
import os
import subprocess
import socket
import argparse
import platform
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if not os.path.exists(REPO_ROOT):
    REPO_ROOT = r"D:\Reality_Science"

def check_port(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def verify_system_requirements() -> bool:
    print("=" * 70)
    print("REALITY SCIENCE — Local Development Pre-Flight Verification")
    print("=" * 70)
    
    # 1. Python version
    py_ver = sys.version_info
    py_ok = (py_ver.major == 3 and py_ver.minor >= 11)
    status = "[ PASS ]" if py_ok else "[ FAIL ]"
    print(f"{status} Python version: {platform.python_version()} (requires >= 3.11)")
    
    # 2. Node.js version
    node_ok = False
    node_ver = "Not installed"
    try:
        res = subprocess.run(["node", "-v"], capture_output=True, text=True, check=True)
        node_ver = res.stdout.strip()
        major = int(node_ver.lstrip("v").split(".")[0])
        node_ok = (major >= 20)
    except Exception:
        pass
    status = "[ PASS ]" if node_ok else "[ FAIL ]"
    print(f"{status} Node.js version: {node_ver} (requires >= 20)")
    
    # 3. Docker CLI / Daemon check
    docker_ok = False
    docker_info = "Not installed on PATH"
    try:
        res = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if res.returncode == 0:
            docker_ok = True
            docker_info = "Daemon running"
        else:
            docker_info = "CLI present, daemon not running"
    except FileNotFoundError:
        pass
    print(f"[{'INFO' if docker_ok else 'WARN'}] Docker Daemon: {docker_info}")
    
    # 4. Local Infrastructure Connectivity (Port checks)
    pg_alive = check_port("localhost", 5432)
    redis_alive = check_port("localhost", 6379)
    print(f"[{'PASS' if pg_alive else 'WARN'}] PostgreSQL: {'Port 5432 listening' if pg_alive else 'Port 5432 not responding (use Docker or local PG)'}")
    print(f"[{'PASS' if redis_alive else 'WARN'}] Redis:      {'Port 6379 listening' if redis_alive else 'Port 6379 not responding (use Docker or local Redis)'}")
    
    # 5. Environment Templates Check
    env_root = os.path.join(REPO_ROOT, ".env.example")
    env_backend = os.path.join(REPO_ROOT, "backend", ".env.example")
    env_worker = os.path.join(REPO_ROOT, "worker", ".env.example")
    env_frontend = os.path.join(REPO_ROOT, "frontend", ".env.example")
    
    all_env_exist = all(os.path.exists(p) for p in [env_root, env_backend, env_worker, env_frontend])
    print(f"[{'PASS' if all_env_exist else 'FAIL'}] Environment Templates: {'All 4 .env.example files present' if all_env_exist else 'Missing template files'}")
    
    # 6. Worker Zero-Database Isolation Pre-flight
    worker_isolation_ok = True
    if os.path.exists(env_worker):
        with open(env_worker, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
            for l in lines:
                if "DATABASE_URL" in l or "POSTGRES" in l:
                    worker_isolation_ok = False
    print(f"[{'PASS' if worker_isolation_ok else 'FAIL'}] Worker Zero-Database Invariant: {'Enforced (zero DB vars)' if worker_isolation_ok else 'VIOLATION: Database vars found in worker env'}")
    
    # 7. Lockfiles Verification
    lock_shared = os.path.join(REPO_ROOT, "shared", "requirements.lock")
    lock_backend = os.path.join(REPO_ROOT, "backend", "requirements.lock")
    lock_worker = os.path.join(REPO_ROOT, "worker", "requirements.lock")
    lock_frontend = os.path.join(REPO_ROOT, "frontend", "package-lock.json")
    all_locks_exist = all(os.path.exists(p) for p in [lock_shared, lock_backend, lock_worker, lock_frontend])
    print(f"[{'PASS' if all_locks_exist else 'FAIL'}] Dependency Lockfiles: {'All 4 lockfiles present (shared, backend, worker, frontend)' if all_locks_exist else 'Missing lockfiles'}")

    print("-" * 70)
    return py_ok and node_ok and all_env_exist and worker_isolation_ok and all_locks_exist

def run_service(service: str):
    if service == "backend":
        print("Starting FastAPI backend (Zone 2)...")
        backend_dir = os.path.join(REPO_ROOT, "backend")
        subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"], cwd=backend_dir)
    elif service == "worker":
        print("Starting Celery compute worker (Zone 3)...")
        worker_dir = os.path.join(REPO_ROOT, "worker")
        pool = ["--pool=solo"] if platform.system() == "Windows" else []
        subprocess.run([sys.executable, "-m", "celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "-Q", "compute_tasks", "--concurrency=1"] + pool, cwd=worker_dir)
    elif service == "frontend":
        print("Starting Next.js frontend (Zone 1)...")
        frontend_dir = os.path.join(REPO_ROOT, "frontend")
        shell_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
        subprocess.run([shell_cmd, "run", "dev"], cwd=frontend_dir)
    else:
        print(f"Unknown service: {service}. Available: backend, worker, frontend")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="REALITY SCIENCE Dev & Orchestration Tool")
    parser.add_argument("command", choices=["verify", "run"], nargs="?", default="verify")
    parser.add_argument("--service", choices=["backend", "worker", "frontend"], default="backend")
    args = parser.parse_args()
    
    if args.command == "verify":
        success = verify_system_requirements()
        sys.exit(0 if success else 1)
    elif args.command == "run":
        run_service(args.service)
