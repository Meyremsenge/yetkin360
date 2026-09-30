---
task_slug: guv-02-davet-yaniti-duzeltmesi
jira_id: YET-165
saga_task_id: null
threat_model: done
priority: high
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 15
  integration: 70
  e2e: 15
affected_modules:
  - backend/app/api/organizations.py
  - backend/app/api/institutions.py
  - backend/app/services/organization.py
  - backend/app/services/institution.py
  - docs/API.md
  - backend/tests/authorization/test_organization_authorization.py
  - backend/tests/authorization/test_institution_authorization.py
---

# ATDD — guv-02-davet-yaniti-duzeltmesi

## Jira Kaynağı
[YET-165 — [HATA.md GUV-02/A-09] Davet uçları: 500 hatası, e-posta numaralandırma, rol doğrulama (dar kapsam)](https://kuyusuzyusuf123.atlassian.net/browse/YET-165)
Açıklama (Jira'dan birebir, bu oturumda yazıldı — bkz. Jira issue body): HATA.md GUV-02/GUV-07/L-01 kaynaklı, HATA_DUZELTME_PROMPT.md K1=(b) kararına dayalı dar kapsamlı düzeltme. AUTHZ-01/A-08 (çoklu rol) bu görevin KAPSAMI DIŞINDA.

## Persona
Organizasyon veya kurum ADMIN'i — mevcut bir üyeyi davet ederek (e-posta ile) organizasyonuna/kurumuna ekliyor.

## Hedef (Neden)
HATA.md denetiminde bulunan üç somut açığı kapatmak:
- **GUV-07**: Organizasyona bilinmeyen e-posta davet edilince yakalanmayan `ValueError` → 500.
- **Numaralandırma oracle'ı**: Org tarafı (bilinmeyen→500, bilinen→201) ile kurum tarafı (bilinmeyen→422, bilinen→201) tutarsız VE her ikisi de yanıt kodundan "bu e-posta sistemde kayıtlı mı" bilgisini sızdırıyor.
- **Rol validasyon boşluğu**: Kurum tarafında rol Pydantic'te doğrulanmıyor, geçersiz değer DB CHECK'e (`ck_institution_members_role`) çarpıp yakalanmayan `IntegrityError` ile 500'e düşüyor.
- **L-01**: Kurum tarafında mevcut üyenin rolü davet ucu üzerinden sessizce UPSERT ile değiştiriliyor — son ADMIN kendini/başka son admin'i düşürebilir, ayrı bir "rol değiştir" işlemi yok.

**Bilinçli sınırlama:** GUV-02'nin asıl güvenlik etkisi (kurbanın `kind`'ı değişip kendi talent işlevlerini kaybetmesi) AUTHZ-01/A-08'e (çoklu rol düzeltmesi) bağımlı — bu görev onu ÇÖZMÜYOR, kullanıcı onayıyla ayrı görev olarak bırakıldı.

## User Story
As an org/institution ADMIN
I want davet ucunun tutarlı, sızıntısız ve doğru hata kodları döndürmesini
So that ne bir 500 hatası alırım ne de davetim bir numaralandırma saldırısına araç olur

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given org/institution ADMIN'i geçerli oturumla, When bilinen (sistemde kayıtlı) bir e-postaya geçerli rolle davet gönderir, Then `202 {"status": "queued"}` döner; üyelik DB'ye yazılır ve aynı transaction'da outbox'a bildirim enqueue edilir (org ve institution için birebir aynı yanıt şekli).
2. [Critical] Given aynı ADMIN, When **bilinmeyen** (sistemde kayıtlı olmayan) bir e-postaya davet gönderir, Then org ve institution ikisinde de **AYNI** `202 {"status": "queued"}` döner — hiçbir üyelik oluşmaz, yalnızca audit event yazılır (e-posta/hash PII olarak yazılmadan); önceki davranış (org: 500, institution: 422) kalkar.
3. [Critical] Given geçersiz bir rol değeri (Literal setinin dışında), When org veya institution davet ucuna gönderilir, Then `422 ApiError{code:"INVALID_ROLE"}` döner, DB'ye hiç dokunulmaz (institution tarafında artık DB CHECK'e hiç düşmez).
4. [High] Given org/institution'da zaten üye olan bir kullanıcı, When aynı kişi tekrar davet edilirse, Then yanıt şekli (1) ve (2) ile AYNI kalır (`202 queued`) ve mevcut üyenin **rolü değişmez** — institution tarafındaki sessiz UPSERT kaldırılır.
5. [Critical] Given bir kurumda tam olarak tek ADMIN varken, When bu ADMIN (veya başka bir ADMIN) kendini/diğer ADMIN'i tekrar davet ederse (ör. rol=COORDINATOR ile), Then AC-4 gereği rol değişmediği için ADMIN sayısı asla sıfıra düşmez — bu regresyon testiyle kilitlenir.
6. [High] Given institution invite ucu, When herhangi bir davet denemesi (başarılı/başarısız/bilinmeyen e-posta) yapılır, Then bir audit event yazılır (şu an institution tarafında HİÇ audit logging yok — bu görev ekliyor), org tarafındaki `INVITE_ORG_MEMBER` deseniyle tutarlı.
7. [Critical] **AC-S1** — Given bir ORG_ADMIN'in yönetmediği bir organizasyon, When o organizasyona davet göndermeye çalışırsa, Then `404` döner (mevcut tenant izolasyonu korunur, regresyon testiyle kilitlenir).
8. [High] **AC-S5** — Given bir kurumun COORDINATOR'ı (ADMIN değil), When `POST /institutions/{id}/members` çağırırsa, Then `404` döner (mevcut rol/tenant kontrolü korunur, regresyon testiyle kilitlenir).

