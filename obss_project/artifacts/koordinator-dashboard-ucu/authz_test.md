# authz-test — koordinator-dashboard-ucu

Kaynak: `atdd.md` AC-S1–AC-S4 (threat-model tarafından üretildi).
Uç: `GET /institutions/{institution_id}/dashboard` — GET-only, yazma yok.

## Test Matrisi (test-copilot'a extra_instructions olarak verilecek)

| # | Aktör | İstek | Beklenen | AC |
|---|---|---|---|---|
| 1 | A = COORDINATOR, kurum X üyesi, X'te 3 PENDING_APPROVAL + 7 PENDING_EVALUATION var | `GET /institutions/{X}/dashboard` | 200 + `summary.pending_approval==3`, `summary.pending_evaluation==7`, listelerde SADECE X'in kayıtları | AC-1 |
| 2 | B = COORDINATOR, kurum Y üyesi (X üyesi DEĞİL) | `GET /institutions/{X}/dashboard` | **404**, gövdede X'in hiçbir engagement alanı yok (id, talent_id, title dahil hiçbiri) | AC-2 / AC-S1 |
| 3 | C = TALENT (herhangi bir kurumla ilişkisiz veya X'in öğrencisi olsa bile) | `GET /institutions/{X}/dashboard` | **404** (403 değil) | AC-3 / AC-S2 |
| 4 | D = ORG_MEMBER (X ile aktif engagement'ı olsa bile) | `GET /institutions/{X}/dashboard` | **404** | AC-3 / AC-S2 |
| 5 | Anon / oturumsuz (cookie yok) | `GET /institutions/{X}/dashboard` | **401** | AC-4 / AC-S4 |
| 6 | Süresi geçmiş/bozuk JWT cookie | `GET /institutions/{X}/dashboard` | **401** — mevcut `get_current_principal` middleware testleriyle aynı, bu görev için yeni bir davranış değil, sadece bu uçta da tekrar doğrulanır | AC-4 |
| 7 | A = COORDINATOR, X'te `confidential=true` VE `confidential=false` engagement'lar karışık | `GET /institutions/{X}/dashboard` | Her ikisi de listelenir (confidential sadece Evidence görünürlüğünü etkiler, dashboard'u değil) AMA başka kurumun (Y) hiçbir kaydı sızmaz | AC-7 / AC-S3 |
| 8 | A = COORDINATOR, X'te hiç engagement yok | `GET /institutions/{X}/dashboard` | 200 + boş listeler + sıfır sayaçlar (404 DEĞİL — "veri yok" ile "yetkin yok" ayrımı) | AC-5 |

### Uygulanmayan satırlar (matris şablonundan, gerekçeli silindi)
- **Rol yükseltme denemesi (`role: admin` body'de)**: N/A — bu bir GET uç, request body yok, tek girdi `institution_id` path param'ı (zaten satır 2-4'te test ediliyor).
- **Başkasının id'siyle yazma/silme**: N/A — endpoint hiçbir DB yazması yapmıyor (atdd.md Davranış Sözleşmesi: "Kısmi başarı: Uygulanmaz").

### Kritik kural (test-copilot'a aktarılacak)
- Satır 2/3/4: **boş liste `200 + {"pending_approval": [], ...}` DEĞİL, 404 olmalı.** Boş liste ile "erişimin yok" karıştırılırsa bu tam da bu skill'in uyardığı sessiz-sızıntı riskidir (politika değişirse fark edilmeden veri sızmaya başlar). Test, durum kodunu VE gövdenin X'e ait hiçbir alan içermediğini ayrı ayrı assert etmeli.
- Satır 7: yazma testi olmadığı için "son durumu doğrula" kuralı uygulanmaz; onun yerine **yanıt gövdesinin tam içeriği** (Y'nin hiçbir kaydının bulunmadığı) doğrulanmalı.
- Mock yasak: bu testler gerçek test DB'sine karşı (proje `pytest tests/authorization`/`tests/test_institution_authorization.py` deseni) çalışmalı, `scoped_engagements`/`get_current_principal` mock'lanmamalı.

## Canlı Sonda
**Yapılmadı — bu adımda uç henüz kodlanmadı.** `code-copilot` bittikten ve
`verify` yeşil olduktan sonra, kullanıcı test/geliştirme ortamını onaylarsa
satır 2 ve 3 (farklı kurum + yetkisiz rol) gerçek bir HTTP isteğiyle tekrar
doğrulanmalı — bu ATDD adımının hemen sonrasında endpoint yokken canlı sonda
atılamaz. **Eksik**, "uygulanmadı" değil — sonraki `verify` adımında hatırlanmalı.

## Supabase notu
Bu proje PostgreSQL + SQLAlchemy kullanıyor, Supabase/RLS yok (final-analiz
§15.2: RLS bilinçli olarak MVP'de ertelendi) — bu bölüm N/A.
