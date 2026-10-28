# TÀI LIỆU TỔNG QUAN HỆ THỐNG (High-Level SRS)
**Hệ thống:** ACS Backend – Hệ thống điều khiển & quản lý AMR (Automated Mobile Robot)  
**Khu vực vận hành:** CNC Prod 2G | **Tiêu chuẩn giao thức:** VDA 5050 v2.1.0  
**Ngày lập tài liệu gốc:** 16/10/2026 | **Phiên bản hệ thống:** 2.1.0  

---

## 1. TỔNG QUAN HỆ THỐNG (System Overview)

Hệ thống **ACS Backend (AGV/AMR Control System Backend)** là hạt nhân trung tâm chịu trách nhiệm điều hành, phân bổ nhiệm vụ và giám sát đội robot vận chuyển tự hành (AMR/AGV) hoạt động trong phân xưởng sản xuất **CNC Prod 2G**. Toàn bộ quá trình giao tiếp giữa hệ thống trung tâm và đội robot tuân thủ nghiêm ngặt tiêu chuẩn công nghiệp quốc tế **VDA 5050 (Version 2.1.0)** thông qua giao thức truyền thông nhẹ MQTT.

### Trách nhiệm cốt lõi của hệ thống:
1. **Tiếp nhận yêu cầu vận chuyển:** Thu nhận các đơn hàng vận chuyển (orders/suborders) từ hệ thống quản lý sản xuất bên ngoài (Aligo MES/ERP) cũng như từ thao tác thủ công của vận hành viên.
2. **Tìm lộ trình tối ưu:** Tính toán đường đi ngắn nhất và an toàn nhất trên bản đồ nhà máy (`find_path_vda`) sử dụng giải thuật Dijkstra kết hợp trọng số thực tế và lưu trữ đồ thị thông minh (cache graph TTL 60s).
3. **Điều phối giao thông & Chống tắc nghẽn (Traffic Control):** Sử dụng cơ chế đặt chỗ tài nguyên theo thời gian (State/Resource Reservation) trên các node và edge, ngăn ngừa nguy cơ xung đột, va chạm hoặc khóa chết (deadlock).
4. **Lập lịch tối ưu toàn cục (Fleet Scheduling):** Áp dụng thuật toán Hungarian (Kuhn-Munkres qua `scipy.optimize.linear_sum_assignment`) để gán tối ưu bài toán cặp đôi giữa Robot và Đơn hàng nhằm giảm thiểu tối đa quãng đường chạy không tải (deadhead distance).
5. **Giám sát thời gian thực:** Tiếp nhận và xử lý dòng dữ liệu đo xa (telemetry), trạng thái pin, cảm biến an toàn, vị trí tọa độ của từng robot qua broker MQTT chuẩn công nghiệp (EMQX).
6. **Tích hợp MES:** Đồng bộ dữ liệu liên tục 2 chiều với hệ thống dây chuyền Aligo (MES) theo chu kỳ 3–5 giây, tự động nhận diện nhu cầu cấp phôi/vật tư (Supply Request) và điều robot thực hiện.

### Đối tượng sử dụng chính:
* **Vận hành viên / Operator dây chuyền:** Thao tác trên giao diện điều khiển (Qt6 C++ Desktop App hoặc Web Console) để ra lệnh gọi robot, tạo đơn vận chuyển phôi/thành phẩm giữa các công đoạn và theo dõi trực quan vị trí robot trên bản đồ.
* **Quản trị viên hệ thống (System Administrator):** Sử dụng trang quản trị chuyên sâu (Django Admin), xem xét sơ đồ node/edge/zone, cấu hình trạm đệm (buffer), giám sát worker nền và tra cứu log hệ thống.
* **Hệ thống bên ngoài (Aligo MES/ERP):** Trao đổi thông tin tự động hai chiều qua hệ thống REST API chuẩn hóa và các worker đồng bộ chuyên dụng.

---

## 2. KIẾN TRÚC CÔNG NGHỆ (Technology Stack)

| Thành phần | Công nghệ / Thư viện | Vai trò trong hệ thống |
| :--- | :--- | :--- |
| **Backend Core** | Python 3.10+, Django 6.x | Khung phát triển ứng dụng web & ORM quản lý dữ liệu nghiệp vụ |
| **REST API** | Django REST Framework (DRF), drf-spectacular | Cung cấp chuẩn REST API, tài liệu hóa tự động bằng OpenAPI 3.0 / Swagger / Redoc |
| **Real-time Web** | Django Channels, ASGI (Daphne / Uvicorn) | Kênh giao tiếp WebSocket thời gian thực đẩy trạng thái xe lên giao diện người dùng |
| **Frontend Clients** | • Qt6 + C++ (Desktop App chuyên dụng)<br>• Web: Django Templates, Bootstrap 5, Leaflet.js<br>• WebAssembly (`acs_sevt.wasm`) | Ứng dụng điều hành sản xuất, hiển thị bản đồ nhà xưởng thời gian thực và mô phỏng giám sát số hóa (SEVT simulator) |
| **Cơ sở dữ liệu** | PostgreSQL (psycopg2) | Lưu trữ bền vững ~30 bảng nghiệp vụ chia theo các tiền tố: `acs_`, `amr_`, `buffer_`, `map_`, `auth_` |
| **Giao tiếp IoT/AMR** | MQTT (paho-mqtt), Broker **EMQX** | Hạ tầng kết nối hàng trăm robot đồng thời với độ trễ thấp, hỗ trợ QoS và retained topic |
| **Thư viện Toán học** | SciPy (`scipy.optimize`), NumPy | Thực thi thuật toán Hungarian (Linear Sum Assignment), tối ưu chi phí phân phối đội xe |
| **Định dạng VDA 5050** | `ujson`, `cbor2`, `msgpack`, `dataclasses` | Tuần tự hóa / giải tuần tự nhanh thông điệp VDA 5050 giữa ACS và robot |
| **Tích hợp bên ngoài** | Requests, HTTP Client, Job Cache | Kết nối Aligo External API (REST) đồng bộ trạng thái line và lệnh cung ứng vật tư |
| **DevOps & Vận hành** | Linux (`acs_start.sh`), Windows (`runacs.bat`), `acs_launch.py`, Pytest | Khởi chạy độc lập các worker tiến trình nền, tự phục hồi, kiểm thử tự động |

