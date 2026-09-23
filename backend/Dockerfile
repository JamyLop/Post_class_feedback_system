FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Office conversion is optional at build time so core API releases are not held
# hostage by a transient Debian mirror outage; PDF export reports a clear error
# when no converter is present.
ARG INSTALL_OFFICE=true
RUN if [ "$INSTALL_OFFICE" = "true" ]; then \
      apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 -o Acquire::http::Timeout=30 update \
      && apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 -o Acquire::http::Timeout=30 install -y --no-install-recommends libreoffice-writer fonts-noto-cjk \
      && rm -rf /var/lib/apt/lists/*; \
    fi

COPY requirements.txt .
# 公网构建偶发 PyPI 读超时不应中断发布；安装仍保持无缓存镜像层。
RUN pip install --no-cache-dir --retries 3 --timeout 60 -r requirements.txt
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations

RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2}"]
