FROM python@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
RUN pip install --no-cache-dir --report /dependencies.json psycopg==3.3.6 psycopg-binary==3.3.6 pika==1.3.2 typing-extensions==4.15.0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /lab
ENTRYPOINT ["python", "/kit/probe.py"]
