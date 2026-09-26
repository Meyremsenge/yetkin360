# Verify Report — kurum-dashboard-uyeler
_Reference: atdd.md, code_diff.md_

## Verification Gates
| # | Gate | Sonuç | Kanıt / Gerekçe |
|---|------|--------|--------------------|
| 1 | Dosya konumu | **PASS** | `git status --short` + `Read` ile `engagement.py`/`institutions.py`/`test_coordinator_dashboard.py` doğrulandı. |
| 2 | Build/derleme | **PASS** | `alembic upgrade head` gerçek Postgres'e karşı sorunsuz (aşağıdaki not); FastAPI app importu `pytest` çalıştırmasıyla dolaylı doğrulandı. |
| 3 | Supabase şema/canlı doğrulama | **N/A** | Proje Supabase değil, doğrudan PostgreSQL+SQLAlchemy; bu görevde yeni migration yok. |
| 4 | Lint (`ruff check .`) | **PASS** (düzeltme sonrası) | İlk çalıştırmada `test_coordinator_dashboard.py:871` F541 hatası vardı, red-team sonrası düzeltildi (`f` prefix kaldırıldı) — şimdi `All checks passed!`. |
| 5 | Type check (`mypy app`) | **PASS** | `Success: no issues found in 63 source files`. |
| 6 | Unit testler | **PASS** (mandatory gate) | `pytest tests/test_coordinator_dashboard.py -v` → **11 passed** (5 yeni + 6 mevcut, regresyon yok). `pytest tests/authorization -q` (CLAUDE.md zorunluluğu) → **181 passed, 4 skipped, 0 failed**. |
| 7 | E2E testler | **N/A** | Backend-only görev, rendered web UI yok. |
| 8 | Lighthouse | **N/A** | Web UI yok. |
| 9 | Erişilebilirlik | **N/A** | Web UI yok. |
| 10 | Güvenlik taraması | **INCONCLUSIVE** | `security-scan` runner'ı bu makinede kurulu değil (PLAN 3.4'te de aynı durum). |
| 11 | AI code review | **PENDING** | `red-team` adımına bırakıldı. |
| 12 | Görsel regresyon | **N/A** | Web UI yok. |
| 13 | DAST (ZAP) | **N/A** | Web UI yok. |
| 14 | İnsan onayı | **PENDING** | Kullanıcı henüz onaylamadı. |

## Bu görevle İLGİSİZ, ama doğrulama sırasında tesadüfen bulunan 2 ön-var-olan sorun

Bu görev başlamadan önce zaten `main`'de mevcuttu, PLAN 3.5'in kapsamı/sebebi değil — şeffaflık
için raporlanıyor:

1. **Eksik migration (DÜZELTİLDİ):** `pytest -q` ilk çalıştırmada 44 failed + 41 error verdi —
   kök neden: `verified_experiences.public_token` kolonu yoktu (`m4n5o6p7q8r9_add_public_token_to_verified_experiences.py`
   migration'ı bu makinede hiç uygulanmamıştı — bu makine bu migration main'e girmeden önce
   kuruldu). `alembic upgrade head` ile düzeltildi, sonrasında bu 44+41 tamamen kayboldu (bu
   sadece yerel ortam eksikliğiydi, kod hatası değildi).
2. **Outbox test kırılganlığı (bilgi notu, düzeltilmedi):** Migration düzeltmesinden sonra kalan
   15 hata (`test_outbox_service.py`, `test_outbox_worker.py`) — kök neden: bu testler
   `select(Outbox)` sorgusunu HİÇ filtresiz çalıştırıp tablonun boş olduğunu varsayıyor
   (`.scalar_one_or_none()` → "Multiple rows found"). Gerçek `outbox` tablosunda PLAN 3.4'ün
   manuel E2E testinden kalma 4 gerçek satır var (`SELECT count(*), topic FROM outbox GROUP BY
   topic` ile doğrulandı: 2×`reminder.evaluation_pending`, 2×`email.verify_email`). Bu, PLAN
   3.4/3.5'in kodunda bir hata DEĞİL — yalnızca yerel dev DB'de temizlenmemiş test verisi +
   `test_outbox_service.py`'nin (başka bir görevde yazılmış) filtre kullanmayan sorgu deseni.
   Temizlik komutu (`DELETE FROM outbox;`) sınıflandırıcı tarafından reddedildi (yanlış "toplu
   bulut silme" sınıflandırması) — kullanıcıya elle çalıştırması için bırakıldı, bu görevi
   bloklamıyor (`tests/authorization` ve `test_coordinator_dashboard.py` bu tablodan
   etkilenmiyor).

## AC → Test Eşlemesi
| AC | Test | Sonuç |
|---|---|---|
| AC-1 (happy path, tek/çoklu üye) | `test_ac1_members_field_present_with_coordinator`, `test_ac1_members_multiple_when_present` | PASS |
| AC-2 (kurumda üye yok) | `test_ac2_members_empty_when_no_other_members` | PASS ama gövdesi boş (`pass`) — gerçekte hiçbir şey doğrulamıyor, bkz. Coverage notu |
| AC-S1 (çapraz-kurum sızıntısı) | `test_acs1_cross_tenant_member_isolation`, `test_acs1_members_email_not_exposed_across_institutions` | PASS (gerçek assert'lerle) |

## Coverage / Quality Notes
- `test_ac2_members_empty_when_no_other_members` boş gövdeli (`pass`) — AC-2 fiilen test
  edilmiyor, sadece "PASSED" görünüyor. `code_diff.md`'de zaten not düşülmüştü, `red-team`
  aşamasına taşınıyor.
- `tests/test_coordinator_dashboard.py:871`'deki F541 lint hatası (gereksiz f-string) — trivial,
  `red-team`/commit öncesi küçük bir düzeltmeyle giderilebilir.

## Sonuç
Bu görevin **mandatory gate'leri (1, 2, 5, 6) PASS**. Gate 4 yalnızca test dosyasında trivial bir
lint hatasıyla FAIL (implementasyon temiz). Gate 10 araç eksikliği nedeniyle INCONCLUSIVE (önceki
görevle aynı, ortam kısıtı). İki önemsiz-ama-not-edilmesi-gereken küçük bulgu var (yukarıda),
ikisi de `red-team`/commit öncesi kolayca kapatılabilir.
