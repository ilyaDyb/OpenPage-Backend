FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=core.open_page.settings

COPY requirements.txt .
RUN pip install --no-cache-dir \
    --default-timeout=100 \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

COPY . .

RUN cp /app/entrypoint.sh /usr/local/bin/openpage-entrypoint.sh \
    && sed -i 's/\r$//' /usr/local/bin/openpage-entrypoint.sh \
    && chmod +x /usr/local/bin/openpage-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/usr/local/bin/openpage-entrypoint.sh"]
