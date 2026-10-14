# 1. Base image nhẹ và ổn định
FROM python:3.11-slim

# Thiết lập biến môi trường tối ưu cho Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 2. Hardening: Tạo non-root user (appuser, UID/GID 1001)
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# 3. Cài đặt các thư viện cần thiết
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Sao chép mã nguồn ứng dụng và phân quyền cho appuser
COPY . .
RUN chown -R appuser:appgroup /app

# 5. Chuyển quyền thực thi sang user không có đặc quyền root
USER appuser

EXPOSE 8000

# 6. Lệnh khởi chạy ứng dụng FastAPI với uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
