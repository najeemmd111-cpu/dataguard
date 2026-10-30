FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/models
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY dataguard_agent ./dataguard_agent
COPY eval ./eval
ENTRYPOINT ["python", "-m", "dataguard_agent"]
CMD ["--help"]
