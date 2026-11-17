# REALITY SCIENCE — Bàn giao compute/queue local

Ngày: 2026-11-16. Checkout: `D:/Reality_Science`.
Phân công từ ALL: `6927175a-fd31-4b86-981d-3cb60ee2b1f9`.
HEAD tại lúc nhận việc nằm trong `head.txt`; checkout đã có dirty work, được giữ nguyên trong baseline.

Trong lúc chốt evidence, một thao tác ngoài phiên thực hiện slice đã đổi HEAD từ `c6062783f760f126ca87340f3c0736d11010d659` sang `595e3f0232e06e3f76fa770430a05213f6cda7d2` lúc23:42:11+07:00. Local `origin/main` ref cũng trỏ commit mới; không gọi remote hoặc xác minh deploy trong lượt kiểm tra này. Cả19 hash source/test/runner và13 baseline vẫn khớp, nên evidence của slice giữ nguyên phạm vi. Xem `concurrent-head-change.json`; không suy diễn kết quả test của slice thành nghiệm thu toàn commit mới.

## Kết quả

Đã sửa nguyên nhân compute/history HTTP 503: API từng import worker trong process có biến môi trường DB, khiến guard zero-DB của worker chặn đúng thiết kế. Hai endpoint `/validation/verify` và `/versions/{id}/validate` nay đi qua Redis/Celery thật, worker riêng tính toán rồi trả kết quả để API kiểm tra và ghi PostgreSQL. API vẫn giữ cấu hình DB. Guard worker giữ nguyên.

Luồng local đã chứng minh: HTTP → Redis broker → Celery worker riêng chạy engine → Redis result backend → kiểm tra correlation → PostgreSQL → history qua request mới và kết nối DB mới. Lỗi transport/timeout/kết quả không hợp lệ trả 503, không tạo scientific finding. Scientific FAIL hợp lệ vẫn được lưu và đọc lại như kết quả khoa học.

## Thay đổi

- Publisher dùng Celery protocol v2 JSON hiện có, queue `compute_tasks`, ID do server sinh, expiry, hard/soft timelimit và giới hạn body 10 MiB. Backend không thêm dependency Celery.
- Redis `SET NX` với TTL 86400 giây giữ dấu job đã dispatch; cùng job ID không được publish lần thứ hai. Đây là chặn dispatch trùng qua API, không phải exactly-once execution trước mọi trường hợp broker redelivery.
- API đợi tối đa `bundle.timeout_seconds + 5`; Redis socket/connect timeout 2 giây. Không có background ingestion sau timeout/cancel. Result đến muộn không gắn được vào UUID mới; result worker có TTL 3600 giây.
- Kiểm tra Celery `task_id`, finding `job_id`, `version_id`, target type/ID, SHA256 toàn bộ JobBundle và đủ đúng layer 1–6. `_persist_validation` kiểm tra lần nữa trước DB write; đã bỏ nhánh tự tạo layer record khi thiếu layer.
- Job ID cũng là durable run ID; mỗi finding lưu job/run ID và provenance hash/version. Không tự đổi publication state khi PASS hoặc FAIL.
- Worker kiểm tra Celery task ID khớp input, thêm provenance vào output. Unexpected engine exception trở thành Celery failure; soft-timeout result được API chuyển thành lỗi unavailable.
- Cluster dispatcher không có transport báo lỗi rõ `Cluster node transport is not configured`; bỏ direct-worker/fake PASS fallback. Transport được cấu hình luôn phải kiểm tra provenance, kể cả khi một mock executor không được dùng cũng có mặt.

17 file product/test được ghi trong `slice-files.json`, cùng 2 script lifecycle evidence. `slice.patch` là diff từ **baseline dirty tại lúc nhận slice**, bao gồm đầy đủ file mới; không phải diff toàn checkout so với Git HEAD. `slice-sha256.json` chứa hash của 19 file này. `artifact-integrity.json` xác nhận cả 19 hash hiện tại và 13 hash baseline khớp; kiểm tra AST bỏ docstring cho live85 cũng khớp. Stage1 được snapshot nhưng không sửa. Bộ live85 chỉ sửa docstring cũ; assertion vẫn giữ nguyên.

