---
task_slug: yet-241-237-alan-adi-kisitlari
jira_id: YET-241, YET-237
saga_task_id: null
priority: high
threat_model: done
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 20
  integration: 70
  e2e: 10
affected_modules:
  - backend/alembic/versions (yeni migration)
  - backend/app/services/organization.py
  - backend/app/api/organizations.py
  - backend/app/api/admin.py
  - backend/tests/authorization/test_domain_squatting_guv09.py (eski test değişir)
---

# ATDD — YET-241 (önce) + YET-237 (sonra)

Not: 4z adımındaki Sonnet alt-ajanı kullanılmadı (kullanıcı kuralı: ALT-AJAN YOK). Kategoriler kullanıcı mesajı, Jira açıklaması ve gerçek-API sondasıyla yanıtlandı.

## Jira Kaynağı
YET-241 "GUV-09b: Doğrulanmış alan adı için DB kısıtı yalnız T2'yi kapsıyor (T3/T4 ve admin yükseltmesi)".
Yapılacak (birebir): index'i `IN ('T2','T3','T4') AND deleted_at IS NULL` olacak şekilde yeni migration ile genişlet (mevcut veride çakışma var mı önce sorgula), admin ucunda çakışmada 409. up/down/up doğrulaması.
YET-237 "L-02: Organizasyon alan adı oluşturulduktan sonra değiştirilemiyor": PATCH ucu yok; alan adı yoksa verify-domain 400. Konum: organizations.py. Üst görev: YET-225.

## Kanıt (sonda, test DB yetkin360_test)
- DB: T3+T2 ve T3+T3 aynı alan adı INSERT kabul (boşluk).
- Admin set_verification_level: çakışan alan adındaki kuruma T2/T3/T4 → 200 (boşluk).
- İki oturum, gerçek commit: T2/T2 yarışını DB yakalıyor ama IntegrityError yakalanmıyor (uç 500 verir).
- PATCH/PUT /organizations/{id} → 405. Alan adsız org için verify-domain → 400.
- DEV DB (salt-okunur): 5 org, hepsi T1, çakışma yok.

## Persona
Platform yöneticisi (admin), kurum/org yöneticisi (ADMIN üye), saldırgan (alan adı gaspçısı).

## Hedef
Doğrulanmış alan adı bir kuruma ait olsun: DB seviyesinde tek sahip (T2/T3/T4), admin yolu ve yarış dahil. Org ADMIN alan adını yanlış girdiyse düzeltebilsin, ama değişiklik doğrulama seviyesini sızdırmasın.

## Acceptance Criteria
YET-241
1. [Critical] DB: aynı alan adı (büyük/küçük harf duyarsız) iki aktif org'da T2/T3/T4 olarak bulunamaz (IntegrityError); silinmiş (deleted_at) ve T1 org'lar hariç.
2. [Critical] Admin verification-level: yeni seviye T2/T3/T4 ve başka aktif T2+ org aynı alan adına sahipse → 409 DOMAIN_ALREADY_VERIFIED, seviye/verified_at/verified_by değişmez, audit'e başarı yazılmaz.
3. [Critical] verify-domain yarışı: DB IntegrityError → 409 DOMAIN_ALREADY_VERIFIED (500 değil), kaybeden org T1 kalır.
4. [High] Admin T1'e düşürme / alan adsız org / aynı org'un kendi seviyesini yeniden ayarlaması çakışma kontrolüne takılmaz.
5. [High] Migration up/down/up çalışır; çakışma varsa upgrade açık hata verir; downgrade T2-only indeksi geri koyar.
YET-237
6. [Critical] PATCH /organizations/{id} {domain}: yalnız o org'un ADMIN'i; MEMBER, başka kiracı, platform-admin-değil-üye, bilinmeyen id → 404.
7. [Critical] T1'de değişir (200). T2'de değişir → T1'e düşer; verified_at, verified_by_user_id, domain_verification_token, last_verify_attempt_at sıfırlanır (seviye sızmaz).
8. [Critical] T3/T4'te → 409 ALAN_ADI_KILITLI, hiçbir alan değişmez.
9. [High] Geçersiz biçim (IP, localhost, port, yol) ve boş/null → 422; serbest e-posta alan adı → 400 FREE_EMAIL_DOMAIN; başka aktif T2+ org'un alan adı → 409 DOMAIN_ALREADY_VERIFIED (T1 kalır, T2'den düşmüş olmaz — çakışma kontrolü seviye düşmeden önce).
10. [High] Aynı değerle PATCH → 200, seviye düşmez (no-op).
11. [High] Audit: ORGANIZATION_DOMAIN_CHANGED (eski/yeni seviye, domain değeri loglanmaz); reddedilen denemeler audit'e DENIED yazılır (404 hariç).
12. [Medium] Yeni alan adıyla verify-domain çalışır (T1→T2).

