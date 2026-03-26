FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir imap-tools

COPY forwarder.py .

CMD ["python", "forwarder.py"]
