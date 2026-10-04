---
task_slug: a01-giris-kilitleme
jira_id: null
saga_task_id: null
priority: critical
threat_model: done
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 15
  integration: 80
  e2e: 5
affected_modules:
  - backend/app/services/auth.py
  - backend/tests/ (auth servis testleri + rollback semantiğini sınayan yeni test)
---

# ATDD — a01-giris-kilitleme

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Kaynak: HATA.md GUV-01, L-03; PLAN 3.24;
HATA_DUZELTME_PROMPT.md §8 A-01.

## Persona
Sistemin kendisi (güvenlik mekanizması düzeltmesi, yeni kullanıcı akışı değil).
İki zımni taraf senaryolarda yer alır: **brute-force deneyen taraf** (art arda
yanlış parola giren istemci — kilitleme mekanizmasının hedeflediği taraf) ve
**meşru kullanıcı** (happy path + kilit süresi dolduktan sonra kurtarma, AC-4).
(Sonnet 5 low alt-ajanı tarafından yanıtlandı: görev davranışsal bir düzeltme,
persona ayrımı ayrı AC gerektirmiyor, yalnız test adlandırmasını etkiliyor.)

## Hedef (Neden)
Şu an `authenticate()` başarısız girişte sayaç artışını, `locked_until`'i ve
DENIED audit kaydını `session.flush()` ile yazıp `InvalidCredentials`/
`AccountLocked` fırlatıyor; `get_session` (backend/app/core/deps.py:20-29)
istisnayı yakalayınca **tüm transaction'ı rollback ediyor** → bu güvenlik izleri
(sayaç, kilit, audit) hiç kalıcı olmuyor, brute-force koruması fiilen çalışmıyor.
Düzeltme, `refresh_tokens()`'taki mevcut "Commit it now, before raising" deseniyle
aynı yaklaşımı `authenticate()`'e taşıyarak bu izleri istisna öncesi kalıcı hale
getiriyor. (Sonnet 5 low alt-ajanı tarafından yanıtlandı, kod okumasıyla teyitli.)

## User Story
As a platformun kimlik doğrulama alt sistemi
I want başarısız girişlerde sayaç/kilit/audit kaydının rollback'ten bağımsız kalıcı olmasını
So that brute-force koruması gerçekten işlesin ve askıya alınmış/silinmiş hesaplar giriş yapamasın

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given var olan ACTIVE bir kullanıcı ve yanlış parola, When
   `POST /auth/login` çağrılır, Then 401 INVALID_CREDENTIALS döner ve DB'de
   (gerçek `get_session` semantiğiyle, override'sız) `failed_login_count` bir
   önceki değerden +1 olarak kalıcıdır. (AC-1)
2. [Critical] Given bir kullanıcının `failed_login_count`'u 9 (art arda yanlış
   parola ile), When 10. yanlış deneme yapılır, Then bu 10. denemenin kendisi
   401 INVALID_CREDENTIALS döner (henüz kilitli değil) ve `locked_until` ≈
   now+15dk olarak DB'de kalıcı olur; When bundan sonra 11. deneme (parola doğru
   olsa bile) yapılır, Then 423 ACCOUNT_LOCKED döner. (AC-2)
3. [Critical] Given her başarısız giriş denemesi (kullanıcı var/yok, kilitli/
   değil), When `authenticate()` çalışır, Then `audit_events` tablosunda
   `USER_LOGIN`/`DENIED` satırı gerçek DB'de (rollback sonrası da) kalıcı olur;
   kilitli hesap yolunda `metadata = {"reason": "locked"}`, e-posta adresi
   metadata'ya yazılmaz. (AC-3)
4. [High] Given `locked_until <= now` (kilit süresi dolmuş) bir kullanıcı, When
   doğru parolayla giriş yapılır, Then 200 döner ve `failed_login_count = 0`,
   `locked_until = NULL` olarak kalıcı olur. (AC-4)
5. [Critical] Given `status = 'SUSPENDED'` veya `'DELETED'` bir kullanıcı, When
   doğru parolayla giriş denenir, Then 401 INVALID_CREDENTIALS döner (ACTIVE
   kullanıcının yanlış-parola hatasıyla **aynı** mesaj/kod — ayırt edici bilgi
   yok, numaralandırma koruması). (AC-5)
