# Sử dụng môi trường Node.js siêu nhẹ
FROM node:18-alpine

# Cài đặt thư mục làm việc
WORKDIR /app

# Copy các file cấu hình và cài đặt thư viện
COPY package*.json ./
RUN npm install

# Copy toàn bộ code (index.js) vào container
COPY . .

# Mở cổng cho Web Server của Render
EXPOSE 8080

# Lệnh khởi chạy bot
CMD ["node", "index.js"]