// STATE
let allProducts = [];
let categories = [];
let cart = [];
let selectedCategory = 'ALL';

// INIT
document.addEventListener("DOMContentLoaded", () => {
    loadCategories();
    loadProducts();
    loadStats();
});

// SWITCH TAB
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(`tab-${tabId}`).classList.add('active');
    event.currentTarget.classList.add('active');

    if (tabId === 'inventory') {
        loadInventory();
        loadStats();
    }
}

// FETCH CATEGORIES
async function loadCategories() {
    try {
        const res = await fetch('/api/categories');
        const json = await res.json();
        if (json.success) {
            categories = json.data;
            renderCategoryFilters();
            renderModalCategoryOptions();
        }
    } catch (e) {
        console.error("Lỗi tải danh mục:", e);
    }
}

function renderCategoryFilters() {
    const wrap = document.getElementById('categoryFilters');
    let html = `<button class="cat-pill active" onclick="filterByCategory('ALL', this)">Tất Cả</button>`;
    categories.forEach(cat => {
        html += `<button class="cat-pill" onclick="filterByCategory(${cat.id}, this)">${cat.name}</button>`;
    });
    wrap.innerHTML = html;
}

function renderModalCategoryOptions() {
    const select = document.getElementById('modalCategory');
    let html = '';
    categories.forEach(cat => {
        html += `<option value="${cat.id}">${cat.name}</option>`;
    });
    select.innerHTML = html;
}

function filterByCategory(catId, btnElement) {
    selectedCategory = catId;
    document.querySelectorAll('.cat-pill').forEach(btn => btn.classList.remove('active'));
    if (btnElement) btnElement.classList.add('active');
    renderProducts();
}

// FETCH PRODUCTS
async function loadProducts() {
    try {
        const res = await fetch('/api/products');
        const json = await res.json();
        if (json.success) {
            allProducts = json.data;
            renderProducts();
        }
    } catch (e) {
        console.error("Lỗi tải sản phẩm:", e);
    }
}

