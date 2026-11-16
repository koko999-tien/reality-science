# Backend fixes — 2026-11-16

**Ba lỗi trong scope đã sửa và kiểm chứng. Full live backend vẫn PARTIAL vì compute/history503 còn tồn tại.**

Giao việc: ALL `23e7ed68-332b-4896-a88f-7a2d11d8fe0e`. Checkout `D:/Reality_Science`, branch`main`, HEAD`c6062783f760f126ca87340f3c0736d11010d659`. Giữ baseline và dirty edits có trước. Báo cáo này nối tiếp mốc guard; không cộng các checkpoint cũ vào kết quả mới.

## Kết quả thực thi

| Check | Kết quả | Evidence |
|---|---|---|
| Publication regression trước fix | **1 FAIL, 7 PASS**,10 deselected,5.14s | `publication-before.log`; draft+PASS đổi thành verified |
| Targeted backend sau fix | **88 PASS**,6.31s | `targeted-after.log`:37 target guards,18 restart guards,15 project/auth,18 Stage4 |
| Restart đúng instance | **PASS** | `restart-preflight.json`, `restart-identity.json`, `restart.log` |
| Migration003→004 | **PASS**, exit0 | `migration-004.log` |
| Đủ85 ca PostgreSQL/API thật | **84 PASS, 1 FAIL**,24.08s;0 SKIP/0 teardown ERROR | `live-all.log` |
| Full backend trước review | **206 PASS, 85 SKIP**,26.66s | `backend-default.log`; live target không opt-in |
| Runner sau sửa finding P2 | **22 PASS**,0.39s | `runner-review-fix.log` |
| Live bổ sung NEW-owner trên project | **2 PASS**,1.53s, checkpoint riêng | `review-live/owner-transfer.log`;85 cases gốc giữ nguyên |
| Lỗi xác minh sau start, cleanup thật | **PASS** | `restart-failure-check/result.json`, `restart-cleanup.log`; lỗi chèn, DB marker không sửa |
| Full backend cuối sau review | **210 PASS, 87 SKIP**,25.95s | `backend-default-final.log`;87=85 ca gốc+2 ca owner-transfer, không opt-in |
| Policy metadata trước/sau | **PASS** | `policy-comparison.json`:8 SELECT expressions giống hệt;32 command policies; quyền owner OLD/NEW đúng |
| Tái hiện compute import boundary | **PASS cho chẩn đoán guard từ chối**, không phải compute success | `compute-import-boundary.log` |
| `git diff --check` | **PASS**, exit0 | `diff-check.log` |
| Cleanup cuối | **PASS** | `review-live/result.json`, `process-cleanup-final.json`, `instance.json`;0 process/listener |
| Independent source review | **PASS sau sửa P2** | `REVIEW.md`; chỉ đọc, không reviewer test execution |

Warnings có trước: pytest-asyncio chưa đặt default fixture loop scope; passlib dùng `argon2.__version__` deprecated. Không dùng SKIP/xfail hay đổi HTTP200 thành503 để làm xanh live suite.

## Các lỗi và cách sửa

**Quyền ghi:** migration mới `backend/app/db/migrations/versions/004_owner_only_dml.py`, revision`004_owner_only_dml` dài18 ký tự. Các policy cũ FOR ALL cho phép DELETE theo điều kiện đọc, và UPDATE lấy row public/org rồi chuyển về parent của người đang ghi. Migration giữ SELECT public/owner/org như cũ, tách INSERT WITH CHECK(owner), UPDATE USING(owner)+WITH CHECK(owner), DELETE USING(owner). Áp dụng8 bảng: research_projects, research_versions, equations, variables, claims, claim_relations, validation_runs, validation_findings. Các policy con truy ngược parent về project owner. ENABLE/FORCE RLS, table ownership và role không bypass giữ nguyên. Đây là sửa implementation theo Brief§5 line125; không mở quyền cộng tác mới theo SQL minh họa ADR-003.

**Project POST500:** `backend/app/modules/research_core/service.py` bỏ commit→refresh gây lazy versions trong response, thay bằng awaited SELECT+selectinload(versions)+populate_existing. Live HTTP chứng minh201 với versions[], GET request mới đúng ID, owner được đọc, anonymous/spoofed/outsider bị404, JWT sai401; kết nối DB riêng đọc đúng project đã commit. Không tạo version ngầm.