Kiểm tra áp patch ban đầu phát hiện script evidence xuất CRLF trên Windows; lỗi và bản cũ được giữ trong `patch-format-first.json`/`slice-initial-crlf.patch`. Đã sửa riêng `finalize_evidence.py` để xuất LF. `patch-roundtrip.json` ghi `git apply --check --whitespace=error-all` và áp thật lên bản sao baseline tạm đều exit0; cả19 file tái tạo khớp nội dung hiện tại khi chuẩn hóa CRLF/LF. Product/test/runner bytes và các hash đã kiểm thử không đổi. SHA256 patch cuối: `184c787c28bcea8663b95c45aec093ec75003fffa4b487008c0bdf1154673cdd`.

## Kiểm chứng đã chạy

| Lượt chạy | Kết quả | Thời gian | Bằng chứng |
|---|---:|---:|---|
| Targeted backend đầu | 47 PASS | 6.94 s | `targeted-first.log` |
| Targeted worker đầu | 9 PASS | 5.91 s | `worker-targeted-first.log` |
| Backend đầy đủ cuối | 237 PASS, 107 SKIP, 1 warning | 28.28 s | `backend-final.log`, `backend-final-command.json` |
| Worker đầy đủ trong venv riêng | 126 PASS | 12.93 s | `worker-default.log`, `worker-default-command.json` |
| Shared schema suite | 53 PASS | 0.49 s | `shared-default.log`, `shared-default-command.json` |
| Original live85 | 85 PASS | 23.35 s | `live-original.log` |
| Owner-transfer + queue lần đầu | 10 PASS, 1 deselected | 36.55 s | `live-extra.log` |
| Live cuối trên code đã bỏ layer fallback | 95 PASS, 12 deselected | 56.45 s | `live-final.log` |
| Không có worker, API deadline | 1 PASS, 8 deselected | 20.02 s | `live-no-worker.log` |
| Real-broker fault injection | 11 PASS, 9 deselected | 52.78 s | `live-faults.log` |
| `git diff --check` | PASS | — | `diff-check.json` |
| Patch áp lại lên baseline tạm | PASS, 19 file khớp | — | `patch-roundtrip.json` |

Không cộng các checkpoints thành tổng test. Backend default 107 SKIP chính là 85 PostgreSQL + 2 owner-transfer + 20 queue tests yêu cầu disposable DB/broker. Tất cả đã được chọn chạy trong các lifecycle tương ứng: live95, no-worker1, faults11. Hai cảnh báo hiện có là pytest-asyncio chưa đặt loop scope và passlib dùng argon2.__version__; không có selected test fail ở lượt cuối.

Live95 gồm nguyên85 ca gốc, 2 owner-transfer và 8 ca queue. Nó kiểm chứng register/login, project POST201/GET mới, RLS trên8 bảng, owner/non-owner/public, transaction context, symbolic PASS, thiếu biến FAIL, sai thứ nguyên FAIL và chia0 FAIL. Bốn ca version bao phủ valid/invalid × private/public: đúng6 finding, run ID=job ID, target đúng, history bằng request mới, PostgreSQL connection mới và publication giữ preprint. Original live85 xác minh publication draft vẫn draft.

11 fault cases gồm JSON hỏng, sai task/job/version/target/hash, thiếu layer, FAILURE, REVOKED, late result và dispatch trùng. Chín result faults và late result dùng HTTP thật, Redis thật, PostgreSQL thật với envelope cố tình sai; trả503, history rỗng, zero validation runs, publication giữ preprint, result key của request bị xóa. Ca duplicate gọi publisher thật hai lần, chỉ có một message, claim TTL đúng. Đây là **fault injection có chủ đích**, không được dùng làm bằng chứng worker đã tính khoa học. Worker unexpected failure còn được kiểm tra bằng unit test; không cố tình crash worker native trong live.