---

## 3. CẤU TRÚC THƯ MỤC HỆ THỐNG (High-Level Folder Structure)

```text
acs_backend/
├── acs/
│   ├── acs/                         # Module lõi dự án Django: settings, urls, asgi, wsgi
│   │   ├── models.py                # Order, OrderMaster, SubOrder, SupplyRequest, Log, ActionDispatch
│   │   ├── serializers.py           # Bộ tuần tự hóa dữ liệu cho API đơn hàng & hệ thống
│   │   ├── views.py                 # API gọi AMR, tìm đường tối ưu (find_path_vda), tra cứu log
│   │   └── vda5050/                 # Gói đặc tả giao thức VDA 5050
│   │       ├── order.py             # Dataclass & schemas cho message Order VDA 5050
│   │       ├── action.py            # Dataclass Action, ActionParameter, BlockingType
│   │       ├── state.py             # Dataclass OrderState, BatteryState, SafetyState
│   │       ├── connection.py        # Dataclass ConnectionState
│   │       └── topic.py             # Bộ sinh Header và định dạng Topic MQTT chuẩn VDA 5050
│   ├── amr/                         # Phân hệ quản lý đội xe AMR
│   │   ├── models.py                # AmrVehicle, TopicControl, AmrStateLog
│   │   ├── serializers.py           # Serializers quản lý xe & topic MQTT
│   │   ├── views.py                 # API quản lý phương tiện, tra cứu telemetry
│   │   └── urls.py
│   ├── buffer/                      # Phân hệ trạm đệm (Buffer) & Lịch trình sản xuất
│   │   ├── models.py                # Buffer, Schedule, ScheduleStop, ActionOption, StopAction
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── map/                         # Phân hệ bản đồ nhà xưởng
│   │   ├── models.py                # MapBase, WorldMapLayer, GridMapLayer, ZoneSet, TrafficZone, Zone, Node, Edge, Action, ActionOnNode, ActionOnEdge
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── traffic/                     # Phân hệ điều phối giao thông & Lập lịch đội xe
│   │   ├── models.py                # In-memory Dataclasses: FleetTask, FleetAssignment, FleetSchedulerResult, RobotPriority, ReservationStatus
│   │   ├── fleet_scheduler.py       # Thuật toán Hungarian (scipy linear_sum_assignment) + Dijkstra cost matrix
│   │   ├── state_reservation_manager.py # Bộ quản trị đặt trước tài nguyên Node/Edge chống xung đột & deadlock
│   │   ├── state_traffic_controller.py  # Bộ điều khiển giao thông thời gian thực
│   │   └── zone_manager.py          # Quản trị vùng giao thông (Traffic Zone, giới hạn vận tốc/số lượng xe)
│   ├── workers/                     # Hệ thống tiến trình nền (Background Workers độc lập)
│   │   ├── worker_schema_class.py   # Lớp cơ sở WorkerThread và MQTTInterfaceWorker
│   │   ├── acs_order_send.py        # Dispatcher & MQTT Publisher gửi lệnh VDA 5050 đến AMR (xử lý ACK, Retry, Timeout)
│   │   ├── acs_order_master.py      # Bộ xử lý hàng đợi FIFO cho các đơn hàng PENDING theo created_at
│   │   ├── acs_supply_request_pairing.py # Ghép cặp nhu cầu cấp phôi (Supply Request) theo tầng ưu tiên & khoảng cách Dijkstra
│   │   ├── acs_aligo_sync.py        # Worker đồng bộ định kỳ 3-5s với Aligo MES API (trạng thái robot & line)
│   │   ├── acs_telemetry_sync.py    # Worker lắng nghe MQTT, cập nhật AmrVehicle và AmrStateLog
│   │   └── utilities/
│   │       └── graph_distance.py    # Module tính khoảng cách đồ thị Dijkstra độc lập (heapq + cache TTL 60s)
│   ├── integrations/                # Tích hợp hệ thống bên ngoài
│   │   └── aligo_client.py          # REST Client giao tiếp Aligo MES kèm cơ chế Retry & Cache
│   ├── logs/                        # Thư mục lưu trữ log vận hành xoay vòng theo ngày/worker
│   └── sql/                         # Các script SQL khởi tạo, schema EMQX Auth, dữ liệu mẫu CNC Prod 2G
├── templates/                       # Giao diện Web Console (Bản đồ Leaflet, điều khiển xe)
├── static/                          # CSS Bootstrap 5, Leaflet, JavaScript điều hành
├── media/maps/                      # File ảnh bản đồ tải lên (Floorplan grid/world)
├── wasm/                            # Module WebAssembly mô phỏng/giám sát (acs_sevt.wasm)
├── docs/                            # Tài liệu hệ thống chi tiết (SRS, API specs, VDA5050 guide)
├── requirements.txt                 # Danh mục thư viện phụ thuộc Python
├── manage.py                        # Django management CLI
├── acs_launch.py                    # Script hợp nhất quản lý khởi chạy toàn bộ server & workers
├── runacs.bat                       # Script khởi động trên Windows OS
├── acs_start.sh                     # Script khởi động trên Linux OS
└── README.md                        # Hướng dẫn cài đặt, cấu hình và vận hành
```

