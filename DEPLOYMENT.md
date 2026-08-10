# Thông Tin Deploy — Checkpoint 5

> Điền file này sau khi deploy xong. `pytest tests/test_cp5.py` đọc file này
> để tìm địa chỉ service của bạn và gọi thử.
>
> **Chỉ ghi TÊN biến môi trường, tuyệt đối không dán giá trị API key vào đây.**
> Repo này công khai — dán khóa vào là mất khóa.

## Thông Tin Học Viên

| Mục         | Nội dung                                                          |
| ----------- | ----------------------------------------------------------------- |
| Họ và tên   | Nguyễn Quang Minh                                                 |
| Mã học viên | 2A202601955                                                       |
| Repo        | https://github.com/quangmingdoc/Day12-2A202601955-NguyenQuangMinh |

## Service

| Mục         | Nội dung                                           |
| ----------- | -------------------------------------------------- |
| Public URL  | https://day12-agent-production-1663.up.railway.app |
| Platform    | Railway                                            |
| Ngày deploy | 10/08/2026                                         |

## Biến Môi Trường Đã Set Trên Cloud

Ghi tên biến và **nguồn giá trị**, không ghi giá trị:

| Biến                    | Đã set | Ghi chú                                           |
| ----------------------- | ------ | ------------------------------------------------- |
| `PORT`                  | ✅     | platform tự gán                                   |
| `AGENT_API_KEY`         | ✅     | đặt trong dashboard, không nằm trong repo         |
| `REDIS_URL`             | ✅     | Redis add-on của Railway (service `day12-redis`, private network) |
| `RATE_LIMIT_PER_MINUTE` | ✅     | 10                                                |
| `MONTHLY_BUDGET_USD`    | ✅     | 10.0                                              |
| `LOG_LEVEL`             | ✅     | INFO                                              |

## Lệnh Kiểm Tra

Thay `<URL>` bằng Public URL ở trên:

```bash
# 1. Liveness — mong đợi 200 {"status":"ok"}
curl -i <URL>/health

# 2. Readiness — mong đợi 200 {"status":"ready"} (đã nối được Redis)
curl -i <URL>/ready

# 3. Không có API key — mong đợi 401
curl -i -X POST <URL>/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'

# 4. Có API key — mong đợi 200 kèm câu trả lời
curl -i -X POST <URL>/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AGENT_API_KEY" \
  -H "X-User-Id: sv-test" \
  -d '{"question":"Deploy là gì?"}'

# 5. Rate limit — gọi 15 lần, những lần cuối phải trả 429
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code} " -X POST <URL>/ask \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $AGENT_API_KEY" \
    -H "X-User-Id: sv-test" \
    -d '{"question":"test"}'
done; echo
```

## Kết Quả Chạy Thật

Dán output của các lệnh trên vào đây:

```
# 1. Liveness
$ curl -i https://day12-agent-production-1663.up.railway.app/health
HTTP/1.1 200 OK
Content-Type: application/json

{"status":"ok","service":"day12-agent","version":"1.0.0"}

# 2. Readiness
$ curl -i https://day12-agent-production-1663.up.railway.app/ready
HTTP/1.1 200 OK
Content-Type: application/json

{"status":"ready","redis":true}

# 3. Không có API key
$ curl -i -X POST https://day12-agent-production-1663.up.railway.app/ask \
    -H "Content-Type: application/json" \
    -d '{"question":"Hello"}'
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{"detail":"invalid or missing API key"}

# 4. Có API key
$ curl -i -X POST https://day12-agent-production-1663.up.railway.app/ask \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $AGENT_API_KEY" \
    -H "X-User-Id: sv-test" \
    -d '{"question":"Deploy là gì?"}'
HTTP/1.1 200 OK
Content-Type: application/json

{"answer":"Ngắn gọn: Deploy la gi phụ thuộc vào ba yếu tố — cấu hình qua biến môi
trường, health check để orchestrator biết trạng thái, và giới hạn tài nguyên.",
"user_id":"sv-test","history_length":0,"cost_usd":2.265e-05,"tokens":{"in":3,"out":37}}

# 5. Rate limit — 15 request liên tiếp (giới hạn RATE_LIMIT_PER_MINUTE=10)
$ for i in $(seq 1 15); do
    curl -s -o /dev/null -w "%{http_code} " -X POST .../ask \
      -H "X-API-Key: $AGENT_API_KEY" -H "X-User-Id: sv-test" \
      -d '{"question":"test"}'
  done
200 200 200 200 200 200 200 200 200 429 429 429 429 429 429
```

## Ảnh Chụp Màn Hình

Ảnh trong thư mục `screenshots/`:

- `screenshots/dashboard.png` — trang quản lý service `day12-agent` trên Railway (deployment ACTIVE, "Deployment successful")
- `screenshots/deployment_successful.png` — chi tiết deployment thành công
- `screenshots/log_output.png` — log runtime khi gọi các endpoint /health, /ready, /ask