Lệnh chạy chính, từ `D:/Reality_Science/backend`:

```powershell
.\.venv\Scripts\python.exe ..\.reality\evidence\2026-11-16-compute-queue\run_checks.py backend backend-final
.\.venv\Scripts\python.exe ..\.reality\evidence\2026-11-16-compute-queue\run_checks.py worker
.\.venv\Scripts\python.exe ..\.reality\evidence\2026-11-16-compute-queue\run_checks.py shared
.\.venv\Scripts\python.exe ..\.reality\evidence\2026-11-16-compute-queue\run_live.py live-final tests/integration/test_decision3_postgres_rls.py tests/integration/test_decision3_project_owner_transfer.py tests/integration/test_compute_queue_live.py -k 'not fault and not without_worker'
$env:REALITY_TEST_NO_WORKER='1'
.\.venv\Scripts\python.exe ..\.reality\evidence\2026-11-16-compute-queue\run_live.py live-no-worker tests/integration/test_compute_queue_live.py -k without_worker
.\.venv\Scripts\python.exe ..\.reality\evidence\2026-11-16-compute-queue\run_live.py live-faults tests/integration/test_compute_queue_live.py -k fault
```

Hai lệnh no-worker dùng process shell riêng, không set môi trường global. `run_live.py` từ chối ghi đè tên evidence cũ; nếu chạy lại phải đặt tên mới. Manifest trong `instance.json` trỏ đúng disposable cluster đã tạo từ slice trước; không dùng runner trên DB khác.

## Runtime và cleanup

PostgreSQL17.12 riêng: database `rs_test_74caee9603bb4ea986e62cb223864982`, system ID `7708747722773675460`, loopback60655, revision `004_owner_only_dml`. Role app `rs_test_app` không superuser, không BYPASSRLS/CREATEDB/CREATEROLE. Checked-start kiểm tra offline system ID/path/port/cluster name/postmaster marker, rồi online database marker trước mọi test write. Bằng chứng: `live-final-db-identity.json` và `live-final-restart/`.

Memurai official MSI URLs trả HTTP403; không installer nào chạy. Runtime dùng Redis8.10.3 **community Windows Cygwin build**, ZIP SHA256 `8000848c48668c8cd32f21386ce951d0e02c1aefae39443ab9d3de11ff8ebf9e`, chỉ dùng dữ liệu synthetic local. Xem `runtime-download.json`; không cài service hay cấu hình global.

Broker cuối chạy loopback57168, run ID `ad144d817c6b35bba2a64a63d30515448c0d74cf`, marker được kiểm tra trước shutdown. Worker thật PID30220 chạy Python3.11.18/venv riêng, guard PASS, không DB env và không các driver asyncpg/psycopg/psycopg2/sqlalchemy/pymysql/pymongo. Audit socket ghi5 connection, tất cả tới broker57168; xem `live-final-worker-identity.json`, `live-final-worker-connections.jsonl`.

Trước shutdown, live-final queue length0/result keys0 và worker còn sống. `live-final-cleanup.json`: PostgreSQL stopped + control state shut down, broker exit0, worker exit1 do task-owned termination chủ đích, tất cả12 cổng đóng. Mỗi lifecycle có cleanup riêng. No-worker còn1 message chưa được consume trước shutdown broker `nosave`; API đã trả503 và không ghi DB. `cleanup-fresh.json` ghi kiểm tra mới: không có process runtime task-owned, không có listener trên 37 cổng tổng hợp từ mọi lifecycle; `pg_controldata` xác nhận đúng system ID, `shut down` và không còn `postmaster.pid`. Không dừng thêm process bằng PID lịch sử.

## Review và giới hạn