---

## 4. CÁC TÍNH NĂNG VÀ PHÂN HỆ LỚN (Core Modules & Features)

### 4.1. Quản lý Đơn vận chuyển (Order Management - Module `acs`)
* **Xử lý chu kỳ sống đơn hàng (Order Lifecycle):** Nhận đơn, thẩm định tính hợp lệ, tách thành các `SubOrder` phân đoạn phù hợp với tiêu chuẩn VDA 5050.
* **Đa dạng hình thức điều phối:**
  - Lệnh di chuyển tới một điểm chỉ định (`Target Node`).
  - Lệnh vận chuyển giữa 2 điểm (Điểm lấy hàng A -> Điểm trả hàng B).
  - Lệnh vận chuyển liên dây chuyền (Inter-line transfer giữa các công đoạn CNC).
  - Lệnh tuần hành theo danh sách node chỉ định với các `actions` đi kèm (nâng hạ hàng, xoay xe, sạc pin).
* **Định tuyến tối ưu:** Gọi dịch vụ `find_path_vda` dựa trên bản đồ đang kích hoạt, tính toán chuỗi node và edge liên tục, gán tham số tốc độ, quỹ đạo cong bezier/spline nếu có.

### 4.2. Quản lý Đội Robot AMR (AMR Fleet Management - Module `amr`)
* **Định danh phương tiện:** Quản lý serial number, model, version VDA 5050, địa chỉ IP/Port và nhà sản xuất.
* **Theo dõi trạng thái thời gian thực:**
  - Tọa độ `(x, y, theta)` và độ tin cậy định vị.
  - Vận tốc tức thời `(vx, vy, omega)`.
  - Mức pin `%`, điện áp, dòng sạc, nhiệt độ pin.
  - Tải trọng thực tế (`loads`), trạng thái tải hàng.
  - Trạng thái an toàn: E-Stop, cảm biến va chạm quang, LiDAR.
  - Danh sách lỗi cảnh báo (`errors`) và thông tin vận hành (`information`).
* **Topic MQTT tương tác động:** Mỗi AMR được ánh xạ với bộ topic VDA 5050 riêng biệt:
  - Lệnh đơn hàng: `uagv/v2/{manufacturer}/{serialNumber}/order`
  - Lệnh tác vụ tức thời: `uagv/v2/{manufacturer}/{serialNumber}/instantActions`
  - Trạng thái trả lời: `uagv/v2/{manufacturer}/{serialNumber}/state`
  - Kết nối (Last Will): `uagv/v2/{manufacturer}/{serialNumber}/connection`

### 4.3. Điều phối Giao thông & Lập lịch (Traffic Control & Scheduling - Module `traffic`)
* **Fleet Scheduler (Bộ lập lịch đội xe):** Áp dụng mô hình ma trận chi phí tối ưu toàn cục. Sử dụng khoảng cách đồ thị Dijkstra từ vị trí hiện tại của các xe rảnh (`is_idle=True`) tới điểm đón hàng để thiết lập cost matrix, giải bằng giải thuật Hungarian giúp cực tiểu hóa tổng quãng đường chạy không tải.
* **State / Resource Reservation (Đặt chỗ tài nguyên động):**
  - Mỗi khi robot di chuyển qua một đoạn đường, hệ thống cấp quyền chiếm dụng (reservation) trước trên các Node và Edge kế tiếp trong một cửa sổ thời gian (time window).
  - Ngăn ngừa tình trạng 2 robot tiến vào giao lộ cùng lúc hoặc đối đầu nhau trên các cung đường đơn tuyến (deadlock resolution).
* **Quản trị vùng giao thông (Zone Manager):** Phân chia bản đồ xưởng thành các khu vực `TrafficZone` với các chính sách riêng biệt: giới hạn số lượng xe tối đa trong vùng (`max_occupancy`), mức độ ưu tiên (`priority`), và tốc độ tối đa cho phép (`max_speed`).

### 4.4. Quản lý Bản đồ Nhà xưởng (Map Management - Module `map`)
* **Mô hình hóa hình học & logic:**
  - `Node`: Điểm định vị tọa độ thực trên mặt sàn, hướng đỗ xe `theta`, sai số cho phép, loại điểm (Pick, Drop, Charge, Park, Transit).
  - `Edge`: Cung kết nối giữa 2 node, hướng đi (một chiều/hai chiều), chiều dài thực, tốc độ tối đa, khả năng xoay xe khi di chuyển.
  - `Action`: Các hành động đặc thù tại điểm dừng hoặc trên đường đi (nâng pallet, hạ pallet, bật còi, chụp camera quét mã QR, sạc tự động) kèm mức độ khóa chuyển động (`NONE`, `SOFT`, `HARD`).
* **Hỗ trợ đa lớp bản đồ (Multi-layer Map):**
  - `WorldMapLayer`: Bản đồ tỷ lệ thực (hệ tọa độ thế giới, resolution, origin x/y).
  - `GridMapLayer`: Bản đồ lưới phục vụ hiển thị trực quan và cấu hình ô giao thông.

### 4.5. Quản lý Trạm đệm & Lịch trình (Buffer & Schedule - Module `buffer`)
* Quản lý các bục giao nhận vật tư (Buffer) đầu vào/đầu ra của máy CNC.
* Cập nhật tự động trạng thái trạm đệm (Trống, Đầy, Đang chờ xe, Lỗi).
* Lập lịch trình cố định hoặc chu kỳ (`Schedule`) phân bổ xe tự động theo ca sản xuất.

