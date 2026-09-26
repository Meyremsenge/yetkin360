# code_diff.md — koordinator-dashboard-ucu

## Değiştirilen Dosyalar
- `backend/app/services/engagement.py` — `get_coordinator_dashboard(session, principal, institution_id)` eklendi (satır ~640-734)
- `backend/app/api/institutions.py` — `GET /institutions/{institution_id}/dashboard` route + `DashboardEngagementItem`/`DashboardSummary`/`DashboardResponse` Pydantic şemaları eklendi (satır ~336-387)

## Yeni Dosya
Yok.

## AC → Implementasyon
| AC | Nasıl karşılandı |
|---|---|
| AC-1 (happy path) | `get_coordinator_dashboard` iki `scoped_engagements` sorgusuyla (PENDING_APPROVAL/PENDING_EVALUATION) listeleri + sayaçları döndürür |
| AC-2 / AC-S1 (farklı kurum → 404) | `inst_uuid not in principal.institution_ids` → `ValueError` → route'ta 404 |
| AC-3 / AC-4 / AC-S2 (TALENT/ORG_MEMBER → 404) | `principal.kind not in ("COORDINATOR","INST_ADMIN")` → `ValueError` → 404 |
| AC-5 (boş liste → 200) | Sorgular 0 satır dönerse `summary` sıfır, listeler `[]`, hata yok |
| AC-6 (geçersiz UUID → 422) | Route imzasında `institution_id: uuid.UUID` — FastAPI path validasyonu handler'a girmeden 422 döner |
| AC-7 / AC-S3 (confidential karışık, cross-tenant sızıntı yok) | Sorgular `scoped_engagements()` (institution_ids filtresi) + `institution_id == inst_uuid` ile sınırlı; `confidential` alanı filtreye dahil değil (görünürlüğü etkilemiyor, atdd.md gereği) |
| AC-S4 (oturumsuz → 401) | Route'ta `principal.user_id is None` kontrolü, endpoint girişinde |

## Düzeltme (orkestratör review'unda bulundu, ayrı Haiku dispatch ile giderildi)
İlk implementasyon iki sorguda çıplak `select(Engagement)` kullanıyordu — CLAUDE.md kuralı "çıplak `select(Model)` yasak" ihlaliydi (institution scope zaten önceden doğrulandığı için pratikte güvenliydi ama proje kuralına aykırıydı). İkinci bir Haiku dispatch ile her iki sorgu da `scoped_engagements(session, principal)` üzerine kuruldu, `Read` ile doğrulandı.

## Kalan Sınırlamalar
- Yok — atdd.md'deki tüm AC'ler kapsandı.

## Varsayımlar
- Servis katmanında hem "yanlış rol" hem "yanlış kurum" hem "kurum yok" aynı `ValueError` ile temsil ediliyor, route'ta tek `except ValueError: 404`'e düşüyor — atdd.md'nin "boş sonuç ↔ hata ayrımı" kuralı bununla çelişmiyor çünkü ayrım zaten 200(boş liste) vs 404(erişim yok) seviyesinde, ValueError'ın kendi iç nedeni response'a sızmıyor (mesaj sızıntısı yok).

## CAVEMAN Self-Review
- Yeni dosya yok.
- Yeni soyutlama/yardımcı fonksiyon yok — tek servis fonksiyonu, mevcut `scoped_engagements`/`scoped_institutions`/`get_scoped_or_404` yeniden kullanıldı.
- Sayfalama/filtreleme/sıralama eklenmedi (kapsam dışı, atdd.md gereği).

## Test Durumu
Alt-ajan gerçek pytest çalıştıramadı (psycopg bağlantı sorunu bildirdi) — bu doğrulama **yapılmadı**, `verify` adımında gerçek test koşusu ile teyit edilmeli.
