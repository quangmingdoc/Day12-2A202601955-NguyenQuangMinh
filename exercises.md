# Phiếu Phản Ánh — K3 Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
>
> Cách trả lời: thay dòng `> *Câu trả lời của bạn*` bằng câu trả lời.
> `grade.py` đếm số câu đã trả lời (15 điểm cho 10 câu).
>
> Họ và tên: ...Nguyễn Quang Minh... Mã học viên: ..2A202601955..

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `agent_api_key` không có giá trị mặc định nên app chết ngay
khi khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà
việc "chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

> khi tôi deploy service day12-agent lên railway. Trong lúc set biến môi trường,tôi set Agent api key trên service redis thay vì service agent. Service vẫn build và start thành công, domain public day12-agent app đã live
> nếu api agent key có default là "changeme" thì app vẫn khởi động bình thường, không có gì sai. Endpoint /ask vẫn nhận request và trả lời cho ai gửi header x-api-key: changeme. Vì code này nằm trên Github public, bất kì ai đọc file config.py đều thấy ngay default đó. Cho đến khi kiểm tra MONTHLY BUDGET USD hoặc nhận bill thì ngân sách 10 đô / tháng đã bị người lạ dùng hết, hoặc tệ hơn là hết ngân sách do chính tôi dùng.
> Vì agent_api_key KHÔNG có default (bắt buộc): App raise pydantic_core.ValidationError: agent_api_key Field required ngay khi có request đầu tiên chạm vào get_settings() (hoặc ngay lúc startup nếu Settings được khởi tạo ở lifespan). Log lỗi xuất hiện ngay trong Railway logs, /health hoặc /ready trả 500 — healthcheck dashboard báo đỏ. Tôi phát hiện ra trong vài phút, trước khi có traffic thật nào đi qua /ask, và sửa bằng cách set đúng biến — không tốn một cent nào cho request nào chưa xác thực.
> "Chết sớm" biến một lỗ hổng bảo mật âm thầm (key yếu, không ai phát hiện) thành một lỗi hiển nhiên (service không chạy được) — và lỗi hiển nhiên luôn được sửa trước khi lên production thật, còn lỗ hổng âm thầm chỉ được phát hiện sau khi đã có thiệt hại (hóa đơn LLM, dữ liệu bị người lạ dùng).

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/ask` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

> {"event":"ask_completed","user_id":"anonymous","tokens_in":1,"tokens_out":35,"cost_usd":2e-05,"timestamp":"2026-08-10T07:46:05.021517+00:00"}
> Nếu có khoảng 10k dòng log như thế trong 1 ngày mà muốn biết tổng chi phí hoặc user nào gọi nhiều nhất thì với print đã trả lời xong sẽ không thể cho tôi những thông tin mà thôi cần biết. Với JSON có const_usd và user_id sẽ cho tôi biết được ai đang dùng và dùng bao nhiêu
> Nếu muốn làm tính năng cảnh báo tự động khi const_usd của 1 user vượt quá ngưỡng hay tokens_out bất thường cao thì field có thên cost_usd=0.0002 cho phép công cụ giám sát filter theo tên field. Với print chỉ có 1 chuỗi text thì mình sẽ không thể làm được điều tương tự

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t agent:single .
docker build -t agent:multi .
docker images | grep agent
```

| Bản               | Dung lượng |
| ----------------- | ---------- |
| 1 stage (bản đầu) | 1730 MB    |
| Multi-stage       | 270 MB     |

Giải thích: phần dung lượng chênh lệch đó là những gì?

> Chênh lệch ~1.46GB. Bản 1 stage dùng `python:3.11` đầy đủ, kèm compiler (gcc), dev headers và nhiều package hệ điều hành chỉ cần để _build_ các thư viện Python phải compile — những thứ đó không cần lúc chạy app.
> Bản multi-stage cũng dùng những thứ nặng đó ở stage `builder` để `pip install`, nhưng stage đó bị **bỏ đi hoàn toàn** sau khi build xong — chỉ có `/install` (kết quả cài đặt đã compile) được `COPY --from=builder` sang stage runtime chạy trên `python:3.11-slim`. Compiler, cache pip, apt lists ở builder không đi theo vào image cuối, nên dung lượng gần bằng đúng phần app + dependency thật, không mang thêm "hành lý" build-time.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