### 4.6. Tích hợp Hệ thống Sản xuất Aligo MES (Module `integrations`)
* Định kỳ 3–5 giây một lần gửi yêu cầu đồng bộ (Polling) tới Aligo API để nắm bắt tình trạng dây chuyền máy CNC.
* Tiếp nhận tự động các lệnh `Supply Command`, khởi tạo `SupplyRequest`, kết nối với cơ chế Pairing Worker để phân bổ AMR đáp ứng kịp thời trước hạn chót SLA.

### 4.7. Giám sát & Nhật ký Vận hành (Audit & Logging)
* Ghi log chuyên biệt theo từng phân hệ: nhật ký đơn hàng, nhật ký thay đổi trạng thái AMR, nhật ký gửi tin MQTT, nhật ký tích hợp Aligo.
* Cung cấp REST API lọc và tra cứu file log trực tiếp phục vụ bảo trì sự cố.

---

## 5. THIẾT KẾ CƠ SỞ DỮ LIỆU & DATA MODELS CHI TIẾT

### 5.1. Phân hệ `acs` (Đơn hàng & Nghiệp vụ Lõi)

#### `Order`
* `id`: UUIDField (Primary Key, mặc định `uuid.uuid4`)
* `order_id`: CharField(max_length=100, unique=True) – Mã đơn hàng hiển thị
* `order_type`: CharField(choices=[('TRANSPORT', 'Vận chuyển'), ('CHARGE', 'Sạc pin'), ('PARK', 'Đỗ xe'), ('MAINTENANCE', 'Bảo trì')])
* `status`: CharField(choices=[('PENDING', 'Chờ xử lý'), ('PROCESSING', 'Đang xử lý'), ('COMPLETED', 'Hoàn thành'), ('FAILED', 'Thất bại'), ('CANCELLED', 'Hủy bỏ')])
* `priority`: CharField(choices=[('LOW', 'Thấp'), ('NORMAL', 'Bình thường'), ('HIGH', 'Cao'), ('URGENT', 'Khẩn cấp')])
* `source_node`: ForeignKey(`map.Node`, on_delete=SET_NULL, null=True, blank=True)
* `target_node`: ForeignKey(`map.Node`, on_delete=SET_NULL, null=True, blank=True)
* `description`: TextField(blank=True)
* `created_at`: DateTimeField(auto_now_add=True)
* `updated_at`: DateTimeField(auto_now=True)

#### `OrderMaster`
* `id`: UUIDField (Primary Key, `uuid.uuid4`)
* `name`: CharField(max_length=100)
* `status`: CharField(choices=[('PENDING', 'Chờ xử lý'), ('PROCESSING', 'Đang thực thi'), ('COMPLETED', 'Hoàn thành'), ('FAILED', 'Thất bại')])
* `created_at`: DateTimeField(auto_now_add=True)
* `updated_at`: DateTimeField(auto_now=True)

#### `SubOrder`
* `id`: UUIDField (Primary Key, `uuid.uuid4`)
* `order`: ForeignKey(`Order`, on_delete=CASCADE, related_name='suborders')
* `order_master`: ForeignKey(`OrderMaster`, on_delete=SET_NULL, null=True, blank=True)
* `order_update_id`: BigIntegerField(default=0) – Mã số tăng dần của đơn theo chuẩn VDA 5050
* `path`: JSONField(default=dict) – Chứa danh sách nodes, edges và zoneSetId
* `status`: CharField(choices=[('PENDING', 'Chờ gửi'), ('SENT', 'Đã gửi tới AMR'), ('PROCESSING', 'AMR đang thực hiện'), ('COMPLETED', 'Hoàn thành'), ('FAILED', 'Thất bại')])
* `outcome`: TextField(blank=True, default='') – Chi tiết kết quả hoặc lý do lỗi
* `created_at`: DateTimeField(auto_now_add=True)
* `updated_at`: DateTimeField(auto_now=True)

#### `SupplyRequest`
* `id`: UUIDField (Primary Key, `uuid.uuid4`)
* `line_id`: CharField(max_length=64) – Định danh dây chuyền sản xuất
* `buffer`: ForeignKey(`buffer.Buffer`, on_delete=CASCADE)
* `material_id`: CharField(max_length=64) – Mã nguyên vật liệu/phôi
* `priority`: IntegerField(default=1) – Mức ưu tiên xử lý (1-10)
* `sla_deadline`: DateTimeField() – Thời hạn phải cấp phát vật tư
* `status`: CharField(choices=[('PENDING', 'Chờ xử lý'), ('PAIRED', 'Đã gán xe'), ('DELIVERED', 'Đã giao'), ('CANCELLED', 'Hủy')])
* `created_at`: DateTimeField(auto_now_add=True)

#### `ActionDispatch`
* `id`: CharField(max_length=128, primary_key=True) – actionId theo VDA 5050
* `sub_order`: ForeignKey(`SubOrder`, on_delete=CASCADE)
* `order`: ForeignKey(`Order`, on_delete=CASCADE)
* `amr`: ForeignKey(`amr.AmrVehicle`, on_delete=CASCADE)
* `action_type`: CharField(max_length=64)
* `blocking_type`: CharField(max_length=16, default='NONE')
* `created_at`: DateTimeField(auto_now_add=True)

#### `Log`
* `id`: BigAutoField(Primary Key)
* `level`: CharField(max_length=16, default='INFO')
* `module`: CharField(max_length=64)
* `message`: TextField()
* `data`: JSONField(default=dict, blank=True)
* `created_at`: DateTimeField(auto_now_add=True)

---

### 5.2. Phân hệ `amr` (Robot Phương Tiện)

