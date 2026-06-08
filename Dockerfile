FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN mkdir -p /app/media /app/staticfiles \
    && python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "yt_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
