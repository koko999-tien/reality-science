# Backend PostgreSQL guard — bàn giao 2026-11-16

**Mốc guard: DONE. Kiểm chứng backend rộng hơn: PARTIAL, có lỗi live chưa sửa.**

ALL thu hẹp phạm vi trong message `566d7075-7865-46ed-86c1-a36b2b365984` về guard chọn DB sau khi một phần live đã thực thi theo giao việc `83c0e945`. Báo cáo giữ cả bằng chứng thành công và thất bại; không gọi các ca live đã chạy là NOT RUN, cũng không gọi full suite mặc định là bằng chứng RLS.

Checkout: `D:/Reality_Science`, branch `main`, HEAD `c6062783f760f126ca87340f3c0736d11010d659`. Dirty work có trước được giữ. Không sửa frontend, worker hoặc shared tracker. Không commit/push/deploy, production DB, dữ liệu người dùng, secrets hay global settings.

## Kết quả kiểm tra

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Guard + live suite khi không opt-in | **37 PASS, 85 SKIP** | `guard-default-final.log` |
| Toàn bộ backend khi không opt-in | **182 PASS, 85 SKIP**, 1 warning trong summary | `backend-default-final.log` |
| `git diff --check` | **PASS**, exit0 | `diff-check.log` |
| Alembic lần đầu trên cluster mới | **FAIL**: revision003 dài37, cột metadata dài32 | `migration-initial.log` |
| Alembic sau mở rộng cột metadata | **PASS**, upgrade001→003 | `migration-revision-fixed.log`; metadata cuối dài64 |
| Live trước sửa chuẩn hóa địa chỉ guard | **30 setup ERROR**, chưa tới fixture write/assertion nghiệp vụ | `live-initial.log`; lỗi `/32` đã sửa |
| Live lần đầu sau sửa guard địa chỉ | **19 live PASS, 11 live FAIL, 2 lỗi teardown**; cùng run có34 guard PASS → tổng53 PASS | `live-reproduced.log` |
| Live reparenting bảy bảng con | **7 FAIL**, 78 deselected | `reparent-reproduced.log` |
| Regression publication với DB mock, worker thật | **1 FAIL, 1 PASS**, 10 deselected | `publication-reproduced.log`; assertion thử nghiệm đã rút sau thu hẹp phạm vi |
| Live bổ sung cuối | **NOT RUN**: runner dừng trước pytest do `ConnectionRefusedError [WinError1225]` trên đúng target | `selected-live-not-run.md` |
| Guard kết nối thật + metadata cuối | **PASS**, role không đặc quyền, marker không ghi được | `identity-and-policies.json` |
| Cleanup | **PASS**: system ID khớp, shutdown sạch, PID marker mất, cổng đóng | `cleanup.log`, `instance.json`, `process-cleanup.json`, `postgres-server.log` |

Các cảnh báo: pytest-asyncio chưa đặt `asyncio_default_fixture_loop_scope`; passlib đọc `argon2.__version__` đã deprecated. Không có assertion failure ở full backend mặc định.

## Thay đổi của slice này

1. `backend/tests/postgres_target.py` — chỉ nhận đồng thời `REALITY_TEST_DATABASE_URL` và `REALITY_TEST_INSTANCE_ID`; không dùng `DATABASE_URL`/`TEST_DATABASE_URL`, không dò cổng. Chỉ nhận asyncpg, loopback literal, cổng riêng khác5432, tên DB `rs_test_<32hex>`, role `rs_test_app`, không query overrides. Trước mọi fixture write: SELECT kiểm tra database/role/owner/host/port/cluster, cấm superuser/BYPASSRLS/CREATEDB/CREATEROLE/membership/table ownership, rồi kiểm tra marker. Dùng `host(inet_server_addr())` vì cast text thực tế trả `127.0.0.1/32`.
2. `backend/tests/unit/test_postgres_target_guard.py` —37 ca: URL/opt-in sai, không fallback, không lộ URL credential trong lỗi, identity/role/marker sai, và gọi trực tiếp fixture để chứng minh thiếu/sai opt-in không tạo engine. Mock chỉ kiểm tra guard, không phải bằng chứng PostgreSQL RLS.
3. `backend/tests/integration/test_decision3_postgres_rls.py` — thay test cũ nguy hiểm bằng85 ca opt-in. Bao phủ tám bảng dự án, owner/public/org/anonymous, CRUD, takeover/reparenting, context qua giao dịch và reuse, HTTP thật. Những assertion live đang FAIL được giữ để chủ tiếp theo sửa lỗi. Bộ85 ca cuối chưa chạy live toàn bộ; phạm vi đã chạy có counts riêng ở trên.
4. `backend/scripts/disposable_postgres.py` — runner tạo cluster mới, manifest/marker riêng; xác minh system ID/data directory trước migrate/test/stop. Không cài service. Đã sửa cách thu output pg_ctl từ PIPE sang file để tiến trình server không giữ lệnh chờ.
5. `backend/app/db/migrations/versions/003_stage3_claims_and_epistemic_logic.py` — thêm đúng một `alter_column` mở `alembic_version.version_num` từ32 lên64 trước migration003; giữ revision ID. Chỉ chạy trên cluster task tạo. Downgrade chưa chạy.