#### `AmrVehicle`
* `serial_number`: CharField(max_length=100, primary_key=True) – Khóa chính, mã định danh xe
* `amr_model`: CharField(max_length=100)
* `interface`: CharField(max_length=50, default='VDA5050_2.1.0')
* `manufacturer`: CharField(max_length=100)
* `version`: CharField(max_length=50, default='2.1.0')
* `ip_address`: GenericIPAddressField(protocol='IPv4', null=True, blank=True)
* `port`: PositiveIntegerField(default=1800)
* `last_heartbeat`: DateTimeField(null=True, blank=True)
* `is_online`: BooleanField(default=False)
* `is_idle`: BooleanField(default=True)
* `is_used_by_master`: ForeignKey(`acs.OrderMaster`, on_delete=SET_NULL, null=True, blank=True)
* **Trạng thái theo chuẩn VDA 5050:**
  - `last_node_id`: CharField(max_length=100, blank=True, default='')
  - `order_id`: CharField(max_length=100, blank=True, default='')
  - `order_update_id`: BigIntegerField(default=0)
  - `node_states`: JSONField(default=list) – Danh sách trạng thái node chưa hoàn thành
  - `edge_states`: JSONField(default=list) – Danh sách trạng thái edge chưa đi qua
  - `action_state`: JSONField(default=list) – Trạng thái thực thi các action
  - `loads`: JSONField(default=list) – Hàng hóa đang mang trên xe
  - `errors`: JSONField(default=list) – Mảng lỗi hệ thống/phần cứng
  - `information`: JSONField(default=list) – Bản tin thông báo trạng thái
  - `amr_position`: JSONField(default=dict) – `{"x": float, "y": float, "theta": float, "mapId": str}`
  - `velocity`: JSONField(default=dict) – `{"vx": float, "vy": float, "omega": float}`
  - `battery_state`: JSONField(default=dict) – `{"batteryCharge": float, "charging": bool}`
  - `safety_state`: JSONField(default=dict) – `{"eStop": str, "fieldViolation": bool}`
  - `driving`: BooleanField(default=False)
  - `paused`: BooleanField(default=False)
  - `new_base_request`: BooleanField(default=False) – Cờ robot yêu cầu gửi tiếp đoạn đường cơ sở
  - `operating_mode`: CharField(choices=[('AUTOMATIC', 'Tự động'), ('SEMIAUTOMATIC', 'Bán tự động'), ('MANUAL', 'Thủ công'), ('SERVICE', 'Bảo dưỡng'), ('TEACHIN', 'Dò đường')])
  - `zone_set_id`: CharField(max_length=100, blank=True, default='')

#### `TopicControl`
* `id`: BigAutoField(Primary Key)
* `topic`: CharField(max_length=255, unique=True)
* `topic_type`: CharField(max_length=50) – `order`, `instantActions`, `state`, `connection`
* `amr`: ForeignKey(`AmrVehicle`, on_delete=CASCADE, related_name='topics')
* `manufacturer`: CharField(max_length=100)
* `version`: CharField(max_length=50)
* `header_id`: PositiveBigIntegerField(default=0) – Bộ đếm số tự tăng của gói tin MQTT
* `last_call`: DateTimeField(null=True, blank=True)

#### `AmrStateLog`
* `id`: AutoField(Primary Key)
* `serialNumber`: ForeignKey(`AmrVehicle`, on_delete=CASCADE, related_name='state_logs')
* `order_id`: CharField(max_length=100, blank=True, default='')
* `order_update_id`: BigIntegerField(default=0)
* `operating_mode`: CharField(max_length=50, blank=True, default='')
* `node_state`: JSONField(default=list)
* `edge_state`: JSONField(default=list)
* `action_state`: JSONField(default=list)
* `loads`: JSONField(default=list)
* `errors`: JSONField(default=list)
* `information`: JSONField(default=list)
* `amr_position`: JSONField(default=dict)
* `velocity`: JSONField(default=dict)
* `battery_state`: JSONField(default=dict)
* `safety_state`: JSONField(default=dict)
* `driving`: BooleanField(default=False)
* `paused`: BooleanField(default=False)
* `new_base_request`: BooleanField(default=False)
* `created_at`: DateTimeField(auto_now_add=True)

---

### 5.3. Phân hệ `buffer` (Trạm Đệm & Lịch Trình)

#### `Buffer`
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `name`: CharField(max_length=100)
* `rssid`: CharField(max_length=100, unique=True) – Mã RFID hoặc thẻ định danh trạm
* `type`: CharField(max_length=50) – Loại bục (PICK, DROP, DUAL)
* `product_model`: CharField(max_length=100, blank=True, default='')
* `process`: CharField(max_length=100, blank=True, default='')
* `role_id`: CharField(max_length=50, blank=True, default='')
* `status`: CharField(choices=[('EMPTY', 'Trống'), ('OCCUPIED', 'Có hàng'), ('RESERVED', 'Đã đặt trước'), ('ERROR', 'Lỗi trạm')])
* `enable`: BooleanField(default=True)
* `ip_address`: GenericIPAddressField(protocol='IPv4', null=True, blank=True)
* `node`: OneToOneField(`map.Node`, on_delete=SET_NULL, null=True, blank=True)
* `handle_order`: ForeignKey(`acs.Order`, on_delete=SET_NULL, null=True, blank=True)
* `update_time`: DateTimeField(auto_now=True)
* `last_success_transfer`: DateTimeField(null=True, blank=True)
* `time_gap_btw_transfer`: DurationField(null=True, blank=True)
* `data`: JSONField(default=dict, blank=True)

