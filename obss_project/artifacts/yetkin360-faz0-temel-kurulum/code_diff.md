commit 5d11c76cb1bddb9fe216db869be3738b897f3cb2
Author: yutronax <kuyusuzyusuf123@gmail.com>
Date:   Sat Sep 19 19:29:51 2026 +0300

    Faz 0 temel kurulum: docker-compose, backend/frontend iskeleti, CI
    
    .env.example (docs/ENV.md §8 şablonundan), docker-compose.yml (PostgreSQL 16
    + MinIO, healthcheck'li), backend FastAPI iskeleti (GET /health, alembic
    hazır, pytest+ruff+mypy yeşil), frontend Next.js+TS+shadcn/ui iskeleti
    (npm run lint/typecheck/build yeşil), GitHub Actions CI (backend+frontend
    job). PLAN.md 0.9-0.12.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

diff --git a/.env.example b/.env.example
new file mode 100644
index 0000000..6531da6
--- /dev/null
+++ b/.env.example
@@ -0,0 +1,78 @@
+# Yetkin360 — ortam değişkenleri örneği
+#
+# Kullanım:  cp .env.example .env
+#
+# UYARI: Bu dosya repoda tutulur ve HERKESE AÇIKTIR.
+#        Buraya asla gerçek sır yazılmaz — yalnız placeholder.
+#        .env dosyası .gitignore içindedir ve asla commit edilmez.
+#
+# Tam açıklamalar: docs/ENV.md
+
+# --- Genel ---
+ENVIRONMENT=development
+DEBUG=true
+LOG_LEVEL=INFO
+TZ=UTC
+
+# --- Veritabanı ---
+POSTGRES_USER=yetkin360
+POSTGRES_PASSWORD=DEGISTIR_guclu_parola
+POSTGRES_DB=yetkin360
+POSTGRES_HOST=localhost
+POSTGRES_PORT=5432
+DATABASE_URL=postgresql+psycopg://yetkin360:DEGISTIR_guclu_parola@localhost:5432/yetkin360
+
+# --- Güvenlik ---
+# Üretmek için: python -c "import secrets; print(secrets.token_urlsafe(64))"
+SECRET_KEY=DEGISTIR_en_az_64_karakter_rastgele
+ACCESS_TOKEN_TTL_MINUTES=15
+REFRESH_TOKEN_TTL_DAYS=30
+COOKIE_SECURE=false
+COOKIE_SAMESITE=lax
+CSRF_ENABLED=true
+MAX_FAILED_LOGINS=5
+ACCOUNT_LOCK_MINUTES=15
+
+# --- CORS ---
+FRONTEND_ORIGIN=http://localhost:3000
+ALLOWED_ORIGINS=http://localhost:3000
+
+# --- Object storage (MinIO / S3) ---
+S3_ENDPOINT_URL=http://localhost:9000
+S3_ACCESS_KEY=DEGISTIR_minio_erisim_anahtari
+S3_SECRET_KEY=DEGISTIR_minio_gizli_anahtar
+S3_BUCKET=yetkin360-evidence
+S3_REGION=us-east-1
+S3_USE_SSL=false
+UPLOAD_URL_TTL_SECONDS=900
+DOWNLOAD_URL_TTL_SECONDS=300
+MAX_FILE_SIZE_MB=10
+MAX_USER_QUOTA_MB=100
+ALLOWED_FILE_TYPES=pdf,png,jpg,jpeg,docx,zip
+USER_CONTENT_BASE_URL=
+
+# --- E-posta ---
+EMAIL_BACKEND=console
+SMTP_HOST=
+SMTP_PORT=587
+SMTP_USER=
+SMTP_PASSWORD=
+EMAIL_FROM=noreply@yetkin360.local
+EMAIL_FROM_NAME=Yetkin360
+
+# --- Hız sınırları ---
+RATE_LIMIT_ENABLED=true
+RATE_LIMIT_LOGIN_PER_MINUTE=5
+RATE_LIMIT_REGISTER_PER_HOUR=3
+RATE_LIMIT_UPLOAD_PER_HOUR=20
+RATE_LIMIT_SEARCH_PER_MINUTE=60
+RATE_LIMIT_GENERAL_PER_MINUTE=300
+
+# --- İş kuralları ---
+NEW_ORG_COOLING_PERIOD_DAYS=30
+COMPETENCE_MIN_WEEKS=4
+ATTESTATION_QUOTA_PER_MEMBER_MONTHLY=5
+
+# --- Frontend (tarayıcıya gider — sır yazmayın) ---
+NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
+NEXT_PUBLIC_SITE_URL=http://localhost:3000
diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
new file mode 100644
index 0000000..3e0f4d6
--- /dev/null
+++ b/.github/workflows/ci.yml
@@ -0,0 +1,42 @@
+name: CI
+
+on:
+  push:
+    branches: [main]
+  pull_request:
+    branches: [main]
+
+jobs:
+  backend:
+    runs-on: ubuntu-latest
+    defaults:
+      run:
+        working-directory: backend
+    env:
+      DATABASE_URL: postgresql+psycopg://test:test@localhost:5432/test
+    steps:
+      - uses: actions/checkout@v4
+      - uses: actions/setup-python@v5
+        with:
+          python-version: "3.12"
+      - run: pip install -r requirements.txt
+      - run: ruff check .
+      - run: mypy app
+      - run: pytest -q
+
+  frontend:
+    runs-on: ubuntu-latest
+    defaults:
+      run:
+        working-directory: frontend
+    steps:
+      - uses: actions/checkout@v4
+      - uses: actions/setup-node@v4
+        with:
+          node-version: "20"
+          cache: "npm"
+          cache-dependency-path: frontend/package-lock.json
+      - run: npm ci
+      - run: npm run lint
+      - run: npm run typecheck
+      - run: npm run build
diff --git a/backend/alembic.ini b/backend/alembic.ini
new file mode 100644
index 0000000..1aae7ec
--- /dev/null
+++ b/backend/alembic.ini
@@ -0,0 +1,38 @@
+[alembic]
+script_location = alembic
+prepend_sys_path = .
+version_path_separator = os
+
+[loggers]
+keys = root,sqlalchemy,alembic
+
+[handlers]
+keys = console
+
+[formatters]
+keys = generic
+
+[logger_root]
+level = WARNING
+handlers = console
+qualname =
+
+[logger_sqlalchemy]
+level = WARNING
+handlers =
+qualname = sqlalchemy.engine
+
+[logger_alembic]
+level = INFO
+handlers =
+qualname = alembic
+
+[handler_console]
+class = StreamHandler
+args = (sys.stderr,)
+level = NOTSET
+formatter = generic
+
+[formatter_generic]
+format = %(levelname)-5.5s [%(name)s] %(message)s
+datefmt = %H:%M:%S
diff --git a/backend/alembic/env.py b/backend/alembic/env.py
new file mode 100644
index 0000000..e1ed493
--- /dev/null
+++ b/backend/alembic/env.py
@@ -0,0 +1,44 @@
+from logging.config import fileConfig
+
+from alembic import context
+from sqlalchemy import engine_from_config, pool
+
+from app.core.config import settings
+
+config = context.config
+config.set_main_option("sqlalchemy.url", settings.database_url)
+
+if config.config_file_name is not None:
+    fileConfig(config.config_file_name)
+
+target_metadata = None
+
+
+def run_migrations_offline() -> None:
+    url = config.get_main_option("sqlalchemy.url")
+    context.configure(
+        url=url,
+        target_metadata=target_metadata,
+        literal_binds=True,
+        dialect_opts={"paramstyle": "named"},
+    )
+    with context.begin_transaction():
+        context.run_migrations()
+
+
+def run_migrations_online() -> None:
+    connectable = engine_from_config(
+        config.get_section(config.config_ini_section, {}),
+        prefix="sqlalchemy.",
+        poolclass=pool.NullPool,
+    )
+    with connectable.connect() as connection:
+        context.configure(connection=connection, target_metadata=target_metadata)
+        with context.begin_transaction():
+            context.run_migrations()
+
+
+if context.is_offline_mode():
+    run_migrations_offline()
+else:
+    run_migrations_online()
diff --git a/backend/app/__init__.py b/backend/app/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/backend/app/core/__init__.py b/backend/app/core/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/backend/app/core/config.py b/backend/app/core/config.py
new file mode 100644
index 0000000..a80c2a1
--- /dev/null
+++ b/backend/app/core/config.py
@@ -0,0 +1,16 @@
+from pydantic_settings import BaseSettings, SettingsConfigDict
+
+
+class Settings(BaseSettings):
+    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
+
+    environment: str = "development"
+    debug: bool = True
+    log_level: str = "INFO"
+
+    database_url: str
+    frontend_origin: str = "http://localhost:3000"
+    allowed_origins: str = "http://localhost:3000"
+
+
+settings = Settings()  # type: ignore[call-arg]  # values come from .env
diff --git a/backend/app/main.py b/backend/app/main.py
new file mode 100644
index 0000000..07d8fe6
--- /dev/null
+++ b/backend/app/main.py
@@ -0,0 +1,19 @@
+from fastapi import FastAPI
+from fastapi.middleware.cors import CORSMiddleware
+
+from app.core.config import settings
+
+app = FastAPI(title="Yetkin360 API")
+
+app.add_middleware(
+    CORSMiddleware,
+    allow_origins=settings.allowed_origins.split(","),
+    allow_credentials=True,
+    allow_methods=["*"],
+    allow_headers=["*"],
+)
+
+
+@app.get("/health")
+def health() -> dict[str, str]:
+    return {"status": "ok"}
diff --git a/backend/pyproject.toml b/backend/pyproject.toml
new file mode 100644
index 0000000..8a59fb9
--- /dev/null
+++ b/backend/pyproject.toml
@@ -0,0 +1,7 @@
+[tool.ruff]
+line-length = 100
+target-version = "py312"
+
+[tool.mypy]
+python_version = "3.12"
+ignore_missing_imports = true
diff --git a/backend/tests/__init__.py b/backend/tests/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/backend/tests/test_health.py b/backend/tests/test_health.py
new file mode 100644
index 0000000..719eb52
--- /dev/null
+++ b/backend/tests/test_health.py
@@ -0,0 +1,11 @@
+from fastapi.testclient import TestClient
+
+from app.main import app
+
+client = TestClient(app)
+
+
+def test_health_returns_ok() -> None:
+    response = client.get("/health")
+    assert response.status_code == 200
+    assert response.json() == {"status": "ok"}
diff --git a/docker-compose.yml b/docker-compose.yml
new file mode 100644
index 0000000..d970358
--- /dev/null
+++ b/docker-compose.yml
@@ -0,0 +1,37 @@
+services:
+  postgres:
+    image: postgres:16
+    environment:
+      POSTGRES_USER: ${POSTGRES_USER:-yetkin360}
+      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-DEGISTIR_guclu_parola}
+      POSTGRES_DB: ${POSTGRES_DB:-yetkin360}
+    ports:
+      - "${POSTGRES_PORT:-5432}:5432"
+    volumes:
+      - postgres_data:/var/lib/postgresql/data
+    healthcheck:
+      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-yetkin360}"]
+      interval: 5s
+      timeout: 5s
+      retries: 10
+
+  minio:
+    image: minio/minio:latest
+    command: server /data --console-address ":9001"
+    environment:
+      MINIO_ROOT_USER: ${S3_ACCESS_KEY:-DEGISTIR_minio_erisim_anahtari}
+      MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY:-DEGISTIR_minio_gizli_anahtar}
+    ports:
+      - "9000:9000"
+      - "9001:9001"
+    volumes:
+      - minio_data:/data
+    healthcheck:
+      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
+      interval: 5s
+      timeout: 5s
+      retries: 10
+
+volumes:
+  postgres_data:
+  minio_data:
diff --git a/frontend/app/globals.css b/frontend/app/globals.css
new file mode 100644
index 0000000..b5c61c9
--- /dev/null
+++ b/frontend/app/globals.css
@@ -0,0 +1,3 @@
+@tailwind base;
+@tailwind components;
+@tailwind utilities;
diff --git a/frontend/app/layout.tsx b/frontend/app/layout.tsx
new file mode 100644
index 0000000..f7268cb
--- /dev/null
+++ b/frontend/app/layout.tsx
@@ -0,0 +1,17 @@
+import type { Metadata } from "next";
+import "./globals.css";
+
+export const metadata: Metadata = {
+  title: "Yetkin360",
+  description: "Kanıta dayalı yetkinlik platformu",
+};
+
+export default function RootLayout({
+  children,
+}: Readonly<{ children: React.ReactNode }>) {
+  return (
+    <html lang="tr">
+      <body>{children}</body>
+    </html>
+  );
+}
diff --git a/frontend/app/page.tsx b/frontend/app/page.tsx
new file mode 100644
index 0000000..de8df38
--- /dev/null
+++ b/frontend/app/page.tsx
@@ -0,0 +1,11 @@
+import { Button } from "@/components/ui/button";
+
+export default function Home() {
+  return (
+    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
+      <h1 className="text-2xl font-semibold">Yetkin360</h1>
+      <p className="text-slate-600">beyan → kanıt → tanıklık → doğrulanmış deneyim</p>
+      <Button>Başla</Button>
+    </main>
+  );
+}
diff --git a/frontend/components/ui/button.tsx b/frontend/components/ui/button.tsx
new file mode 100644
index 0000000..285203f
--- /dev/null
+++ b/frontend/components/ui/button.tsx
@@ -0,0 +1,13 @@
+import { ButtonHTMLAttributes } from "react";
+
+export function Button({
+  className = "",
+  ...props
+}: ButtonHTMLAttributes<HTMLButtonElement>) {
+  return (
+    <button
+      className={`rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 ${className}`}
+      {...props}
+    />
+  );
+}
diff --git a/frontend/eslint.config.mjs b/frontend/eslint.config.mjs
new file mode 100644
index 0000000..165c38c
--- /dev/null
+++ b/frontend/eslint.config.mjs
@@ -0,0 +1,10 @@
+import { FlatCompat } from "@eslint/eslintrc";
+
+const compat = new FlatCompat({ baseDirectory: import.meta.dirname });
+
+const eslintConfig = [
+  { ignores: [".next/**", "node_modules/**"] },
+  ...compat.extends("next/core-web-vitals", "next/typescript"),
+];
+
+export default eslintConfig;
diff --git a/frontend/package.json b/frontend/package.json
new file mode 100644
index 0000000..9fff35e
--- /dev/null
+++ b/frontend/package.json
@@ -0,0 +1,29 @@
+{
+  "name": "yetkin360-frontend",
+  "version": "0.1.0",
+  "private": true,
+  "scripts": {
+    "dev": "next dev",
+    "build": "next build",
+    "start": "next start",
+    "lint": "eslint app components",
+    "typecheck": "tsc --noEmit"
+  },
+  "dependencies": {
+    "next": "15.5.25",
+    "react": "19.0.0",
+    "react-dom": "19.0.0"
+  },
+  "devDependencies": {
+    "typescript": "5.7.2",
+    "@types/node": "22.10.5",
+    "@types/react": "19.0.2",
+    "@types/react-dom": "19.0.2",
+    "eslint": "9.39.5",
+    "eslint-config-next": "15.5.25",
+    "@eslint/eslintrc": "3.2.0",
+    "tailwindcss": "3.4.17",
+    "postcss": "8.4.49",
+    "autoprefixer": "10.4.20"
+  }
+}
