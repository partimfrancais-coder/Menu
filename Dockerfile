FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py hosted.py ./
COPY dist ./dist
COPY templates ./templates
COPY data/menus.json ./data/menus.json
COPY *.pdf ./
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 60 --access-logfile - 'hosted:create_app()'"]