#### `Schedule`
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `name`: CharField(max_length=100)
* `description`: CharField(max_length=255, blank=True, default='')
* `map`: ForeignKey(`map.MapBase`, on_delete=CASCADE)
* `number_of_amr_need`: PositiveIntegerField(default=1)
* `number_of_active_order`: PositiveIntegerField(default=0)
* `enable`: BooleanField(default=True)

#### `ScheduleStop`
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `schedule`: ForeignKey(`Schedule`, on_delete=CASCADE, related_name='stops')
* `role_id`: CharField(max_length=50)
* `sequence`: PositiveIntegerField(default=1)

#### `StopAction`
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `schedule_stop`: ForeignKey(`ScheduleStop`, on_delete=CASCADE, related_name='actions')
* `action`: ForeignKey(`map.Action`, on_delete=CASCADE)
* `sequence`: PositiveIntegerField(default=1)

---

### 5.4. Phân hệ `map` (Bản Đồ Nhà Xưởng)

#### `MapBase`
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `name`: CharField(max_length=100)
* `part`: CharField(max_length=50) – Khu vực xưởng (ví dụ: `CNC_2G`)
* `version`: CharField(max_length=50, default='1.0.0')
* `status`: CharField(choices=[('ACTIVE', 'Đang hoạt động'), ('INACTIVE', 'Ngưng sử dụng'), ('DRAFT', 'Bản thảo')])
* `description`: CharField(max_length=255, blank=True, default='')
* `created_at`: DateTimeField(auto_now_add=True)
* `created_by`: ForeignKey('auth.User', on_delete=SET_NULL, null=True, blank=True)

#### `WorldMapLayer`
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `map`: OneToOneField(`MapBase`, on_delete=CASCADE, related_name='world_layer')
* `name`: CharField(max_length=100)
* `image`: ImageField(upload_to='maps/world/')
* `x_origin`: FloatField(default=0.0)
* `y_origin`: FloatField(default=0.0)
* `resolution`: FloatField(default=0.05) – Mét trên mỗi pixel
* `resize`: FloatField(default=1.0)
* `opacity`: FloatField(default=1.0)
* `description`: CharField(max_length=255, blank=True, default='')

#### `GridMapLayer`
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `map`: OneToOneField(`MapBase`, on_delete=CASCADE, related_name='grid_layer')
* `name`: CharField(max_length=100)
* `image`: ImageField(upload_to='maps/grid/')
* `x_set_background`: IntegerField(default=0)
* `y_set_background`: IntegerField(default=0)
* `resize`: FloatField(default=1.0)
* `opacity`: FloatField(default=1.0)

#### `ZoneSet`
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `map`: ForeignKey(`MapBase`, on_delete=CASCADE, related_name='zone_sets')
* `name`: CharField(max_length=100)
* `description`: CharField(max_length=255, blank=True, default='')
* `version`: CharField(max_length=50, default='1.0')
* `is_active`: BooleanField(default=True)

#### `TrafficZone`
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `zone_set`: ForeignKey(`ZoneSet`, on_delete=CASCADE, related_name='traffic_zones')
* `map`: ForeignKey(`MapBase`, on_delete=CASCADE)
* `name`: CharField(max_length=100)
* `type`: CharField(max_length=50) – Loại vùng (INTERSECTION, AISLE, CHARGING_AREA)
* `description`: CharField(max_length=255, blank=True, default='')
* `max_occupancy`: PositiveIntegerField(default=1) – Số xe tối đa cùng có mặt trong vùng
* `priority`: PositiveIntegerField(default=1) – Mức ưu tiên giao thông
* `max_speed`: FloatField(default=1.5) – Giới hạn tốc độ (m/s)

#### `Zone` (Legacy)
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `zone_id`: CharField(max_length=50)
* `zone_name`: CharField(max_length=100)
* `pos_x`, `pos_y`, `size_x`, `size_y`: FloatField(default=0.0)
* `is_active`: BooleanField(default=True)
* `aligo_metadata`: JSONField(default=dict, blank=True)
* `map`: ForeignKey(`MapBase`, on_delete=CASCADE)
* `zone_set`: ForeignKey(`ZoneSet`, on_delete=SET_NULL, null=True, blank=True)

#### `Node`
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `map`: ForeignKey(`MapBase`, on_delete=CASCADE, related_name='nodes')
* `name`: CharField(max_length=100)
* `type`: CharField(choices=[('TRANSIT', 'Trung chuyển'), ('PICK', 'Lấy hàng'), ('DROP', 'Giao hàng'), ('CHARGE', 'Sạc pin'), ('PARK', 'Đỗ xe')])
* `description`: CharField(max_length=255, blank=True, default='')
* `x`: FloatField() – Tọa độ thực x (m)
* `y`: FloatField() – Tọa độ thực y (m)
* `theta`: FloatField(default=0.0) – Hướng robot yêu cầu (radian)
* `allow_deviation_xy`: FloatField(default=0.05) – Sai số tọa độ vị trí (m)
* `allow_deviation_theta`: FloatField(default=0.05) – Sai số góc xoay (rad)
* `use_node`: BooleanField(default=True)
* `is_init`: BooleanField(default=False)
* `is_extended`: BooleanField(default=False)
* `traffic_zone`: ForeignKey(`TrafficZone`, on_delete=SET_NULL, null=True, blank=True)
* `zone`: ForeignKey(`Zone`, on_delete=SET_NULL, null=True, blank=True)

