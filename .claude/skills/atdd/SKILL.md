---
name: atdd
description: Tool-independent ATDD skill — asks 8-12 adaptive clarification questions (skips categories the user already answered), writes atdd.md with YAML frontmatter (task_slug, priority, coverage_target, performance_target, test_strategy, affected_modules) + Markdown body (Persona, Goal, User Story, prioritized Acceptance Criteria, a mandatory behaviour-contract table pinning what each error case returns, Risks/Assumptions/Unknowns, Test Strategy, Benchmark). Does NOT chain into other pipeline steps (see pipeline). For Jira sync see `jira-sync`, for Saga tasks see `saga` skill.
---

# ATDD Skill

> **KURAL: Netleştirme soruları kullanıcıya değil, otomatik yanıtlanır.**
> `AskUserQuestion` bu skill'de artık KULLANILMAZ — aşağıdaki 4z adımı
> soruları doğrudan bir **Sonnet 5 alt-ajanına** (`Agent`, `model: "sonnet"`,
> `reasoning_effort: "low"`) dispatch eder. Kullanıcı hiç durdurulmaz.
> `claude-omni`/OmniRoute bu akıştan tamamen çıkarıldı (2026-09-05) —
> işlevsizdi (kurulum/child-process/kredi sorunları canlı olarak tekrar
> tekrar tespit edildi) ve fallback zaten her seferinde Sonnet 5'e
> düşüyordu. Cevaplar atdd.md'ye "Sonnet 5 alt-ajanı tarafından yanıtlandı"
> notuyla işlenir — kullanıcı cevabıymış gibi gizlenmez.

## Kullanılacak destek skiller
- `caveman`, `ponytail` (full) — her zaman aktif.
- `superpowers:brainstorming` — kapsam belirsizse, 8-12 soruluk soru listesini hazırlamadan önce.

