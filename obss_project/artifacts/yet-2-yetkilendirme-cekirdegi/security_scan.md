# Security Scan — yet-2-yetkilendirme-cekirdegi

Kapsam: bu görevde değişen 7 dosya (`backend/app/services/authorization.py`, `backend/app/services/audit.py`, `backend/app/models/audit.py`, `backend/alembic/versions/a1b2c3d4e5f6_...py`, `backend/app/models/__init__.py`, `backend/tests/test_authorization.py`, `backend/tests/test_audit_events.py`).

| Gate | Sonuç | Gerekçe |
|---|---|---|
| secrets (detect-secrets) | **PASS** (4 bulgu incelenip baseline'a yazıldı) | İlk taramada 4 bulgu: migration'daki revizyon ID'si (`a1b2c3d4e5f6`, hex-entropy false positive) + test dosyasındaki 3 "Secret Keyword" (`{"password": "secret123"}`, `{"password_hash": "bcrypt$2b$12$..."}`, nested `password` — bunlar AC-S6'nın PII-guard'ının REDDETMESİ gereken kasıtlı test verileri, gerçek sır değil). Tek tek Read edilerek doğrulandı, gerçek kimlik bilgisi yok. |
| python_sast (bandit) | **PASS** | 0 bulgu |
| python_deps (pip-audit) | N/A | `--files` kapsamına `requirements.txt` dahil edilmedi (bu görev yeni bağımlılık eklemedi, sadece `uuid6`/`psycopg` gibi zaten YET-1'de eklenmiş paketleri kullanıyor) |
| node_deps (npm audit) | N/A | Bu görev backend-only, `package.json` kapsamda değil |

**Verdict: PASS**

Not: Bu tarama bilinen imza taraması yapar (sızmış sır, bandit kuralları) — iş mantığı açıklarını (IDOR, tenant sızıntısı) kapsamaz, onlar `red-team` ve `authz-test`'in işi (ayrıca yapıldı, bkz. atdd.md Threat Model bölümü).