function renderProducts() {
    const grid = document.getElementById('productGrid');
    const searchVal = document.getElementById('searchInput').value.toLowerCase().trim();

    const filtered = allProducts.filter(p => {
        const matchCategory = selectedCategory === 'ALL' || p.category_id == selectedCategory;
        const matchSearch = p.name.toLowerCase().includes(searchVal) || p.sku.toLowerCase().includes(searchVal);
        return matchCategory && matchSearch;
    });

    if (filtered.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: #94a3b8; padding: 40px;">Không tìm thấy sản phẩm nào!</div>`;
        return;
    }

    grid.innerHTML = filtered.map(p => {
        let stockClass = 'stock-in';
        let stockText = `Còn ${p.stock_quantity} ${p.unit}`;
        if (p.stock_quantity <= 0) {
            stockClass = 'stock-out';
            stockText = 'Hết hàng';
        } else if (p.stock_quantity <= 20) {
            stockClass = 'stock-low';
            stockText = `Sắp hết (${p.stock_quantity})`;
        }

        const imgUrl = p.image_url || 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=300';

        return `
            <div class="product-card" onclick="addToCart(${p.id})">
                <img src="${imgUrl}" class="prod-img" alt="${p.name}">
                <div class="prod-info">
                    <span class="prod-sku">${p.sku} • ${p.category_name || 'Khác'}</span>
                    <h4 class="prod-name">${p.name}</h4>
                    <div class="prod-bottom">
                        <span class="prod-price">${Number(p.price).toLocaleString()} đ</span>
                        <span class="prod-stock-badge ${stockClass}">${stockText}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function filterProducts() {
    renderProducts();
}

// CART MANAGEMENT
function addToCart(productId) {
    const product = allProducts.find(p => p.id === productId);
    if (!product) return;

    if (product.stock_quantity <= 0) {
        alert("Sản phẩm đã hết hàng trong kho!");
        return;
    }

    const existing = cart.find(item => item.product.id === productId);
    if (existing) {
        if (existing.quantity >= product.stock_quantity) {
            alert(`Kho chỉ còn ${product.stock_quantity} ${product.unit}!`);
            return;
        }
        existing.quantity += 1;
    } else {
        cart.push({
            product: product,
            quantity: 1
        });
    }

    renderCart();
}

function updateQuantity(productId, delta) {
    const item = cart.find(i => i.product.id === productId);
    if (!item) return;

    const newQty = item.quantity + delta;
    if (newQty <= 0) {
        cart = cart.filter(i => i.product.id !== productId);
    } else if (newQty > item.product.stock_quantity) {
        alert(`Số lượng vượt quá số tồn kho (${item.product.stock_quantity})!`);
        return;
    } else {
        item.quantity = newQty;
    }
    renderCart();
}

function clearCart() {
    if (cart.length > 0 && confirm("Bạn có chắc chắn muốn xóa toàn bộ giỏ hàng?")) {
        cart = [];
        renderCart();
    }
}

function renderCart() {
    const list = document.getElementById('cartItemsList');
    const totalItemsEl = document.getElementById('cartTotalItems');
    const totalPriceEl = document.getElementById('cartTotalPrice');

    if (cart.length === 0) {
        list.innerHTML = `
            <div class="empty-cart-state">
                <i class="fa-solid fa-cart-arrow-down"></i>
                <p>Chưa có sản phẩm nào trong giỏ</p>
                <span>Bấm vào sản phẩm bên trái để thêm vào đơn</span>
            </div>
        `;
        totalItemsEl.innerText = "0";
        totalPriceEl.innerText = "0 đ";
        return;
    }

    let totalItems = 0;
    let totalPrice = 0;

    list.innerHTML = cart.map(item => {
        const subtotal = item.quantity * item.product.price;
        totalItems += item.quantity;
        totalPrice += subtotal;

        return `
            <div class="cart-row">
                <div class="cart-row-info">
                    <div class="cart-row-name">${item.product.name}</div>
                    <div class="cart-row-price">${Number(item.product.price).toLocaleString()} đ / ${item.product.unit}</div>
                </div>
                <div class="cart-qty-ctrl">
                    <button class="qty-btn" onclick="updateQuantity(${item.product.id}, -1)">-</button>
                    <span class="qty-num">${item.quantity}</span>
                    <button class="qty-btn" onclick="updateQuantity(${item.product.id}, 1)">+</button>
                </div>
                <div class="cart-row-subtotal">${Number(subtotal).toLocaleString()} đ</div>
            </div>
        `;
    }).join('');

    totalItemsEl.innerText = totalItems;
    totalPriceEl.innerText = `${Number(totalPrice).toLocaleString()} đ`;
}

// CHECKOUT PROCESS
async function processCheckout() {
    if (cart.length === 0) {
        alert("Vui lòng chọn ít nhất 1 sản phẩm vào đơn hàng!");
        return;
    }

    const paymentMethod = document.getElementById('paymentMethod').value;
    const checkoutBtn = document.getElementById('btnCheckout');
    checkoutBtn.disabled = true;
    checkoutBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang thanh toán...`;

    const payload = {
        cashier_name: "Thu Ngân 01",
        customer_name: "Khách lẻ",
        payment_method: paymentMethod,
        items: cart.map(item => ({
            product_id: item.product.id,
            quantity: item.quantity
        }))
    };

    try {
        const res = await fetch('/api/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok && data.success) {
            showReceipt(data, cart, paymentMethod);
            cart = [];
            renderCart();
            await loadProducts(); // Cập nhật lại tồn kho ngay lập tức
        } else {
            alert(`Thanh toán thất bại: ${data.detail || 'Có lỗi xảy ra'}`);
        }
    } catch (e) {
        alert("Lỗi kết nối máy chủ thanh toán!");
        console.error(e);
    } finally {
        checkoutBtn.disabled = false;
        checkoutBtn.innerHTML = `<i class="fa-solid fa-circle-check"></i> THANH TOÁN & IN HÓA ĐƠN`;
    }
}

// RECEIPT MODAL
function showReceipt(orderResult, orderItems, paymentMethod) {
    document.getElementById('receiptCode').innerText = `Mã HĐ: ${orderResult.order_code}`;
    document.getElementById('receiptTime').innerText = `Thời gian: ${new Date().toLocaleString('vi-VN')}`;
    document.getElementById('receiptPaymentMethod').innerText = paymentMethod;

    const tbody = document.getElementById('receiptItemsBody');
    tbody.innerHTML = orderItems.map(item => `
        <tr>
            <td>${item.product.name}</td>
            <td style="text-align: center;">${item.quantity}</td>
            <td style="text-align: right;">${Number(item.product.price).toLocaleString()}</td>
            <td style="text-align: right;">${Number(item.quantity * item.product.price).toLocaleString()}</td>
        </tr>
    `).join('');

    document.getElementById('receiptTotalAmount').innerText = `${Number(orderResult.total_amount).toLocaleString()} đ`;
    document.getElementById('receiptModal').classList.add('active');
}

function closeReceiptModal() {
    document.getElementById('receiptModal').classList.remove('active');
}

// INVENTORY & STATS
async function loadInventory() {
    try {
        const res = await fetch('/api/inventory');
        const json = await res.json();
        if (json.success) {
            const tbody = document.getElementById('inventoryTableBody');
            tbody.innerHTML = json.data.map(p => {
                let badge = '<span class="prod-stock-badge stock-in">Đủ hàng</span>';
                if (p.stock_status === 'OUT_OF_STOCK') {
                    badge = '<span class="prod-stock-badge stock-out">Hết hàng</span>';
                } else if (p.stock_status === 'LOW_STOCK') {
                    badge = '<span class="prod-stock-badge stock-low">Cảnh báo sắp hết</span>';
                }

                return `
                    <tr>
                        <td><strong>${p.sku}</strong></td>
                        <td>${p.name}</td>
                        <td>${p.category_name || 'Khác'}</td>
                        <td>${Number(p.price).toLocaleString()} đ</td>
                        <td><strong style="font-size: 14px;">${p.stock_quantity}</strong></td>
                        <td>${p.unit}</td>
                        <td>${badge}</td>
                    </tr>
                `;
            }).join('');
        }
    } catch (e) {
        console.error("Lỗi tải tồn kho:", e);
    }
}

async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const json = await res.json();
        if (json.success) {
            document.getElementById('statTotalProducts').innerText = json.total_products;
            document.getElementById('statTotalItems').innerText = json.total_items.toLocaleString();
            document.getElementById('statLowStock').innerText = json.low_stock_count;
            document.getElementById('statRevenue').innerText = `${Number(json.total_revenue).toLocaleString()} đ`;
        }
    } catch (e) {
        console.error("Lỗi tải thống kê:", e);
    }
}

// MODAL ADD PRODUCT
function openAddProductModal() {
    document.getElementById('addProductModal').classList.add('active');
}

function closeAddProductModal() {
    document.getElementById('addProductModal').classList.remove('active');
}

async function submitNewProduct(e) {
    e.preventDefault();
    const payload = {
        category_id: parseInt(document.getElementById('modalCategory').value),
        sku: document.getElementById('modalSku').value.trim(),
        name: document.getElementById('modalName').value.trim(),
        unit: document.getElementById('modalUnit').value.trim(),
        price: parseFloat(document.getElementById('modalPrice').value),
        cost_price: parseFloat(document.getElementById('modalPrice').value) * 0.7,
        stock_quantity: parseInt(document.getElementById('modalStock').value),
        image_url: document.getElementById('modalImage').value.trim() || null
    };

    try {
        const res = await fetch('/api/products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.success) {
            alert("Thêm sản phẩm thành công!");
            closeAddProductModal();
            document.getElementById('addProductForm').reset();
            await loadProducts();
            await loadStats();
        } else {
            alert(`Lỗi: ${data.detail || 'Không thể lưu sản phẩm'}`);
        }
    } catch (err) {
        alert("Lỗi kết nối khi thêm sản phẩm!");
        console.error(err);
    }
}