Review độc lập hoàn tất: **No blocker found** trong phạm vi source/baseline/tests/evidence; reviewer không sửa file hoặc chạy process. Hai sửa đổi cuối đã được xác nhận: bỏ synthesized layer fallback ở persistence và không để mock executor không dùng làm bỏ qua kiểm tra cluster transport. Reviewer không tìm thấy race/integrity defect mới cụ thể hoặc đường gắn late result sang job khác; xác nhận claim `SET NX` được giữ khi publication không chắc chắn và Redis client đã khóa không tự retry `LPUSH`. Phạm vi và giới hạn được ghi trong `REVIEW.md`; đây không phải một lượt test độc lập mới.

- Windows Celery solo đã chạy thật; Celery FAQ không hỗ trợ Windows chính thức. **NOT RUN** Linux prefork hard/soft timeout thực, container/network sandbox, production lifecycle. Socket audit là quan sát, không phải firewall/network sandbox.
- **NOT PROVEN** giá trị16m/s/6N: VariableSpec chưa có assigned numeric value; không tự thêm semantics ngoài hợp đồng.
- Version fixture SQL-seeded vì API tạo version chưa tồn tại. **NOT RUN/ngoài slice** save/freeze end-to-end, Layer6 scientific acceptance, full accessibility.
- Queue correlation hash chứng minh kết quả gắn đúng staged input, không phải chữ ký xác thực worker hay snapshot lịch sử đầy đủ. Có Redis redelivery thì worker có thể tính lặp; cùng API context chỉ persist một lần và run primary key chặn trùng ID.
- `validate_version` vẫn dùng primary equation và các payload context theo implementation có sẵn; slice này không tuyên bố đã tính toàn bộ mô hình có nhiều equation/dataset.

## Nguồn

- [Celery Redis broker/result backend](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html): queue LPUSH/BRPOP, result key, visibility timeout, expiry và eviction.
- [Celery message protocol](https://docs.celeryq.dev/en/stable/internals/protocol.html): envelope v2. Trang có mô tả thứ tự timelimit không thống nhất; mã đã cài `celery/app/amqp.py:375` dùng `[time_limit, soft_time_limit]`, `celery/worker/request.py:356` đọc hard,soft. Publisher theo implementation này; Windows solo không xác minh hard limit runtime.
- [Celery FAQ — Windows](https://docs.celeryq.dev/en/stable/faq.html#does-celery-support-windows): không hỗ trợ Windows từ4.x.
- [Redis Windows guidance](https://redis.io/docs/latest/operate/oss_and_stack/install/archive/install-redis/install-redis-on-windows/), [Memurai docs](https://docs.memurai.com/en/installation.html): nghiên cứu runtime trước fallback community build.
- [Redis Windows community release8.10.3](https://github.com/redis-windows/redis-windows/releases/tag/8.10.3): nguồn ZIP thực dùng, được ghi riêng vì không phải official Redis binary.

## Bàn giao

Artifact chính: `REPORT.md`, `REVIEW.md`, `WORK.md`, `HANDOFF.md`, `slice.patch`, `slice-files.json`, `slice-sha256.json`, `baseline-sha256.json`, `artifact-integrity.json`, `patch-roundtrip.json`, `diff-check.json`, `cleanup-fresh.json`, logs/identities/cleanup và JSON evidence từ tests. Shared `.reality/{STATE,NEXT_ACTION,EXECUTION_LOG,TEST_MATRIX,DECISIONS}` thuộc ALL; báo cáo này là đầu vào cập nhật các tracker đó.

Agent thực hiện slice này không commit/push/deploy, không migration/reset DB production hoặc DB người dùng, không sửa secrets/global settings. Checkout đã có commit mới từ thao tác đồng thời nêu ở đầu report; các tài liệu chốt bàn giao tiếp tục là thay đổi local. Bước tiếp theo thuộc điều phối ALL: tích hợp bằng chứng local queue/history và xác định milestone scientific/model/save tiếp theo, giữ nguyên các giới hạn nêu trên.
