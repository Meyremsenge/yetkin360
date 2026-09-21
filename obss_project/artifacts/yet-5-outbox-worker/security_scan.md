# security_scan.md — yet-5-outbox-worker

## Sonuç: INCONCLUSIVE (araç eksik)

`security-scan` skill'inin gerektirdiği araç seti bu makinede kurulu değil:
`~/.claude/security-tools/venv` ve `~/.claude/skills/security-scan/scan.py`
mevcut değil (`ls` ile doğrulandı, `No such file or directory`).

Bu, **PASS değildir** — "bilinen imza taraması yapılamadı" anlamına gelir,
"açık yok" anlamına gelmez.

## Gerekli kurulum (kullanıcı onayı gerektirir — bağımlılık ekleme)
`~/.claude/security-tools/venv` içinde `bandit`, `detect-secrets`,
`pip-audit` kurulu bir sanal ortam ve `~/.claude/skills/security-scan/scan.py`
dosyası gerekiyor. Bu, proje bağımlılığı değil, harness-seviyesi bir araç
kurulumu — CLAUDE.md'nin "bağımlılık ekleme" onay kategorisine girmeyebilir
(proje repo'suna değil, kullanıcı ortamına ekleniyor) ama yine de kullanıcıya
bildirilmesi gereken bir eksiklik.

## Kapsam (eğer araç kurulu olsaydı taranacak dosyalar)
- backend/alembic/versions/7c5d3a1b2f4e_add_outbox_table.py
- backend/app/models/outbox.py
- backend/app/services/outbox.py
- backend/app/workers/__init__.py
- backend/app/workers/outbox_worker.py
- backend/app/models/__init__.py
- backend/app/services/auth.py
- backend/app/core/config.py
- backend/tests/test_outbox_service.py
- backend/tests/test_outbox_worker.py
- backend/tests/test_migration.py

## Manuel gözlem (araç değil, orkestratörün kendi okuması — resmi tarama yerine geçmez)
- `.env`'den okunan değerler (`database_url`, `secret_key`) hiçbir yeni
  dosyada loglanmıyor veya hardcode edilmiyor — `config.py`'deki 3 yeni alan
  (`outbox_poll_interval_seconds`, `outbox_max_attempts`, `email_backend`)
  hepsi varsayılan değerli, sır değil.
- `outbox_worker.py`'deki `logger.error(...)` çağrısı sadece `outbox_id`,
  `topic`, `error_type`, `error_message` basıyor — `row.payload` doğrudan
  loglanmıyor (code_diff.md'de not edilen sınır durum hariç: handler'ın
  kendi exception mesajı payload içeriğini tekrarlarsa sızabilir).
- Migration dosyasında ham SQL yok, `op.create_table`/`op.create_index`
  kullanılmış (CLAUDE.md kuralına uygun).

Bu manuel gözlem **bandit/detect-secrets/pip-audit'in yerini tutmaz** —
sadece "araç yokken hiçbir şey görülmedi" demekten kaçınmak için yapıldı.
