---
task_slug: yet-3-yetkilendirme-test-iskeleti
jira_id: YET-3
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 100
performance_target: null
memory_target: null
test_strategy:
  unit: 20
  integration: 70
  e2e: 10
affected_modules:
  - backend/tests/authorization/ (yeni paket — mevcut backend/tests/test_authorization.py'nin yerini alır)
  - backend/tests/authorization/conftest.py (yeni — Org A/B, Talent A/B fixture'ları)
  - backend/tests/authorization/matrix.py veya matrix.yaml (yeni — parametrik matris kaynağı)
  - backend/app/services/authorization.py (mevcut — DEĞİŞMEZ, sadece test edilir)
  - docs/AUTHORIZATION.md (mevcut — matris kaynağı, değişmez)
---

# ATDD — yet-3-yetkilendirme-test-iskeleti

## Jira Kaynağı
[YET-3 — [PLAN 1.3] Yetkilendirme test iskeleti + fixture'lar (aktör matrisi)](https://kuyusuzyusuf123.atlassian.net/browse/YET-3)

User Story (Jira'dan birebir): "As a developer adding any new endpoint I want a ready authorization test matrix (actor × resource × action × expected HTTP code) with fixtures So that I cannot forget to test an unauthorized-access path before merging"

Açıklama (Jira'dan birebir): "PLAN.md Faz 1, madde 1.3. Owner: backend-2. 1.2'deki can()/scoped_*() çekirdeğinin test iskeleti. docs/AUTHORIZATION.md'deki matrisle birebir örtüşmeli. Yeni endpoint eklenen her commit'te bu paket genişler (CLAUDE.md: 'Testsiz endpoint commit edilmez')."

PLAN.md doğrulaması: Faz 1, madde 1.2 (`can()`/`scoped_*()`/`audit_events`) `[x]` tamamlanmış — YET-3 artık bloke değil. Madde 1.3 kendisi `[ ]`.

**Kapsam sınırlama kararı (YET-2'nin kendi kararıyla tutarlı, önemli):** `docs/AUTHORIZATION.md` §5'teki tam test matrisi (A1-H4, 45+ satır) `Engagement`/`Evidence`/`Evaluation`/`Attestation` gibi Faz 2 tablolarına dayanıyor — bu tablolar henüz yok (`yet-2-yetkilendirme-cekirdegi/atdd.md`da aynı gerekçeyle aynı sınırlama zaten yapılmış: "Tam test matrisi Engagement vb. YET-7/8/9'da genişleyecek"). Bu görev (1.3), **mevcut 7 tablo + mevcut `can()`/`scoped_organizations()`/`scoped_talent_profiles()` yüzeyi** üzerinde çalışan, **yeniden kullanılabilir bir parametrik fixture/matris iskeleti** kurar — matrisin kendisini genişletmez (yeni iş kuralı/yetki kararı yazmaz), sadece var olan `test_authorization.py`'deki ad-hoc testleri **matris satırı → parametrize test** desenine taşır ve CI'nin "yeni satır eklenmeden yeni uç geçemez" kuralını uygulanabilir hale getirir. `YET-7/8/9` (Engagement/Evidence/Evaluation) geldiğinde bu iskelete matris satırı eklemek yeterli olacak — kod tekrar yazılmayacak.

## Persona
Backend geliştirici — `YET-7/8/9/10/11` gibi yeni bir uç eklerken, o ucun yetkilendirme testini bu iskelete matris satırı olarak eklemesi gereken kişi (Jira User Story'sinden birebir).

## Hedef (Neden)
`docs/AUTHORIZATION.md`'nin "her satır bir testtir" ilkesini (§5, §6) gerçek, parametrik bir pytest paketine dönüştürmek — CI'nin "yetkilendirme testi olmadan yeni uç geçmez" kuralını (CLAUDE.md, docs/AUTHORIZATION.md §6) mekanik olarak uygulanabilir kılmak. Şu an `test_authorization.py` elle yazılmış, matrisle birebir izlenebilir değil; bu görev onu matris-satırı → test eşlemesi olan bir yapıya taşır.

## User Story
As a backend developer adding any new endpoint
I want a ready authorization test matrix (actor × resource × action × expected HTTP code) with fixtures
So that I cannot forget to test an unauthorized-access path before merging

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given mevcut `can()`/`scoped_organizations()`/`scoped_talent_profiles()` yüzeyi, When bu fonksiyonlar için docs/AUTHORIZATION.md §5 formatında (aktör, kaynak, eylem, beklenen sonuç) parametrize bir matris tanımlanıp `backend/tests/authorization/` altında çalıştırıldığında, Then her satır ayrı bir test-case olarak görünür (pytest `-v` çıktısında satır kimliği okunur, ör. `test_matrix[A5-org_member-read_member_list]`).
2. [Critical] Given `docs/AUTHORIZATION.md`'de zaten YET-2 kapsamında test edilmiş satırlar (AC-S2 tenant izolasyonu: Org A/B, Talent A/B), When bu satırlar yeni parametrik yapıya taşındığında, Then eski `test_authorization.py`'deki assertion'ların hiçbiri kaybolmaz (davranış korunur, sadece organizasyon değişir).
3. [Critical] Given `conftest.py`'de tanımlı ortak fixture'lar (Org A, Org B, Talent A, Talent B, ilgili `OrganizationMember`/`Principal` nesneleri), When yeni bir matris satırı eklenmek istendiğinde, Then geliştirici yeni bir DB kurulum kodu yazmadan sadece `(aktör_fixture, kaynak_fixture, eylem, beklenen_sonuç)` dörtlüsünü matrise ekler.
4. [High] Given matriste bir satır `can()`/`scoped_*()`'te karşılığı olmayan bir eylem/kaynak tanımlarsa (ör. henüz yazılmamış bir `scoped_evidence()`), When test-suite toplanırken (collection) bu satıra rastlanırsa, Then açıkça `pytest.skip("YET-7/8/9 bekleniyor: scoped_evidence() henüz yok")` ile işaretlenir — sessizce yok sayılmaz, CI raporunda "SKIPPED (gerekçeli)" olarak görünür.
5. [High] Given CI'da `pytest tests/authorization -q` çalıştırıldığında, When test suite'i sıfır assertion çalıştırırsa (boş matris / yanlış fixture eşleşmesi), Then bu durum otomatik FAIL sayılır ("en az 1 matris satırı çalıştı" guard'ı — `conftest.py`'de bir `pytest_collection_modifyitems` veya eşdeğeri ile uygulanır).
6. [Medium] Given mevcut `can()`'ın tanımadığı bir `(kind, action)` kombinasyonu matriste "beklenen: reddedilir" olarak işaretliyse, When test çalıştığında, Then `can()`'ın default-deny davranışı (AC-S1, YET-2) bu matris satırıyla da doğrulanır — aynı davranış iki farklı dosyada iki kez farklı şekilde test edilmez, matris tek kaynak olur.

## Threat Model
Çağrıldı. STRIDE-lite (bu görevin gerçek yüzeyine — bir test-altyapısı paketine — uyarlanmış):
- **Elevation of Privilege / Information Disclosure (asıl risk, bu paketin var olma sebebi):** Yeni bir uç eklendiğinde matrise satır eklemeyi unutmak = o ucun yetkisiz-erişim senaryosunun hiç test edilmemesi. AC-4 ve AC-5 bunu ele alır: karşılığı olmayan satır sessizce atlanamaz (gerekçeli skip zorunlu), boş/no-op test suite otomatik FAIL sayılır.
- **Repudiation:** Bu paket loglama eklemiyor (AuditEvent zaten YET-2'de var) — kapsam dışı, kabul edilen risk olarak aşağı yazıldı.
- **Spoofing, Tampering, DoS:** Bu görevde HTTP yüzeyi yok (test-altyapısı, `can()`/`scoped_*()` doğrudan çağrılıyor, request/token parsing yok) — YET-2'nin kendi threat-model kararıyla aynı gerekçeyle kapsam dışı.

AC-S kriterleri ayrı bölüm açılmadan yukarıdaki Acceptance Criteria'ya (AC-4, AC-5) gömüldü.

`authz-test` skill notu: Bu görev zaten `authz-test`'in önerdiği "en az iki principal (Org A/Org B) karşılaştırmalı test" ve "boş liste PASS'e çevrilmez" ilkelerini YET-2'den devralıyor (bkz. yet-2-yetkilendirme-cekirdegi/atdd.md Threat Model bölümü) — bu görev o ilkeleri TEKRARLAMAZ, sadece onları yeniden kullanılabilir hale getirir. `test-copilot` adımında `authz-test` skill'i yine de bir kez daha çağrılmalı: yeni fixture yapısının BOLA/tenant-izolasyon kalıbını gerçekten koruyup korumadığı (ör. fixture paylaşımı yüzünden testler arası veri sızıntısı olmaması) doğrulanmalı.

## Agentic Değerlendirme Kriterleri
Tetikleyici yok — klasik backend test-altyapısı görevi, LLM agent davranışı değiştirmiyor.

## Davranış Sözleşmesi (hangi durumda ne döner)
Bu bir test-altyapısı görevi (HTTP endpoint değil) — "dönen değer" pytest sonucu/CI durumu.

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — matris satırı mevcut `can()`/`scoped_*()` ile eşleşiyor | pytest PASS | Yok | CI yeşil | AC-1, AC-2 |
| 2 | Girdi geçersiz — matris satırı tanımsız aktör/kaynak/eylem içeriyor | Test collection'da açık hata (fixture bulunamadı) | Test suite hiç çalışmaz | CI kırmızı, "fixture 'X' tanımsız" hatası | AC-3 |
| 3 | Kaynak yok — henüz yazılmamış `scoped_*()`/`can()` yüzeyine atıfta bulunan satır | `pytest.skip(gerekçe)` | Yok | CI'da "SKIPPED: YET-7/8/9 bekleniyor" — FAIL değil ama görünür | AC-4 |
| 4 | Kısmi başarı — bazı matris satırları geçti, bazıları skip/fail | Coverage raporu satır bazında ayrılır | Yok | "42/45 PASS, 3 SKIP (gerekçeli)" — "kısmen geçti" diye tek yeşil rozet YASAK | AC-1 |
| 5 | Hiçbir şey yapılamadı ama hata yok — boş/no-op matris | CI FAIL | Yok | "0 assertion çalıştı" hatası | AC-5 |

Uygulanmayan satırlar ve nedeni:
- **Yetkisiz erişim (401/403/404 dönmesi):** Bu satır YET-2'nin kendi davranış sözleşmesinde zaten var (`can()` False / `scoped_*()` boş sonuç) — bu görev onu TEKRAR tanımlamıyor, sadece test-organizasyonunu değiştiriyor. Ayrı satır açmak yanıltıcı olur.
- **Dış bağımlılık hatası / Zaman aşımı:** Silindi — YET-2 ile aynı gerekçe: bu katman gerçek Postgres'e karşı çalışıyor ama ağ/timeout mantığı barındırmıyor, connection pool seviyesinde yönetiliyor.

Kısmi başarı: Yukarıdaki tabloya işlendi (satır 4) — skip'ler PASS'e karışmaz, ayrı sayılır.
Hiçbir şey yapılamadı ama hata da yok: Boş/no-op matris CI'de otomatik FAIL (satır 5) — bu, threat-model'in ana riskiyle (satır eklemeyi unutmak) doğrudan bağlantılı.
Boş sonuç ↔ hata ayrımı: "Matriste bu satır yok" (henüz yazılmamış) ile "satır var ama FAIL" CI raporunda ayrı kategoriler (SKIP vs FAIL) olarak gösterilir, aynı sembolle karıştırılmaz.

## Test Strategy
Unit: 20% — matris/fixture yükleme mantığının kendisi (parametrize decorator'ın doğru satır sayısı ürettiği, skip mantığı).
Integration: 70% — gerçek Postgres'e karşı, taşınan + genişletilen `can()`/`scoped_*()` testleri (YET-2'nin mevcut testlerinin yeni yapıya taşınmış hali + docs §5'in şu an testedilebilir alt-kümesi: A5 benzeri org-scope, tenant izolasyonu tekrarları farklı fixture kombinasyonlarıyla).
E2E: 10% — Principal oluştur → scoped_*() → can() zincirinin matris-güdümlü birkaç uçtan-uca senaryosu (HTTP yok, YET-2'yle aynı sınır).

## Benchmark / Başarı Ölçütü
Coverage Target: %100 — **mevcut** `can()`/`scoped_organizations()`/`scoped_talent_profiles()` yüzeyinin (Engagement/Evidence gibi henüz var olmayanlar hariç) docs/AUTHORIZATION.md formatındaki her test edilebilir satırının matriste karşılığı olması.
Performance Target: Yok.
Memory: Yok.
Diğer ölçülebilir kriterler: CI'da "boş matris = FAIL" guard'ının aktif olması (AC-5); YET-2'nin mevcut test sayısının (bkz. `test_authorization.py`, ~20 test) yeni yapıya taşındıktan sonra azalmaması.

## Kapsam Dışı
- `docs/AUTHORIZATION.md` §5'teki tam matris (A1-H4) — `Engagement`/`Evidence`/`Evaluation`/`Attestation` kaynaklarına dayanan satırlar (Faz 2, `YET-7/8/9` bekliyor). Bu satırlar iskelette `pytest.skip` ile yer tutucu olarak durabilir ama şimdi implemente edilmez.
- `can()`/`scoped_*()`'in kendi iş mantığının genişletilmesi (ör. `TalentProfile.visibility`'ye göre yeni bir `scoped_*` filtresi, `can()`'a yeni action eklemek) — bu, YET-3'ün değil ileriki uç-özel görevlerin (`YET-7` vb.) işi. YET-3 sadece MEVCUT yüzeyi test eder, yeni yetki kararı yazmaz.
- HTTP endpoint entegrasyonu (401 dönmesi vb.) — henüz hiçbir korumalı HTTP ucu yok (`app/main.py` sadece `/health`).
- Break-glass admin akışı, RLS — Faz 5 (docs/AUTHORIZATION.md §3, §4.1).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/tests/authorization/` (yeni paket: `__init__.py`, `conftest.py`, matris tanımı, test dosyaları) — `backend/tests/test_authorization.py`'nin yerini alır (içerik taşınır, silinmez kaybolmaz).
- `backend/tests/test_authorization.py` — yeni pakete taşındıktan sonra kaldırılır (dosya silme, CLAUDE.md'ye göre önce onay gerekir — bkz. Assumptions).
- `backend/app/services/authorization.py`, `docs/AUTHORIZATION.md` — okunur, DEĞİŞTİRİLMEZ.
- `backend/pytest.ini`/`pyproject.toml` (varsa) — `tests/authorization` yolunun test-discovery'de doğru göründüğünden emin olmak için kontrol edilir, gerekirse küçük bir path güncellemesi.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı: `projelerim/yetkin360` kendi git reposu (`projelerim/obss`'den tamamen bağımsız — Jira YET-3 önce yanlışlıkla `obss` reposunda arandı ve bulunamadı, kullanıcı doğru yolu verdi). `backend/.venv/` altında devasa bir site-packages ağacı var — Grep/Glob **her zaman** `backend/app`, `backend/tests`, `docs/`, `PLAN.md` ile sınırlanmalı, `backend/` kökünden veya `.venv` dahil geniş tarama YAPILMAMALI (bir önceki adımda `find backend` komutu yanlışlıkla `.venv`'i tarayıp 135KB çıktı üretti — bu tekrarlanmamalı, `-path ./.venv -prune` veya eşdeğeri zorunlu).

## Rollback Beklentisi
Sadece test dosyaları + fixture'lar — üretim kodu (`authorization.py`) değişmiyor. Migration yok. Hatalı/eksik fixture eklenirse PR revert edilir, veri/canlı kullanıcı etkisi yok.

## Risks
- **Kabul edilen risk (Repudiation/Spoofing/Tampering/DoS kapsam dışı):** YET-2'nin kendi kabul ettiği risklerle aynı — bu paket HTTP yüzeyi/loglama eklemiyor, sadece mevcut `can()`/`scoped_*()`'i test ediyor.
- Matrisin "genişleyecek" tasarımı (skip yer tutucularıyla) ileride birinin skip'i unutup gerçek implementasyon olmadan "geçti" sanmasına yol açabilir — AC-4'teki gerekçeli-skip zorunluluğu bu riski azaltır ama CI raporunu okumayan biri için sıfırlamaz (kabul edilen kalıntı risk).
- `test_authorization.py`'nin silinmesi CLAUDE.md'nin "var olan dosyayı değiştirmeden önce ne değişeceğini söyle" ve "dosya silme → onay gerekir" kurallarına tabi — `code-copilot`/`test-copilot` bunu tek taraflı silmemeli, kullanıcıya söylenmeli (bkz. Assumptions).
- **`dynamic-pentest` ile pekiştirilmiş kalıntı risk (2026-09-21, `dynamic_pentest.json`):** `can()`/`scoped_organizations()`/`scoped_talent_profiles()` `Principal` nesnesinin `org_ids`/`org_admin_ids`/`kind` alanlarına DB'ye karşı hiçbir yeniden doğrulama yapmadan kör güveniyor. Gerçek bir çalıştırmayla doğrulandı: elle sahte `org_admin_ids` verilen bir `Principal` ile `can(principal, "admin_update", org)` gerçekten `True` döndü. Şu an saldırgan tarafından erişilemez çünkü henüz `Principal`'ı istemci girdisinden kuran bir HTTP/middleware katmanı yok (YET-2'nin kendi varsayımıyla tutarlı) — ama bu varsayımı doğrulayan hiçbir test/kontrat mevcut değil. **Öneri:** `Principal`'ı gerçek isteklerden inşa edecek görev (muhtemelen YET-4, auth/middleware) bunu DB'den taze sorgulayarak kurduğunu kanıtlayan bir test eklemeli.

## Assumptions
- `test_authorization.py`'deki mevcut testlerin İÇERİĞİNİN (assertion'ların) yeni `tests/authorization/` paketine taşınacağı, silinmeyeceği varsayıldı — CLAUDE.md'nin dosya silme onay kuralı gereği gerçek silme işlemi `test-copilot`/`code-copilot` adımında kullanıcıya ayrıca bildirilmeli.
- Matris formatının Python içinde (ör. bir liste-of-dataclass veya `pytest.mark.parametrize`) tutulacağı varsayıldı, ayrı bir YAML/JSON dosyası değil — docs/AUTHORIZATION.md zaten Markdown tablo, ekstra bir format katmanı CLAUDE.md'nin "gereksiz soyutlama yok" ilkesine aykırı olurdu.
- Saga entegrasyonu bu oturumda kurulamadı (bağlantı hatası, önceki `atdd` denemesinde tespit edildi) — `saga_task_id: null`.

## Unknowns
- `backend/pytest.ini`/`pyproject.toml`'da test-discovery ayarları henüz okunmadı — `plan` adımında `tests/authorization/` alt-paketinin otomatik keşfedildiğinden emin olunmalı.
- CI pipeline config'i (`.github/workflows/`) henüz okunmadı — "boş matris = FAIL" guard'ının CI'da gerçekten yeşil/kırmızı olarak yansıyıp yansımadığı `verify` adımında doğrulanmalı.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → Backend geliştirici, yeni endpoint eklerken (Sonnet 5 low alt-ajanı tarafından yanıtlandı, ilk taslakta — Jira User Story'sinden)
2. Ana hedef/neden → Matris satırlarını unutmadan test edilebilir kılmak (Sonnet 5 low alt-ajanı tarafından yanıtlandı, ilk taslakta)
3. Kapsam sınırlama kararı (Engagement/Evidence hariç mevcut yüzeyle sınırlı) → gerçek koda bakılınca (backend/app/models, backend/app/services/authorization.py) çıkarıldı; YET-2'nin kendi atdd.md'sindeki aynı kararla (satır 31) doğrulandı — bu, kullanıcı mesajından değil, doğrudan repo keşfinden.
4. Davranış sözleşmesi tablosu → yukarıya işlendi, "yetkisiz erişim" satırı YET-2'yle çakışmaması için silindi ve gerekçesi yazıldı.
5. Başarı ölçütü → mevcut yüzeyin %100 kapsaması (repo keşfinden çıkarıldı, ilk taslaktaki "tüm matris" hedefinden daraltıldı).
6. Kapsam dışı → tam matris + iş mantığı genişletmesi + HTTP entegrasyonu (repo keşfinden).
7. Bağımlılıklar → `authorization.py`, `docs/AUTHORIZATION.md`, mevcut `test_authorization.py` (artık gerçek dosya yollarıyla doğrulandı — ilk taslaktaki "varsayımla" notu kaldırıldı).
8. Threat-model tetikleyici → var (yetkilendirme), `threat-model` skill'i çağrıldı, AC-4/AC-5 buradan üretildi.
9. Test stratejisi oranı → unit 20/integration 70/e2e 10, YET-2'nin (40/50/10) DB-ağırlıklı deseniyle tutarlı ama bu görev saf test-altyapısı olduğu için unit payı biraz düştü, integration arttı (bu oturumda karar verildi, kullanıcıya ayrıca sorulmadı çünkü YET-2 emsali zaten var).
10. Proje dizini → İlk denemede `obss` reposunda arandı, bulunamadı; kullanıcı doğru yolu (`projelerim/yetkin360`) verdi, oturum bu dizine taşındı.