Hashes của năm file này: `owned-files-sha256.json`. Diff hai tracked files thuộc slice: `tracked-owned.patch`. Các thay đổi khác hiển thị trong git status là dirty work có trước; không thuộc deliverable này. Assertion publication tạm thêm vào test_stage4 đã được gỡ đúng phần thêm, giữ phần dirty work cũ.

## PostgreSQL thật và dữ liệu thử nghiệm

- PostgreSQL **17.12**, binary Windows x64 từ EDB, `postgres.exe` Authenticode **Valid**, signer EnterpriseDB Corporation.
- Instance ID `74caee9603bb4ea986e62cb223864982`; system identifier `7708747722773675460`.
- DB `rs_test_74caee9603bb4ea986e62cb223864982`; loopback `127.0.0.1:60655`.
- App role `rs_test_app`: superuser=false, bypassrls=false, createdb=false, createrole=false, membership=false, không sở hữu bảng. DB/table owner `rs_test_admin`.
- Cả tám bảng project-bound ENABLE/FORCE RLS. `user_accounts` và `research_actors` không có RLS trong schema hiện tại. Không suy rộng kết quả tám bảng thành toàn DB.
- Trust chỉ giới hạn loopback và hai task roles trong cluster riêng, mọi hàng là synthetic fixtures. Marker schema do admin sở hữu; app chỉ đọc.
- Thư mục task: `C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-postgres-83c0e945/`. ZIP/binaries/data được giữ để bàn giao; không listener/service chạy. Đây là tài nguyên thử nghiệm đã dừng, không phải runtime ứng dụng.

## Điều live đã chứng minh

19 ca live PASS gồm: ENABLE/FORCE RLS tám bảng; tám owner-positive/non-owner-negative/anonymous/private/public/org-read cases; tám outsider-private DELETE bị chặn; một owner INSERT commit→fresh session read và non-owner INSERT bị chặn; một actor/org qua commit/rollback và pool_size1 reuse cùng backend PID không rò sang anonymous/actor khác.

Lỗi live cần sửa tiếp:

- **Public DELETE và takeover:** tám DELETE public đều xóa được row (transaction rollback sau đo); đổi owner project public cũng thành công. `FOR ALL USING(public/owner/org) WITH CHECK(owner)` kiểm tra owner cho row mới nhưng không bảo vệ DELETE hoặc row cũ của UPDATE. Tài liệu PostgreSQL xác nhận semantics này. Brief §5 yêu cầu public read-only; ADR-003 SQL example hiện có mâu thuẫn. Chưa thêm migration004 trong mốc guard.
- **Reparenting:** cả bảy bảng con cho non-owner chuyển row public sang parent họ sở hữu. `reparent-reproduced.log` có từng case. Org/anonymous deletion mới thêm trong85 ca cuối chưa chạy live.
- **Project POST:** HTTP thật trả500 sau khi commit; response serialize `versions` gây `MissingGreenlet`. Log gốc: `project-api-reproduced.log`. Chưa sửa service.
- **Validate/history thành công:** API thật trả503 vì import worker trong tiến trình mang `DATABASE_URL`/`REALITY_TEST_DATABASE_URL` bị `worker/config.py` zero-DB guard chặn. Không vô hiệu guard, không đưa DB driver/credential vào worker. Trước503, register/login đúng/sai mật khẩu, bearer checks, equation/variable POST và GET read-after-write, private/public child access đã thực thi qua Uvicorn/PostgreSQL thật. Test kết thúc FAIL; không có bằng chứng validation result/history thành công end-to-end.
- **Publication:** regression dùng mocked DB/access dependency và compute thật tái hiện validation PASS đổi `draft`→`verified`, trái ba trục trạng thái độc lập trong Brief. Đây không phải bằng chứng live persistence. Log retained; product chưa sửa.

