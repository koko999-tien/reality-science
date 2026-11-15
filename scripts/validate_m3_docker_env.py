import re
import os
import sys

def audit_docker_compose(compose_path):
    with open(compose_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    checks = []
    
    # 1. Networks Check
    has_app_net = "app_net:" in content
    has_data_net = "data_net:" in content
    has_compute_net = "compute_net:" in content
    checks.append(("Networks Defined: app_net, data_net, compute_net", has_app_net and has_data_net and has_compute_net, 
                   f"app_net={has_app_net}, data_net={has_data_net}, compute_net={has_compute_net}"))
    
    # 2. Network Isolation Check (internal: true)
    data_net_internal = bool(re.search(r"data_net:\s*\n\s*driver:\s*bridge\s*\n\s*internal:\s*true", content))
    compute_net_internal = bool(re.search(r"compute_net:\s*\n\s*driver:\s*bridge\s*\n\s*internal:\s*true", content))
    checks.append(("Network Isolation: data_net internal: true", data_net_internal, "Blocks external routing to/from database zone"))
    checks.append(("Network Isolation: compute_net internal: true", compute_net_internal, "Blocks external internet access for compute sandbox"))
    
    # 3. Services network bindings
    # frontend should have only app_net
    frontend_block = re.search(r"\n  frontend:(.*?)(?=\n  [a-z_]+:|\Z)", content, re.DOTALL)
    if frontend_block:
        f_text = frontend_block.group(1)
        f_app_net = "app_net" in f_text
        f_data_net = "data_net" in f_text
        f_compute_net = "compute_net" in f_text
        f_valid = f_app_net and not f_data_net and not f_compute_net
        checks.append(("Service Isolation: frontend on app_net only", f_valid, f"app={f_app_net}, data={f_data_net}, compute={f_compute_net}"))
    else:
        checks.append(("Service Isolation: frontend on app_net only", False, "frontend service missing"))

    # api should bridge app_net and data_net (strict Zone 2 isolation without direct compute_net)
    api_block = re.search(r"\n  api:(.*?)(?=\n  [a-z_]+:|\Z)", content, re.DOTALL)
    if api_block:
        a_text = api_block.group(1)
        a_app = "app_net" in a_text
        a_data = "data_net" in a_text
        a_compute = "compute_net" in a_text
        a_valid = a_app and a_data and not a_compute
        checks.append(("Service Orchestration: api triage gateway (Zone 1 & 2)", a_valid, f"app={a_app}, data={a_data}, compute={a_compute}"))
    else:
        checks.append(("Service Orchestration: api triage gateway (Zone 1 & 2)", False, "api service missing"))

    # postgres should be on data_net only
    pg_block = re.search(r"\n  postgres:(.*?)(?=\n  [a-z_]+:|\Z)", content, re.DOTALL)
    if pg_block:
        p_text = pg_block.group(1)
        p_data = "data_net" in p_text
        p_app = "app_net" in p_text
        p_compute = "compute_net" in p_text
        p_valid = p_data and not p_app and not p_compute
        checks.append(("Service Isolation: postgres on data_net only", p_valid, f"data={p_data}, app={p_app}, compute={p_compute}"))
    else:
        checks.append(("Service Isolation: postgres on data_net only", False, "postgres service missing"))

    # redis should be dual-homed on data_net and compute_net, but NOT app_net
    redis_block = re.search(r"\n  redis:(.*?)(?=\n  [a-z_]+:|\Z)", content, re.DOTALL)
    if redis_block:
        r_text = redis_block.group(1)
        r_data = "data_net" in r_text
        r_compute = "compute_net" in r_text
        r_app = "app_net" in r_text
        r_valid = r_data and r_compute and not r_app
        checks.append(("Service Isolation: redis dual-homing conduit", r_valid, f"data={r_data}, compute={r_compute}, app={r_app}"))
    else:
        checks.append(("Service Isolation: redis dual-homing conduit", False, "redis service missing"))

    # minio should be on data_net only
    minio_block = re.search(r"\n  minio:(.*?)(?=\n  [a-z_]+:|\Z)", content, re.DOTALL)
    if minio_block:
        m_text = minio_block.group(1)
        m_data = "data_net" in m_text
        m_app = "app_net" in m_text
        m_compute = "compute_net" in m_text
        m_valid = m_data and not m_app and not m_compute
        checks.append(("Service Isolation: minio on data_net only", m_valid, f"data={m_data}, app={m_app}, compute={m_compute}"))
    else:
        checks.append(("Service Isolation: minio on data_net only", False, "minio service missing"))

    # compute_worker should be on compute_net only
    worker_block = re.search(r"\n  compute_worker:(.*?)(?=\nvolumes:|\Z)", content, re.DOTALL)
    if worker_block:
        w_text = worker_block.group(1)
        w_compute = "compute_net" in w_text
        w_data = "data_net" in w_text
        w_app = "app_net" in w_text
        w_valid = w_compute and not w_data and not w_app
        checks.append(("Service Isolation: compute_worker on compute_net only", w_valid, f"compute={w_compute}, data={w_data}, app={w_app}"))
        
        # Check worker hardening
        has_non_root = 'user: "10001:10001"' in w_text
        has_read_only = "read_only: true" in w_text
        has_cap_drop = "cap_drop:" in w_text and "- ALL" in w_text
        has_no_new_priv = "no-new-privileges:true" in w_text
        has_tmpfs = "/tmp:rw,noexec,nosuid,size=64m" in w_text
        has_cpus = "cpus: 1.0" in w_text or 'cpus: "1.0"' in w_text
        has_mem = "mem_limit: 512m" in w_text
        has_pids = "pids_limit: 100" in w_text
        
        checks.append(("Worker Hardening: non-root UID 10001", has_non_root, 'user: "10001:10001"'))
        checks.append(("Worker Hardening: read_only root filesystem", has_read_only, "read_only: true"))
        checks.append(("Worker Hardening: cap_drop ALL", has_cap_drop, "cap_drop: ALL"))
        checks.append(("Worker Hardening: no-new-privileges", has_no_new_priv, "no-new-privileges:true"))
        checks.append(("Worker Hardening: tmpfs noexec/nosuid", has_tmpfs, "/tmp:rw,noexec,nosuid,size=64m"))
        checks.append(("Worker Hardening: resource limits (CPU/Mem/PIDs)", has_cpus and has_mem and has_pids, "1 CPU, 512MB RAM, 100 PIDs"))
    else:
        checks.append(("Service Isolation: compute_worker on compute_net only", False, "compute_worker service missing"))

    return checks

def audit_redis_conf(conf_path):
    with open(conf_path, 'r', encoding='utf-8') as f:
        content = f.read()
    checks = []
    
    checks.append(("Redis Auth: requirepass configured", "requirepass" in content, "requirepass directive present"))
    checks.append(("Redis Memory: maxmemory cap", "maxmemory" in content, "maxmemory 512mb present"))
    
    disabled_cmds = ["FLUSHALL", "FLUSHDB", "CONFIG", "DEBUG", "SHUTDOWN", "SAVE", "BGSAVE", "EVAL", "EVALSHA"]
    all_renamed = True
    renamed_details = []
    for cmd in disabled_cmds:
        expected = f'rename-command {cmd} ""'
        if expected in content:
            renamed_details.append(cmd)
        else:
            all_renamed = False
            
    checks.append(("Redis Command Hardening: Dangerous admin/eval commands disabled", all_renamed, 
                   f"Disabled: {', '.join(renamed_details)}"))
    return checks

def audit_env_files(root_dir):
    env_files = [
        os.path.join(root_dir, ".env.example"),
        os.path.join(root_dir, "backend", ".env.example"),
        os.path.join(root_dir, "worker", ".env.example"),
        os.path.join(root_dir, "frontend", ".env.example"),
    ]
    
    checks = []
    suspicious_patterns = [
        r"sk-[a-zA-Z0-9]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"ghp_[a-zA-Z0-9]{36}",
        r"BEGIN (RSA|EC|OPENSSH) PRIVATE KEY",
    ]
    
    for ef in env_files:
        if not os.path.exists(ef):
            checks.append((f"Env file exists: {os.path.basename(ef)}", False, f"Missing {ef}"))
            continue
            
        with open(ef, 'r', encoding='utf-8') as f:
            content = f.read()
            
        has_leak = False
        for pattern in suspicious_patterns:
            if re.search(pattern, content):
                has_leak = True
                break
                
        rel_path = os.path.relpath(ef, root_dir)
        checks.append((f"Env Secret Hygiene: {rel_path}", not has_leak, "Zero real secrets/keys detected"))
        
        # Check worker zero postgres invariant (excluding comment lines)
        if "worker" in rel_path:
            uncommented = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
            has_pg = any("DATABASE_URL" in l or "POSTGRES" in l for l in uncommented)
            checks.append(("Worker Zero Postgres Invariant: worker/.env.example", not has_pg, 
                           "Strictly zero DATABASE_URL or POSTGRES credentials in worker env variables"))
                           
    return checks

def audit_dockerfiles(docker_dir):
    checks = []
    
    # Backend Dockerfile
    bf = os.path.join(docker_dir, "backend.Dockerfile")
    if os.path.exists(bf):
        with open(bf, 'r', encoding='utf-8') as f:
            b_text = f.read()
        has_multistage = "AS builder" in b_text and "AS runner" in b_text
        has_nonroot = "USER 10001:10001" in b_text
        has_alembic = "alembic.ini" in b_text
        checks.append(("backend.Dockerfile: multi-stage build", has_multistage, "builder + runner stages"))
        checks.append(("backend.Dockerfile: non-root execution (10001)", has_nonroot, "Runs as appuser 10001:10001"))
    else:
        checks.append(("backend.Dockerfile exists", False, "Missing file"))
        
    # Worker Dockerfile
    wf = os.path.join(docker_dir, "worker.Dockerfile")
    if os.path.exists(wf):
        with open(wf, 'r', encoding='utf-8') as f:
            w_text = f.read()
        has_multistage = "AS builder" in w_text and "AS runner" in w_text
        has_nonroot = "USER 10001:10001" in w_text
        no_postgres_libs = "libpq" not in w_text and "psycopg" not in w_text
        checks.append(("worker.Dockerfile: multi-stage build", has_multistage, "builder + runner stages"))
        checks.append(("worker.Dockerfile: non-root execution (10001)", has_nonroot, "Runs as worker 10001:10001"))
        checks.append(("worker.Dockerfile: zero PostgreSQL client libraries", no_postgres_libs, "No libpq or postgres drivers in build"))
    else:
        checks.append(("worker.Dockerfile exists", False, "Missing file"))
        
    # Frontend Dockerfile
    ff = os.path.join(docker_dir, "frontend.Dockerfile")
    if os.path.exists(ff):
        with open(ff, 'r', encoding='utf-8') as f:
            f_text = f.read()
        has_multistage = "AS deps" in f_text and "AS builder" in f_text and "AS runner" in f_text
        has_nonroot = "USER 10001:10001" in f_text
        has_standalone = "standalone" in f_text
        checks.append(("frontend.Dockerfile: 3-stage alpine build", has_multistage, "deps + builder + runner"))
        checks.append(("frontend.Dockerfile: non-root execution (10001)", has_nonroot, "Runs as nextjs 10001:10001"))
        checks.append(("frontend.Dockerfile: standalone output copy", has_standalone, "Copies .next/standalone"))
    else:
        checks.append(("frontend.Dockerfile exists", False, "Missing file"))
        
    return checks

if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if not os.path.exists(os.path.join(repo_root, "docker-compose.yml")):
        repo_root = r"D:\Reality_Science"
    compose_path = os.path.join(repo_root, "docker-compose.yml")
    redis_path = os.path.join(repo_root, "docker", "redis.conf")
    docker_dir = os.path.join(repo_root, "docker")
    
    print("=" * 80)
    print("REALITY SCIENCE — MILESTONE M3 STATIC DOCKER & ENV AUDIT SUITE")
    print("=" * 80)
    
    all_results = []
    all_results.extend(audit_docker_compose(compose_path))
    all_results.extend(audit_redis_conf(redis_path))
    all_results.extend(audit_env_files(repo_root))
    all_results.extend(audit_dockerfiles(docker_dir))
    
    passed_count = sum(1 for _, ok, _ in all_results if ok)
    total_count = len(all_results)
    
    for title, ok, details in all_results:
        status_str = "[ PASS ]" if ok else "[ FAIL ]"
        print(f"{status_str:9} | {title:50} | {details}")
        
    print("-" * 80)
    print(f"Audit Summary: {passed_count}/{total_count} checks passed ({passed_count/total_count*100:.1f}%)")
    print("=" * 80)
    sys.exit(0 if passed_count == total_count else 1)
