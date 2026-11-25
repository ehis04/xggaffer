# Deployment guide

The supported production path is Docker Compose on a small Linux host. This is
the simplest low-cost layout for the application because the API, PostgreSQL,
Redis, background jobs, and the large prediction datasets need persistent
storage. Caddy obtains and renews HTTPS certificates automatically.

## Host prerequisites

- A Linux host with Docker Engine and the Compose plugin
- DNS `A`/`AAAA` records for `xggaffer.site` and `www.xggaffer.site` pointing to
  the host
- Inbound TCP ports 80 and 443, plus UDP 443, open
- Enough disk for the database, uploads, and prediction data (the current data
  bundle is approximately 3.6 GB)

## Hosting size and cost

Avoid free application platforms that sleep, provide only a few hundred MB of
memory, or do not offer persistent disks. This deployment runs PostgreSQL,
Redis, Django, Caddy, and prediction models on one machine.

- Oracle Cloud Always Free Ampere is the preferred zero-cost starting point
  when capacity is available. Its free allocation is sufficient for this
  stack, but account creation and regional capacity can be unreliable, and
  Oracle may reclaim very idle free instances.
- For a paid fallback, use an x86-64 VPS with at least 2 vCPU, 4 GB RAM, and
  40 GB disk. Budget roughly EUR 5-10 per month from a low-cost VPS provider.
- Mainstream providers commonly charge around USD 20-30 per month for a 4 GB
  instance. Splitting the app across paid web, database, Redis, and disk
  services is normally more expensive than a single VPS.

Provider prices change, so confirm the checkout total and tax before creating
the server. Keep background workers disabled initially to reduce load.

## Transfer prediction data from Windows

The cloud coding workspace cannot see files on the local laptop. Transfer the
data directly to the server instead. From PowerShell, create an archive (adjust
the path if the project is on a different drive):

```powershell
cd $HOME\projects\xgGaffer
tar -czf xggaffer-data.tar.gz src\data
scp -i $key .\xggaffer-data.tar.gz ubuntu@SERVER_IP:~/
```

On the server:

```sh
sudo mkdir -p /srv/xggaffer-data
sudo tar --no-same-owner -xzf ~/xggaffer-data.tar.gz -C /srv/xggaffer-data --strip-components=2
```

Set `DATA_HOST_PATH=/srv/xggaffer-data` in `.env.staging`. The production
containers mount this directory read/write at `/app/data`; the bundle never
needs to be committed to GitHub or copied into a Docker volume.

## First deployment

```sh
cp .env.staging.example .env.staging
# Replace SECRET_KEY and POSTGRES_PASSWORD, then configure optional API keys.
./scripts/preflight.sh
docker compose --env-file .env.staging -f docker-compose.staging.yml build
# Give the backend user ownership of the mounted data directory.
docker compose --env-file .env.staging -f docker-compose.staging.yml run --rm --no-deps --user root backend \
  sh -c 'chown -R "$(id -u xggaffer):$(id -g xggaffer)" /app/data'
docker compose --env-file .env.staging -f docker-compose.staging.yml up -d
docker compose --env-file .env.staging -f docker-compose.staging.yml ps
./scripts/smoke-test.sh
```

Generate a secret with `openssl rand -base64 48`. Use a URL-safe database
password because it is embedded in `DATABASE_URL`.

Run `CHECK_DNS=true ./scripts/preflight.sh` after changing DNS to verify both
hostnames resolve. The preflight also rejects placeholders, checks the domain
security settings, validates both Compose profiles, and checks available disk
space.

The deployment exposes:

- `https://xggaffer.site/health/live/` for process liveness
- `https://xggaffer.site/health/ready/` for database and cache readiness

## Prediction data

The backend reads datasets and model artifacts from `/app/data`, backed by the
host directory configured in `DATA_HOST_PATH`. Validate it after the first
startup:

```sh
docker compose --env-file .env.staging -f docker-compose.staging.yml exec backend python manage.py check_prediction_assets --strict
docker compose --env-file .env.staging -f docker-compose.staging.yml restart backend
# If the background profile is enabled:
docker compose --profile background --env-file .env.staging -f docker-compose.staging.yml restart celery_worker
```

Do not commit the data bundle to Git. Back up the `postgres_data` and
`backend_media` volumes and the `DATA_HOST_PATH` directory separately.

## Updates

```sh
git pull --ff-only
docker compose --env-file .env.staging -f docker-compose.staging.yml build
docker compose --env-file .env.staging -f docker-compose.staging.yml up -d
```

The one-shot `migrate` service applies migrations and collects static files
before the web and worker services start.

## Lower-cost feature set

Background workers are optional and do not start in the default low-cost
deployment. Enable scheduled imports and asynchronous jobs with the
`background` profile:

```sh
docker compose --profile background --env-file .env.staging -f docker-compose.staging.yml up -d
```

Without this profile the web application remains available, but imports,
cleanup jobs, and other background work do not run. A split free-tier
deployment is possible only if the chosen providers offer persistent
PostgreSQL, Redis, and sufficient model storage; verify their current limits
before relying on it.

## Backups and restore

Create a timestamped database and media backup with:

```sh
./scripts/backup.sh
```

Prediction data is large and usually comes from a separate source bundle. To
include it in an occasional full backup, run `INCLUDE_DATA=true
./scripts/backup.sh`. Copy completed backup directories off the server; a
backup on the same disk does not protect against host or disk loss.

For daily database/media backups at 03:15 UTC, add this entry with `crontab -e`
on the host and replace the repository path:

```cron
15 3 * * * cd /srv/xggaffer && ./scripts/backup.sh >> /var/log/xggaffer-backup.log 2>&1
```

Container logs are rotated automatically at three 10 MB files per service.

Restore is intentionally guarded because it replaces the database:

```sh
./scripts/restore.sh --confirm /absolute/path/to/backups/20261124T120000Z
./scripts/smoke-test.sh
```

The media and prediction archives are overlaid onto their volumes. Files added
after the backup are not deleted automatically.
