import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import time
import random
from datetime import datetime
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from database import get_db_connection, init_db

# --- PROMETHEUS METRICS SETUP ---
REQUEST_COUNT = Counter('pos_http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status_code'])
REQUEST_LATENCY = Histogram('pos_http_request_duration_seconds', 'HTTP request duration in seconds', ['endpoint'])
ORDERS_COUNT = Counter('pos_orders_total', 'Total POS Orders Created', ['payment_method'])
REVENUE_TOTAL = Counter('pos_revenue_vnd_total', 'Total Revenue in VND')

app = FastAPI(
    title="Hệ Thống Quản Lý Cửa Hàng & POS",
    description="Bài tập lớn Triển khai và Quản trị Hệ thống Phần mềm - Đề 21 - ICTU 2026",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware đo lường và ghi log cho Prometheus + Loki
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    endpoint = request.url.path
    status_code = str(response.status_code)
    
    REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)
    
    # Ghi log ra stdout để Promtail thu thập đưa về Loki
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {endpoint} -> Status: {status_code} ({duration*1000:.2f}ms)")
    return response

# Khởi tạo DB khi ứng dụng chạy
@app.on_event("startup")
def on_startup():
    print("[Application] Ứng dụng Web POS đang khởi động...")
    init_db()

# --- METRICS ENDPOINT (Cho Prometheus) ---
@app.get("/metrics")
def get_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# --- MODELS ---
class ProductCreate(BaseModel):
    category_id: int
    sku: str
    name: str
    price: float
    cost_price: float = 0
    stock_quantity: int
    unit: str = "cái"
    image_url: Optional[str] = None

class OrderItemRequest(BaseModel):
    product_id: int
    quantity: int

class OrderCreateRequest(BaseModel):
    cashier_name: str = "Thu Ngân 01"
    customer_name: str = "Khách lẻ"
    payment_method: str = "Tiền mặt"
    items: List[OrderItemRequest]

# --- API ENDPOINTS ---

@app.get("/api/products")
def get_products():
    """Lấy danh sách tất cả sản phẩm kèm danh mục và tình trạng tồn kho"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT p.*, c.name as category_name, c.code as category_code
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.id DESC
            """)
            products = cursor.fetchall()
        conn.close()
        return {"success": True, "data": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/products")
def create_product(product: ProductCreate):
    """Thêm sản phẩm mới vào kho hàng"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO products (category_id, sku, name, price, cost_price, stock_quantity, unit, image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                product.category_id, product.sku, product.name, product.price,
                product.cost_price, product.stock_quantity, product.unit, product.image_url
            ))
            new_id = cursor.lastrowid
        conn.close()
        return {"success": True, "message": "Thêm sản phẩm thành công", "product_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi khi thêm sản phẩm: {str(e)}")

@app.get("/api/categories")
def get_categories():
    """Lấy danh mục sản phẩm"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM categories ORDER BY id ASC")
            categories = cursor.fetchall()
        conn.close()
        return {"success": True, "data": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/orders")
def checkout_order(order_req: OrderCreateRequest):
    """Tạo hóa đơn bán hàng POS và tự động trừ tồn kho nhanh"""
    if not order_req.items:
        raise HTTPException(status_code=400, detail="Giỏ hàng trống!")
    
    conn = get_db_connection()
    try:
        conn.begin()
        with conn.cursor() as cursor:
            order_code = f"HD{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(10, 99)}"
            total_amount = 0
            order_items_prepared = []

            # Kiểm tra tồn kho và tính tổng tiền
            for item in order_req.items:
                cursor.execute("SELECT id, name, price, stock_quantity FROM products WHERE id = %s FOR UPDATE", (item.product_id,))
                prod = cursor.fetchone()
                if not prod:
                    conn.rollback()
                    raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm ID: {item.product_id}")
                
                if prod['stock_quantity'] < item.quantity:
                    conn.rollback()
                    raise HTTPException(status_code=400, detail=f"Sản phẩm '{prod['name']}' chỉ còn {prod['stock_quantity']} trong kho, không đủ bán!")
                
                subtotal = float(prod['price']) * item.quantity
                total_amount += subtotal
                order_items_prepared.append({
                    "product_id": prod['id'],
                    "product_name": prod['name'],
                    "quantity": item.quantity,
                    "unit_price": float(prod['price']),
                    "subtotal": subtotal
                })

            # Tạo hóa đơn
            cursor.execute("""
                INSERT INTO orders (order_code, cashier_name, customer_name, total_amount, payment_method, status)
                VALUES (%s, %s, %s, %s, %s, 'COMPLETED')
            """, (order_code, order_req.cashier_name, order_req.customer_name, total_amount, order_req.payment_method))
            order_id = cursor.lastrowid

            # Thêm chi tiết và trừ tồn kho
            for oi in order_items_prepared:
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price, subtotal)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (order_id, oi['product_id'], oi['product_name'], oi['quantity'], oi['unit_price'], oi['subtotal']))

                # Trừ tồn kho nhanh
                cursor.execute("""
                    UPDATE products SET stock_quantity = stock_quantity - %s WHERE id = %s
                """, (oi['quantity'], oi['product_id']))

        conn.commit()
        conn.close()

        # Update metrics Prometheus
        ORDERS_COUNT.labels(payment_method=order_req.payment_method).inc()
        REVENUE_TOTAL.inc(total_amount)

        print(f"[POS Checkout] Đã thanh toán đơn hàng {order_code} - Tổng tiền: {total_amount:,.0f} VND ({order_req.payment_method})")
        return {
            "success": True,
            "message": "Thanh toán thành công!",
            "order_code": order_code,
            "order_id": order_id,
            "total_amount": total_amount,
            "items_count": len(order_items_prepared)
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Lỗi thanh toán: {str(e)}")

@app.get("/api/inventory")
def get_inventory():
    """Xem báo cáo tồn kho nhanh và cảnh báo sắp hết hàng"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.sku, p.name, c.name as category_name, p.price, p.stock_quantity, p.unit,
                       CASE 
                           WHEN p.stock_quantity <= 0 THEN 'OUT_OF_STOCK'
                           WHEN p.stock_quantity <= 20 THEN 'LOW_STOCK'
                           ELSE 'IN_STOCK'
                       END as stock_status
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.stock_quantity ASC
            """)
            items = cursor.fetchall()
        conn.close()
        return {"success": True, "data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
def get_dashboard_stats():
    """Thống kê tổng quan nhanh cho dashboard bán hàng"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total_products, SUM(stock_quantity) as total_items FROM products")
            prod_stat = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) as low_stock FROM products WHERE stock_quantity <= 20")
            low_stock = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) as total_orders, COALESCE(SUM(total_amount), 0) as total_revenue FROM orders")
            order_stat = cursor.fetchone()

        conn.close()
        return {
            "success": True,
            "total_products": prod_stat['total_products'] or 0,
            "total_items": prod_stat['total_items'] or 0,
            "low_stock_count": low_stock['low_stock'] or 0,
            "total_orders": order_stat['total_orders'] or 0,
            "total_revenue": float(order_stat['total_revenue'] or 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount thư mục static & Serve HTML
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/index.php")
def php_redirect(request: Request):
    """Tự động chuyển hướng các truy vấn phpMyAdmin về đúng tiền tố /pma/"""
    query = str(request.query_params)
    target = f"/pma/index.php?{query}" if query else "/pma/"
    return RedirectResponse(url=target)

@app.get("/", response_class=HTMLResponse)
def index_page():
    html_file = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Hệ Thống POS Đang Khởi Động...</h1>"