> Mình thêm một khoảng trắng vào dòng `SERVICE_NAME = "day12-agent"` trong `app/main.py` rồi build lại với `--progress=plain`. Kết quả thật:
>
> - **CACHED**: toàn bộ stage `builder` (`WORKDIR /build`, `COPY requirements.txt .`, `RUN pip install ...`) và bước `COPY --from=builder /install /usr/local` ở stage runtime — vì `requirements.txt` không đổi.
> - **Chạy lại (không cache)**: `COPY app/ app/`, `COPY utils/ utils/`, và cả `RUN useradd --no-create-home appuser` phía sau — dù `useradd` chẳng liên quan gì tới code app. Lý do: Docker cache theo layer _tuần tự_, layer nào bị "bể cache" (input thay đổi) thì mọi layer đứng sau nó trong Dockerfile cũng phải build lại, bất kể nội dung layer đó có thay đổi hay không.
> - Nếu đặt `COPY . .` lên **trước** `RUN pip install`: mọi lần sửa 1 dòng code (dù không đụng tới `requirements.txt`) cũng làm bể cache ngay từ layer COPY, kéo theo `RUN pip install` phải chạy lại toàn bộ — tốn vài chục giây tới vài phút mỗi lần build chỉ vì cài lại dependency không đổi. Đây chính là lý do Dockerfile hiện tại COPY `requirements.txt` riêng và cài trước khi COPY source code.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

> Chuỗi sự kiện nếu container chạy root: (1) attacker tìm được lỗ hổng trong code Python — ví dụ một endpoint deserialize input không kiểm soát, hoặc một dependency có RCE (remote code execution). (2) Lỗ hổng đó cho attacker chạy lệnh tùy ý _trong tiến trình app_ — tiến trình app đang chạy với UID 0 (root) vì container không có `USER`. (3) Attacker giờ có quyền root **trong container** — ghi được vào bất kỳ file nào, cài binary, đọc mọi biến môi trường (kể cả secret). (4) Nếu container có lỗ hổng escape (kernel bug, hoặc mount volume/socket Docker không cẩn thận), quyền root trong container leo thang thành quyền root trên **máy host** — attacker giờ kiểm soát toàn bộ máy chủ, không chỉ riêng service này.
> Lệnh `USER appuser` cắt đứt chuỗi ở bước (2)→(3): dù attacker chạy được lệnh tùy ý trong tiến trình app, tiến trình đó chỉ có quyền của user thường (`appuser`), không phải root. Attacker có thể phá được app, nhưng không tự động có toàn quyền trong container, và càng khó leo thang ra host hơn nhiều — mất đi bước bẩy quan trọng nhất trong chuỗi tấn công.

---

### Câu 6 — Cửa sổ trượt (CP3)

Rate limit của bạn dùng sliding window 60 giây. Nếu thay bằng cách đếm theo
phút đồng hồ (reset lúc giây 00), một người dùng có thể gửi tối đa bao nhiêu
request trong 2 giây liên tiếp khi hạn mức là 10/phút? Giải thích cách đạt được
con số đó.

> Tối đa **20 request trong 2 giây**. Cách đạt được: gửi đúng 10 request vào lúc `10:00:59` (giây cuối của phút đó, vẫn tính vào bucket phút `10:00`) và gửi tiếp 10 request vào lúc `10:01:01` (2 giây sau, nhưng đã rơi sang bucket phút `10:01` vì bộ đếm reset lúc giây 00). Với cách đếm theo phút đồng hồ, cả hai đợt đều "hợp lệ" theo luật riêng của từng bucket (10/phút), nhưng gộp lại là 20 request trong một khoảng 2 giây thực tế — gấp đôi hạn mức dự kiến. Sliding window (đếm 60 giây gần nhất tính từ _thời điểm hiện tại_, không neo theo mốc đồng hồ cố định) không có lỗ hổng này vì cửa sổ luôn trượt theo request mới nhất, không có "đường biên" cố định để lợi dụng.

---

### Câu 7 — Rate limit và cost guard (CP3)

Hai cơ chế này khác nhau ở điểm nào? Cho một tình huống mà rate limit cho qua
nhưng cost guard phải chặn, và một tình huống ngược lại.

> Khác nhau ở **đơn vị đo**: `RateLimiter` giới hạn _số lượng_ request trong 60 giây (đếm bằng Redis ZSET, không quan tâm request đó tốn bao nhiêu tiền). `CostGuard` giới hạn _số tiền_ đã chi trong tháng (đọc/cộng dồn `cost_usd` theo `user_id` + tháng hiện tại), không quan tâm request đó là request thứ mấy.
>
> - **Rate limit cho qua, cost guard phải chặn**: user gửi đúng 5 request/phút (dưới hạn mức 10/phút) nhưng mỗi request hỏi một câu hỏi dài, tốn 50,000 token — vài request như vậy đã vượt `MONTHLY_BUDGET_USD`. Rate limit thấy `hit_count < limit` nên cho qua, nhưng `CostGuard.check()` thấy `spent + estimated_cost > budget` nên raise 402.
> - **Ngược lại**: user gửi câu hỏi rất ngắn, chi phí mỗi request gần như 0 — cả tháng chưa chạm ngân sách $10. Nhưng user này gửi 50 request trong 1 phút (spam). `CostGuard.check()` vẫn cho qua vì tổng tiền chưa vượt, nhưng `RateLimiter.check()` thấy `hit_count >= limit` (10) nên raise 429 ngay từ request thứ 11.

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với cụm
3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự kiện.

