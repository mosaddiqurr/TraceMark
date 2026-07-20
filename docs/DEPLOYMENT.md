# Deployment

The supported demonstration deployment is Docker Compose with Nginx, web, API, worker, PostgreSQL, Redis, MinIO, and bucket initialization services.

Copy '.env.example' to '.env'; replace passwords and generate high-entropy master/report keys; then run 'docker compose up --build'. Run migrations and seed only after readiness succeeds. Persistent database, Redis, and object data use named volumes.

For nonlocal deployment enable TLS and secure cookies, allow-list the exact public origin, disable interactive API docs if required, provide secret mounts rather than committed environment files, authenticate infrastructure services, back up PostgreSQL and object storage consistently, and set container CPU/memory limits.

Rollback application containers to the previous image while retaining schema-compatible migrations. Back up before irreversible migrations and object-retention changes.