**Publication:** `backend/app/modules/reality_constraint_engine/router.py` bỏ phép gán draft→verified khi validation PASS. Stage4 regression chạy compute thật cho đủ/thiếu biếna, nhận PASS/FAIL tương ứng và giữ draft/preprint/published/retracted. Published là giá trị fixture legacy đang có, được bảo toàn chứ không định nghĩa trạng thái mới. Các ca này override DB/access; không phải bằng chứng live successful computation hay durable run persistence.

## Phạm vi84 ca live PASS

| Nhóm | Số ca PASS | Nội dung |
|---|---:|---|
| RLS flags | 1 | Cả8 bảng ENABLE/FORCE |
| Visibility | 8 | Owner/public/anonymous/org đọc theo semantics cũ |
| Non-owner DELETE | 48 |8 bảng ×2 visibility ×3 reader(outside/org/anonymous) |
| Project takeover | 1 | Public project không bị đổi chủ bởi outsider |
| Non-owner reparent | 7 | Chặn chuyển row public và org-visible sang parent của outsider |
| INSERT/read-after-commit | 1 | Outsider bị42501; owner commit rồi connection mới đọc thấy |
| Owner CRUD + non-owner INSERT/UPDATE | 8 | Cả8 bảng; private/public; owner positive |
| NEW parent ownership | 7 | Owner không chuyển child sang parent thuộc owner khác |
| Transaction context | 2 | Actor/org qua commit/rollback/reused connection; unique-error rollback không rò context |
| Live login/project/persistence | 1 | Real JWT/hash/Uvicorn/PostgreSQL; POST201 và request/connection mới đọc đúng |

Đây là toàn bộ83 ca SQL và1 ca live project trong bộ85 hiện có, không phải lời khẳng định mọi hợp đồng RLS/privacy đã nghiệm thu. File85 ca live không đổi so baseline. Hai ca bổ sung ở file riêng kiểm tra owner không thể tự chuyển project private/public sang actor khác và quyền sở hữu không đổi sau rollback/connection mới;2 PASS là checkpoint riêng, không cộng vào run84/1.

## Failure còn lại và phần chưa chạy

`test_live_version_writes_history_and_access` vẫn **FAIL** tại assertion HTTP200, thực tế503. Trước điểm này, register/login, owner equation/variable POST201, GET read-after-write và private/public endpoint access đã chạy qua HTTP/DB thật. Không đếm các bước này thành test PASS riêng.

API import `worker.tasks.compute_tasks` trong chính process mang `DATABASE_URL` và `REALITY_TEST_DATABASE_URL`; worker/config.py từ chối các tên biến này theo invariant zero-DB. Chẩn đoán riêng cùng environment xác nhận RuntimeError/FATAL SECURITY VIOLATION. Không sửa worker guard hoặc xóa biến môi trường API để giả success, không mock compute ở85 live cases. Log API hiện chỉ lifecycle; exact guard exception được giữ riêng trong `compute-import-boundary.log`.

Các assertion sau503 về run/history/findings/publication persisted/export chưa tới được (**NOT RUN**). Successful queue/compute, version-create/atomic save/freeze là scope tiếp theo. Không nghiệm thu Layer6, production topology, RLS dưới race đồng thời, frozen-child protection hoặc privacy contracts ngoài8 bảng. Migration downgrade chưa thực thi (**NOT RUN**); nó phục hồi semantics003 cũ.

## Restart và cleanup

Instance`74caee9603bb4ea986e62cb223864982`, DB`rs_test_74caee9603bb4ea986e62cb223864982`, system ID`7708747722773675460`, PostgreSQL17.12, loopback60655. Data path `C:/Users/TIEN PC/AppData/Local/Temp/opencode/reality-postgres-83c0e945/data`.

`scripts/disposable_postgres.py start` kiểm tra manifest/token/DB/port/path, pg_controldata system ID và clean shutdown, không postmaster.pid, cấu hình data_directory/port/listen_addresses/cluster_name và cổng khả dụng. Sau start kiểm tra online identity/DB marker rồi mới cho migrate/test; lấy PID hiện tại từ postmaster marker mới, không dùng PID lịch sử để restart. Admin connection đóng khi identity/marker sai. Có22 regression guard/lifecycle; successful start/stop được chứng minh live.

