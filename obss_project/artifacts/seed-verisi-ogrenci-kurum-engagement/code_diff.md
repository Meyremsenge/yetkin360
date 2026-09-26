# Code Diff — seed-verisi-ogrenci-kurum-engagement
_Green step (code-copilot) — Haiku alt-ajanı tarafından yazıldı, orkestratör tarafından Read + gerçek pytest çalıştırmasıyla doğrulandı_

## Değiştirilen Dosya
- `backend/scripts/seed.py` — mevcut `seed_skills()` korunarak 3 yeni fonksiyon eklendi:
  - `seed_talents(session)` — 20 öğrenci (`ogrenciN@seed.local`), idempotent, ENVIRONMENT koruması
  - `seed_institutions_and_organizations(session)` — 5 kurum + 5 organizasyon (`kurumN-admin@seed.local` / `orgN-admin@seed.local`), idempotent, ENVIRONMENT koruması
  - `seed_engagements(session)` — 15 engagement, tam servis zinciriyle (`create_engagement` → `transition_engagement` ×3 → `create_engagement_task`+`create_deliverable` → `create_evaluation` → `create_attestation`) VERIFIED durumuna taşıyor, idempotent, ENVIRONMENT koruması
  - `if __name__ == "__main__":` bloğu genişletildi (tüm 4 seed fonksiyonu + rollback/commit)

## Doğrulama (orkestratör tarafından, sub-agent özetine güvenilmedi)
- `git status --short` ile dosyanın gerçekten değiştiği doğrulandı (714 satır).
- `ast.parse` ile sözdizimi geçerliliği doğrulandı.
- **Testler gerçekten çalıştırıldı** (sub-agent'ın "8 test geçecek" iddiasına ilk turda güvenilmedi, gerçekten koşturuldu): İlk çalıştırmada 6/8 geçti, 2 hata bulundu — **implementasyon değil test hatasıydı** (yanlış mock patch hedefi: `app.services.auth.register_user` yerine `scripts.seed.register_user` patch'lenmeliydi; `session.close()` DB bağlantı kaybını gerçekten simüle etmiyordu). Test dosyası 3. bir Haiku dispatch'iyle düzeltildi, **yeniden çalıştırıldı: 8/8 PASS** (gerçek PostgreSQL'e karşı, 28.4s).

## AC Kapsama (test koşumuyla teyit edildi)
| AC | Sonuç | Kanıt |
|---|---|---|
| AC-1 (happy path) | PASS | 20 öğrenci + 5 kurum + 5+ org + 15 VERIFIED engagement, gerçek DB'de sayıldı |
| AC-2 (idempotency) | PASS | İki kez çağrı, sayılar aynı |
| AC-3 (append-only zinciri) | PASS | Her VERIFIED engagement'ta ≥1 Attestation + ≥1 VerifiedExperience + AuditEvent (subject_type="ATTESTATION") |
| AC-4 (rollback) | PASS | `register_user`'ın 3. çağrısında `IntegrityError` enjekte edildi, gerçek `seed_talents()` hatayı yakalayıp state'i tutarlı bıraktı |
| AC-5 (production guard) | PASS | `settings.environment="production"` iken hiçbir kayıt oluşmadan hata |
| AC-6 (DB hatası) | PASS | `session.flush` mock'lanıp `OperationalError` enjekte edildi, anlamlı hata ile patladı |
| AC-7 (FK dağılımı) | PASS | 15 engagement, eşit olmayan dağılım, tüm FK'ler geçerli |

## Kalan Sınırlamalar
- `verify` adımında henüz çalıştırılmadı: `ruff check`, `mypy app`, tüm backend test paketi (regresyon kontrolü), `pytest tests/authorization -q` (bu görev yeni bir authz dalı eklemiyor ama proje kuralı gereği yine de kontrol edilmeli çünkü `app/services/*.py` dosyalarına dokunulmadı, sadece `scripts/seed.py` — düşük risk ama doğrulanmalı).
- Görsel/UI kriteri yok (backend CLI script'i).
