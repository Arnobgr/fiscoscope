FROM python:3.12-slim

WORKDIR /app

# Install runtime deps first for layer caching.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source (api.py, run_pipeline.py, config.py, fetchers/, processors/).
COPY backend/ .

EXPOSE 8000

# Default command = the API. The pipeline service overrides the entrypoint.
# --proxy-headers + --forwarded-allow-ips=127.0.0.1 let uvicorn trust nginx's
# X-Forwarded-For so slowapi rate-limits on the real client IP. We restrict
# to 127.0.0.1 (not "*") because the container is bound to 127.0.0.1:8077
# on the host, so the only legitimate upstream is host nginx.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips=127.0.0.1"]