#### `Edge`
* `id`: UUIDField(Primary Key, `uuid.uuid4`)
* `map`: ForeignKey(`MapBase`, on_delete=CASCADE, related_name='edges')
* `start_node`: ForeignKey(`Node`, on_delete=CASCADE, related_name='outgoing_edges')
* `end_node`: ForeignKey(`Node`, on_delete=CASCADE, related_name='incoming_edges')
* `max_speed`: FloatField(default=1.2) – Vận tốc tối đa cho phép (m/s)
* `orientation`: FloatField(default=0.0)
* `max_rotation_speed`: FloatField(default=0.5) – Tốc độ xoay tối đa (rad/s)
* `length`: FloatField(default=1.0) – Chiều dài cung đường (m)
* `orientation_type`: CharField(max_length=50, default='TANGENTIAL')
* `direction`: CharField(choices=[('FORWARD', 'Tiến'), ('REVERSE', 'Lùi'), ('BIDIRECTIONAL', 'Hai chiều')], default='FORWARD')
* `rotation_allowed`: BooleanField(default=True)
* `trajectory`: JSONField(default=dict, blank=True) – Mô tả quỹ đạo cong
* `traffic_zone`: ForeignKey(`TrafficZone`, on_delete=SET_NULL, null=True, blank=True)
* `zone`: ForeignKey(`Zone`, on_delete=SET_NULL, null=True, blank=True)
* `name`: CharField(max_length=100, blank=True, default='')
* `description`: CharField(max_length=255, blank=True, default='')

#### `Action` & Gắn Kết
* `Action`: `id` (UUID), `type` (CHARGING, LIFT, DROP, SCAN, WAIT), `blocking_type` (`NONE`, `SOFT`, `HARD`), `parameters` (JSONField), `description`.
* `ActionOnNode`: `id` (UUID), `action` (FK), `node` (FK) – Ràng buộc duy nhất `(action, node)`.
* `ActionOnEdge`: `id` (UUID), `action` (FK), `edge` (FK) – Ràng buộc duy nhất `(action, edge)`.

---

## 6. CÁC THUẬT TOÁN ĐÃ SỬ DỤNG (Algorithms)

### 6.1. Thuật toán Hungarian (Linear Sum Assignment)
* **Vị trí cài đặt:** `traffic/fleet_scheduler.py`
* **Mục tiêu:** Giải quyết bài toán phân công công việc tối ưu toàn cục (Bipartite Matching): gán tập hợp $M$ robot rảnh với tập hợp $N$ đơn hàng vận chuyển đang chờ xử lý sao cho tổng chi phí quãng đường di chuyển không tải (Deadhead Distance) là nhỏ nhất.
* **Cơ chế:**
  - Xây dựng ma trận chi phí $C_{i,j}$ với phần tử đại diện cho khoảng cách đồ thị đường đi thực tế từ Robot $i$ tới điểm đón hàng của Đơn hàng $j$ (tính bởi Dijkstra).
  - Sử dụng hàm `scipy.optimize.linear_sum_assignment(cost_matrix)`.
  - Có sẵn cơ chế tự động chuyển đổi sang thuật toán tham lam (Greedy Fallback) khi môi trường thiếu thư viện SciPy hoặc ma trận có kích thước suy biến.

### 6.2. Thuật toán Dijkstra Shortest Path (Đường đi Ngắn nhất)
* **Vị trí cài đặt:**
  - `workers/utilities/graph_distance.py`: Module tính khoảng cách phục vụ gán việc và ghép cặp.
  - `traffic/fleet_scheduler.py`: Dùng tính toán các phần tử trong ma trận chi phí của Hungarian.
  - `acs/views.py` (`find_path_vda`): Tìm lộ trình chi tiết hoàn chỉnh từ node xuất phát tới node đích để đóng gói payload VDA 5050.
* **Cơ chế tối ưu hóa:**
  - Cài đặt với cấu trúc hàng đợi ưu tiên `heapq` và đồ thị kề có trọng số (weighted adjacency list).
  - Trọng số cạnh là chiều dài Euclidean thực tế kết hợp hệ số phạt nếu tốc độ quy định bị giới hạn.
  - Cơ chế **Graph Cache TTL 60 giây**: Bản đồ nhà xưởng được lưu trữ sẵn trong bộ nhớ RAM, tự làm mới sau 60 giây hoặc khi có sự kiện cập nhật cấu hình đường/node, giảm thiểu tối đa tải truy vấn cơ sở dữ liệu.

### 6.3. Đặt Chỗ Tài Nguyên Không Gian - Thời Gian (State/Resource Reservation)
* **Vị trí cài đặt:** `traffic/state_reservation_manager.py` và `traffic/state_traffic_controller.py`.
* **Mục tiêu:** Ngăn chặn xung đột va chạm và giải quyết triệt để tình trạng khóa chết (deadlock) giữa nhiều robot cùng lưu thông.
* **Cơ chế:**
  - Phân hoạch mỗi hành trình thành chuỗi bước thời gian dự kiến (time windows).
  - Robot chỉ được phép di chuyển vào Node/Edge kế tiếp nếu tài nguyên đó đã được đặt chỗ thành công (`ReservationStatus.RESERVED`).
  - Nếu xảy ra tranh chấp giao lộ, robot có mức ưu tiên cao hơn (`RobotPriority`) hoặc đang chở tải nặng sẽ được ưu tiên giữ chỗ trước, robot còn lại chuyển sang trạng thái tạm dừng an toàn (`SOFT` blocking).

### 6.4. Phân bổ Đa tầng kèm Phá vỡ Hòa vị (Priority Tiers + Tie-breaker)
* **Vị trí cài đặt:** `workers/acs_supply_request_pairing.py`
* **Mục tiêu:** Ghép nối các yêu cầu cấp vật tư (`SupplyRequest`) phát sinh từ dây chuyền Aligo với xe vận chuyển.
* **Cơ chế:**
  - Phân tầng ưu tiên theo độ khẩn cấp của công đoạn sản xuất (Tầng 1: Dây chuyền sắp dừng thiếu phôi; Tầng 2: Cấp phôi theo kế hoạch; Tầng 3: Thu hồi pallet rỗng).
  - Trong cùng một tầng ưu tiên, sử dụng khoảng cách đồ thị Dijkstra đến vị trí bục cấp hàng và mốc thời gian hạn chót cam kết (SLA Deadline) làm tiêu chí phá vỡ hòa vị (Tie-breaker).

