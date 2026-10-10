# authz-test — ogrenci-profili-hakkimda-sertifika

Tarih: 2026-10-10 · Kaynak: `/talents/me/portfolio-items` (GET/POST/PATCH/DELETE), `PATCH /talents/me` (about), `GET /public/talents/{slug}` (about, certificates)

Not: Bu görev boru hattı (pipeline) dışında yürütüldü; testleri `test-copilot` değil ana ajan yazdı. Hiçbiri mock kullanmıyor — gerçek PostgreSQL + FastAPI TestClient.

## Matris

| # | Aktör | Beklenen | Otomatik test | Canlı sonda (dev, 8011) | Sonuç |
|---|---|---|---|---|---|
| 1 | Sahibi (A) | 200/201 + kendi verisi | `test_owner_creates_lists_updates_and_deletes` | POST 201, GET 200 | PASS |
| 2 | Başka öğrenci (B) | 404, gövdede A'nın alanı yok | `test_other_talent_cannot_update_or_delete`, `test_other_talent_items_not_listed`, `test_foreign_and_unknown_ids_are_indistinguishable` | B listesinde A kaydı yok; PATCH/DELETE 404 `PORTFOLIO_ITEM_NOT_FOUND` | PASS |
| 3 | Kimliksiz | 401 | `test_unauthenticated_is_rejected` (GET, POST) | GET 401, PATCH 401 | PASS |
| 4 | Bozuk token | 401 | — (mevcut auth paketi kapsıyor) | GET 401 "Oturum geçersiz" | PASS (canlı) |
| 5 | Yükseltme (`talent_id`, `badge`, `decision`, `evidence_id` gövdede) | Yok sayılır | `test_talent_id_in_body_is_ignored`, `test_client_cannot_forge_badge_or_relink_evidence` | 201, kayıt oturum sahibine | PASS |
| 6 | Başkasının id'siyle yazma/silme + son durum | 404 ve veri değişmemiş | `test_other_talent_cannot_update_or_delete` (refresh ile) | B denemelerinden sonra A kaydı: başlık ve rıza aynı | PASS |
| — | Başkasının kanıtını bağlama | 404, satır yok | `test_cannot_link_someone_elses_evidence` | — | PASS |
| — | Rozet ödünç alma | Kendi beyanı | `test_badge_cannot_be_borrowed_from_foreign_evidence` | — | PASS |
| — | Rıza kapalıyken public | Görünmez | `test_public_lists_only_consented_items` | Rıza kapalı kayıt public yanıtta yok | PASS |
| — | CSRF'siz yazma | 403 `CSRF_FAILED` (belgelenmiş istisna) | mevcut paket | 403 | PASS |

## "Boş liste" kuralı
`GET /talents/me/portfolio-items` talent profili olmayan kullanıcıya `200 + {items: [], engagement_certificates: []}` döner. Bu bir id taşımayan `/me` ucu: filtrelenen başkasının verisi değil, aktörün sahip olduğu küme boş. Mevcut `GET /evidence` ile aynı sözleşme. Yazma uçları (POST/PATCH/DELETE) aynı aktöre 404 döner — `test_talentless_user`.

## Eksik
- Satır 4 için bu uçlara özel otomatik test yok (canlı sonda + genel auth paketi kapsıyor).
- Satır 3: kapatıldı — `test_unauthenticated_is_rejected` artık PATCH/DELETE da kapsıyor.

## Yan etki
Sonda dev DB'de iki kayıt oluşturdu ve soft delete ile kaldırdı (`SONDA-A`, `SONDA-B`; `deleted_at` dolu, public'te görünmez).

## Paket
`pytest tests/authorization -q` → 976 passed, 9 skipped (skip'ler önceden var).
