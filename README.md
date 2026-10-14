# HỆ THỐNG QUẢN LÝ CỬA HÀNG VÀ BÁN HÀNG POS (ĐỀ 21)
> **Học phần**: Triển khai và Quản trị Hệ thống Phần mềm (TKQT HTPM K23)  
> **Trường**: Đại học Công nghệ Thông tin & Truyền thông - Đại học Thái Nguyên (ICTU)  
> **Sinh viên thực hiện**: Dương Quý Hiếu  
> **Giảng viên hướng dẫn**: Thầy Vũ Việt Dũng  

---

## 📌 1. Giới thiệu Đề tài
Dự án triển khai một hệ thống quản lý bán hàng tại cửa hàng tiện lợi / siêu thị mini (**Smart Retail POS**) kết hợp cơ sở dữ liệu **MySQL** và giao diện quản trị **phpMyAdmin**. Toàn bộ dịch vụ được đóng gói độc lập theo kiến trúc microservices container hóa với **Docker Compose**.

### Các tính năng chính của Web POS:
* **Giao diện bán hàng (POS Terminal)**: Lựa chọn mặt hàng, tìm kiếm nhanh theo tên hoặc mã SKU, phân loại theo danh mục ngành hàng, giỏ hàng trực quan, tính tổng tiền, hỗ trợ nhiều phương thức thanh toán (Tiền mặt, Chuyển khoản QR, Quẹt thẻ).
* **Tự động trừ tồn kho nhanh**: Khi tạo và thanh toán đơn hàng thành công, hệ thống sử dụng MySQL Transaction tự động cập nhật số lượng tồn kho theo thời gian thực.
* **Cảnh báo tồn kho**: Trực quan hóa tình trạng kho hàng (*Đủ hàng*, *Cận date / Sắp hết hàng*, *Hết hàng*).
* **Quản trị cơ sở dữ liệu**: Tích hợp trực tiếp **phpMyAdmin** để theo dõi và quản lý dữ liệu bảng `products`, `categories`, `orders`, `order_items`.

---

## 🏗️ 2. Kiến trúc dịch vụ (Docker Containers)
1. **`web_pos`**: Ứng dụng Web POS viết bằng FastAPI / Python 3.11, đóng gói dưới quyền non-root user (`appuser`, UID 1001).
2. **`db_mysql`**: Cơ sở dữ liệu MySQL 8.0, cấu hình phân tách mạng nội bộ an toàn (`backend-net`), nạp sẵn dữ liệu mẫu qua `init.sql`.
3. **`phpmyadmin`**: Giao diện web trực quan để quản trị MySQL.

---

## 🚀 3. Hướng dẫn Khởi chạy Hệ thống

### Bước 1: Sao chép tệp cấu hình biến môi trường
```bash
cp .env.example .env
```
*(Chỉnh sửa mật khẩu hoặc giữ nguyên các giá trị mặc định an toàn trong tệp `.env`)*

### Bước 2: Khởi động hệ thống bằng Docker Compose
```bash
docker-compose up -d --build
```

### Bước 3: Kiểm tra trạng thái các container
```bash
docker-compose ps
```

---

## 🌐 4. Địa chỉ truy cập dịch vụ
| Dịch vụ | Địa chỉ truy cập | Tài khoản / Ghi chú |
| :--- | :--- | :--- |
| **Giao diện Bán hàng POS** | [http://localhost:8000](http://localhost:8000) | Giao diện thu ngân bán hàng & kho |
| **Quản trị phpMyAdmin** | [http://localhost:8080](http://localhost:8080) | User: `pos_user` / Pass: xem trong `.env` |
| **Metrics Endpoint** | [http://localhost:8000/metrics](http://localhost:8000/metrics) | Cung cấp số liệu cho Prometheus |

---

## 🛡️ 5. Các biện pháp Bảo mật (Hardening) đã áp dụng
1. **Container Non-Root**: Ứng dụng web chạy dưới `appuser` (UID 1001), ngăn ngừa đặc quyền root.
2. **Docker Network Isolation**: Phân tách mạng `frontend-net` và `backend-net`, cô lập hoàn toàn cơ sở dữ liệu.
3. **Bảo mật Secrets**: Quản lý mật khẩu qua `.env`, loại bỏ khỏi Git bằng `.gitignore`.
4. **Giới hạn tài nguyên (Resource Limits)**: Giới hạn CPU và RAM trên từng container trong `docker-compose.yml`.
