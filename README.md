# ACS Backend – AMR Fleet Control & Management System

> **Hệ thống điều khiển & quản lý đội robot vận chuyển tự hành (AMR/AGV) theo chuẩn quốc tế VDA 5050 (Version 2.1.0)**  
> **Khu vực vận hành:** Phân xưởng sản xuất **CNC Prod 2G**  
> **Tài liệu đặc tả kiến trúc chi tiết:** [docs/ACS_BACKEND_SRS.md](file:///d:/acs_backend/docs/ACS_BACKEND_SRS.md)

---

## 1. Giới Thiệu Tổng Quan

**ACS Backend (AGV/AMR Control System)** là giải pháp điều hành trung tâm cho đội robot vận chuyển công nghiệp trong phân xưởng sản xuất CNC Prod 2G. Hệ thống kết nối thời gian thực với hàng trăm robot AMR qua hạ tầng MQTT (Broker EMQX), tích hợp tự động với hệ thống quản lý sản xuất **Aligo MES**, giải quyết bài toán giao thông, lập lịch phân bổ xe và tránh tắc nghẽn thông minh.

### Tính năng then chốt:
* **Chuẩn hóa VDA 5050 v2.1.0:** Giao tiếp toàn diện qua các thông điệp `order`, `state`, `instantActions`, `connection` với định dạng JSON chuẩn quốc tế.
* **Lập lịch tối ưu toàn cục (Hungarian Algorithm):** Tối thiểu hóa quãng đường chạy không tải (Deadhead Distance) qua ma trận chi phí giải bởi `scipy.optimize.linear_sum_assignment`.
* **Định tuyến Dijkstra có bộ nhớ đệm (Cache Graph TTL 60s):** Tìm lộ trình di chuyển nhanh chóng, cập nhật liên tục theo trọng số thực tế.
* **Chống va chạm & Khóa chết (State/Resource Reservation):** Cơ chế đặt chỗ trước tài nguyên Node và Edge theo cửa sổ thời gian (time-window reservation).
* **Tích hợp Aligo MES:** Tự động bắt cặp nhu cầu cấp phôi (Supply Request) với robot gần nhất theo tầng ưu tiên và hạn chót SLA.
* **Giao diện Web Điều hành & OpenAPI:** Bảng điều khiển trực quan với bản đồ Leaflet.js thời gian thực và tài liệu API Swagger tự động.

---

## 2. Kiến Trúc Ngăn Xếp Công Nghệ (Technology Stack)

* **Ngôn ngữ & Khung phát triển:** Python 3.10+, Django 6.x, Django REST Framework.
* **Tài liệu hóa API:** `drf-spectacular` (OpenAPI 3.0 / Swagger UI / Redoc).
* **Truyền thông IoT/MQTT:** `paho-mqtt` kết nối Broker **EMQX**.
* **Thuật toán & Khoa học Dữ liệu:** `scipy` (Hungarian Assignment), `numpy`, cấu trúc hàng đợi `heapq`.
* **Tuần tự hóa VDA 5050:** `dataclasses`, `ujson`, `cbor2`, `msgpack`.
* **Cơ sở dữ liệu:** PostgreSQL 14+ (hỗ trợ sẵn sàng fallback sang SQLite3 cho Development).
* **Giao diện Web:** HTML5, CSS3, Bootstrap 5, Leaflet.js (bản đồ nhà máy).
* **Kiểm thử tự động:** `pytest`, `pytest-django`.

---

## 3. Cấu Trúc Thư Mục Dự Án

```text
acs_backend/
├── acs/                             # Thư mục mã nguồn chính (Django project & apps)
│   ├── acs/                         # Module lõi: settings, urls, wsgi, asgi
│   │   ├── models.py                # Order, OrderMaster, SubOrder, SupplyRequest, ActionDispatch, Log
│   │   ├── serializers.py           # Serializers cho các REST API
│   │   ├── views.py                 # API find_path_vda, dispatch_amr, system_logs_file
│   │   └── vda5050/                 # Đặc tả giao thức VDA 5050 v2.1.0
│   │       ├── order.py             # Dataclass Order, Node, Edge, NodePosition
│   │       ├── action.py            # Dataclass Action, ActionState, BlockingType
│   │       ├── state.py             # Dataclass OrderState, BatteryState, SafetyState
│   │       ├── connection.py        # Dataclass ConnectionState
│   │       └── topic.py             # Helper sinh topic MQTT và Header VDA 5050
│   ├── amr/                         # App quản lý đội xe AMR
│   │   ├── models.py                # AmrVehicle, TopicControl, AmrStateLog
│   │   ├── serializers.py & views.py
│   │   └── urls.py
│   ├── buffer/                      # App quản lý bục giao nhận (Buffer) & Lịch trình
│   │   ├── models.py                # Buffer, Schedule, ScheduleStop, StopAction
│   │   ├── serializers.py & views.py
│   │   └── urls.py
│   ├── map/                         # App quản lý bản đồ nhà máy & topo giao thông
│   │   ├── models.py                # MapBase, Layers, ZoneSet, TrafficZone, Node, Edge, Action
│   │   ├── serializers.py & views.py
│   │   └── urls.py
│   ├── traffic/                     # Phân hệ giải thuật điều phối & giao thông
│   │   ├── models.py                # In-memory Dataclass: FleetTask, FleetAssignment, ReservationStatus
│   │   ├── fleet_scheduler.py       # Thuật toán Hungarian + Dijkstra Cost Matrix
│   │   ├── state_reservation_manager.py # Quản trị đặt chỗ trước tài nguyên Node/Edge
│   │   ├── state_traffic_controller.py  # Điều khiển lưu lượng hành trình robot
│   │   └── zone_manager.py          # Quản trị mật độ xe và tốc độ trong Traffic Zone
│   ├── workers/                     # Hệ thống tiến trình nền (Background Workers)
│   │   ├── worker_schema_class.py   # Lớp cơ sở WorkerThread & MQTTInterfaceWorker
│   │   ├── acs_order_send.py        # Worker gửi lệnh VDA 5050 qua MQTT (Multi-thread, ACK, Timeout)
│   │   ├── acs_order_master.py      # Bộ xử lý hàng đợi FIFO đơn hàng theo created_at
│   │   ├── acs_supply_request_pairing.py # Ghép cặp yêu cầu cấp phôi theo tầng ưu tiên
│   │   ├── acs_aligo_sync.py        # Worker đồng bộ định kỳ 3-5s với Aligo MES
│   │   ├── acs_telemetry_sync.py    # Lắng nghe trạng thái xe qua MQTT và ghi DB/Audit
│   │   └── utilities/
│   │       └── graph_distance.py    # Thuật toán Dijkstra độc lập với cache graph TTL 60s
│   ├── integrations/
│   │   └── aligo_client.py          # REST Client gọi API bên ngoài Aligo MES
│   ├── logs/                        # Nhật ký vận hành hệ thống
│   └── seed_cnc_prod_2g.py          # Script nạp dữ liệu mẫu ban đầu cho CNC Prod 2G
├── docs/
│   └── ACS_BACKEND_SRS.md           # Tài liệu đặc tả yêu cầu hệ thống đầy đủ
├── templates/                       # Giao diện Web Console (Bản đồ Leaflet, điều khiển xe)
├── static/                          # Tài nguyên CSS, JS tĩnh
├── tests/                           # Bộ kiểm thử hệ thống tự động
├── requirements.txt                 # Danh mục thư viện Python phụ thuộc
├── manage.py                        # Django Management Tool
├── acs_launch.py                    # Trình điều phối khởi động hợp nhất hệ thống
├── runacs.bat                       # Script khởi chạy nhanh trên Windows
└── acs_start.sh                     # Script khởi chạy nhanh trên Linux
```

---

## 4. Hướng Dẫn Khởi Chạy & Vận Hành

### Cách 1: Khởi động tự động bằng Script (Khuyến nghị)
* **Trên Windows:**
  Nhấp đúp chuột hoặc chạy từ Command Prompt / PowerShell:
  ```cmd
  runacs.bat
  ```
* **Trên Linux:**
  ```bash
  chmod +x acs_start.sh
  ./acs_start.sh
  ```

### Cách 2: Khởi động thủ công bằng Python
1. **Kích hoạt môi trường ảo (Virtualenv):**
   ```cmd
   .\.venv\Scripts\activate
   ```
2. **Áp dụng Migration và Nạp dữ liệu mẫu:**
   ```bash
   python manage.py migrate
   python acs/seed_cnc_prod_2g.py
   ```
3. **Khởi động toàn bộ Web Server và các Background Workers:**
   ```bash
   python acs_launch.py
   ```

---

## 5. Truy Cập Giao Diện & API

Sau khi hệ thống khởi động thành công:
* **Web Dashboard Điều hành & Bản đồ:** [http://localhost:8000/](http://localhost:8000/)
* **Tài liệu Swagger API (Interactive):** [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
* **Tài liệu Redoc API:** [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)
* **Trang Quản trị Django Admin:** [http://localhost:8000/admin/](http://localhost:8000/admin/)

---

## 6. Chạy Bộ Kiểm Thử (Tests)

Kiểm tra độ chính xác của các thuật toán Hungarian, Dijkstra và Đặt chỗ tài nguyên:
```bash
.\.venv\Scripts\python -m pytest tests/test_acs_system.py -v -s
```
