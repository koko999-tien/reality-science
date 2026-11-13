# REALITY SCIENCE — Phân Tích Kiến Trúc, PRD, Sitemap & Lộ Trình Triển Khai

> [!IMPORTANT]
> Tài liệu này thực hiện **Bước Tiền Triển Khai (Mục 25.1)** của Master Project Brief v1.0: bóc tách mâu thuẫn tiềm ẩn, điểm khuyết đặc tả, đánh đổi kỹ thuật, chuẩn hóa PRD, Sitemap toàn ứng dụng và Lộ trình phân kỳ thực tế.

---

## 1. Phân Tích Phản Biện: Mâu Thuẫn, Điểm Khuyết & Đánh Đổi Kiến Trúc

Trước khi viết dòng code đầu tiên, có **6 điểm xung đột / thiếu hụt kỹ thuật trọng yếu** trong Master Brief cần được giải quyết dứt điểm ở tầng thiết kế:

| # | Vấn đề / Xung đột trong Đặc tả | Tác động nếu bỏ qua | Giải pháp Kiến trúc Đề xuất |
| :--- | :--- | :--- | :--- |
| **1** | **Mạng Hybrid (14.1 vs 14.2):** Worker chạy trên Cloud đàn hồi (AWS/GCP) nhưng Dữ liệu gốc & DB nằm ở Private Data Layer không mở ra Internet. | Worker trên Cloud bị nghẽn băng thông qua Tunnel khi đọc dataset hàng GB, hoặc buộc phải mở port DB gây mất an toàn. | **Job Bundle Staging + Ephemeral Signed Read:** Worker chỉ nhận *Immutable Job Snapshot* (input đã lọc quyền + script + hash) qua S3/MinIO Gateway có chữ ký ngắn hạn; kết quả chạy xong được đẩy lại qua Queue, **Worker không bao giờ nối trực tiếp tới PostgreSQL Production**. |
| **2** | **An toàn tính toán Python (13.1 vs 15.2):** Backend dùng chung hệ sinh thái Python (`FastAPI` + `SymPy` + `SciPy`), nhưng biểu thức toán của người dùng có thể gây nổ RAM/CPU (*Symbolic Bomb*) hoặc RCE (`eval`/`lambdify`). | Một biểu thức SymPy độc hại hoặc tích phân quá phức tạp làm treo toàn bộ API Gateway/Backend. | **Tách cứng Process & Sandbox:** `FastAPI` tuyệt đối không import/chạy `SymPy`/`SciPy` trực tiếp trong HTTP request. Mọi phép tính/biểu thức đều đẩy sang **Compute Sandbox Worker** (Container cô lập `--network=none`, giới hạn CPU/RAM/Timeout qua cgroups). |
| **3** | **Bất biến Nghiên cứu (12.4) vs Quyền xóa Dữ liệu Cá nhân (12.5):** Lịch sử phiên bản & chứng cứ phải bất biến, nhưng thông tin cá nhân (PII) không được giữ vĩnh viễn khi user yêu cầu xóa. | Vi phạm luật bảo vệ dữ liệu (GDPR/PDPD) hoặc làm vỡ toàn bộ khóa ngoại/lịch sử trích dẫn khi xóa user. | **Tách danh tính (Identity Split):** Tách bảng `user_accounts` (chứa PII: email, tên thật, auth) khỏi `research_actors` (chứa `actor_uuid` và `public_handle`). Khi xóa tài khoản, PII bị xóa sạch nhưng `actor_uuid` chuyển sang trạng thái `[Deleted Contributor]` giúp giữ nguyên vẹn chuỗi provenance. |
| **4** | **Nhập công thức LaTeX vs Kiểm tra SymPy/Pint (5.2 & 7.3):** LaTeX thuần túy bị nhập nhằng ngữ nghĩa (ví dụ `m` là khối lượng hay mét? `E(x)` là hàm hay phép nhân `E * (x)`?). | Layer 2 (Math) và Layer 3 (Dimensional) của Reality Constraint Engine sẽ báo lỗi sai hàng loạt nếu chỉ parse LaTeX thô. | **Symbol-First Authoring:** Bắt buộc khai báo bảng **Variables & Units** trước (hoặc kèm theo) khi viết phương trình. Công thức lưu dưới 2 dạng song song: **Display LaTeX** (hiển thị) + **Canonical AST / SymPy JSON** (kiểm chứng). |
| **5** | **19 Thành phần Research Object vs Versioning (6.1 & 12.4):** Nếu mỗi lần sửa lưu bản sao cả 19 bảng quan hệ, CSDL sẽ phình cực nhanh và khó so sánh diff. | Chi phí lưu trữ bùng nổ, khó truy vết chính xác phiên bản dataset/validator nào đi với phiên bản nghiên cứu nào. | **Mutable Draft + Immutable Content-Addressed Snapshot:** Khi đang soạn thảo (`Draft`), chỉnh sửa trên bảng làm việc. Khi bấm Publish/Submit Validation, đóng băng thành `research_version_snapshots` bất biến (pin rõ `claim_ids`, `equation_ids`, `dataset_version_id`, `rce_ruleset_version`). |
| **6** | **Khả năng Validate Vũ trụ học / Vật lý nâng cao (1.2 vs 25.3):** Ví dụ minh họa dùng giả thuyết thay thế Big Bang, nhưng việc kiểm chứng tự động vũ trụ học đòi hỏi bộ dữ liệu quan sát chuyên sâu. | Dễ tạo kỳ vọng ảo hoặc gắn nhãn sai cho mô hình lý thuyết phức tạp. | Áp dụng nghiêm ngặt trạng thái `NOT APPLICABLE` / `NEEDS EXPERT REVIEW` ở RCE Layer 4–5 cho các lĩnh vực chưa có bộ rule/dataset chuẩn hóa, chỉ kích hoạt tự động theo từng miền đã kiểm định (Stage 1–2 chỉ mở **Đại số, Giải tích cơ bản, Cơ học cổ điển & Thứ nguyên SI**). |

