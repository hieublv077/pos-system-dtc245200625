import os
import time
import pymysql
from pymysql.cursors import DictCursor

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "pos_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "PosSecurePassword_2026!")
DB_NAME = os.getenv("DB_NAME", "pos_retail_db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

def get_db_connection():
    """Tạo kết nối tới cơ sở dữ liệu MySQL với cơ chế retry khi khởi động"""
    max_retries = 10
    retry_delay = 3
    for attempt in range(max_retries):
        try:
            conn = pymysql.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT,
                cursorclass=DictCursor,
                autocommit=True,
                charset='utf8mb4'
            )
            with conn.cursor() as cur:
                cur.execute("SET NAMES utf8mb4;")
            return conn
        except pymysql.MySQLError as e:
            if attempt < max_retries - 1:
                print(f"[Database] Đang chờ kết nối MySQL ({DB_HOST}:{DB_PORT}) - Thử lại lần {attempt+1}/{max_retries}... Lỗi: {e}")
                time.sleep(retry_delay)
            else:
                print(f"[Database Error] Không thể kết nối tới MySQL sau {max_retries} lần thử.")
                raise e

def init_db():
    """Khởi tạo các bảng cơ sở dữ liệu nếu chưa tồn tại"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. Bảng danh mục
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(50) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            ''')

            # 2. Bảng sản phẩm
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category_id INT,
                sku VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                price DECIMAL(12, 2) NOT NULL,
                cost_price DECIMAL(12, 2) DEFAULT 0,
                stock_quantity INT NOT NULL DEFAULT 0,
                unit VARCHAR(20) DEFAULT 'cái',
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            ''')

            # 3. Bảng hóa đơn
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_code VARCHAR(50) UNIQUE NOT NULL,
                cashier_name VARCHAR(100) DEFAULT 'Thu Ngân 01',
                customer_name VARCHAR(100) DEFAULT 'Khách lẻ',
                total_amount DECIMAL(14, 2) NOT NULL,
                payment_method VARCHAR(30) DEFAULT 'Tiền mặt',
                status VARCHAR(30) DEFAULT 'COMPLETED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            ''')

            # 4. Bảng chi tiết hóa đơn
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                product_id INT NOT NULL,
                product_name VARCHAR(255) NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(12, 2) NOT NULL,
                subtotal DECIMAL(12, 2) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            ''')

            # Nạp và đồng bộ danh mục mẫu chuẩn
            categories_data = [
                (1, 'Đồ uống & Giải khát', 'BEV'),
                (2, 'Bánh kẹo & Ăn vặt', 'SNK'),
                (3, 'Thức ăn nhanh & Nóng', 'FST'),
                (4, 'Thực phẩm đóng gói', 'FOD'),
                (5, 'Hóa mỹ phẩm & Đồ dùng', 'HOU')
            ]
            for cid, cname, ccode in categories_data:
                cursor.execute("""
                    INSERT INTO categories (id, name, code)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE name = VALUES(name), code = VALUES(code);
                """, (cid, cname, ccode))

            # Nạp và đồng bộ danh sách sản phẩm mẫu (14 sản phẩm đa dạng)
            products_data = [
                (1, 'SP001', 'Nước Ngọt Coca Cola 320ml', 10000, 7500, 150, 'lon', 'https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=300'),
                (1, 'SP002', 'Cà Phê Highlands Lon 235ml', 16000, 12000, 80, 'lon', 'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=300'),
                (1, 'SP003', 'Trà Xanh Không Độ 455ml', 11000, 8000, 120, 'chai', 'https://images.unsplash.com/photo-1556881286-fc6915169721?w=300'),
                (1, 'SP009', 'Trà Sữa Trân Châu Đường Đen 500ml', 28000, 18000, 95, 'ly', 'https://images.unsplash.com/photo-1558857563-b37cb3874288?w=300'),
                (1, 'SP014', 'Cà Phê Sữa Đá Sài Gòn 300ml', 22000, 14000, 60, 'ly', 'https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=300'),
                (2, 'SP004', 'Bánh Snack Lay Khoai Tây 95g', 22000, 16000, 65, 'gói', 'https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=300'),
                (2, 'SP005', 'Bánh Quy Oreo Socola 133g', 18000, 13500, 90, 'gói', 'https://images.unsplash.com/photo-1582293041079-7814c2f12063?w=300'),
                (2, 'SP012', 'Socola KitKat Thanh 4 Ngón', 15000, 10000, 85, 'thanh', 'https://images.unsplash.com/photo-1549007994-cb92caebd54b?w=300'),
                (3, 'SP010', 'Bánh Mì Pate Chả Lụa Nóng Giòn', 25000, 16000, 50, 'ổ', 'https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=300'),
                (3, 'SP011', 'Đùi Gà Rán Giòn Cay Giòn Rụm', 35000, 24000, 40, 'cái', 'https://images.unsplash.com/photo-1562967914-608f82629710?w=300'),
                (4, 'SP006', 'Mì Ăn Liền Hảo Hảo Tôm Chua Cay', 5000, 3800, 300, 'gói', 'https://images.unsplash.com/photo-1612927601601-6638404737ce?w=300'),
                (4, 'SP007', 'Xúc Xích Tiệt Trùng CP 4 Cây', 19000, 14000, 110, 'gói', 'https://images.unsplash.com/photo-1585325701165-351af916e581?w=300'),
                (4, 'SP013', 'Cơm Nắm Tam Giác Cá Hồi Mayo', 18000, 12000, 70, 'cái', 'https://images.unsplash.com/photo-1618449840665-9ed506d73a34?w=300'),
                (5, 'SP008', 'Khăn Giấy Ướt Cao Cấp 80 Tờ', 25000, 17000, 45, 'gói', 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300')
            ]
            for p in products_data:
                cursor.execute("""
                    INSERT INTO products (category_id, sku, name, price, cost_price, stock_quantity, unit, image_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        name = VALUES(name),
                        price = VALUES(price),
                        cost_price = VALUES(cost_price),
                        unit = VALUES(unit),
                        image_url = VALUES(image_url),
                        category_id = VALUES(category_id);
                """, p)

        conn.close()
        print("[Database] Khởi tạo và đồng bộ 14 sản phẩm & danh mục MySQL thành công!")
    except Exception as e:
        print(f"[Database Error] Lỗi trong quá trình init_db: {e}")
