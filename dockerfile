FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CORRECCIÓN: Copiamos el archivo correcto
COPY miturno.py .

EXPOSE 8505

CMD ["streamlit", "run", "miturno.py", "--server.port=8505", "--server.address=0.0.0.0"]