### Các điểm khuyết cần làm rõ thêm với Chủ dự án
1. **Phạm vi thực thi mã nguồn người dùng ở MVP:** Trong MVP (Stage 1–2), có cho phép người dùng upload file script `.py` tự do không, hay chỉ cho nhập biểu thức toán học + tham số qua giao diện có cấu trúc (an toàn hơn gấp nhiều lần)?
2. **Hạ tầng Private Data Layer ban đầu:** Bạn dự kiến đặt ở VPS/Dedicated Server tự quản lý (`Docker Compose`/`k3s`), hay Private VPC trên AWS/GCP?
3. **Mô hình Tổ chức (Multi-tenancy):** MVP mở hoàn toàn cho tài khoản cá nhân công khai hay cần không gian làm việc kín theo nhóm/viện nghiên cứu (`Private Organization Workspace`) ngay từ đầu?

---

## 2. Product Requirements Document (PRD) — Phiên Bản Tóm Lược Thực Thi

### 2.1. Đối tượng sử dụng & Vai trò (User Personas)
1. **Nhà nghiên cứu độc lập / Người yêu khoa học:** Cần trình bày giả thuyết có cấu trúc, định nghĩa ký hiệu mới, kiểm tra tính nhất quán toán/đơn vị, nhận phản biện công bằng.
2. **Nhà khoa học / Giảng viên / Sinh viên:** Cần tra cứu nền tảng tri thức chuẩn có nguồn trích dẫn, chạy mô phỏng kiểm chứng, phản biện ngang hàng (Peer Review) và tái lập kết quả (Replication).
3. **Chuyên gia Thẩm định (Verified Expert):** Đánh giá sâu các mô hình vượt ngưỡng tự động của RCE (`NEEDS_EXPERT_REVIEW`), công khai xung đột lợi ích.
4. **Quản trị Dữ liệu & Kiểm duyệt viên (Data Steward / Moderator):** Giám sát tính toàn vẹn dữ liệu, xử lý khiếu nại đạo văn/giả mạo dữ liệu theo quy trình minh bạch, kiểm tra Audit Log.

### 2.2. Nguyên tắc Sản phẩm Bắt buộc (Product Invariants)
- **Tách 3 chiều trạng thái độc lập** cho mọi Research Object:
  1. `publication_status`: `draft` -> `submitted` -> `preprint` -> `under_review` -> `peer_reviewed` -> `revised` / `corrected` / `withdrawn` / `retracted`.
  2. `validation_status`: `not_tested` -> `in_progress` -> `passed_selected` / `passed_with_warnings` / `failed` / `insufficient_data` / `needs_expert_review` / `independently_reproduced`.
  3. `evidence_maturity`: `exploratory_idea` -> `formally_developed` -> `preliminary_evidence` -> `independently_supported` -> `strongly_convergent`.
- **Kiến trúc lấy Khẳng định làm trung tâm (Claim-Centered):** Một bài nghiên cứu có thể chứa nhiều `Claims`; mỗi Claim mang trạng thái kiểm chứng, phương trình và bằng chứng ủng hộ/phản bác độc lập.
- **Không xếp hạng chân lý bằng lượt thích (No Popularity Truth):** Tuyệt đối không dùng Like/Follow làm trọng số xếp hạng độ tin cậy khoa học.

