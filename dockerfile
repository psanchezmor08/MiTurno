FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Exponemos el puerto solicitado
EXPOSE 8505

# Comando para arrancar Streamlit en el puerto 8505
CMD ["streamlit", "run", "miturno.py", "--server.port=8505", "--server.address=0.0.0.0"]