6. [Critical] Given var olan ACTIVE, kilitli olmayan kullanıcı, When doğru
   parolayla giriş yapılır, Then 200 döner, cookie'ler (access/refresh/csrf) ve
   yanıt gövdesi bu değişiklik öncesiyle birebir aynı davranır. (AC-6)
7. [High] Given `refresh_tokens()` çağrısında token'ın sahibi kullanıcının
   `status` alanı ACTIVE/PENDING değilse, When refresh denenir, Then
   `InvalidRefreshToken` fırlatılır. (AC-7, L-03 refresh tarafı)
8. [High] Given kilit süresi dolmuş (`locked_until <= now`) bir kullanıcı, When
   **yanlış** parolayla giriş denenir, Then sayaç önce 0'a sıfırlanır, bu yanlış
   deneme +1 olarak commit edilir (sonuç: `failed_login_count = 1`,
   `locked_until = NULL`), 401 INVALID_CREDENTIALS döner — yani süresi dolmuş
   kilit tek bir yanlış denemeyle yeniden aktive olmaz. (AC-8)
9. [Medium] Rollback semantiğini gerçekten sınayan en az bir test: üretimdeki
   `get_session` gibi `yield` + istisnada rollback yapan yerel bir generator
   override kullanılarak AC-1/AC-3'ün gerçekten rollback'e dayanıklı olduğu
   kanıtlanır (mevcut `tests/conftest.py::override_get_session` bunu YAPMIYOR —
   HATA.md TEST-02, bu görev onu değiştirmez, yalnız yerel bir override ekler).
10. [Critical] **(Güvenlik — threat-model)** Given kilitli hesap yoluna giden
    her DENIED audit satırı, When DB'den `audit_events.metadata` okunur, Then
    içerik yalnızca `{"reason": "locked"}` olur — email, password,
    password_hash gibi hiçbir PII alanı bulunmaz. (AC-S1)
11. [Critical] **(Güvenlik — threat-model)** Given SUSPENDED bir kullanıcı
    doğru parolayla, ACTIVE bir kullanıcı yanlış parolayla `POST /auth/login`
    çağırır, When iki yanıt karşılaştırılır, Then HTTP durum kodu, `error.code`
    ve `error.message` alanları **birebir aynıdır** (numaralandırma korumasının
    otomatik testle doğrulanan hâli — "aynı mesaj" iddiasının kendisi test
    edilir, varsayılmaz). (AC-S2)

