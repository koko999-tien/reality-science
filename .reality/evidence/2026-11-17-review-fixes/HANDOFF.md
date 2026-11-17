# Bàn giao local cho ALL — review fixes 2026-11-17

**Đã hoàn tất ba finding trong review hiệu chỉnh
`5d8c87aa-b4e7-4393-8c75-02cda4254b92` ở phạm vi local.**
HEAD vẫn là `595e3f0232e06e3f76fa770430a05213f6cda7d2`.

- Worker truyền `SoftTimeLimitExceeded` qua các helper về handler chung;
  timeout không trở thành kết luận khoa học PASS/FAIL hoặc finding được lưu.
- Harness giữ Popen cha để dừng cả cây pytest/API khi timeout; từng bước teardown
  tiếp tục chạy khi bước trước lỗi, lưu evidence rồi mới báo lỗi tổng hợp.
- Worker143 PASS; backend247 PASS/108 SKIP; lifecycle10 PASS.
- Live thường8 PASS; hai timeout helper riêng biệt1 PASS mỗi lượt. Đã đối chiếu
  injection job/PID → result `COMPUTE_TIMEOUT_EXCEEDED` → API503 → zero persisted
  runs/findings, publication giữ `preprint`.
- Hai live failure checks PASS: Redis shutdown lỗi vẫn dọn DB/process; pytest
  timeout30s với API con đang hoạt động vẫn dọn sạch cây tiến trình và PostgreSQL.
- Review độc lập đọc source không tìm thêm blocker; không có reviewer-run suite.
- Final inventory00:38:12+07:00:26 cổng đóng,0 task process, PostgreSQL `shut down`,
  không còn postmaster marker. Hash10 owned files và164 verification inputs đã lưu;
  Git diff check và reverse patch check PASS.

Đọc `REPORT.md`, `REVIEW.md`, `live-correlation.json`,
`final-cleanup-inventory.json`, `owned-source-sha256.json` và
`verification-inputs-sha256.json`. `owned-changes.patch` chỉ gồm10 file của slice.
Không cộng các checkpoint thành một suite tổng.

Lần live đầu bị outer-shell timeout sau6 ca đã hoàn tất, giữ nguyên evidence và
không gọi PASS. Cluster đã được xác minh identity, crash recovery bình thường và
dừng sạch trước retry. Chi tiết nằm trong `outer-timeout-recovery/`.

Windows solo dùng exception injection; native Linux/prefork timer vẫn NOT RUN.
Không mở rộng nghiệm thu sang durable compute recovery, save/freeze, numeric
16m/s/6N, container network hoặc Layer6. Retracted dispatch-atomicity finding và
preexisting remote-cluster deadline không được sửa trong slice này.

ALL giữ quyền cập nhật shared trackers. Tích hợp receipt này vào STATE,
NEXT_ACTION, EXECUTION_LOG và TEST_MATRIX theo thứ tự công việc đã thống nhất;
không cần chạy lại các suite không đổi chỉ để nhận bàn giao. Các thay đổi còn local,
chưa commit/push/deploy. Không có production/secrets/global settings mutation.

**Trạng thái gửi: chưa gửi.** Session hiện không có công cụ OpenBot message hoặc
attachment; handoff này được lưu để ALL đọc trực tiếp. Không giả định đã nhận.
