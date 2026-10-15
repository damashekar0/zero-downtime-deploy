FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask prometheus_client
COPY app.py .
ARG VERSION=v1
ARG ERROR_RATE=0
ENV VERSION=$VERSION
ENV ERROR_RATE=$ERROR_RATE
CMD ["python", "app.py"]