## Agentic Değerlendirme Kriterleri
Tetikleyici yok — bu görev bir LLM agent/sub-agent tool-calling davranışını
veya prompt'unu değiştirmiyor, salt backend auth servis kodu.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: ACTIVE kullanıcı, doğru parola | 200 OK | `failed_login_count=0`; access/refresh/csrf cookie'leri set edilir; audit USER_LOGIN/SUCCESS | Giriş başarılı, mevcut body/cookie'ler | AC-6 |
| 2 | Kullanıcı yok (email kayıtlı değil) | 401 INVALID_CREDENTIALS | DENIED audit kalıcı (`actor_user_id=None`, `subject_id=None`); commit istisnadan önce | "E-posta veya parola hatalı" (numaralandırma korumalı) | AC-1, AC-3 |
| 3 | Var olan kullanıcı, yanlış parola | 401 INVALID_CREDENTIALS | `failed_login_count += 1` kalıcı; eşik aşıldıysa `locked_until` set edilir; DENIED audit kalıcı; commit istisnadan önce | "E-posta veya parola hatalı" | AC-1, AC-2, AC-3 |
| 4 | Kilitli hesap (`locked_until > now`) | 423 ACCOUNT_LOCKED | DENIED audit kalıcı, `metadata={"reason":"locked"}`, e-posta YAZILMAZ; commit istisnadan önce | "Hesabınız geçici olarak kilitlendi" (süre/deneme sayısı sızdırılmaz) | AC-2, AC-3 |
| 5 | Kilit süresi dolmuş (`locked_until<=now`), doğru parola | 200 OK | Sayaç 0'a, `locked_until=NULL`'a sıfırlanır; normal başarılı giriş | Giriş başarılı | AC-4 |
| 6 | Kilit süresi dolmuş (`locked_until<=now`), yanlış parola | 401 INVALID_CREDENTIALS | Önce sayaç 0'a sıfırlanır, sonra bu deneme +1 olarak commit edilir (`failed_login_count=1`, `locked_until=NULL`); DENIED audit kalıcı | "E-posta veya parola hatalı" | AC-8 |
| 7 | SUSPENDED/DELETED kullanıcı, doğru parola | 401 INVALID_CREDENTIALS (ACTIVE'in yanlış-parola hatasıyla aynı) | DENIED audit kalıcı | "E-posta veya parola hatalı" — ayırt edilemez | AC-5 |
| 8 | Refresh token'ın kullanıcısı ACTIVE/PENDING değil | `InvalidRefreshToken` → 401 | Mevcut hata biçimiyle tutarlı | Refresh reddedilir, yeniden login gerekir | AC-7 |

Kısmi başarı: Uygulanmaz — audit yazımı ve sayaç/kilit güncellemesi aynı
transaction içinde, tek `session.commit()` ile birlikte kalıcı olur; biri
yazılıp diğerinin yazılmadığı bir ara durum kod akışında oluşmaz.

Hiçbir şey yapılamadı ama hata yok: Uygulanmaz — her yol ya (a) DB'ye kalıcı
yazıp istisna fırlatır (401/423) ya da (b) DB'ye kalıcı yazıp 200 döner; sessiz
"hiçbir şey olmadı" dalı yok. `session.commit()` kendisi başarısız olursa (ör.
DB bağlantı hatası) bu görev özel bir davranış eklemiyor — SQLAlchemy istisnası
genel exception handler'a düşer, 500 döner (YAGNI; görev tanımında özel bir
istek yok).

Boş sonuç ↔ hata ayrımı: n/a — bu görev liste/koleksiyon dönmüyor, tekil
kimlik doğrulama sonucu (200 ya da tipik hata kodu) dönüyor.

Girdi geçersiz/eksik (satır silinmedi, kapsam dışı olarak not düşüldü): Mevcut
Pydantic şema validasyonu (422) değişmiyor, bu görevin kapsamında değil.
Zaman aşımı (satır silinmedi, kapsam dışı olarak not düşüldü): Ayrı ele
alınmıyor, DB bağlantı hatasıyla aynı genel 500 yoluna girer.
Yetkisiz erişim (satır silindi): n/a — login akışı kimliksiz çalışır, kaynak-
sahiplik/404 kuralı burada uygulanmaz.

## Test Strategy
Unit: 15% — eşik karşılaştırma mantığı (`failed_login_count >= THRESHOLD`),
kilit süresi sınır durumu (`locked_until == now` → sıfırlama tarafında).
Integration: 80% — gerçek `Session` + rollback yapan gerçek/yerel `get_session`
semantiğiyle AC-1, AC-2, AC-3, AC-4, AC-5, AC-7, AC-8, AC-9; bulgunun kendisi
bir DB-persistence/transaction hatası olduğu için ağırlık burada.
E2E: 5% — `POST /auth/login` tam HTTP akışı, cookie/body değişmediğini
doğrulayan 1-2 test (AC-6).

