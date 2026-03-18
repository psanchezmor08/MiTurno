@echo off
echo Construyendo y levantando en puerto 8505...
docker-compose up -d --build
echo Descargando modelo de IA...
docker exec -it ollama ollama pull llama3
echo Servidor listo en http://localhost:8505
pause