Bu skill, sonraki pipeline adımlarının (`plan`/`code-copilot`/`test-copilot`/
`verify`/`red-team`) referans aldığı **tek gerçek kaynağı** (`atdd.md`)
üretir. Tek işi budur — Jira senkronizasyonu **`jira-sync`** skill'inde, 
Saga senkronizasyonu **`saga`** skill'inde, adımlar arası geçiş **`pipeline`** 
skill'indedir. Bu araçları karıştırma: burada doğrudan Jira/Saga çağrısı 
yapma (bunun yerine ilgili skill'i çağır), burada bir sonraki skill'e otomatik geçme.

## Adımlar

0. **Fast-Track Kontrolü:** Görev çok küçük, basit ve düşük riskliyse (örn. yazım hatası, CSS renk değişimi, ufak linter düzeltmesi), ATDD sürecini BAŞLATMA. Doğrudan `fast-track` skill'ine devret.
1. **Görev slug'ı belirle.** Kullanıcının isteğinden kısa bir `kebab-case`
   slug türet (örn. `pdf-export-butonu`). Kullanıcıya onaylat.
2. **Jira veya Saga bağlamı gerekiyorsa ilgili skill'i (`jira-sync` veya `saga`) çağır, kendin sorgulama.**
   - Kullanıcı bir Jira ID verdiyse (örn. "KAN-14'ten devam") önce `jira-sync`
     ile issue'yu çek, dönen bilgiyi (özet, AC, öncelik, `saga_task_id`) burada kullan.
   - Kullanıcı bir Saga ID verdiyse (örn. "Saga #254'ten devam") `saga` skill'ini
     çağırarak (özellikle `mcp__saga__task_get` üzerinden) task'ın güncel bilgilerini
     (title, description, priority vs.) çekip burada kullan. İkinci kez sorgu atma.
   - **Ne Jira ne Saga ID'si verilmediyse (yerel/yeni görev) — yine de bir
     Saga task'ı olmalı, yoksa oluştur.** `mcp__saga__task_list` (veya
     `tracker_search`) ile bu task-slug için zaten bir Saga kaydı var mı
     kontrol et; yoksa `mcp__saga__task_create` ile aç. Başlık formatı
     **zorunlu**: `<proje klasörü adı> - <görev başlığı>` (örn.
     `my-app - feature-slug`). Dönen `task_id`'yi atdd.md'nin
     frontmatter'ına (`saga_task_id`) yaz — bu, uzun bir pipeline sohbeti
     yarıda kesilip yeni bir sohbette devam edilmek zorunda kalırsa (bkz.
     `pipeline` skill'inin "context doldu" notu) ilerlemenin kaybolmaması
     içindir.
3. **Kullanıcının mesajında zaten netleşmiş kategorileri tespit et.** Aşağıdaki
   9 kategoriyi gözden geçir; kullanıcı bir kategoriyi zaten somut ve
   belirsizlik bırakmayacak şekilde yanıtlamışsa (mesajında veya jira-sync'in
   getirdiği AC'lerde) o kategori için **yeniden sorma** — mevcut bilgiyi
   "Sorular ve Cevaplar" bölümüne `(kullanıcı mesajından)` notuyla yaz.
4. **Adaptif olarak 8-12 soru sor** (minimum 8, maksimum 12 — kaç kategori
   zaten netse o kadar az sor, hiçbiri netse üst sınıra çık). Kategoriler:
   - Kullanıcı rolü / persona ("kim kullanacak?")
   - Ana hedef / "neden" (bu özellik hangi sorunu çözüyor?)
   - Happy path senaryosu (adım adım, somut girdi/çıktı)
   - En az 2 edge case / hata senaryosu
   - **Davranış sözleşmesi: hangi durumda ne dönecek** (aşağıda 4a —
     bu kategori atlanamaz, "hata olursa hata döner" cevabı kabul edilmez)
   - Başarı ölçütü / benchmark (ölçülebilir: süre, doğruluk, coverage,
     performans, hata oranı vb. — sayısal hedef iste, "iyi olsun" yetmez)
   - Kapsam dışı (explicitly out of scope — ne YAPILMAYACAK)
   - Bağımlılıklar / etkilenen mevcut dosyalar-modüller
   - Performans/güvenlik kısıtı varsa
   - Geri dönüş/rollback beklentisi (hata olursa ne olmalı)
   - Kabul kriteri sahibi kimin onayı yeterli (kullanıcı mı, otomatik test mi)
   - Test stratejisi oranı (unit/integration/e2e yüzdeleri) — kullanıcı
     bilmiyorsa proje tipine göre makul bir varsayılan öner (örn. backend
     API: 70/20/10) ve onaylat, "belirtilmedi" bırakma
   - Bilinen riskler/varsayımlar/bilinmeyenler (varsa)

4z. **Soruları Sonnet 5 alt-ajanına (low reasoning effort) dispatch et —
   `AskUserQuestion` YOK.**
   4. adımdaki soru listesini kullanıcıya sorma. Prompt'u hazırla:

   ```
   Aşağıdaki özellik için ATDD netleştirme sorularını YANITLA.
   BU BİR ARAŞTIRMA GÖREVİ DEĞİL — hiçbir tool (Read/Grep/Glob/
   WebSearch/Bash vb.) KULLANMA, kod tabanını tarama. SADECE aşağıda
   verilen bağlamdan en makul cevabı seç/üret. Bağlam yetersizse bile
   araştırmaya başlama — en makul varsayımı gerekçesiyle yaz.
   Her soru için en makul/varsayılan seçeneği seç (veya seçenek yoksa
   kısa bir cevap üret), 1 cümlelik gerekçeyle. Kullanıcının orijinal
   isteği: <kullanıcının mesajı>. Proje bağlamı: <atdd.md'nin
   task_slug'ı, ilgiliyse jira-sync/plan.md'den gelen özet>.
   Sorular:
   1. <soru 1 + varsa seçenekler>
   2. ...
   Yanıt formatı: her soru için 'N. <seçilen cevap> — <gerekçe>'.
   ```

   ```
   Agent({
     description: "Answer ATDD clarification questions for <task-slug>",
     subagent_type: "general-purpose",
     model: "sonnet",
     reasoning_effort: "low",
     run_in_background: false,
     prompt: "<yukarıdaki prompt, birebir>"
   })
   ```
   Cevaplar "Sorular ve Cevaplar" bölümüne `(Sonnet 5 low alt-ajanı
   tarafından yanıtlandı: <gerekçe>)` notuyla işlenir — kendi başına
   değiştirme/yeniden yorumlama. Sonuç, taslak doldurulurken 5. adımda
   kullanılır, kullanıcı cevabı gibi gösterilmez.

   İstisna: kullanıcı mesajında zaten net bir cevap varsa (3. adım), o
   kategori için alt-ajana SORULMAZ, doğrudan `(kullanıcı mesajından)`
   notuyla kullanılır — gereksiz Sonnet 5 çağrısı yapılmaz.

4a. **Davranış sözleşmesini tablo olarak çıkar — zorunlu adım.**

   Belirsiz bırakılan hata davranışı, bu boru hattının en pahalı hata
   sınıfını üretiyor: **başarı bildiren ama hiçbir şey yapmayan çağrı.**
   2026-08-16'da Codex köprüsünde birebir bu yaşandı — `write_code()`
   `success: True` döndürdü, tek dosya bile değişmemişti; sonraki adım buna
   güvenip üstüne inşa edecekti. Sözleşme yazılmadığı için "hiçbir şey
   yazamadım" durumunun ne dönmesi gerektiği hiç kararlaştırılmamıştı.

   Her yeni özellik/fonksiyon/uç için şu tabloyu doldur. Satırları sen
   önerirsin, 4z adımındaki Sonnet 5 low alt-ajanı çağrısına bu tabloyu da
   (boş satır önerileriyle) dahil et — alt-ajan doldurur/düzeltir,
   kullanıcıya ayrıca sorulmaz:

   | # | Durum (girdi/koşul) | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür |
   |---|---|---|---|---|
   | 1 | Happy path | | | |
   | 2 | Girdi geçersiz/eksik | | | |
   | 3 | Kaynak yok (dosya/kayıt bulunamadı) | | | |
   | 4 | Yetkisiz erişim | | | |
   | 5 | Dış bağımlılık hatası (ağ/DB/API) | | | |
   | 6 | Zaman aşımı | | | |
   | 7 | **Kısmi başarı** (bir kısmı oldu, kalanı olmadı) | | | |
   | 8 | **Hiçbir şey yapılamadı ama hata da yok** | | | |

   Uygulanmayan satırı **sil ve neden sildiğini yaz** — boş bırakma.

   Üç kural, hepsi gerçek olaydan geliyor:
   - **7 ve 8 pazarlıksız.** En sinsi hatalar bu ikisinde saklanır. "Bu
     durum oluşmaz" cevabı yetmez; oluşursa ne döneceği yazılır.
   - **Boş sonuç ile hata ayrılır.** `200 + []` "veri yok" mu, "yetkin yok"
     mu, "sorgu başarısız" mı? Aynı değeri döndürüyorlarsa sözleşme
     bozuktur (bkz. `authz-test`, RLS'te en tehlikeli sonuç budur).
   - **Başarı iddiası doğrulanabilir olmalı.** "Başarılı" dönen bir çağrının
     doğruluğu, çağıranın gözlemleyebileceği bir şeye bağlanmalı (dosya
     değişti, kayıt oluştu, sayaç arttı) — sadece dönüş değerine değil.

   Her satır bir Acceptance Criteria'ya dönüşür (`AC-<n>`) ve
   `test-copilot` bunları test eder. Tabloda olmayan bir hata durumu, test
   edilmeyen bir hata durumudur.

5. **ATDD taslağını doldur** (şablon aşağıda), cevapları birebir kullanarak —
   soru sorup cevabı görmezden gelme, önceden netleşmiş kategorileri de dahil et.
6. **Kaydet.** `artifacts/<task-slug>/atdd.md` yoluna yaz (klasör
   yoksa oluştur). Var olan bir dosyayı sessizce ezme — üzerine yazmadan önce
   kullanıcıya söyle.
7. **DUR VE ONAY BEKLE (Hard Stop).** Kaydettikten sonra kullanıcıya dosya yolunu ver ve ŞUNU SOR: *"atdd.md dosyasını oluşturdum. Lütfen dosyayı okuyun ve yanlış/eksik bir varsayım varsa düzeltin. Onaylıyorsanız 'devam' deyin, sonraki adıma geçelim."*
   Kullanıcı açıkça onay vermeden KESİNLİKLE kendi kendine `plan` veya `code-copilot` adımlarına geçme. Onay geldiğinde (veya düzeltmeler yapıldığında) pipeline'ın sonraki adımı başlar.

## ATDD Şablonu (atdd.md içeriği — YAML frontmatter + Markdown)

```markdown
---
task_slug: <task-slug>
jira_id: <JIRA-ID veya null>
saga_task_id: <id veya null>
priority: critical | high | medium | low
coverage_target: <yüzde, örn. 85>
performance_target: <örn. "<200ms" veya null>
memory_target: <örn. "<100MB" veya null>
test_strategy:
  unit: <yüzde>
  integration: <yüzde>
  e2e: <yüzde>
affected_modules:
  - <modül/dosya yolu>
---

# ATDD — <task-slug>

## Jira Kaynağı
(jira-sync'ten geldiyse) [<JIRA-ID> — <tam başlık>](https://.../browse/<JIRA-ID>)
User Story (Jira'dan birebir): "..."
AC (Jira'dan birebir): Given ..., When ..., Then ...
(jira-sync çağrılmadıysa: "Jira'ya bağlı değil — yerel görev")

## Persona
<kim, hangi bağlamda kullanıyor>

## Hedef (Neden)
<bu iş neden yapılıyor>

## User Story
As a <persona>
I want <capability>
So that <benefit>

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given <bağlam>, When <eylem>, Then <beklenen sonuç>
2. [High] ...
3. [Medium] ...
(en az happy path [Critical] + 2 edge case olacak şekilde; test-copilot
Critical olanları önce yazabilsin diye öncelik etiketi zorunlu)

## Agentic Değerlendirme Kriterleri (opsiyonel — sadece görev bir LLM agent/sub-agent tool-calling davranışını veya prompt'unu değiştiriyorsa doldurulur)
Tetikleyici yoksa bu bölümü sil, "tetikleyici yok" yazma.
- Beklenen tool-calling trajectory'si: <hangi tool'lar hangi sırayla çağrılmalı>
- Hassas (`sensitive: true`) tool'lar: <PII/finansal veri döndüren tool isimleri — agentic-judge scope-creep'i bunlarla eşleşince severity'yi otomatik critical'a çıkarır>
- Response kalite kriterleri: <faithfulness/completeness/tone_fit/actionability için proje-özel eşik veya beklenti, varsa>
- Bu bölüm doluysa `agentic-judge` skill'i `red-team`'in yanına koşullu adım olarak eklenir (bkz. `pipeline` SKILL.md).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | <happy path> | <ör. 200 + {id, ad}> | <ör. kayıt oluşur> | <ör. "Kaydedildi"> | AC-1 |
| 2 | <girdi geçersiz> | <ör. 400 + {hata: "ad boş olamaz"}> | <yok> | <alan altı hata> | AC-2 |
| ... | | | | | |

Kısmi başarı: <bir kısmı olup kalanı olmazsa ne döner — "olmaz" yazma, oluşursa ne olacağını yaz>
Hiçbir şey yapılamadı ama hata da yok: <bu durumda ne döner — sessiz başarı YASAK>
Boş sonuç ↔ hata ayrımı: <"veri yok" ile "yetkin yok" nasıl ayırt edilir>

<Uygulanmayan satır silinir ve nedeni buraya yazılır. Tabloda olmayan hata
durumu, test edilmeyen hata durumudur.>

## Test Strategy
Unit: <yüzde>% — <hangi katman/fonksiyonlar>
Integration: <yüzde>% — <hangi akışlar>
E2E: <yüzde>% — <varsa hangi senaryolar>

## Benchmark / Başarı Ölçütü
Coverage Target: <yüzde>%
Performance Target: <varsa>
Memory: <varsa>
Görsel/UI kriteri (varsa): <ör. "layout bozulmamalı", "hata mesajı görünür
olmalı" — bu tür kriterler `verify` adımında `vision-test` skill'iyle
kontrol edilir, buraya not düşülmezse unutulur>
Diğer ölçülebilir kriterler: <...>

## Kapsam Dışı
<açıkça yapılmayacaklar>

## Etkilenen Dosyalar/Modüller (bilinen)
<varsa>

## Proje Ortamı Kısıtı (arama/grep kapsamı)
<Bu makinede git reposunun kökü proje klasörü değil, DAHA GENİŞ bir dizin
(örn. ev dizini) olabilir ve devasa bir git geçmişi taşıyabilir —
doğrulanmadıysa "doğrulanmadı" yaz, "yok" deme. Doğruysa: sonraki adımlarda
(özellikle `plan`'ın kod keşfi, `code-copilot`/`test-copilot`/`red-team`'in
Grep/Glob/Bash kullanımı) arama HER ZAMAN gerçek proje klasörüyle
sınırlanmalı — sınırsız arama (`git log -p --all`, kök dizinden `grep -r`,
tam-repo indexleme) devasa geçmişi/ilgisiz dosyaları tarayıp RAM'i
tüketebilir (canlı olay: `security-scan` ve harici araçlarda (tgrep)
tekrarladı, bkz. proje hafızası).>

## Rollback Beklentisi
<hata durumunda davranış>

## Risks
- <bilinen risk, varsa>

## Assumptions
- <varsayım — kullanıcı onaylamadıysa açıkça "varsayım" olarak işaretli>

## Unknowns
- <henüz netleşmemiş, ileride tekrar sorulması gereken>

## Sorular ve Cevaplar (ham kayıt)
1. Soru → Cevap (veya "kullanıcı mesajından, tekrar sorulmadı")
2. ...
```

## Kural
- **Netleştirme soruları (4z) → Sonnet 5 low alt-ajanı. Slug onayı (1. adım) ve
  dosya üzerine yazma uyarısı (6. adım) → HÂLÂ kullanıcıya.** İkincisi
  geri dönüşü zor/veri kaybı riskli işlemler, insan onayı burada kalıyor
   — sadece taslak-doldurma soruları otomatik.
- 8 sorudan az soru sorup taslağı doldurma; hiçbir kategori netleşmemişse
  12'ye kadar çık. Adaptif olmak "atla" demek değil — sadece zaten cevaplanmış
  kategoriyi tekrar sorma, geri kalanları sor.
- Taslağı doldururken kullanıcı cevaplarında olmayan varsayım ekleme;
  belirsizse **Assumptions** veya **Unknowns** bölümüne yaz, "belirtilmedi"
  diye gizleme.
- Jira bağlamı `jira-sync`'ten geldiyse sonuçları (ID, URL, açıklama, AC)
  **birebir** atdd.md'ye göm — sonraki skill'ler bir daha Jira'ya sorgu
  atmamalı, hepsi atdd.md'den okumalı.
- Acceptance Criteria'da öncelik etiketi ([Critical]/[High]/[Medium]) zorunlu.
- `test_strategy` yüzdeleri toplamı 100 olmalı; kullanıcı vermediyse proje
  tipine göre makul bir varsayılan öner ve **onaylat**, sessizce icat etme.