Review tìm một P2 trong bản runner đầu: start thành công nhưng online verification lỗi có thể để manifest vẫn ghi stopped. Đã sửa: lưu starting/stopped=false trước spawn, bỏ PID lịch sử, lưu PID mới trước verification; failure recheck core server identity và fresh marker trước shutdown. Nếu identity không xác minh được thì giữ cleanup_required và từ chối kill. Bài live chèn lỗi sau online verification thật đã kiểm tra cleanup thật; không đổi marker DB. Reviewer đọc lại và không còn correctness finding trong scope. Chi tiết `REVIEW.md`.

`run_live.py` chứa một lifecycle bounded, finally dừng đúng instance sau kiểm tra online. `run_review_live.py` tiếp tục cùng cluster cho failure injection rồi2 ca mới. Stop kiểm tra PID hiện tại/data/port rồi pg_ctl fast; offline state cuối `shut down`, marker mất, DB60655/API51531/API51578 đều đóng. OS inventory cuối21:33:07+07:00:0 task process/0 listener. PostgreSQL ZIP/binaries và synthetic DB được giữ ở task temp directory; pytest cache, __pycache__ và evidence là local writes bình thường. Không service/global install hoặc Windows policy change.

## Files, diff, hashes và lệnh

Code/tests changed in this slice:

1. `backend/app/db/migrations/versions/004_owner_only_dml.py` — mới, split policies.
2. `backend/app/modules/research_core/service.py` — eager response query.
3. `backend/app/modules/reality_constraint_engine/router.py` — bỏ publication mutation.
4. `backend/scripts/disposable_postgres.py` — checked start/admin identity/stop.
5. `backend/tests/unit/test_disposable_postgres_runner.py` — mới,22 guard/lifecycle cases.
6. `backend/tests/integration/test_stage4_final_e2e_integration.py` —8 combinations publication×compute thay2 cases cũ.
7. `backend/tests/unit/test_research_project_auth.py` — mock result hỗ trợ scalar_one cho awaited query.
8. `backend/tests/integration/test_decision3_project_owner_transfer.py` — mới,2 live NEW-owner regressions; không sửa85 cases gốc.

Baseline8 files được giữ trong `baseline/`, kèm `baseline-sha256.json`. `baseline-preservation.json` xác nhận guard/85 live cases/migration003 giữ nguyên checkpoint cũ. Exact delta so baseline và file mới nằm ở `slice.patch`; SHA256 hiện tại ở `changed-files-sha256.json`, `verification-inputs-sha256.json`. Các dirty changes khác không thuộc slice này. Shared trackers do ALL giữ; không commit/push/deploy, frontend/worker write, DB người dùng, .env.production hoặc global settings.

Lệnh thực thi bằng `backend/.venv/Scripts/python.exe`, working directory `D:/Reality_Science/backend`:

```text
python -m pytest -q --tb=short tests/integration/test_stage4_final_e2e_integration.py -k test_tier3_full_version_validate_and_persistence
python -m pytest -q --tb=short tests/unit/test_disposable_postgres_runner.py tests/unit/test_postgres_target_guard.py tests/unit/test_research_project_auth.py tests/integration/test_stage4_final_e2e_integration.py
python ../.reality/evidence/2026-11-16-backend-fixes/run_live.py
python -m pytest -q --tb=short tests/unit/test_disposable_postgres_runner.py
python ../.reality/evidence/2026-11-16-backend-fixes/run_review_live.py
python -m pytest -q --tb=short tests
git diff --check
```

Wrapper live gọi checked start, migrate head, rồi `pytest -vv --tb=short --basetemp <evidence>/pytest-live tests/integration/test_decision3_postgres_rls.py`, cuối cùng checked stop. Các lệnh default dùng child env xóa riêng2 biến opt-in, không đổi environment toàn máy.

Nguồn chính thức và mapping nguyên nhân: `SCOPE.md`. Evidence failure cũ trong `2026-11-16-backend-live/` không bị ghi đè.

Thời gian lượt tiếp sau khôi phục ngữ cảnh: khoảng25 phút, gồm review/fix và các lần live lifecycle; từ regression log mới đầu tiên tới chốt hashes là19.5 phút. Report được copy vào OpenBot Shared chỉ để đính kèm bàn giao; code/test/evidence chính ở checkout. Ownership backend được release khi gửi kết quả cho ALL; phần compute/queue và version-save/freeze tiếp theo chưa được triển khai trong slice này.
