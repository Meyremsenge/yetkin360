# Entegrasyon Notu — YET-73/95/96/97 (PLAN 2.11) Engagement Frontend

**Durum: Backend GET uçları eksik olduğu için MOCK VERİYLE geliştirildi. Tam entegre DEĞİL.**

Bu görev Jira'da bana atanmıştı (YET-73 → YET-95/96/97), PLAN.md madde 2.11
("Frontend: engagement listesi + detay + durum geçiş aksiyonları"). Backend
tarafında (PLAN 2.1-2.6, `@be1`/`@be2` — bana ait değil) inceleme yapıldığında
şu uçların **henüz yazılmadığı** görüldü:

## Eksik backend uçları

| Uç | Durum | Nerede beklenir |
|---|---|---|
| `GET /engagements` (liste) | ❌ Yok | `backend/app/api/engagements.py` — şu an sadece `POST` uçları var |
| `GET /engagements/{id}` (detay, tasks+deliverables dahil) | ❌ Yok | `backend/app/api/engagements.py` |
| `POST /engagements/{id}/transitions` | ✅ Var | `backend/app/api/engagements.py:236` — gerçek engagement ID'leri için doğrudan kullanılıyor |

Ayrıca:

- `GET /me` yanıtı (`backend/app/api/me.py`) `principal.kind`/`role` bilgisini
  **döndürmüyor**. Bu yüzden frontend, durum geçiş butonlarını (`available_transitions`)
  role göre değil, **sadece durum bazlı** hesaplıyor (bkz. `availableTransitions()`
  fonksiyonu). Gerçek yetkilendirme sunucuda `POST /transitions` çağrısında
  uygulanıyor; kullanıcı yetkisizse sunucu `403 FORBIDDEN` döner ve arayüz bunu
  gösterir (bu, YET-97'nin "hata gösterimi (403)" gereksinimiyle örtüşüyor).

## Ne yapıldı

`frontend/lib/api/engagements.ts` içinde tek bir entegrasyon noktası oluşturuldu:

- `listEngagements()`, `getEngagement(id)` → şu an **mock store**'dan okuyor
  (`USE_MOCK_LIST` / `USE_MOCK_DETAIL` sabitleri `true`).
- `transitionEngagement(id, payload)` → **gerçek** engagement ID'leri için
  doğrudan gerçek backend ucuna (`POST /engagements/{id}/transitions`) gidiyor;
  mock listesindeki ID'ler için ise backend'deki durum makinesi kurallarının
  (`backend/app/services/engagement.py:257-292`) birebir kopyası olan bir
  simülasyon üzerinden çalışıyor (409/422/403 hata şekilleri backend ile aynı).

Ekranlar (`app/calismalar/page.tsx`, `app/calismalar/[id]/page.tsx`,
`app/calismalar/[id]/transition-actions.tsx`) sadece bu tek dosyayı
(`lib/api/engagements.ts`) import ediyor — mock/gerçek ayrımından habersiz.

## Backend GET uçları eklendiğinde yapılacaklar

`frontend/lib/api/engagements.ts` dosyasının başındaki yorum bloğu ve
"MOCK STORE" bölümü bunu adım adım anlatıyor, özet:

1. `USE_MOCK_LIST` ve `USE_MOCK_DETAIL` sabitlerini `false` yap.
2. `mockEngagements`, `findMock`, `toSummary` ve `transitionEngagement()`
   içindeki mock dallanmasını sil.
3. `availableTransitions()`/`isReasonRequired()` fonksiyonları **kalır** —
   bunlar backend'in durum makinesiyle eşleşen genel mantık, mock'a özel değil.
   Ancak `/me`'ye `principal.kind` eklenirse, bu fonksiyonlar role göre
   filtreleme yapacak şekilde genişletilebilir (şu an bilinçli olarak yapılmadı).
4. Gerçek `GET /engagements` ve `GET /engagements/{id}` response şemalarının
   burada tanımlı `EngagementSummary`/`EngagementDetail` tipleriyle eşleştiğini
   doğrula (alan adları özellikle: `organization_name` — backend'de bugün
   sadece `organization_id` var, response'a insan-okunur ad eklenmesi gerekebilir).

## Test durumu

- `lib/api/engagements.test.ts`: mock durum makinesi mantığı (transition table,
  version conflict, reason zorunluluğu) gerçek backend kurallarıyla birebir
  test edildi.
- `app/calismalar/page.test.tsx`, `app/calismalar/[id]/page.test.tsx`,
  `app/calismalar/[id]/transition-actions.test.tsx`: UI, `lib/api/engagements`
  modülünü mock'layarak test edildi (backend'in var/yok olmasından bağımsız).
- **Uçtan uca (gerçek backend ile) entegrasyon testi YAPILMADI** — çünkü
  gerçek uçlar yok. Bu görev bu haliyle **"tamamen entegre" sayılmamalı.**
