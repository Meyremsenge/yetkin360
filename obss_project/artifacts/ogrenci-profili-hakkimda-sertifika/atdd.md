---
task_slug: ogrenci-profili-hakkimda-sertifika
jira_id: null
saga_task_id: null
threat_model: done
priority: high
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 30
  integration: 60
  e2e: 10
affected_modules:
  - backend/app/models/portfolio_item.py
  - backend/app/models/identity.py
  - backend/alembic/versions/a7c3e9d1f2b4_talent_about_ve_portfolio_items.py
  - backend/app/services/authorization.py
  - backend/app/services/portfolio.py
  - backend/app/services/public_profile.py
  - backend/app/api/portfolio_items.py
  - backend/app/api/me.py
  - backend/app/api/public.py
  - frontend/app/profil/*
  - frontend/app/p/[slug]/*
---

# ATDD — Öğrenci profili: "Hakkımda" + sertifika/çalışma vitrini

Kaynak: `docs/sonraki-oturum-promptlari.md` §2 · Tasarım: `docs/arastirma-ogrenci-profili.md` (onaylı: model A, 1000 karakter, alan adı görünür link).

## Persona / Hedef
Öğrenci kendini kısaca anlatır ve çalışma dışı sertifika/çalışmalarını ekler; jüri ve işverenler public profilde **doğrulanmış** ile **kendi beyanını** karıştırmadan görür.

## Kabul kriterleri

### "Hakkımda"
- AC-1: `PATCH /talents/me {"about": "..."}` en fazla 1000 karakter kaydeder; 1001 → 422; yalnız boşluk → `null`. DB CHECK aynı sınırı uygular.
- AC-2: `about` yalnız profil `PUBLIC` iken `/public/talents/{slug}` yanıtında çıkar; değilse yanıt 404.

### Vitrin kayıtları
- AC-3: Sahibi `GET/POST/PATCH/DELETE /talents/me/portfolio-items` ile kendi kayıtlarını yönetir; `show_on_profile` varsayılan `false`; silme soft delete, bağlı kanıt dosyasına dokunmaz.
- AC-4: Public profil yalnız `show_on_profile=true` ve silinmemiş kayıtları listeler; onaylılar önce.
- AC-S1 (E/IDOR): A'nın oturumuyla B'nin kayıt id'sine PATCH/DELETE → 404 `PORTFOLIO_ITEM_NOT_FOUND`, gövde bilinmeyen id ile birebir aynı; B'nin kaydı değişmez. Talent'sız kullanıcı → 404.
- AC-S2 (T): Gövdede `talent_id` gönderilirse yok sayılır, kayıt oturum sahibine yazılır.
- AC-S3 (T/IDOR): `evidence_id` = B'nin kanıtı veya silinmiş kanıt → 404 `EVIDENCE_NOT_FOUND`, satır oluşmaz. Aynı kanıt ikinci kez → 409 (yalnız kendi kanıtında ulaşılabilir; varlık kâhini yok).
- AC-S4 (T — rozet sahteciliği): Gövdede `badge: "COORDINATOR_CONFIRMED"`, `provider`, `decision` gönderilirse yok sayılır → rozet `SELF_DECLARED`. PATCH ile `evidence_id` değiştirilemez (alan yok sayılır).
- AC-S5 (T — rozet ödünç alma): B'nin kaydı (API dışından) A'nın CONFIRMED kanıtına bağlansa bile B'nin public kartı `SELF_DECLARED` döner.
- AC-S6 (T — onaylı kartı sahte bilgiyle süsleme): Rozet `COORDINATOR_CONFIRMED` iken public karttaki `credential_id` ve `provider` **yalnız** `certificate_checks`'ten gelir; öğrencinin yazdığı `credential_id`/`issuer` onaylı kartta gösterilmez. Başlık öğrenci beyanıdır; karşılığı "Resmi doğrulama" linkiyle herkesçe kontrol edilebilir.
- AC-S7 (T — reddedilen sertifika): Kanıtın kontrolü `REJECTED` ise kayıt public profilde **hiç** görünmez (kendi beyanı olarak da); sahibine rozet `COORDINATOR_REJECTED` döner.
- AC-S8 (I): Public sertifika öğesi tam olarak şu anahtarları taşır: `kind,title,issuer,issued_on,credential_id,badge,provider,verify_url,link_url,link_host`. `extracted_name`, `qr_raw_data`, `page_name`, `storage_key`, evidence id yanıtta geçmez.
- AC-S9 (I — açık yönlendirme/phishing): `verify_url` yalnız `https` ve `coursera.org|www.coursera.org|udemy.com|www.udemy.com|ude.my` ise döner; `https://coursera.org.evil.example/...` → `null`.
- AC-S10 (XSS/phishing): `external_url` yalnız `https://` (API 422 + DB CHECK); `javascript:`/`http:`/kimlik bilgili/standart dışı port → 422. `link_host` IDN alan adlarında punycode döner (`https://gооgle.com` → `xn--ggle-55da.com`), böylece homograf görünür olur.
- AC-S11 (D): Bir öğrencinin silinmemiş kayıt sayısı 50 ile sınırlı; 51. POST → 409 `PORTFOLIO_LIMIT_REACHED`. Public liste en fazla 50 öğe.
- AC-S12 (R): Oluşturma, rıza değişimi ve silme `audit_events`'e yazılır (metadata'da PII yok).
- AC-S13 (frontend XSS): `about`, `title`, `issuer` düz metin olarak render edilir (`dangerouslySetInnerHTML` yok); dış link `rel="nofollow ugc noopener noreferrer"` ve `target="_blank"` ile, alan adı görünür.

## Davranış sözleşmesi

| Durum | Yanıt |
|---|---|
| Başkasının / bilinmeyen kayıt id | 404 `PORTFOLIO_ITEM_NOT_FOUND` |
| Başkasının / silinmiş kanıt | 404 `EVIDENCE_NOT_FOUND` |
| Kanıt zaten vitrinde | 409 `EVIDENCE_ALREADY_IN_PORTFOLIO` |
| 50 kayıt sınırı | 409 `PORTFOLIO_LIMIT_REACHED` |
| Geçersiz alan / http link / gelecek tarih | 422 |
| Zorunlu alana null (PATCH) | 422 `FIELD_REQUIRED` |
| Oturum yok | 401 |

## Riskler / Kabul edilen riskler
- **Başlık sahteciliği (kalıntı risk):** Onaylı kartın başlığı öğrenci beyanıdır; `certificate_checks` kurs adını tutmaz. Azaltım: AC-S6 + herkese açık resmi doğrulama linki. Tam çözüm (çıkarılan kurs adını saklamak) kapsam dışı.
- **Rate limit yok:** POST için ayrı hız sınırı eklenmedi; AC-S11 kayıt tavanı sınırsız büyümeyi keser. Yük, tek kiracılı MVP'de kabul edildi.
- **"Hakkımda"da öğrencinin kendi kişisel verisi** (telefon vb.): Öğrencinin kendi tercihi; UI'da KVKK özel nitelikli veri uyarısı (final analiz §17.2). Sunucu tarafı içerik filtresi yok.
- **Aynı dosyanın çalışma dışı yeniden yüklenmesi:** Reddedilen sertifika, kontrol talep edilmeden kendi beyanı olarak tekrar eklenebilir; görsel olarak mühürsüz ve "Kendi beyanı" etiketli kalır.
- **Yarış durumu:** 50 sınırı uygulama kontrolüdür; eşzamanlı isteklerle birkaç kayıt aşılabilir — zararsız.

## Test stratejisi
- `tests/authorization/test_portfolio_items_authz.py` — AC-S1…S9, S12
- `tests/test_portfolio_items.py` — AC-1, AC-S10, AC-S11, DB CHECK'ler
- Mevcut public allowlist testleri (`about`, `certificates` eklendi)
- Frontend: bileşen testleri (AC-S13), Playwright ekran görüntüsü
