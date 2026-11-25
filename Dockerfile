FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x /app/entrypoint.sh
ENV TZ=Asia/Shanghai
ENV NETEASE_DOWNLOADS_DIR=/app/downloads
ENV NETEASE_COOKIE_FILE=/app/data/cookie.txt
EXPOSE 5023
CMD ["/app/entrypoint.sh"]