Không dependency override hoặc compute mock trong live API tests. Version fixtures được seed trực tiếp bằng owner app role vì API không có endpoint tạo version. JWT signing key/password là ngẫu nhiên cho fixture, không ghi evidence. Không chạy Redis/Celery/container/network isolation.

## Hợp đồng chưa có và giới hạn

Source review thấy chưa có version-create, atomic editor save/update/delete hoặc freeze workflow hoàn chỉnh. Project POST tạo zero versions; API mới chỉ append child records. Freeze trigger chỉ bảo vệ UPDATE/DELETE version row; chưa kiểm chứng bảo vệ child rows hoặc race. Chưa tự định nghĩa version/save/freeze/hash semantics.

API owner-only private reads khác SQL same-org reads. Evidence artifacts chưa có migration/RLS; IAM encryption/anonymization chưa hoàn chỉnh. Đây là source findings, chưa thành live acceptance trong slice. Layer6 vẫn unresolved. Không có production assurance hay canvas/scientific numeric acceptance mới.

## Cleanup và bất thường của harness

Init đầu đã timeout do server kế thừa PIPE; hồi phục đúng cluster, không reset. Live API teardown trước sửa còn listener ngay sau terminate của venv launcher; đã đổi fixture dừng Popen-owned process tree và đợi cổng đóng, nhưng đường teardown mới chưa chạy live. Sau đó xác minh hai cổng API65193/57310 không còn listener hoặc process.

Trước kiểm tra cuối, PostgreSQL không còn process/listener nhưng còn stale PID11164 và control state chưa clean; nguyên nhân dừng không xác định. Đã đối chiếu offline system ID, data path, PID vắng và port đóng, recovery đúng cluster rồi chụp identity/policies bằng SELECT. Tắt sạch bằng pg_ctl fast, PID phục hồi32100; xác minh control state `shut down`, `postmaster.pid` mất, port60655 đóng. Script một lần `finalize_instance.py` được giữ làm bằng chứng, không dùng nó như runner restart tổng quát.

## Lệnh đã chạy

Working directory `D:/Reality_Science/backend`, Python `./.venv/Scripts/python.exe`:

```powershell
python -m pytest -q --tb=short tests/unit/test_postgres_target_guard.py tests/integration/test_decision3_postgres_rls.py
python -m pytest -q --tb=short tests
python scripts/disposable_postgres.py migrate --evidence ../.reality/evidence/2026-11-16-backend-live --log migration-revision-fixed.log
python scripts/disposable_postgres.py test --evidence ../.reality/evidence/2026-11-16-backend-live --log live-reproduced.log -q --tb=short tests/unit/test_postgres_target_guard.py tests/integration/test_decision3_postgres_rls.py
python scripts/disposable_postgres.py test --evidence ../.reality/evidence/2026-11-16-backend-live --log reparent-reproduced.log -q --tb=short tests/integration/test_decision3_postgres_rls.py -k nonowner_cannot_reparent
python ../.reality/evidence/2026-11-16-backend-live/finalize_instance.py
```

Hai lệnh default cuối chạy bằng wrapper xóa riêng `REALITY_TEST_DATABASE_URL`/`REALITY_TEST_INSTANCE_ID` khỏi child environment, không đổi global env. Lệnh `git diff --check` chạy tại repository root.

## Nguồn chính thức

- https://www.postgresql.org/download/windows/
- https://www.enterprisedb.com/download-postgresql-binaries
- https://get.enterprisedb.com/postgresql/postgresql-17.12-1-windows-x64-binaries.zip
- https://www.postgresql.org/docs/17/ddl-rowsecurity.html
- https://www.postgresql.org/docs/17/sql-createpolicy.html
- https://www.postgresql.org/docs/17/sql-set.html
- https://www.postgresql.org/docs/17/app-initdb.html
- https://docs.sqlalchemy.org/en/20/orm/events.html#sqlalchemy.orm.SessionEvents.after_begin

ZIP SHA256 `a2cd8a774389347b70be7748ac4a37ef43cb6ee539c5fc3e85ae264b15e4a04c` là digest đo local, không phải đối chiếu checksum vendor độc lập.

**Bàn giao:** ALL có thể tích hợp mốc guard qua hashes/logs hiện có; ownership backend slice được release khi gửi báo cáo. Bước tiếp theo là sửa quyền DML/project serialization trên scope riêng rồi chạy các ca live đang FAIL; successful worker/queue contract và version/save/freeze cần xử lý riêng. M-002 vẫn IN PROGRESS.
