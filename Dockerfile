FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# gettext: compilemessages (.mo files are not committed)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Build-time steps need no secrets: no R2 keys → local storage settings,
# and static files are served by WhiteNoise from STATIC_ROOT.
RUN python manage.py compilemessages \
    && python manage.py collectstatic --noinput

RUN useradd --create-home app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["sh", "./docker-entrypoint.sh"]