> Thứ tự sự kiện nếu gộp `/health` = `/ready` và cả hai đều kiểm tra Redis:
>
> 1. Redis mất kết nối. Cả 3 container gọi `store.ping()` bên trong endpoint gộp đều trả `False`.
> 2. Endpoint gộp trả 503 cho **mọi** probe — cả liveness lẫn readiness — vì giờ chỉ còn một endpoint duy nhất mang cả hai vai.
> 3. Orchestrator (Docker/Kubernetes/Railway) đọc probe liveness thấy 503 liên tục, hiểu nhầm là "process đã chết/kẹt cứng" (đúng ra process vẫn sống, chỉ là _dependency_ của nó chết) → sau vài lần fail liên tiếp, orchestrator **restart cả 3 container** cùng lúc.
> 4. Container restart xong, khởi động lại, nhưng Redis vẫn chưa hồi phục (mới 30 giây, có thể chưa xong) → probe gộp lại trả 503 → orchestrator lại restart tiếp — vòng lặp "crash loop" trong khi lẽ ra service vẫn có thể tiếp tục phục vụ các request không cần Redis (ví dụ health check đơn giản).
> 5. Nếu tách riêng: `/health` (không đụng Redis) vẫn trả 200 suốt 30 giây đó → orchestrator không restart container. `/ready` trả 503 → load balancer/orchestrator chỉ **ngừng route traffic mới** vào container đó, không giết process. Khi Redis sống lại, `/ready` tự trả 200, traffic tiếp tục vào bình thường — không có container nào bị restart, không có crash loop.

---

### Câu 9 — Stateless (CP4)

Chạy `docker compose up --scale agent=3` rồi gọi `/ask` nhiều lần với cùng một
`X-User-Id`. Quan sát `history_length` trong response. Nếu lịch sử được lưu
trong một dict Python thay vì Redis, bạn sẽ thấy con số đó thay đổi thế nào?

> Mình chạy `docker compose up -d --build --scale agent=3` rồi gọi `/ask` 5 lần qua nginx (port 8000) với cùng `X-User-Id: sv-test-scale`. Kết quả `history_length` thật thu được: **0 → 2 → 4 → 6 → 8** — tăng đều đặn dù mỗi request rất có thể được nginx route tới một trong 3 container agent khác nhau. Điều này đúng như thiết kế: lịch sử được lưu trong Redis (một service dùng chung cho cả 3 container), nên container nào xử lý request cũng đọc/ghi vào đúng một nguồn dữ liệu.
> Nếu lịch sử lưu trong dict Python (biến toàn cục trong tiến trình): mỗi container có dict riêng, không chia sẻ gì với nhau. Với cùng 5 request rải ngẫu nhiên qua 3 container, `history_length` sẽ **không tăng đều** — có thể thấy 0, 0, 2, 0, 2... tùy request đó rơi vào container nào (mỗi container chỉ "nhớ" các lượt hỏi mà chính nó từng xử lý). Đây chính là lý do CP4 yêu cầu state phải nằm ngoài process (Redis), không phải trong RAM của từng container — nếu không, scale ngang sẽ làm vỡ tính đúng đắn của tính năng "nhớ hội thoại".

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

> **Lỗi:** service `day12-agent` trên Railway ở trạng thái Failed ngay sau deploy. Xem log runtime thấy:
>
> ```
> Usage: uvicorn [OPTIONS] APP
> Error: Invalid value for '--port': '$PORT' is not a valid integer.
> ```
>
> **Tìm nguyên nhân:** `Dockerfile` dùng đúng shell-form (`CMD ["sh", "-c", "exec uvicorn ... --port ${PORT:-8000}"]`) nên biến `$PORT` được shell expand đúng. Nhưng `railway.toml` có thêm một dòng `startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"` — Railway ưu tiên chạy `startCommand` này thay vì `CMD` của Dockerfile, và chạy nó **không qua shell** nên `$PORT` không được expand, uvicorn nhận đúng chuỗi ký tự `"$PORT"` làm giá trị port và crash.
> **Sửa:** xóa dòng `startCommand` khỏi `railway.toml`, để Railway rơi về dùng `CMD` trong Dockerfile (đã viết đúng). Commit, push, service deploy lại thành công, `/health` trả 200.