### 2.3. Phân kỳ Yêu cầu Chức năng (MVP P0 -> P1 -> P2)
- **P0 (MVP Cốt lõi — Bắt buộc chạy trơn tru trước khi mở rộng):**
  - Định danh, phân quyền RBAC/ABAC, hồ sơ nhà nghiên cứu & công khai xung đột lợi ích.
  - Kho Tri thức Nền tảng (Knowledge Base có version: Định nghĩa, Tiên đề, Định luật, Hằng số vật lý).
  - Research Studio: Soạn thảo Research Object có cấu trúc + Bảng Biến/Đơn vị + Soạn thảo LaTeX/Math + Gắn Nguồn/Tài liệu.
  - RCE Cấp độ 1–3: Kiểm tra định nghĩa/biến chưa khai báo (Semantic), Kiểm tra đại số/đạo hàm/tích phân qua SymPy (Math), Kiểm tra tương thích đơn vị SI qua Pint (Dimensional).
  - Đóng băng Phiên bản (Immutable Versioning) + Lưu vết Audit Log bắt buộc.
  - Thảo luận khoa học có cấu trúc theo từng Claim/Version (phản biện, đặt câu hỏi, đính kèm phản chứng).
- **P1 (Mở rộng Tính toán & Trợ lý AI):**
  - Tính toán số (`NumPy`/`SciPy`), biểu đồ khoa học thực (`Plotly`).
  - AI Research Assistant (chỉ hoạt động qua Tool API: phát hiện thiếu định nghĩa, gợi ý kiểm tra SymPy/Pint, tóm tắt tài liệu, bị cấm tự bịa nguồn hay tự kết luận đúng/sai).
  - Môi trường mô phỏng cơ bản (Cơ học cổ điển, động học, bảo toàn năng lượng) chạy trong Worker cô lập.
- **P2 (Hệ sinh thái Khoa học Toàn cầu):**
  - RCE Lớp 4–6 đầy đủ (Thư viện ràng buộc vật lý có điều kiện biên, So sánh sai số thực nghiệm Residual Analysis, Gói tái lập Reproducibility Bundle).
  - Khám phá Đồ thị Tri thức (Knowledge Graph Explorer), Mô phỏng 3D (`Three.js`), Không gian hợp tác Viện/Trường.

---

## 3. Application Sitemap (Cấu Trúc Toàn Ứng Dụng)

```text
REALITY SCIENCE
├── / (Home — Tổng quan hệ sinh thái, nghiên cứu mới thẩm định, câu hỏi mở)
├── /discover (Khám phá Tri thức & Nghiên cứu)
│   ├── /discover/knowledge (Kho Tri thức Chuẩn: Định nghĩa, Định luật, Hằng số, Lý thuyết)
│   ├── /discover/research (Thư viện Research Objects — lọc theo lĩnh vực, validation & maturity)
│   ├── /discover/claims (Tra cứu theo từng Khẳng định khoa học & Bằng chứng trái chiều)
│   └── /discover/questions (Các vấn đề khoa học mở & Thách thức nghiên cứu)
├── /research (Không gian Nghiên cứu)
│   ├── /research/new (Trình tạo Research Object có hướng dẫn từng bước)
│   ├── /research/[id] (Trang đọc Research Object: Tóm tắt, Claims, Giả định, Phương trình, Báo cáo RCE)
│   ├── /research/[id]/versions/[v] (Xem bất biến một phiên bản đã phát hành & diff giữa 2 version)
│   ├── /research/[id]/studio (Trình soạn thảo: Variables/Units Table, LaTeX/SymPy Editor, References)
│   ├── /research/[id]/validation (Chi tiết RCE: Semantic, Math, Dimensional, Physical, Empirical)
│   └── /research/[id]/reproduce (Gói tái lập: Tham số, Code/Model hash, Log thực thi, So sánh kết quả)
├── /workspace (Phòng Lab Tính toán & Mô phỏng)
│   ├── /workspace/math (Trình giải biểu thức & kiểm tra đạo hàm/tích phân với SymPy)
│   ├── /workspace/units (Trình kiểm tra thứ nguyên & quy đổi đơn vị SI với Pint)
│   ├── /workspace/data-lab (Upload dataset thô, làm sạch có vết biến đổi, phân tích sai số)
│   └── /workspace/simulations (Môi trường mô phỏng vật lý gắn chặt với phương trình & giả định)
├── /graph (Knowledge Graph Explorer — Truy vết nguồn gốc khái niệm, giả định & xung đột)
├── /community (Cộng đồng Khoa học)
│   ├── /community/reviews (Hàng đợi Peer Review & Phản biện chuyên sâu)
│   ├── /community/challenges (Thách thức lý thuyết & Tái lập độc lập)
│   └── /community/groups (Nhóm chuyên ngành: Vật lý, Toán, Vũ trụ học, Khoa học dữ liệu...)
├── /profile/[handle] (Hồ sơ đóng góp khoa học, lịch sử phản biện, khai báo xung đột lợi ích)
└── /admin [Private VPN / 2FA Mandatory] (Trung tâm Kiểm soát Dữ liệu & Quản trị)
    ├── /admin/governance (Audit Logs thời gian thực, Truy vết sửa đổi, Kiểm tra tính toàn vẹn Hash)
    ├── /admin/rce-rules (Quản lý & Phiên bản hóa Bộ luật Ràng buộc Vật lý RCE)
    ├── /admin/moderation (Xử lý tố cáo giả mạo dữ liệu, đạo văn, khiếu nại phản biện)
    └── /admin/ops (Giám sát Compute Workers, Hàng đợi Celery, Dung lượng MinIO/PostgreSQL, Backup)
```