## Benchmark / Başarı Ölçütü
Coverage Target: %90 (değiştirilen `authenticate()`/`refresh_tokens()`
fonksiyonları için; proje genel eşiği %85, bu görev auth-kritik olduğu için
daha yüksek hedeflenir).
Performance Target: Belirtilmedi/kritik değil — ek bir `commit()` çağrısı
mikrosaniye-milisaniye mertebesinde, görev performans değil güvenlik/doğruluk
odaklı (CLAUDE.md'de proje genelinde açık bir SLA yok).
Memory: Belirtilmedi.
Görsel/UI kriteri: n/a — backend-only değişiklik, UI yok.
Diğer ölçülebilir kriterler: Bilinen kırık test sayısı (HATA_DUZELTME_PROMPT.md
§1.7) bu değişiklikten sonra **artmamalı**.

## Kapsam Dışı
- IP bazlı hız sınırı (A-10'un işi).
- Kayıt zamanlaması/timing saldırıları (A-10'un işi).
- Multi-factor authentication, CAPTCHA.
- Kilitlendiğinde kullanıcıya e-posta/SMS bildirimi.
- Admin panelinden manuel kilit açma arayüzü.
- Kilit süresi/eşik sabitlerini yapılandırılabilir kılmak (10 deneme, 15 dk
  sabit kalacak).
- Ayrı bir audit "UNLOCK" event tipi eklemek.
- `tests/conftest.py::override_get_session`'ın genel olarak düzeltilmesi
  (HATA.md TEST-02 — A-13'ün işi); bu görev yalnız kendi test dosyasında
  yerel bir doğru-davranan override kullanır.
- `backend/app/core/deps.py`'ye dokunmak — production `get_session` zaten
  doğru davranıyor (rollback yapıyor), değişiklik gerekmiyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/services/auth.py` — `authenticate()` (erken commit, kilit-
  süresi-dolmuş sıfırlama, L-03 status kontrolü) ve `refresh_tokens()` (L-03
  status kontrolü).
- `backend/tests/` — mevcut auth servis test dosyası (kesin ad `plan` adımında
  kod keşfiyle netleşecek) + rollback semantiğini sınayan yerel generator
  override içeren yeni/genişletilmiş test(ler).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu oturumda git kökünün proje klasörüyle (`C:\Users\Meyrem\
Desktop\P\yetkin360`) aynı olup olmadığı ayrıca teyit edilmedi, ancak ek
çalışma dizinleri (environment bilgisinde listelenen, ilgisiz başka projeler)
mevcut. Sonraki adımlarda (`plan`, `test-copilot`, `code-copilot`, `red-team`)
arama bu proje klasörüyle sınırlı tutulmalı; kök dizinden sınırsız `grep -r`
veya `git log -p --all` kullanılmamalı.

## Rollback Beklentisi
`session.commit()` kendisi başarısız olursa (DB bağlantı hatası vb.) özel bir
try/except eklenmiyor — istisna genel exception handler'a düşer, 500 döner;
bu durumda commit edilmediği için DB durumu değişmemiş kalır (YAGNI, görev
tanımında özel bir istek yok).

## Risks
- Erken `commit()` deseni transaction'ı ikiye böler; bu spesifik akışta
  commit'ten sonra aynı request içinde başka bir DB işlemi yapılmıyor (risk
  yok), ama ileride bu fonksiyona commit'ten sonra kod eklenirse bu risk
  unutulabilir (kod yorumunda `refresh_tokens()`'taki gibi açıkça belirtilmeli).
- Testte kullanılacak yerel "rollback simülasyonu yapan generator override"
  production `get_session` ile davranışsal olarak tam örtüşmeyebilir (ör.
  finally/close sırası) — bu yüzden override'ın `get_session`'ın gerçek
  yapısını (yield → commit / except → rollback+raise / finally → close)
  birebir taklit etmesi gerekiyor.
- **(Kabul edilen risk — threat-model AC-S3, DoS):** Bu kilitleme mekanizması,
  saldırganın yalnızca kurbanın email adresini bilerek (parolasını bilmeden)
  kurbanın hesabını art arda 10 yanlış denemeyle 15 dakika kilitleyebilmesine
  izin verir (hedefli DoS). IP bazlı hız sınırı olmadığı için bu risk MVP'de
  **bilinçli olarak kabul edilmiştir** (K1 kararı: davet akışı yok; A-10 IP
  bazlı hız sınırını ayrıca ele alacak). Bu görev bu riski **azaltmaz** —
  yalnızca mekanizmanın rollback'e karşı güvenilir/kalıcı çalışmasını sağlar;
  risk zaten var olan tasarımın bir parçasıdır, bu görevle büyümez.
- **(Kabul edilen risk — threat-model, bilgi sızıntısı):** 423 ACCOUNT_LOCKED
  yanıtı, isteği yapan tarafa "bu email'e ait bir hesap var ve kilitli"
  bilgisini zaten sızdırır (var olan tasarım kararı, GUV-01/K1 kapsamı dışı).
  Bu görev bu sızıntıyı büyütmez veya küçültmez, mevcut haliyle bırakır.

## Assumptions
- `log_audit_event` zaten `session.flush()` kullanıyor (kod okumasıyla
  teyitli), bu yüzden erken `commit()` öncesi ek bir flush gerekmiyor.
- Var olan test dosyasının tam yolu `plan` adımında netleşecek (bu adımda
  "muhtemelen tests/ altında bir auth servis test dosyası" varsayımıyla
  bırakıldı).

## Unknowns
- Mevcut auth servis test dosyasının kesin adı/yolu (plan adımında Glob/Grep
  ile netleştirilecek).

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Sistem kendisi (güvenlik düzeltmesi); brute-force taraf + meşru
   kullanıcı senaryoya zımnen dahil, ayrı AC gerektirmiyor. (Sonnet 5 low
   alt-ajanı tarafından yanıtlandı)
2. Hedef/neden → Rollback'in sayaç/kilit/audit izlerini silmesi sorunu; erken
   commit ile bu izler rollback'ten bağımsız kalıcı hale geliyor. (Sonnet 5
   low alt-ajanı tarafından yanıtlandı, kod okumasıyla teyitli)
3. Happy path → ACTIVE + doğru parola → 200, sayaç sıfırlanır, cookie'ler set
   edilir, davranış değişmiyor. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
4. Edge case (10. deneme) → 10. deneme kendisi 401 döner ama locked_until'i
   set eder; 11. deneme 423 döner (increment sonrası eşik kontrolü). (Sonnet 5
   low alt-ajanı tarafından yanıtlandı, kod sıralamasıyla teyitli)
5. Edge case (locked_until==now sınırı) → Kilitli SAYILMAZ, `>` strict
   karşılaştırma; sıfırlama tarafında. (Sonnet 5 low alt-ajanı tarafından
   yanıtlandı, görev tanımındaki `<=` ifadesiyle tutarlı)
6. Davranış sözleşmesi kısmi başarı/sessiz başarı → İkisi de uygulanmaz;
   gerekçeler yukarıdaki tabloda. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
7. Coverage/performans → %90 coverage (auth-kritik); performans belirtilmedi.
   (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Kapsam dışı ek → MFA, CAPTCHA, kilit bildirimi, admin unlock UI, sabit
   yapılandırılabilirliği, UNLOCK audit tipi. (Sonnet 5 low alt-ajanı
   tarafından yanıtlandı)
9. Etkilenen dosyalar → auth.py kesin; deps.py'ye DOKUNULMUYOR (production
   zaten doğru); test dosyası adı plan adımında netleşecek. (Sonnet 5 low
   alt-ajanı tarafından yanıtlandı)
10. Erken commit riski → Bu akışta risk yok (commit sonrası başka DB işlemi
    yok); genel risk ikiye bölünmüş transaction, emsal zaten refresh_tokens()
    içinde kabul edilmiş. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
11. Commit başarısızlığı → Özel davranış yok, genel exception handler'a düşer,
    500. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
12. Kabul kriteri sahibi → Otomatik testler yeterli; ancak auth mantığı
    değişikliği olduğu için kod yazmadan önce kullanıcı onayı da gerekiyor
    (CLAUDE.md "onay sınırları"). (Sonnet 5 low alt-ajanı tarafından
    yanıtlandı; ayrıca kullanıcı görevinde "ONAY NOKTASI" zaten açık talimat)
13. Test stratejisi oranı → unit 15 / integration 80 / e2e 5 (DB-persistence
    hatası olduğu için entegrasyon ağırlıklı). (Sonnet 5 low alt-ajanı
    tarafından yanıtlandı)
14. Riskler/varsayımlar/bilinmeyenler → Yukarıdaki Risks/Assumptions/Unknowns
    bölümlerine işlendi. (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