## Davranış Sözleşmesi
| # | Durum | Dönen | Yan etki | AC |
|---|---|---|---|---|
| 1 | PATCH happy (T1) | 200 OrganizationResponse | domain güncellenir, token sıfırlanır, audit | 6,7 |
| 2 | PATCH T2 | 200, verification_level=T1 | verified_at/by/token/last_verify temizlenir | 7 |
| 3 | PATCH T3/T4 | 409 ALAN_ADI_KILITLI | yok | 8 |
| 4 | Biçim hatası / boş | 422 | yok | 9 |
| 5 | Serbest e-posta | 400 FREE_EMAIL_DOMAIN | audit DENIED | 9 |
| 6 | Çakışma (aktif T2+ başka org) | 409 DOMAIN_ALREADY_VERIFIED | yok | 9 |
| 7 | Yetkisiz/yok | 404 NOT_FOUND | yok | 6 |
| 8 | Aynı değer | 200, seviye korunur | yok (no-op) | 10 |
| 9 | Admin çakışmalı yükseltme | 409 DOMAIN_ALREADY_VERIFIED | yok | 2 |
| 10 | verify-domain yarış kaybı | 409 DOMAIN_ALREADY_VERIFIED | rollback, kaybeden T1 | 3 |
| 11 | DB bağlantı hatası | 500 (mevcut davranış) | — | satır ağ/DB hatası: yeni davranış tanımlanmadı |
Kısmi başarı: tek transaction; hata → tam rollback, kısmi alan güncellemesi yok.
Hiçbir şey yapılamadı ama hata yok: aynı değer PATCH'i 200 + audit yok (no-op açıkça).
Boş sonuç ↔ hata: yetkisiz ve yok → ikisi de 404 (ayrıştırılamaz, bilinçli).
Silinen satırlar: zaman aşımı satırı (DNS commit sonrası, mevcut pending davranışı).

## Threat model (özet)
- Seviye sızdırma: T2 org alan adını başka değerle değiştirip T2 gösterir → AC-7 (T1'e düşüş).
- TOCTOU: PATCH çakışma kontrolü ile yazma arası yarış → DB kısmi UNIQUE son bariyer (AC-1); IntegrityError 409.
- Kiracı sınırı: org_admin_ids + scoped_organizations, yetkisiz 404 (IDOR).
- Admin onayını sessizce kaybetme: T3/T4 kilitli (AC-8).
- Numaralandırma: 409 çakışma "alan adı başka org'da doğrulanmış" ifşa eder; yalnız yetkili ADMIN görür, kabul (verify-domain'de zaten aynı sözleşme). Başka org kimliği/adı dönmez.
- CSRF: PATCH require_csrf + get_verified_principal.
- Log: alan adı değeri audit metadata'sında yok.
- Kota: ek kota yok (karar); her değişim T1'e döndürdüğü için kazanç yok.

## Kapsam dışı
Kurum (institution) alan adı admin ucu (YET-242); org adı taklidi; domain boşaltma; T3/T4 için admin onaylı alan adı değişikliği yolu; frontend; kota.

## Rollback
Migration downgrade; kod değişikliği git revert.

## Risks
- Eski test test_conflict_with_several_verified_orgs_is_409_not_500 T2+T3 aynı alan adı kuruyor: DB'de artık kurulamaz → test yeni sözleşmeye göre değişir (rapor).
- Domain CITEXT; index büyük/küçük harf duyarsız.
- PATCH için /organizations/ ile aynı OrganizationResponse.

## Assumptions
- Org ADMIN (OrganizationMember role ADMIN) PATCH edebilir; platform-admin üye değilse edemez (404).
- PATCH gövdesi yalnız {domain}; ad/legal_id kapsam dışı.
