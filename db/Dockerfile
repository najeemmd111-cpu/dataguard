FROM python:3.12-slim
WORKDIR /seed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY seed.py .
RUN useradd --uid 10001 seeder
USER 10001
CMD ["python", "seed.py"]
