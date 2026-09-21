---
name: threat-model
description: Turns a feature's acceptance criteria into abuse cases before any code or test is written — asks "what would a malicious user do with this?" and appends testable security acceptance criteria to atdd.md. Runs between `atdd` and `plan` in the TDD/ATDD pipeline. Use when a task touches authentication, authorization, user input, file upload/download, payments, personal data, or any multi-tenant boundary. Produces requirements, never code.
---

# threat-model — güvenliği sonradan aramak yerine baştan gereksinim yap

## Kullanılacak destek skiller
- `caveman`, `ponytail` (full) — her zaman aktif. Tehdit listesi şişirilmez.

## Neden var
Mevcut boru hattında `atdd` hep happy-path kabul kriteri üretiyordu
("kullanıcı profilini görebilmeli"), `red-team` ise en sonda diff'e bakıyordu.
Arada bir boşluk vardı: **güvenlik gereksinimi hiç doğmuyordu**. Doğmayan
gereksinimin testi de yazılmaz — `test-copilot` sadece atdd.md'deki AC'leri
test eder. Bu skill o boşluğu kapatır: tehdit, kod yazılmadan önce
**testi yazılabilir bir kabul kriterine** dönüşür.

Ucuzluk sırası: gereksinimde yakalanan açık < testte yakalanan < üretimde.

## Ne zaman çalışır
`atdd` bitti, `plan` başlamadan önce. **Her görevde değil** — şu tetikleyiciler
varsa: kimlik doğrulama/yetkilendirme, kullanıcı girdisi, dosya yükleme/indirme,
ödeme, kişisel veri (KVKK), çok kiracılı (multi-tenant) sınır, dış API çağrısı,
arka plan işi (background job), ya da yeni bir HTTP ucu. Hiçbiri yoksa
"tetikleyici yok" diye tek satır not düş ve geç.

## Yöntem

### 1. Varlıkları ve sınırları yaz
Bu değişiklik neye dokunuyor: hangi veri (kimin?), hangi güven sınırını geçiyor
(tarayıcı→API, servis→DB, kiracı→kiracı). Sınırı olmayan yerde tehdit yoktur.

### 2. STRIDE-lite — her satırda tek soru sor
Altı kategoriyi sırayla geç, **uymayanı atla ve atladığını yaz**:

| Kategori | Soru | Tipik açık |
|---|---|---|
| **S**poofing | Kim olduğunu nasıl kanıtlıyor? | zayıf token, süresiz oturum |
| **T**ampering | İstemciden gelen neye güveniyoruz? | `role`/`price`/`user_id` body'den okunuyor |
| **R**epudiation | Kim yaptı, izi var mı? | kritik işlemde log yok |
| **I**nfo disclosure | Fazlası dönüyor mu? | hata mesajında stack trace, API'de gereksiz alan |
| **D**oS | Sınırsız ne var? | rate limit yok, sayfalama yok, sınırsız upload |
| **E**levation | Yetki nerede kontrol ediliyor? | sadece UI'da gizleme, sunucuda kontrol yok |

En sık gerçek açık **T** ve **E**'dir: istemciden gelen kimliğe güvenmek ve
yetkiyi sunucuda değil arayüzde uygulamak.

### 3. Her tehdidi testedilebilir AC'ye çevir
Belirsiz tehdit işe yaramaz. Dönüşüm somut olmalı:

- Kötü: "SQL injection'a karşı korunmalı"
- İyi: `AC-S1: /api/jobs?q= ucuna "' OR 1=1--" gönderildiğinde 400 döner, DB sorgusu parametreli çalışır, yanıtta başka kullanıcının kaydı bulunmaz`

- Kötü: "Yetkilendirme doğru olmalı"
- İyi: `AC-S2: A kullanıcısının token'ıyla GET /api/profiles/{B_id} çağrıldığında 403/404 döner, B'nin hiçbir alanı yanıtta geçmez`

Her AC'de **saldırganın somut girdisi** ve **beklenen gözlenebilir sonuç**
bulunmalı; yoksa `test-copilot` onu test edemez.

### 4. atdd.md'ye ekle
Güvenlik AC'lerini `AC-S<n>` ön ekiyle, mevcut kabul kriterlerinin **içine**
ekle (ayrı bir "güvenlik" bölümüne değil — ayrı bölüm görmezden gelinir).
Frontmatter'a `threat_model: done` ekle.

Yetkilendirme AC'si ürettiysen, `authz-test` skill'ini de çağır — IDOR/RLS
testleri kendi kalıbını ister.

### 5. Kabul edilen riski yaz
Bilinçli olarak kapsam dışı bırakılan tehdit varsa (ör. "rate limit bu sürümde
yok, tek kiracı iç araç") atdd.md'nin Risks bölümüne **gerekçesiyle** yaz.
Sessizce atlanan tehdit, kabul edilmiş risk değildir.

## Yapmayacakların
- Kod veya test yazmaz — sadece gereksinim üretir.
- Genel güvenlik dersi anlatmaz; her madde bu göreve bağlı olmalı.
- Tehdit listesini uzunluk için şişirmez. 3 gerçek AC, 15 genel maddeden iyidir.
- `security-scan`'in işini yapmaz (bağımlılık/sızıntı taraması onun gate'i).
