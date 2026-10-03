---
task_slug: acik-kaynak-paketi-dogrulama
jira_id: YET-119
saga_task_id: null
threat_model: not-applicable
priority: medium
coverage_target: null
performance_target: null
memory_target: null
test_strategy:
  unit: 0
  integration: 0
  e2e: 0
affected_modules:
  - README.md
  - .env.example
  - docker-compose.yml
  - LICENSE
  - SECURITY.md
  - CONTRIBUTING.md
  - security-scan skill (detect-secrets konfigürasyonu)
---

# ATDD — acik-kaynak-paketi-dogrulama

## Jira Kaynağı
[YET-119 — [PLAN 3.15] Açık kaynak paketi: kurulum talimatı sıfırdan doğrulanır, sır taraması](https://kuyusuzyusuf123.atlassian.net/browse/YET-119)
Açıklama (Jira'dan birebir): "PLAN.md Faz 3 — madde 3.15. Sahip: @all"
AC: Jira'da ayrı bir AC alanı yok — PLAN.md madde 3.15 tek satırlık görev tanımı: "Açık kaynak paketi: kurulum talimatı sıfırdan doğrulanır, sır taraması @all". PLAN.md'de 3.14 (Deploy) ile 3.16 (Kod dondurma) arasında, Faz 3'ün son güvenlik/hazırlık maddesi.

Not: Bu ortamda Saga MCP bağlı değildi (`mcp__saga__*` araçları bulunamadı) — Saga task'ı oluşturulamadı, `saga_task_id: null`. İlerleyen bir oturumda Saga bağlanırsa `jira-sync` skill'i ile bu görev için task açılıp bu alan güncellenmeli.

## Persona
Proje sahibi / hazırlayan geliştirici (jüri üyesi değil). Görev "@all" sahipli, deploy sonrası (3.14) ve kod dondurma öncesi (3.16) son iç kontrol adımı. Jüri işin sonucunu (public repo) görecek, işi bizzat yapan proje ekibi.

## Hedef (Neden)
Repo public yapıldığında iki somut risk önlenir: (a) dışarıdan gelen birinin README'yi izleyip projeyi çalıştıramaması, (b) commit geçmişinde/dosyalarda unutulmuş gerçek bir API key/şifre/token'ın herkese açık hale gelmesi. CLAUDE.md'nin "açık kaynak → bir yetkilendirme açığı herkes tarafından okunabilir" ilkesinin doğrudan sonucu.

## User Story
As a proje sahibi
I want kurulum talimatlarının sıfır ortamda çalıştığını ve repoda hiçbir sırrın bulunmadığını doğrulamak
So that repo herkese açık yapıldığında ne kurulum ne de güvenlik açısından dışarıya kötü görünmeyiz veya zarar vermeyiz

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given temiz bir dizine yapılan `git clone` (önceden kurulu bağımlılık/`.env` yok), When README.md'deki kurulum adımları (`docker compose up -d`, `.env.example` → `.env`, backend `uvicorn` başlatma, frontend `npm install && npm run dev`) harfiyen izlenir, Then uygulama ekstra elle müdahale gerekmeden ayağa kalkar ve temel bir sayfa (ör. login) hatasız yüklenir.
2. [Critical] Given repo kökü ve tüm git geçmişi, When `security-scan` skill'i (detect-secrets vb.) çalıştırılır, Then sıfır gerçek-pozitif sır bulgusu döner.
3. [High] Given README'de eksik/yanlış bir kurulum adımı, When temiz ortamda izlenir, Then doğrulama FAIL olarak işaretlenir ve README'de eksik adım düzeltilip yeniden denenir.
4. [High] Given tarama sonucunda gerçek bir sır (API key/token/şifre) bulunur, When bulgu doğrulanır, Then görev kritik olarak bloklanır — sır derhal rotate edilir, git geçmişinden temizlenir (force-push yalnız açık onayla) ve `.env.example`'a placeholder konur.
5. [Medium] Given tarama sonucunda örnek/placeholder bir değer sır sanılır (false positive), When incelenir, Then `detect-secrets` baseline/allowlist dosyasına eklenir ve doğrulama PASS olarak notla kapatılır.
6. [Medium] Given backend kurulumu başarılı ama frontend kurulumu (veya tersi) başarısız, When bu kısmi durum tespit edilir, Then doğrulama "kısmi FAIL" sayılır ve yalnız başarısız tarafın README adımı düzeltilir.

## Threat Model
Tetikleyici yok — değerlendirilen tetikleyiciler: kimlik doğrulama/yetkilendirme, kullanıcı girdisi, dosya yükleme/indirme, ödeme, KVKK/kişisel veri, çok kiracılı sınır, dış API çağrısı, arka plan işi, yeni HTTP ucu. Hiçbiri uymuyor çünkü bu görev kod/endpoint değişikliği değil, mevcut dokümantasyon + repo durumunun (README doğruluğu, sır taraması) statik/manuel denetimidir — yeni bir saldırı yüzeyi eklenmiyor.

## Agentic Değerlendirme Kriterleri
(Tetikleyici yok — bu görev bir LLM agent/sub-agent tool-calling davranışını veya prompt'unu değiştirmiyor, bölüm silindi.)

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (temiz clone + README adım adım izlenir, sır bulunmaz) | Doğrulama: PASS | Yok (salt-okunur denetim) | Jira YET-119 "Done"a geçer, kısa rapor: "README doğrulandı, 0 sır bulundu" | AC-1, AC-2 |
| 2 | Kurulum talimatı eksik/yanlış adım içeriyor | Doğrulama: FAIL | README.md'de eksik adım düzeltilir (yeni commit) | Jira'da yorum: "README adım X eksikti, düzeltildi", görev tekrar denenene kadar açık kalır | AC-3 |
| 3 | Sır taramasında gerçek bir sır bulunur | Doğrulama: FAIL (kritik) | Sır derhal rotate edilir + git geçmişinden temizlenir (ayrı, açık onaylı işlem) | Görev bloklanır, kullanıcıya acil bildirim: "gerçek sır bulundu, repo public yapılamaz" | AC-4 |
| 4 | Sır taramasında false positive bulunur | Doğrulama: PASS (not düşülerek) | `detect-secrets` baseline/allowlist dosyasına placeholder eklenir | Rapor: "1 false positive, baseline'a eklendi, gerçek risk yok" | AC-5 |
| 5 | Dış bağımlılık hatası (docker/pip/npm ağ hatası) | Doğrulama: INCONCLUSIVE (tekrar denenmeli) | Yok | "Ağ/altyapı hatası nedeniyle doğrulama tamamlanamadı, tekrar denenecek" — README/sır hatası sayılmaz | — |
| 6 | Kısmi başarı (backend OK, frontend FAIL veya tersi) | Doğrulama: FAIL (kısmi) | Başarısız tarafın README adımı düzeltilir | Rapor: "Backend OK, frontend kurulumu adım Y'de başarısız, düzeltiliyor" | AC-6 |
| 7 | Hiçbir şey yapılamadı ama hata da yok (tarama aracı 0 dosya taradı) | Doğrulama: INCONCLUSIVE → yanlış yapılandırma sayılır | `security-scan` konfigürasyonu (dosya kapsamı/glob) düzeltilir, tarama tekrarlanır | "Tarama 0 dosya kapsadı, bu PASS değil — konfigürasyon hatası, düzeltilip tekrar koşulacak" | — |

Silinen satır: "Zaman aşımı" — PLAN.md madde 3.15 ve final-analiz §39'da kurulum süresi için somut bir zaman aşımı eşiği tanımlanmamış; bu bir canlı API endpoint'i değil denetim/runbook görevi olduğu için keyfi bir süre sınırı uydurulmadı.

Kısmi başarı: Satır 6'da ele alındı — hangi taraf (backend/frontend) başarısızsa yalnız o adım düzeltilir, diğer taraf tekrar test edilmez.
Hiçbir şey yapılamadı ama hata da yok: Satır 7'de ele alındı — sessiz "0 sır bulundu = PASS" kabul edilmez, önce taramanın gerçekten dosyaları kapsadığı doğrulanır.
Boş sonuç ↔ hata ayrımı: "0 sır bulundu" (gerçek tarama, PASS) ile "0 dosya tarandı" (yapılandırma hatası, INCONCLUSIVE) durum kodu olarak ayrı tutulur — aynı "0" çıktısı asla aynı anlama gelmez.

## Test Strategy
Bu görev bir kod birimi değil "talimat + repo durumu" denetimi olduğu için klasik unit/integration/e2e piramidi uygulanamaz.
Manuel temiz-ortam kurulum denemesi: %70 — README adımlarının bizzat, sıfırdan, adım adım izlenmesi (AC-1, AC-3, AC-6).
Otomatik secret-scan: %30 — `security-scan` skill'i / detect-secrets ile repo + git geçmişi taraması (AC-2, AC-4, AC-5).

## Benchmark / Başarı Ölçütü
Coverage Target: yok (bu görev için anlamsız — kod coverage değil)
Performance Target: yok — PLAN.md/final-analiz'de somut bir kurulum süresi eşiği tanımlı değil (varsayım olarak makul süre 15-20 dk, ama bu bir kabul kriteri değil, gözlem notu)
Memory: yok
Görsel/UI kriteri: yok (bu görev UI değiştirmiyor)
Diğer ölçülebilir kriterler: README'deki kurulum adımları sıfırdan bir ortamda ekstra müdahalesiz %100 tekrarlanabilir olmalı VE `security-scan` (detect-secrets) çalıştırıldığında sıfır gerçek-pozitif sır bulgusu dönmeli.

## Kapsam Dışı
Yeni CI/CD pipeline kurulumu; deploy'un kendisi (3.14'te zaten yapıldı); kod dondurma (3.16'da yapılacak); README dışındaki içerik/dokümantasyon kalite incelemesi (yazım/üslup); herhangi bir yeni özellik veya mimari değişiklik.

## Etkilenen Dosyalar/Modüller (bilinen)
`README.md` (birincil doğrulama hedefi), `.env.example` (placeholder'ların güncelliği), `docker-compose.yml` (kurulum adımının parçası, değiştirilmez sadece çalıştırılır), `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md` (güncellik kontrolü), `security-scan` skill'inin detect-secrets konfigürasyonu.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökünün proje klasörüyle (`yetkin360`) aynı olup olmadığı bu oturumda kontrol edilmedi. Sonraki adımlarda (`security-scan` dahil) arama/tarama komutları proje klasörüyle sınırlı tutulmalı; sınırsız `git log -p --all` veya kök dizinden `grep -r` çalıştırmadan önce repo kökü teyit edilmeli.

## Rollback Beklentisi
Gerçek bir sır bulunursa: (a) sır derhal rotate edilir (eski değer iptal/yenilenir), (b) git geçmişinden temizlenir (ör. `git filter-repo` ile — force-push yalnız açık kullanıcı onayıyla, CLAUDE.md gereği), (c) yerine `.env.example`'a placeholder konur. Sadece placeholder eklemek yetmez — sır zaten sızmışsa rotasyon şarttır.

## Risks
- Git geçmişi taraması (tüm commit'ler) büyük bir repo geçmişinde RAM/performans sorunu yaratabilir — proje hafızasında daha önce benzer bir sorun (tgrep, security-scan) not edilmiş.
- README'nin "sıfırdan" doğrulanması tamamen manuel olduğu için insan hatasına (bir adımı atlama) açık.

## Assumptions
- Kurulum süresi için sabit bir zaman aşımı eşiği yok — bu bir varsayım olarak belirtildi, kabul kriteri değildir.
- `security-scan` skill'inin detect-secrets aracı hem mevcut dosyaları hem git geçmişini tarayabilecek şekilde çalıştırılabilir; bu doğrulanmadı, `verify`/`security-scan` adımında teyit edilmeli.

## Unknowns
- Bu makinedeki git reposu kökünün proje klasörüyle birebir aynı olup olmadığı (bkz. "Proje Ortamı Kısıtı").
- `security-scan` skill'inin şu an bu projede daha önce hiç çalıştırılıp çalıştırılmadığı / mevcut bir baseline dosyası olup olmadığı.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü / persona → Proje sahibi / hazırlayan geliştirici (jüri üyesi değil) — görev "@all" sahipli, deploy sonrası son iç kontrol adımı. (Sonnet 5 low alt-ajanı tarafından yanıtlandı: PLAN.md'deki konumdan çıkarım)
2. Ana hedef / neden → Dışarıdan birinin README'yi izleyip projeyi çalıştıramaması ve unutulmuş bir sırrın public olması riskini önlemek. (Sonnet 5 low alt-ajanı tarafından yanıtlandı: CLAUDE.md açık-kaynak ilkesinden çıkarım)
3. Happy path senaryosu → Temiz clone → README adımları → uygulama ayağa kalkar + paralelde security-scan PASS döner. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
4. Edge case'ler → README'de eksik adım / gerçek sır bulunması. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
5. Davranış sözleşmesi tablosu → Yukarıdaki tabloda dolduruldu, "zaman aşımı" satırı silindi (gerekçeli). (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
6. Başarı ölçütü → README %100 tekrarlanabilir + sıfır gerçek-pozitif sır bulgusu; süre hedefi konulmadı (dayanaksız varsayım olur). (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
7. Kapsam dışı → CI/CD kurulumu, deploy'un kendisi, kod dondurma, dokümantasyon üslup incelemesi, yeni özellik. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Bağımlılıklar/etkilenen dosyalar → README.md, .env.example, docker-compose.yml, LICENSE, SECURITY.md, CONTRIBUTING.md, security-scan config. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
9. Tarama kapsamı → Tüm git geçmişi (sadece mevcut dosyalar yetmez). (Sonnet 5 low alt-ajanı tarafından yanıtlandı: CLAUDE.md "commit geçmişi temiz tutulur" ilkesinden çıkarım)
10. Rollback beklentisi → Sır bulunursa rotate + git history temizliği + placeholder. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
11. Kabul kriteri sahibi → Kullanıcı (proje sahibi) onayı; security-scan PASS tek başına yeterli değil çünkü kurulum doğrulaması manuel. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
12. Test stratejisi oranı → %70 manuel temiz-ortam kurulum + %30 otomatik secret-scan. (Sonnet 5 low alt-ajanı tarafından yanıtlandı: klasik unit/integration/e2e bu görev tipine uymuyor)