### 6.5. Xử lý Hàng đợi FIFO có Giới hạn Luồng (FIFO Queue Processing)
* **Vị trí cài đặt:** `workers/acs_order_master.py`
* **Cơ chế:** Xử lý các đơn hàng ở trạng thái `PENDING` theo đúng thứ tự thời gian khởi tạo (`created_at`). Khống chế số lượng tác vụ xử lý đồng thời thông qua giới hạn Worker Pool để đảm bảo hệ thống không bị quá tải.

---

## 7. KIẾN TRÚC VÀ NGUYÊN LÝ HOẠT ĐỘNG CỦA CÁC WORKER TIẾN TRÌNH NỀN

Hệ thống được thiết kế theo mô hình phi tập trung hóa tác vụ, vận hành thông qua các tiến trình nền độc lập (Workers). Trong đó, worker quan trọng nhất chịu trách nhiệm giao tiếp robot là **`workers/acs_order_send.py`**.

### 7.1. Phân tích Chi tiết Worker `acs_order_send.py` (Từ Tài liệu & Mã Nguồn Gốc)
Worker này vận hành theo mô hình Đa luồng (Multi-threading) kết hợp hàng đợi nội bộ an toàn:

#### Các thành phần chính trong `acs_order_send.py`:
1. **Cấu trúc lưu vết Anchor (`_sent_anchor_history`, `_last_sent_anchor_seq`):**
   - Theo dõi thứ tự node cơ sở mà robot đã chấp nhận thực thi, đảm bảo các `SubOrder` tiếp theo nối tiếp chính xác vào node đuôi của hành trình trước đó mà không làm robot bị đứt đoạn quãng đường (`new_base_request`).
2. **Luồng điều phối `SubOrderDispatcher` (`WorkerThread`):**
   - Quét định kỳ các `OrderMaster` đang ở trạng thái `PROCESSING`.
   - Tìm kiếm xe `AmrVehicle` đang được gán cho đơn hàng.
   - Thẩm định điều kiện sẵn sàng (`_amr_ready_for_update`): đối soát `order_id` hiện tại và cờ `new_base_request=True`.
   - Đóng gói đối tượng `vda_5050_order.Order` kèm số hiệu `headerId` tự tăng, thời gian UTC và các hành động gắn kèm.
   - Đăng ký các hành động cần thực thi vào bảng `ActionDispatch`.
   - Đẩy thông điệp vào hàng đợi `queue_order_2_sent`.
3. **Luồng giao tiếp MQTT `OrderSendMqtt` (`MQTTInterfaceWorker`):**
   - Đọc dữ liệu từ hàng đợi `queue_order_2_sent` và phát hành lên MQTT Broker.
   - Quản lý danh sách gửi chờ xác nhận `_pending_publishes`.
   - Cơ chế tự động gửi lại (`_resend`) sau mỗi `RESEND_INTERVAL_SECONDS = 3.0` giây nếu robot chưa kịp phản hồi.
   - Nhận diện phản hồi `ACKED` (khi xe cập nhật `order_id` và `order_update_id` tương ứng trong bản tin State) -> Chuyển trạng thái `SubOrder` từ `PENDING` sang `SENT`.
   - Tự động hủy (`DROP`) khi đơn hàng bị đánh dấu lỗi.
   - Xử lý timeout khi quá hạn gửi (`SENT_TIMEOUT_SECONDS = 300` giây) -> Gọi `_mark_publish_failed`.
4. **Luồng giám sát thời gian thực `SubOrderSentTimeoutChecker`:**
   - Quét các đơn hàng đã gửi tới xe nhưng bị treo quá 300 giây mà robot không hoàn thành -> Đánh dấu `FAILED` với thông báo `"Stuck in SENT execution loop state (> 300s)"`.
5. **Cơ chế dừng tiến trình an toàn (Graceful Shutdown):**
   - Bắt các tín hiệu hệ điều hành (`SIGINT`, `SIGTERM`, `SIGBREAK` trên Windows) và hàm `atexit`.
   - Dừng toàn bộ các luồng con, giải phóng kết nối MQTT và đợi các tác vụ hoàn tất trước khi thoát sạch sẽ.

---

## 8. QUY TRÌNH VẬN HÀNH VÀ TRIỂN KHAI (Deployment & Operations)

### 8.1. Yêu cầu Hệ thống
* Hệ điều hành: Linux (Ubuntu 22.04 LTS khuyến nghị) hoặc Windows 10/11 / Windows Server.
* Python: Phiên bản 3.10 trở lên (hỗ trợ tốt trên Python 3.13).
* Cơ sở dữ liệu: PostgreSQL 14+ (có thể dùng SQLite cho môi trường Development / Testing).
* Message Broker: EMQX Broker phiên bản 5.x.

### 8.2. Khởi chạy Hệ thống
Hệ thống cung cấp điểm khởi động tập trung thông qua tập lệnh:
* **Trên Windows:** Chạy tập tin batch `runacs.bat`.
* **Trên Linux:** Chạy script bash `./acs_start.sh`.
* **Trực tiếp bằng Python:** Chạy lệnh `python acs_launch.py`.
Tập lệnh khởi động sẽ kiểm tra cơ sở dữ liệu, áp dụng migration, khởi chạy máy chủ web ASGI (Daphne/Uvicorn) và đồng loạt khởi động các background workers.