## Threat Model
Çağrıldı — AC-S1, AC-S5 (yukarıdaki 7 ve 8 numaralı kriterler) + aşağıdaki STRIDE-lite analizi eklendi.

**Varlıklar/sınırlar:** Tenant (organizasyon/kurum) üyelik sınırı; kimin sistemde kayıtlı olduğu bilgisi (e-posta varlığı); rol ataması (ADMIN/COORDINATOR/MEMBER) yetki sınırı.

- **Spoofing**: Yeni bir yüzey açılmıyor — mevcut `get_current_principal` bağımlılığı korunuyor. Atlandı.
- **Tampering**: `role` alanı istemciden geliyor ama zaten sunucuda kontrol ediliyor (bu görev bunu Literal'e yükseltiyor, AC-3). `organization_id`/`institution_id` URL'den geliyor ama `principal.org_admin_ids`/`institution_admin_ids` ile scope kontrolü zaten var (AC-7/AC-8 regresyon testiyle kilitleniyor).
- **Repudiation**: **Gerçek bulgu** — `backend/app/api/institutions.py`'de invite ucu hiç audit event yazmıyor (org tarafında `INVITE_ORG_MEMBER` var, institution'da yok). AC-6 bunu kapatıyor.
- **Information disclosure**: **Ana hedef** — numaralandırma oracle'ı (AC-2). Kabul edilen risk: yanıt SÜRESİ farkı (bilinen yolda DB yazma + outbox, bilinmeyen yolda sadece audit) tam olarak eşitlenmiyor — saldırgan zaten kimliği doğrulanmış bir tenant ADMIN'i olmak zorunda olduğundan (anonim değil), bu düşük risk kabul edildi; tam zaman-sabitleme (dummy iş) MVP kapsamı dışı bırakıldı (bkz. Risks).
- **DoS**: Davet ucuna hız sınırı yok (GUV-11/A-10'un kapsamı, bu görev DEĞİL) — kabul edilen risk, ayrı görev.
- **Elevation of privilege**: **Ana hedef** — son ADMIN'in davet ucu üzerinden dolaylı olarak düşürülmesi (L-01). AC-4/AC-5 bunu kapatıyor (UPSERT kaldırılıyor, rol artık davet ucundan asla değişmiyor).

**Not:** Bu görev yeni yetkilendirme (authz) davranışı ürettiği için (AC-7/AC-8 tenant izolasyonu regresyon testleri + AC-2/AC-4'ün "zaten üye"/"bilinmeyen e-posta" dallarının doğru yetki bağlamında çalıştığının doğrulanması) pipeline'da `plan`'dan sonra **`authz-test` skill'i zorunlu** — saldırgan matrisi (org ADMIN A vs org ADMIN B vs COORDINATOR vs TALENT × her iki uç) `test-copilot`'un genel testlerinden ayrı olarak orada işlenmeli.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: bilinen e-posta, geçerli rol, yeni üye (org) | `202 {"status":"queued"}` | Üyelik DB'ye yazılır + aynı tx'te outbox'a enqueue + audit | "Davet gönderildi" | AC-1 |
| 2 | Happy path: bilinen e-posta, geçerli rol, yeni üye (institution) | `202 {"status":"queued"}` | Aynı — üyelik + outbox + audit (yeni eklenen) | Aynı mesaj, org ile tutarlı | AC-1 |
| 3 | Bilinmeyen e-posta (org) | `202 {"status":"queued"}` (önceki: 500) | Üyelik oluşmaz, yalnız audit (e-posta yazılmadan) | Aynı "davet gönderildi" mesajı | AC-2 |
| 4 | Bilinmeyen e-posta (institution) | `202 {"status":"queued"}` (önceki: 422) | Aynı — yalnız audit | Aynı mesaj | AC-2 |
| 5 | Geçersiz rol değeri (org/institution) | `422 ApiError{code:"INVALID_ROLE"}` | Yok, DB'ye dokunulmaz | "Geçersiz rol" hatası | AC-3 |
| 6 | Zaten üye (org/institution) | `202 {"status":"queued"}` (önceki: org 409, institution sessiz upsert) | Hiçbir şey değişmez — rol AYNI kalır | Aynı "davet gönderildi" mesajı | AC-4 |
| 7 | Davet eden bu org/kurumun ADMIN'i değil (tenant izolasyonu) | `404` | Yok | "Kaynak bulunamadı" | AC-7, AC-8 |
| 8 | **Kısmi başarı** (üyelik DB'ye yazıldı, aynı transaction'da outbox enqueue başarısız) | `500 ApiError{code:"INTERNAL_ERROR", request_id}` | Transaction ROLLBACK — üyelik de outbox da hiç yazılmamış olur (hepsi-ya-da-hiçbiri, outbox DB yazması olduğu için aynı transaction'da) | Genel hata, davet gönderilmedi | — |
| 9 | **Hiçbir şey yapılamadı ama hata da yok** (bilinmeyen e-posta yolunda audit yazımı başarısız olsa bile dış yanıt 202 kalır) | `202 {"status":"queued"}` (dış davranış değişmez — numaralandırma korunmalı) | Audit eksik kalabilir — bu iç bir gözlemlenebilirlik riski, PII içermeyen bir log/monitoring uyarısına düşmeli | Kullanıcı fark etmez | AC-6 (kısmi) |

Boş sonuç ↔ hata ayrımı: Bu uçta "boş sonuç" kavramı yok (tekil kaynak oluşturma ucu) — ama "bilinmeyen e-posta" (AC-2) ile "geçersiz rol" (AC-3) farklı durum kodlarıyla (202 vs 422) ayrılır; "bilinmeyen e-posta" ile "bilinen e-posta" ise BİLEREK aynı kodu döner (numaralandırmayı kapatmak bu görevin amacı).

## Test Strategy
Unit: 15% — Pydantic `Literal` rol validasyonu, ApiError şekli.
Integration: 70% — gerçek PostgreSQL'e karşı: org/institution invite uçlarının her davranış-sözleşmesi satırı, `tests/authorization` paketindeki mevcut testlerin tamamının yeşil kalması, yeni AC-7/AC-8 regresyon testleri, audit event'in gerçekten yazıldığının DB'den doğrulanması.
E2E: 15% — org ve institution için birer uçtan uca "davet gönder → outbox'ta doğru topic'in enqueue edildiğini doğrula" senaryosu.

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: yok (yanıt süresi farkı kabul edilen risk, bkz. Threat Model)
Memory: yok
Görsel/UI kriteri: yok (bu görev yalnız backend API, frontend bu uçları henüz çağırmıyor — HATA.md §3)
Diğer ölçülebilir kriterler: Bilinen/bilinmeyen e-posta için durum kodu VE yanıt gövdesi şekli birebir aynı; org/institution arası davranış tutarlı; `pytest tests/authorization -q` tamamı yeşil; hiçbir yol 500/yakalanmayan exception üretmiyor.

## Kapsam Dışı
- AUTHZ-01/A-08 (çoklu rol/`kind` düzeltmesi) — GUV-02'nin "kurbanın kendi talent işlevlerini kaybetmesi" etkisi bu görevde ÇÖZÜLMÜYOR, ayrı görev.
- Davet + kabul akışı (yeni durum kolonu/migration) — K1=(b) kararı gereği MVP'de yok, doğrudan ekleme modeli korunuyor.
- Institution'a yeni bir "member status" kolonu eklenmesi — "zaten üye" durumu ek kolon olmadan, kod seviyesinde ele alınıyor.
- Hız sınırlama (GUV-11/A-10'un kapsamı) — davet ucuna rate limit bu görevde eklenmiyor.
- `docs/API.md`'nin bu iki uç dışındaki kısımlarının güncellenmesi.

## Etkilenen Dosyalar/Modüller (bilinen)
`backend/app/api/organizations.py`, `backend/app/api/institutions.py`, `backend/app/services/organization.py`, `backend/app/services/institution.py`, ilgili Pydantic şemaları (`OrganizationMemberInvite`/`InstitutionMemberInvite`'ın `role` alanı), `docs/API.md` (bu iki uç için), `backend/tests/authorization/test_organization_authorization.py`, `backend/tests/authorization/test_institution_authorization.py`.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı (önceki görevde, `acik-kaynak-paketi-dogrulama`) — repo kökü proje klasörüyle aynı. Yine de arama/tarama komutları proje klasörüyle sınırlı tutulmalı.

## Rollback Beklentisi
Üyelik yazması ve outbox enqueue'u aynı transaction'da olduğu için (outbox bir DB yazması, ağ çağrısı değil — CLAUDE.md'nin "ağ çağrısı asla açık transaction içinde" kuralına aykırı değil) bir hata durumunda tüm transaction rollback olur, kısmi bir "üyelik var ama bildirim yok" durumu oluşmaz.

## Risks
- Yanıt süresi farkı (bilinen e-posta yolunda ekstra DB yazması + outbox var, bilinmeyende yok) tam olarak eşitlenmiyor — kabul edilen risk, gerekçe: saldırgan zaten kimliği doğrulanmış bir tenant ADMIN'i olmalı (anonim saldırı yüzeyi değil). Genel güvenlik sertleştirme turunda (A-10 hız sınırı ile birlikte) yeniden değerlendirilebilir.
- Davet ucuna hız sınırı yok (GUV-11) — ayrı görev (A-10), kabul edilen risk.
- Bu görev AUTHZ-01'i çözmediği için GUV-02'nin tam kapanmadığı — Jira YET-165'te ve bu dosyada açıkça belgelendi.

## Assumptions
- "Zaten üye" durumunda 202 queued (numaralandırmayı tam kapatmak için) tercih edildi — alternatif olarak org'daki mevcut 409 ALREADY_MEMBER korunabilirdi (davet eden zaten o tenant'ın ADMIN'i olduğu için üye listesini görebiliyor, bu sızıntı kabul edilebilir sayılabilirdi) ama tutarlılık için 202 seçildi. Bu bir varsayımdır, kullanıcı onayı bekliyor.
- Audit event'in institution tarafına eklenmesi (AC-6) HATA.md'de doğrudan bir ID ile anılmıyor ama threat-model'in Repudiation analizinde bulunan gerçek bir boşluk — bu görevin parçası sayıldı.

## Unknowns
- `docs/API.md`'nin mevcut sözleşmesinin bu iki uç için tam olarak ne dediği bu oturumda okunmadı — `plan` aşamasında okunup güncellenmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → org/institution ADMIN'i. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
2. Ana hedef → GUV-07 + numaralandırma + rol validasyonu; AUTHZ-01 kapsam dışı. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
3. Happy path → davet → DB yazma + outbox enqueue (aynı tx) → 202 queued. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
4. Edge case'ler → bilinmeyen e-posta, geçersiz rol, zaten üye. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
5. Davranış sözleşmesi tablosu → yukarıda dolduruldu. (Sonnet 5 low alt-ajanı tarafından yanıtlandı + threat-model'in AC-S satırlarıyla genişletildi)
6. Başarı ölçütü → durum kodu/gövde şekli birebir eşleşmesi, tests/authorization tam yeşil. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
7. Kapsam dışı → AUTHZ-01, davet+kabul akışı, yeni migration, hız sınırı. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Bağımlılıklar → yukarıda listelenen dosyalar. (Sonnet 5 low alt-ajanı tarafından yanıtlandı, kod okumasıyla doğrulandı)
9. Performans/güvenlik kısıtı → tam zaman-sabitleme yapılmayacak, kabul edilen risk. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
10. Rollback beklentisi → aynı transaction, hepsi-ya-da-hiçbiri. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
11. Kabul kriteri sahibi → kullanıcı onayı + tests/authorization tam yeşil. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
12. Test stratejisi oranı → 15/70/15 (unit/integration/e2e). (Sonnet 5 low alt-ajanı tarafından yanıtlandı, kullanıcı onayı bekliyor)
