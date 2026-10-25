# Servidor MCP de Beakman y su web. El temario no va en la imagen: lo lee de GitHub al arrancar
# y lo refresca solo (ver beakman_mcp/content.py). Las webs sí van: docs/ en / y lab/site/ en lab.beakman.kademy.net.
# Se construye desde la raíz del repo: docker build -f mcp/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mcp/beakman_mcp ./beakman_mcp
COPY docs ./site
COPY lab/site ./lab

RUN useradd --system --uid 10001 beakman && mkdir /data && chown beakman /data
USER beakman
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/up', timeout=4)"
CMD ["uvicorn", "beakman_mcp.server:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
