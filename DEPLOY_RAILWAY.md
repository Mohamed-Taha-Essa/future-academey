# Deploying on Railway (Docker)

Railway builds `Dockerfile` (selected by `railway.json`). On every start
the container runs `docker-entrypoint.sh`: `migrate`, then Gunicorn on
Railway's `$PORT`.

Build time (no secrets needed): `pip install`, `compilemessages`,
`collectstatic` (static files served by WhiteNoise).

## Service variables

| Variable | Required | Example / note |
|---|---|---|
| `SECRET_KEY` | yes | long random string |
| `DEBUG` | no | leave unset (= `False`) in production |
| `DATABASE_URL` | yes | reference the Railway Postgres: `${{Postgres.DATABASE_URL}}`. Without it the app uses SQLite **inside the container, which is wiped on every deploy** |
| `ALLOWED_HOSTS` | no | default covers `.futureacademey.com` and `.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | if admin is used on the Railway URL | `https://<service>.up.railway.app` (comma-separated extra origins) |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | yes | R2 API token |
| `R2_BUCKET_NAME` | yes | bucket name |
| `R2_ENDPOINT_URL` | yes | `https://<account-id>.r2.cloudflarestorage.com` |
| `R2_CUSTOM_DOMAIN` | recommended | e.g. `media.futureacademey.com` — host only, no `https://`, no trailing `/` |
| `CERTIFICATE_PUBLIC_BASE_URL` | no | default `https://www.futureacademey.com` (encoded in every QR) |
| `WEB_CONCURRENCY` | no | Gunicorn workers, default 3 |

## R2 custom domain

1. Cloudflare → R2 → bucket → Settings → **Custom Domains** → connect
   e.g. `media.futureacademey.com` (the zone must be on Cloudflare).
2. Set `R2_CUSTOM_DOMAIN=media.futureacademey.com` on Railway and redeploy.

With it, media links become permanent public URLs
(`https://media.futureacademey.com/certificates/...pdf`) instead of
signed R2 URLs that expire after 1 hour. Everything in the bucket is then
publicly readable by URL — file names have random parts, but the bucket
should only contain public site media.

The admin QR placement preview streams PDFs through Django (same origin),
so no CORS rule is needed on the bucket.

## Deploy steps

1. Push the branch; Railway builds the image.
2. Set the variables above (first deploy: also add the Postgres plugin).
3. Watch deploy logs for `Applying certificate_app.0004_certificate_qr_stamping... OK`.
4. Admin → site settings → set the default QR position once.
5. Create one certificate, print it, scan it with a phone.

## Local image test

```bash
docker build -t future-academy .
docker run --rm -e PORT=8080 -e SECRET_KEY=dev -p 8080:8080 future-academy
```

## Example homepage content (optional, one time)

Fills empty homepage sections (hero slides, services, courses, course
videos, reviews) with example records so admins can see each section's
shape. Never touches certificates, codes, contact messages or settings,
and skips any section that already has data.

Railway → service → **Shell** (or `railway run`):

```bash
python manage.py load_demo_content --dry-run   # preview, writes nothing
python manage.py load_demo_content             # create, hidden from the public site
```

Records are created **inactive**. In the admin, tick «نشط» on an item to
preview it on the site, then edit it with real content or delete it.
`--active` publishes everything at once (placeholder prices and reviews
would then be visible to visitors).

Data lives in `academy_app/demo_content/` (export of the local dev data).
