"""Fail-closed opt-in for committed tests on a disposable PostgreSQL instance.

The runner creates a fresh cluster and a marker before this module may write.
DATABASE_URL / TEST_DATABASE_URL are deliberately never used as fallbacks.
"""

from dataclasses import dataclass
import re
from typing import Mapping

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url


class UnsafePostgresTarget(ValueError):
    pass


@dataclass(frozen=True)
class PostgresTarget:
    url: URL
    instance_id: str


def disposable_target(environ: Mapping[str, str]) -> PostgresTarget | None:
    raw_url = environ.get("REALITY_TEST_DATABASE_URL")
    instance_id = environ.get("REALITY_TEST_INSTANCE_ID")
    if not raw_url and not instance_id:
        return None
    if not raw_url or not instance_id or not re.fullmatch(r"[a-f0-9]{32}", instance_id):
        raise UnsafePostgresTarget("Disposable test URL and 32-character instance ID are required together")
    try:
        url = make_url(raw_url)
    except Exception:
        raise UnsafePostgresTarget("Invalid disposable PostgreSQL URL") from None
    if (
        url.drivername != "postgresql+asyncpg"
        or url.host not in {"127.0.0.1", "::1"}
        or url.port is None
        or not 1024 <= url.port <= 65535
        or url.port == 5432
        or url.database != f"rs_test_{instance_id}"
        or url.username != "rs_test_app"
        or url.query
    ):
        raise UnsafePostgresTarget("Target must be an explicit loopback disposable database and test app role")
    return PostgresTarget(url, instance_id)


async def verify_disposable_connection(connection, target: PostgresTarget) -> dict:
    """Only SELECTs until both server identity and privilege guards pass."""
    row = (await connection.execute(text("""
        SELECT current_database() AS database, current_user AS role,
               host(inet_server_addr()) AS host, inet_server_port() AS port,
               current_setting('cluster_name') AS cluster,
               current_setting('server_version') AS version,
               r.rolsuper, r.rolbypassrls, r.rolcreatedb, r.rolcreaterole,
               pg_get_userbyid(d.datdba) AS database_owner,
               EXISTS (SELECT 1 FROM pg_auth_members WHERE member = r.oid) AS has_memberships,
               EXISTS (SELECT 1 FROM pg_class WHERE relowner = r.oid
                       AND relnamespace = 'public'::regnamespace) AS owns_tables
        FROM pg_roles r JOIN pg_database d ON d.datname = current_database()
        WHERE r.rolname = current_user
    """))).mappings().one()
    if (
        row["database"] != target.url.database
        or row["role"] != "rs_test_app"
        or row["database_owner"] != "rs_test_admin"
        or row["host"] != target.url.host
        or row["port"] != target.url.port
        or row["cluster"] != f"rs_test_{target.instance_id}"
        or any(row[name] for name in ("rolsuper", "rolbypassrls", "rolcreatedb", "rolcreaterole",
                                     "has_memberships", "owns_tables"))
    ):
        raise UnsafePostgresTarget("Connected instance identity or unprivileged role guard failed")
    marker = (await connection.execute(text(
        "SELECT instance_id FROM test_control.instance_identity"
    ))).scalars().all()
    if marker != [target.instance_id]:
        raise UnsafePostgresTarget("Disposable instance marker mismatch")
    return dict(row)