---

## 4. Lộ Trình Triển Khai Phân Kỳ (Phased Implementation Roadmap)

1. **Stage 0 — Nền Tảng Hạ Tầng & Kiểm Soát Dữ Liệu (Tuần 1–2):**
   - Thiết lập Monorepo (`apps/web`, `services/api`, `services/compute_worker`), `docker-compose` Private Core (PostgreSQL 16, Redis, MinIO, Caddy).
   - Thiết kế Database Migrations đầu tiên: Identity Split, RBAC/ABAC, PostgreSQL RLS, Bảng `audit_events` + Outbox Worker.
   - *Tiêu chí nghiệm thu:* API có xác thực + phân quyền chạy được; mọi thao tác ghi đều sinh audit log không thể sửa/xóa; kiểm thử cô lập dữ liệu RLS đạt 100%.
2. **Stage 1 — Kho Tri Thức & Research Studio MVP (Tuần 3–6):**
   - CRUD cho Knowledge Base Entries (có version) và Research Objects (Draft -> Immutable Version Snapshot).
   - Tách Claim-centered data model; gắn Citation/Evidence và Thảo luận phản biện theo Claim.
   - *Tiêu chí nghiệm thu:* Người dùng tạo được dự án nghiên cứu hoàn chỉnh, phát hành `v1.0`, chỉnh sửa sang `v1.1` mà không ghi đè `v1.0` hay mất lịch sử đánh giá.
3. **Stage 2 — Reality Constraint Engine Lớp 1–3 & Sandbox Toán Học (Tuần 7–10):**
   - Tích hợp Bảng Biến/Đơn vị bắt buộc + Canonical AST.
   - Dựng **Isolated Compute Worker** chạy `SymPy` và `Pint` trong container khóa mạng (`--network=none`, giới hạn CPU/RAM/Timeout).
   - Triển khai RCE Layer 1 (Semantic/Undefined symbols), Layer 2 (Algebra/Calculus check), Layer 3 (Dimensional SI check).
   - *Tiêu chí nghiệm thu:* Vượt qua bộ **Golden Test Suite** (>100 bài kiểm thử đúng/sai về biến thiếu, lỗi đại số, sai đơn vị `m + s`, và chống Symbolic Bomb timeout).
4. **Stage 3 — Evidence Lab & AI Research Assistant An Toàn (Tuần 11–14):**
   - Tải lên Dataset thô vào MinIO qua Presigned URL; tách Raw Dataset và Derived Dataset kèm Transformation Lineage.
   - Tích hợp AI Assistant qua Tool-calling (chỉ đọc qua API được cấp phép, mọi gợi ý gắn cờ `ai_assisted`, bắt buộc gọi SymPy/Pint khi tính toán).
5. **Stage 4 — RCE Lớp 4 (Physical Constraints) & Mô Phỏng Cô Lập (Tuần 15–20):**
   - Thư viện Ràng buộc Vật lý có phiên bản (Cơ học cổ điển, bảo toàn năng lượng/động lượng) kèm điều kiện áp dụng (`Applicability Conditions`).
   - Mô phỏng số (`NumPy`/`SciPy`) + biểu đồ `Plotly` gắn chặt với phiên bản phương trình và tham số đầu vào.
6. **Stage 5–6 — Independent Replication, Knowledge Graph & Global Scale (Tháng 6+):**
   - Đóng gói Reproducibility Bundle (pin dependencies + seed + input hash).
   - Mở rộng đồ thị tri thức đa tầng, Peer Review ẩn danh/mở chuyên sâu, kết nối bộ dữ liệu quan sát chuẩn quốc tế và `Three.js` 3D mô phỏng khoa học.
