# SPRINT.md — Kuruluş odaklı son sprint (10-11 Ekim 2026)

> **Ne bu dosya:** Sunum provasından sonra alınan kararların iş paketlerine bölünmüş hâli.
> Paralel oturumlar (en fazla 3) bu dosyadan beslenir. Her paket kendi başına okunabilir.
> **Nasıl kullanılır:** `/sprint durum` → hangi paket boşta; `/sprint <ID>` → paketi başlat;
> `/sprint birlestir <ID>` → bitmiş paketi taban dala al. Skill: `.claude/skills/sprint/SKILL.md`.
>
> **Oturum kuralı:** Bu dosyanın tamamını okuma. §3 (ortak kurallar) + kendi paket bölümün yeter.
> **Teslim:** 11 Ekim 12:00. Taban dal: `feat/kurum-kurulus-panelleri`. `main`'e hiçbir şey gitmez.

---

## ⚠ Güncelleme — 10 Ekim gece (her oturum önce bunu okur)

1. **`main` taban dala alındı** (`70867a0`). Ekip arkadaşının PR #59-#61 işleri artık tabanda. Paket dalın daha
   eskiyse **bir kez** `git merge feat/kurum-kurulus-panelleri` yap. Bu dosyadaki **satır numaraları eskimiş olabilir**:
   fonksiyonu `grep -n` ile bul, numaraya güvenme.
2. **Migration head artık `53d336a5a854`** (eskiden `f2a6c8e0b913`). M0 buna bağlanır.
3. **`.env` repo kökünde**, `backend/` altında değil. `config.py` yalnız kendi repo kökündeki `.env`'i okur
   (`backend/app/core/config.py:11,27`). Worktree'de `.env` yok, izin kuralı kopyalamayı yasaklıyor (**aşma**).
   Çözüm S0'a eklendi: `YETKIN360_ENV_FILE` ortam değişkeni. S0 birleştikten sonra worktree'de backend testi:
   `YETKIN360_ENV_FILE=C:/Users/Meyrem/Desktop/P/yetkin360/.env TEST_DB_SUFFIX=<id> <venv-python> -m pytest ...`
4. **Ekip arkadaşının yaptıkları (yeniden yazma, kullan):**
   - #60: Kurum/kuruluş kullanıcısı `/calismalar`'da kendi **"Sizden işlem bekleyenler"** görünümünü görüyor
     (`frontend/app/calismalar/review-view.tsx`, `list-parts.tsx`, `frontend/lib/ui/engagement-review.ts` →
     `reviewAction`, `isInReviewerScope`). Liste yanıtında `talent_id`, `talent_name`, `organization_id`, `institution_id` zaten var.
   - #61: `DRAFT → PENDING_APPROVAL` geçişi `notify_emails` (1-5 adres) ister; öğrenci koordinatör e-postasını yazar
     (`frontend/lib/ui/notify-emails.ts`, `transition-actions.tsx` içindeki kutu).
   - #59: Görev ekleme/doğrulama (`task-list.tsx`, `engagement_tasks` doğrulama alanları migration'ı).
   Bu dosyalar **ekip arkadaşının**: okuyup içe aktar, değiştirmen gerekiyorsa paket sahibi B'dir ve değişikliği commit gövdesinde açıkla.
5. **Uzaktaki `sprint/s0` dalı** yönetici oturumunun deneme dalıdır (`d75ef50`) — **yok say**. Asıl S0 oturumu
   kendi dalını `sprint/s0-opus` adıyla push eder; birleştirmede o kullanılır.
6. **Yönetim modu:** Paketler kullanıcının açtığı oturumlarda `/sprint <ID>` ile yürür. Yönetici oturumu kod yazmaz.

---

## 0. Hikâye — neden bu sprint

Provada çıkan ana eleştiri: kurum ve kuruluş ekranları öğrenci ekranının kopyası gibi duruyor;
kuruluşun platformda **neden hesap açacağı** görünmüyor. Kararımız:

- **Kuruluş (şirket) ön planda, bireysel kullanıcı ikinci ağırlık.** Kuruluşun hesap açma sebebi
  **başvuranı doğrulamak**; hesapta kalma sebebi **kendi stajyerine mühür vermek ve vitrin**.
  ("DenizBank sırf çalışanını onaylamak için hesap açmaz; başvuranın kaydını doğrulamak için açar.")
- **Kurum (üniversite)** kendi öğrencisini öne çıkaran, iş birliklerini ve raporu tek yerde gören taraf.
- **Bireysel kullanıcı** ("öğrenci" değil) — mezun ve çalışanlar da var.

### Demo senaryosu (5 dk, hedef akış)

| # | Aktör | Ekran | Ne görülür |
|---|---|---|---|
| 1 | Ayşe Yılmaz (bireysel, Galata Teknik) | Yeni çalışma | Lale Yazılım'ı seçer, onaylayıcı olarak **Mehmet Kaya · Yazılım** seçer |
| 2 | Kerem Taşkın (Galata koordinatörü) | Kurum paneli | Onay kutusunda satır içi **Onayla** |
| 3 | Mehmet Kaya (Lale, Yazılım birimi) | Kuruluş paneli → "Bana atananlar" | Değerlendirir |
| 4 | Kerem Taşkın | Kurum paneli → "Mühür bekleyen" | Mühürler → **çift imzalı kayıt** |
| 5 | Kuzey Enerji İK | Kuruluş paneli → **Aday doğrula** | Ayşe'nin CV'sindeki bağlantıyı yapıştırır → imzalı kaydı görür |
| 6 | Herkes | Keşfet → Lale Yazılım → **Vitrin** | "Bu şirkette yapılmış, imzalı işler" |

---

## 1. Açık kararlar (kullanıcı cevaplayacak — plan ikisine de hazır)

> **KARAR (10 Ekim gece, varsayılan — kullanıcı değiştirebilir):** K1 = **Seçenek A (çift imza)** → K paketi yapılır.
> K2 = **H-0** (seçenek arayüzden kaldırılır); H yapılmaz. Yürütme: kullanıcının açtığı oturumlarda `/sprint <ID>`.

### K1 — Mührü kim veriyor?
Bugün: çalışma bir kuruma (üniversiteye) bağlıysa **mührü koordinatör verir**, kuruluş yalnız
değerlendirme formunu doldurur (`backend/app/services/attestation.py:211-226`). Kurumsuz çalışmada
mührü kuruluş **yöneticisi** verir.
- **Seçenek A (önerilen):** Kural aynı kalır, anlatı "**çift imza**" olur: kuruluş değerlendirir +
  üniversite mühürler. K paketi bunu görünür yapar. Yetkilendirme değişmez.
- **Seçenek B:** Mentor (atanan kuruluş üyesi) mühürler, koordinatör ortak imzacı olur. Yetkilendirme
  ve durum makinesi değişir → yeni bir Opus paketi gerekir (K paketinin yerine geçer).
- **Plan etkisi:** Yalnız K paketi bu karara bağlı. Diğer hiçbir paket etkilenmez.

### K2 — "Kuruluşlar görebilir" görünürlüğü gerçek olsun mu? (basit anlatım)
Profil ayarında kullanıcı "Kuruluşlar görebilir" seçebiliyor. **Bugün bu seçenek hiçbir şey yapmıyor**:
profil herkese kapalı kalıyor, hiçbir kuruluş ekranı bu ayarı okumuyor.
- **Gerçek yaparsak (H paketi):** Kullanıcı CV'sine `/p/ayse-yilmaz` bağlantısını koyar. Bağlantı
  herkese kapalıdır; **alan adı doğrulanmış bir şirketin çalışanı giriş yapmışsa** açılır.
  DenizBank İK'sı başvuranın tüm profilini böyle görür. Gizlilik korunur, en güçlü argüman çalışır.
- **Gerçek yapmazsak (H-0):** Seçeneği arayüzden kaldırırız (15 dk). "Aday doğrula" yine çalışır ama
  yalnız tek tek herkese açık kayıt bağlantılarıyla (`/v/...`).
- **Plan etkisi:** Yalnız H paketi. Hiçbir paket H'ye bağımlı değil. Karar gelmezse H-0 uygulanır.

---

## 2. Bulgular — arayüzde var, arkasında karşılığı yok (veya tersi)

| # | Bulgu | Kanıt | Hangi paket kapatır |
|---|---|---|---|
| Y1 | "Kuruluşlar görebilir" (`ORGANIZATIONS`) görünürlüğü hiçbir yerde okunmuyor | `backend/app/models/identity.py:88`, `scoped_public_talent_profile` yalnız `PUBLIC` | H / H-0 |
| Y2 | Çalışma detayındaki durum düğmeleri **role bakmıyor** → yanlış kişi tıklayınca 403 (demoda patlar) | `frontend/lib/api/engagements.ts:7` "BACKEND GAP" | A |
| Y3 | `/me` rol döndürmüyor → admin/koordinatör arayüzde ayırt edilemiyor | `backend/app/api/me.py:60-77` | A |
| Y4 | `engagements.supervisor_user_id` kolonu var, hiçbir kod kullanmıyor | `backend/app/models/engagement.py:47` | D1 |
| Y5 | Kurumda `SUPERVISOR` (akademisyen) rolü DB'de var; davet API'si reddediyor, arayüz yok | `backend/app/api/institutions.py:250` | Ö6 (yol haritası) |
| Y6 | T4 "Kuruluş + Üniversite ortak onayı" etiketi var, hesaplayan mantık yok (admin elle atar) | `backend/app/api/admin.py:67` | K (çift imza rozeti) |
| Y7 | Ana sayfa kurum vaatleri: "iş birliklerini görün", "rapor için tek kaynak" — panelde yok | `frontend/messages/tr.json` `home.personas.institution` | I + E |
| Y8 | Kayıttaki belge kontrolü "Örnek sonuç… henüz bağlı değil" diyor | `tr.json` `kayit.documentDemoNote` | C (metin) — sunumda gösterilmez |
| Y9 | `PATCH /organizations/{id}` yalnız alan adı değiştiriyor; kuruluş ayarı yok | `backend/app/api/organizations.py:274` | D2 |
| Y10 | Kuruluş çalışmanın **başlangıcını onaylamıyor**; kurumsuz çalışmayı kişi kendisi `ACTIVE` yapıyor. Kuruluşun ilk teması değerlendirme | `backend/app/services/engagement.py:319-324` | Ö2 (yol haritası; anlatı: "kuruluş imzası olmadan hiçbir şey mühürlenmez") |
| Y11 | Bilinmeyen e-postaya davet **sessizce düşüyor** ama ekranda "Davet kuyruğa alındı" yazıyor | `organizations.py:333-420` (AC-2) | Demo'da yalnız kayıtlı hesap davet edilir; Ö8 |
| Y12 | Her kayda bir `TalentProfile` açılıyor → kurum/kuruluş kullanıcısı öğrenci ekranlarına düşüyor. Ayrıca **kurum ADMIN'i onay veremez** (yalnız COORDINATOR) ama ekran bunu söylemiyor | `backend/app/services/auth.py:211`, `authorization.py` `coordinator_institution_ids` | B + E |
| Y13 | Koordinatör dashboard satırlarında öğrenci adı ve kuruluş adı yok (yalnız başlık) | `services/engagement.py:749-870` `get_coordinator_dashboard` | I |
| Y14 | Kuruluş paneli tüm `/engagements`'ı çekip tarayıcıda filtreliyor (varsayılan limit 50) | `frontend/app/kurulus/[id]/panel/page.tsx:173` | D1 (`organization_id` filtresi) + F |
| Y15 | Her `pytest` test DB'sini `DROP … WITH (FORCE)` ile siliyor → paralel oturumlar birbirini öldürür | `backend/tests/conftest.py:105-160` | S0 |

---

## 3. Ortak kurallar (her oturum okur)

### 3.1 Dal ve worktree
- Her paket kendi dalında: `sprint/<id>` (küçük harf: `sprint/s0`, `sprint/d1`). Taban: `feat/kurum-kurulus-panelleri`.
- Her paket kendi worktree'sinde: `.claude/worktrees/sprint-<id>` (gitignore'da).
- Ana klasör (`yetkin360/`) **yalnız birleştirme ve demo** içindir; orada paket kodu yazılmaz.
- Bağımlı olduğun paket birleşince kendi dalına al: `git merge feat/kurum-kurulus-panelleri`.

### 3.2 Worktree ortamı
- **Backend Python:** ana klasörün venv'i kullanılır: `C:/Users/Meyrem/Desktop/P/yetkin360/backend/.venv/Scripts/python.exe`
  (komutlar worktree'nin `backend/` klasöründe çalışır: `<venv-python> -m pytest ...`).
- **`.env`:** Kopyalama (izin kuralı yasaklıyor, aşma). Backend komutlarına
  `YETKIN360_ENV_FILE=C:/Users/Meyrem/Desktop/P/yetkin360/.env` öneki ekle (S0 birleştikten sonra çalışır).
  Frontend `.env` istemez (`NEXT_PUBLIC_API_BASE_URL` varsayılanı `http://localhost:8000`).
- **node_modules:** `cmd //c mklink //J frontend\\node_modules <ana>\\frontend\\node_modules` (junction).
  Junction'la `vitest`/`tsc` sorun çıkarırsa `npm ci`.
- **Test DB:** her oturum **kendi test DB'sini** kullanır: `TEST_DB_SUFFIX=<id> <venv-python> -m pytest ...`
  (S0 birleştikten sonra geçerli; S0'dan önce backend testi koşulmaz).
- **Sunucular:** 8000/3000 portları ana klasöre aittir. Worktree'de sunucu açma; görsel kontrol
  birleştirmeden sonra ana klasörde yapılır. Kaçınılmazsa backend `--port 8001`, frontend
  `NEXT_PUBLIC_API_BASE_URL=http://localhost:8001 npx next dev -p 3001`.
- **Migration:** Dev DB'ye (`alembic upgrade head`) yalnız **M0** ve **birleştirme** oturumu uygular.

### 3.3 Dosya sahipliği (çakışma önleme)
Bir pakete ait dosyaya başka paket dokunmaz. Paylaşılan dosyalar **sıralı hatta** durur.

| Dosya / alan | Sahip paket(ler) — sırayla |
|---|---|
| `backend/tests/conftest.py`, `backend/tests/_testdb.py` | S0 |
| `backend/alembic/versions/*`, `backend/app/models/identity.py` | M0 |
| `backend/app/services/engagement.py` | A → D1 (Hat 1). **İstisna:** `get_coordinator_dashboard` fonksiyonu → I |
| `backend/app/api/engagements.py` | A → D1 |
| `backend/app/api/me.py`, `backend/app/services/talent.py` (`get_me_context`) | A |
| `backend/app/services/evaluation.py`, `attestation.py` (yalnız yardımcı çıkarma) | A |
| `backend/app/api/organizations.py`, `backend/app/services/organization.py` | D2 |
| `backend/app/api/institutions.py`, `backend/app/services/institution.py` | I |
| `backend/app/api/public.py`, `backend/app/services/public_profile.py`, yeni `organization_showcase.py` | G → H → K (Hat 3 sırası) |
| `backend/app/services/authorization.py` | G (yeni `scoped_*` ekler) → H. Başka paket **ekleme yapmaz** |
| `backend/scripts/seed.py` | J |
| `frontend/messages/tr.json` | C önce birleşir; sonra herkes **yalnız kendi ad alanına anahtar ekler**, var olanı değiştirmez |
| `frontend/components/app-shell.tsx`, `frontend/app/giris/*`, `frontend/app/calismalar/page.tsx`, `frontend/lib/session/roles.ts` (yeni) | B |
| `frontend/app/page.tsx`, `frontend/app/kayit/form.tsx` | C |
| `frontend/lib/session/types.ts`, `frontend/lib/api/engagements.ts`, `frontend/app/calismalar/[id]/*` | A → D1 |
| `frontend/app/calismalar/olustur/*` | D1 |
| `frontend/lib/api/organizations.ts` | D2 (fonksiyon ekler) → F (kullanır, değiştirmez) |
| `frontend/app/kurulus/[id]/panel/*` | F |
| `frontend/lib/api/institutions.ts`, `frontend/app/kurum/[id]/panel/*` | I (api fonksiyonları) → E |
| `frontend/app/kesfet/*`, yeni `frontend/app/o/[id]/*`, `frontend/lib/auth/should-redirect.ts` | G |
| `frontend/app/p/[slug]/*`, `frontend/app/profil/profile-form.tsx` | H / H-0 |
| `frontend/app/v/[token]/*` | K |

### 3.4 Model ve skill kullanımı
- **Opus:** yetkilendirme, migration, herkese açık uç (gizlilik), durum makinesine dokunan her şey.
- **Sonnet:** arayüz, metin, mevcut bir kalıbın kopyası olan basit uçlar, seed.
- **Kullanılmayacak skill'ler:** `test-copilot`, `code-copilot` — işi Haiku alt-ajanına devrediyorlar;
  Haiku bu repoda daha önce git kuralını çiğnedi. **Kodu ve testi oturumun kendi modeli yazar.**
- **Backend yetki paketi akışı:** `threat-model` (kısa, çıktı sohbette) → uygula → `authz-test`
  (matris + canlı yoklama yerine test) → `verify` → `red-team`.
- **Frontend paketi akışı:** uygula → `verify` (lint + typecheck + ilgili vitest) → birleştirmeden sonra
  ana klasörde `vision-test` veya tarayıcıda göz kontrolü.
- **Metin paketi:** `fast-track` (commit adımı hariç — commit kuralı §3.5).
- Görsel dil: `docs/sayfa-tasarim-brifi.md` (yalnız ilgili bölüm) + `frontend/components/panel-kit.tsx`
  bileşenleri. Yeni renk/stil icat etme; mor/cırtlak yok (kâğıt-mürekkep-mühür paleti).

### 3.5 Commit ve push
- Paket bitince **sormadan** kendi dalına commit + push (`git push -u origin sprint/<id>`).
- `main`'e push **asla**. PR açma, `--force` yok. Dosyalar **adıyla** eklenir (`git add -A` yasak).
- Commit mesajı Türkçe: `feat(<alan>): <özet>` + gövde. **Co-Authored-By satırı ve "Generated with" yok.**
- **Gövde = devir notu:** ne değişti, sözleşmeden sapma (varsa), açık kalan, çalıştırılan doğrulama.
  Birleştiren kişi yalnız commit gövdesini okuyarak devam edebilmeli.

### 3.6 Değişmez kurallar (CLAUDE.md'den hatırlatma)
- Yetkisiz erişim **404**, 403 değil. Çıplak `select(Model)` yok → `scoped_*()`.
- Yeni uç = aynı commit'te pozitif + **negatif (başka kiracı → 404)** yetki testi.
- ORM modeli doğrudan dönülmez; ayrı Pydantic şeması.
- Loga PII yok (tam e-posta, ad soyad audit metadata'sına yazılmaz).
- UI metni `tr.json`'dan; koda gömülmez.
- Yetkilendirme dosyasına dokunan paket **`pytest tests/authorization -q` tamamını** koşar.

---

## 4. Paket tablosu ve hatlar

<!-- sprint-tablosu: /sprint durum bu tabloyu okur. Sütun sırasını değiştirme. -->
| ID | Başlık | Hat | Model | Sert bağımlılık | Sözleşmeyle erken başlar mı | Boyut |
|---|---|---|---|---|---|---|
| S0 | Paralel test veritabanı | 1 | Sonnet | — | — | S |
| M0 | Migration: birim + vitrin | 1 | Opus | S0 | — | S |
| A | Rol bilgisi + izinli eylemler | 1 | Opus | M0 | — | L |
| D1 | Onaylayıcı atama (çalışma tarafı) | 1 | Opus | A | — | M |
| H | "Kuruluşlar görebilir" (K2) | 1 | Opus | A, G | — | M |
| C | Terimler ve anlatı metinleri | 2 | Sonnet | — | — | S |
| B | Rol bazlı yönlendirme ve menü | 2 | Sonnet | C | — | M |
| D2 | Ekip, birim, onaylayıcı listesi, vitrin ayarı | 2 | Opus | M0 | — | M |
| F | Kuruluş paneli yeniden | 2 | Sonnet | D2 | evet (A, D1 sözleşmesi) | L |
| I | Kurum backend: dashboard, iş birlikleri, CSV | 3 | Sonnet | S0 | — | M |
| E | Kurum paneli yeniden | 3 | Sonnet | I | evet (A sözleşmesi) | M |
| G | Kuruluş vitrini (public) + Keşfet | 3 | Opus | M0 | — | M |
| K | Çift imza rozeti + değerlendiren adı (K1) | 3 | Sonnet | G | — | S |
| J | Demo seed'i | son | Sonnet | D1, D2, G | — | M |
| R | Prova + son kalite kapısı | son | Opus | hepsi | — | S |

```
Hat 1 (Opus)        S0 ─► M0 ─► A ─────────► D1 ─────────► H*
                           │     ╲             ╲
Hat 2 (Sonnet/Opus) C ─► B ┼──► D2 ─► F ◄──────┘ (F: A+D1 sözleşmesiyle erken başlar)
                           │                  
Hat 3 (Sonnet/Opus) (S0'ı bekle) I ─► E ─► G ─► K*
                                       ▲
Son                              J ─► R      (* = K1/K2 kararına bağlı)
```

**Başlangıç sırası:** Hat 1 S0'ı bitirip birleştirir (~15 dk). Bu sürede Hat 2 C'ye başlar
(test DB'si gerekmez). Hat 3, S0 birleşince I'ya başlar.

**Kesme listesi (zaman daralırsa, bu sırayla kes):** K → H (yerine H-0) → I'daki CSV →
F'deki "İş birlikleri" bölümü → G'nin istatistikleri. **Asla kesilmez:** S0, A, B, C, D1, D2, F'nin
onay kutusu, E'nin satır içi onayı, J. Bir paket kesilirse C'nin yazdığı ana sayfa vaadini de geri al.

---

## 5. Paketler

---

### S0 — Paralel test veritabanı

**Hat 1 · Sonnet · Boyut S · Bağımlılık: yok**

**Sorun:** `backend/tests/conftest.py:105-160` her oturumda test DB'sini siliyor
(`DROP DATABASE … WITH (FORCE)`). Ad türetimi `conftest.py:13-14` + `tests/_testdb.py`
`resolve_test_database_url`. Paralel oturumlar aynı `yetkin360_test`'i kullanır → birbirini öldürür.

**Hedef:** `TEST_DB_SUFFIX` ortam değişkeni verilirse test DB adı `yetkin360_<suffix>_test` olur.

**Sahip dosyalar:** `backend/tests/_testdb.py`, `backend/tests/conftest.py`, `backend/tests/test_db_isolation.py`, `backend/app/core/config.py` (yalnız `env_file` satırı), `CONTRIBUTING.md` (bir satır).

**Ek hedef (10 Ekim gece):** Worktree'lerde `.env` yok ve kopyalanamaz. `config.py:27`:
`env_file=os.environ.get("YETKIN360_ENV_FILE") or (REPO_ROOT / ".env")`. Dosyanın içeriği okunmaz/yazdırılmaz;
yalnız yol verilir. Birim testi: değişken verildiğinde `Settings.model_config["env_file"]` o yolu gösterir
(gerçek `.env` açılmadan, `monkeypatch` + yeniden import ya da yardımcı fonksiyonla).

**Adımlar:**
1. `_testdb.py`'ye saf fonksiyon: `apply_test_db_suffix(url: str, suffix: str | None) -> str`.
   - `suffix` yoksa/boşsa URL aynen döner.
   - `^[a-z0-9]{1,16}$` değilse `ValueError` (SQL tanımlayıcısına gireceği için katı allowlist).
   - DB adı `..._test` ise `_test` öncesine `_<suffix>` eklenir; sonuç yine `test` ile bitmeli
     (`assert_safe_test_url` ile doğrula). Parola korunur (`render_as_string(hide_password=False)`), hata mesajında URL basılmaz.
2. `conftest.py:14`'ten hemen sonra: `test_url = apply_test_db_suffix(test_url, os.environ.get("TEST_DB_SUFFIX"))`.
   CI yolu (`dev_url == test_url`) **etkilenmemeli**: CI'da değişken set değil.
3. `test_db_isolation.py`'ye birim testleri: suffix yok / geçerli / geçersiz (`"a;drop"`, `"A"`, 17 karakter) / parola korunuyor.
4. `CONTRIBUTING.md` test bölümüne tek satır: paralel çalışma için `TEST_DB_SUFFIX`.

**Kabul:**
- AC-1 `TEST_DB_SUFFIX=s0 pytest tests/test_db_isolation.py -q` geçer ve `yetkin360_s0_test` kullanılır.
- AC-2 Değişken yokken davranış birebir aynı.
- AC-S1 Geçersiz suffix testler başlamadan hata verir; DB adına ham girdi gitmez.

**Doğrulama:** `TEST_DB_SUFFIX=s0 pytest tests/test_db_isolation.py -q`, ardından bir kez tam `TEST_DB_SUFFIX=s0 pytest -q` (yalnız bu pakette; süreyi rapora yaz).

**Skill:** doğrudan uygula → `verify` (backend kapıları).

---

### M0 — Migration: birim etiketi + vitrin anahtarı

**Hat 1 · Opus · Boyut S · Bağımlılık: S0**
**Onay durumu:** Kullanıcı 10 Ekim'de planı onayladı (migration dahil). Yine de dev DB'ye uygulamadan önce tek satırla haber ver.

**Hedef şema (yalnız ekleme, geriye uyumlu):**

| Tablo | Kolon | Tip | Kısıt |
|---|---|---|---|
| `organization_members` | `unit` | `VARCHAR(60) NULL` | `CHECK (unit IS NULL OR char_length(btrim(unit)) BETWEEN 1 AND 60)` adı `ck_organization_members_unit_length` |
| `organizations` | `showcase_public` | `BOOLEAN NOT NULL DEFAULT false` | — |

Kurum üyelerine birim **eklenmez** (YAGNI; akademisyen akışı yol haritası).

**Sahip dosyalar:** yeni `backend/alembic/versions/<rev>_org_member_unit_ve_vitrin.py`, `backend/app/models/identity.py` (yalnız iki alan + CHECK).

**Adımlar:**
1. `alembic heads` → tek head olmalı (şu an `53d336a5a854`). Değilse DUR, bildir.
2. Migration'ı **elle** yaz (autogenerate gürültü getirebilir; kullanırsan diff'i ayıkla). `down_revision = "53d336a5a854"`.
   `downgrade` iki kolonu ve CHECK'i kaldırır.
3. `identity.py`: `OrganizationMember.unit: Mapped[str | None] = mapped_column(String(60))`, `__table_args__`'a CHECK;
   `Organization.showcase_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())`.
4. API/servis **değiştirme** (D2 ve G'nin işi).

**Kabul:**
- AC-1 `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` dev DB'de sorunsuz.
- AC-2 `tests/test_migration.py` geçer; yeni CHECK için bir test: 61 karakter ve yalnız boşluk reddedilir.
- AC-3 Mevcut tüm testler değişmeden geçer (kolonlar nullable/default'lu).

**Doğrulama:** `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`; `TEST_DB_SUFFIX=m0 pytest -q`.

**Skill:** doğrudan uygula → `verify`.

---

### A — Rol bilgisi ve izinli eylemler (Y2, Y3)

**Hat 1 · Opus · Boyut L · Bağımlılık: M0** · *En kritik paket: demo'daki 403 riskini kapatır, E/F/B'nin rol mantığı buna dayanır.*

**Sorun:** Arayüz düğmeleri yalnız duruma göre hesaplanıyor (`frontend/lib/api/engagements.ts:7-11`,
`availableTransitions`). `/me` yalnız `{id, name}` dönüyor (`backend/app/api/me.py:60-77`, `179-183`).

**Okunacak yerler:** `services/engagement.py:238-499` (`transition_engagement`, tablo 311-357),
`services/authorization.py:99-152` (`engagement_relation`), `services/evaluation.py:95-135`,
`services/attestation.py:151-230`, `api/deps.py` (`get_current_principal`), `services/talent.py:19-50`,
`api/engagements.py:251-277` ve `437-536`, frontend `calismalar/[id]/transition-actions.tsx`,
`attestation-form.tsx`, `task-form.tsx`, `deliverable-form.tsx`, `page.tsx`.

#### API sözleşmesi (E, F, B buna göre yazar — değiştirme, ekle)

`GET /me` (ekleme):
```json
{
  "organizations": [{ "id": "uuid", "name": "Lale Yazılım A.Ş.", "role": "ADMIN|MEMBER", "unit": "Yazılım|null" }],
  "institutions":  [{ "id": "uuid", "name": "Galata Teknik Üniversitesi", "role": "ADMIN|COORDINATOR|SUPERVISOR" }]
}
```

`GET /engagements/{id}` (ekleme):
```json
"viewer": {
  "relation": "SUBJECT|ORG_ADMIN|ORG_MEMBER|COORDINATOR|INSTITUTION_ADMIN|OBSERVER",
  "allowed_transitions": ["PENDING_APPROVAL", "ACTIVE", "REJECTED", "CANCELLED", "PENDING_EVALUATION"],
  "reason_required": ["REJECTED", "CANCELLED"],
  "can_add_task": true,
  "can_add_deliverable": false,
  "can_evaluate": false,
  "can_attest": false,
  "attest_blocker": "ORG_NOT_VERIFIED|null"
}
```
`relation` önceliği: SUBJECT > ORG_ADMIN > ORG_MEMBER > COORDINATOR > INSTITUTION_ADMIN > OBSERVER.
`EVALUATED→VERIFIED` hiçbir zaman `allowed_transitions`'ta yer almaz (mühür ayrı uçtan: `can_attest`).

#### Backend adımları
1. **Tek kaynak kuralı:** `transition_engagement` içindeki tabloyu modül düzeyinde
   `_transition_specs(principal, engagement, rel) -> dict` fonksiyonuna taşı; `transition_engagement`
   bunu kullanmaya devam etsin. **Davranış birebir aynı** — `tests/test_engagement_transitions.py`
   ve `tests/authorization/test_engagement_authorization.py` değişmeden geçmeli.
2. `viewer_capabilities(session, principal, engagement) -> dict` (services/engagement.py):
   - `allowed_transitions`: mevcut durumdan çıkan her spec için `can_transition()` doğru **ve** ucuz
     ön koşullar sağlanıyorsa (`institution_id_not_null`, `has_deliverable` — tek `count`). `reason_not_empty`
     ve `date_validation` listelemeyi engellemez (arayüz gerekçe sorar) → `reason_required`'a yazılır.
   - `can_evaluate`: `services/evaluation.py`'deki kuralı **yardımcı fonksiyona çıkar**
     (`can_submit_org_evaluation(rel, engagement, already_submitted: bool)`) ve hem servis hem viewer onu çağırsın.
     Aynı kullanıcının aynı yönde değerlendirmesi varsa `false`.
   - `can_attest`: `attestation.py:211-226` rol kuralını `attestation_role_allowed(rel, engagement)` yardımcısına
     çıkar; viewer ve `create_attestation` aynı fonksiyonu kullanır. Durum `EVALUATED` olmalı. Bu kullanıcının
     aktif tanıklığı varsa `false`. Kuruluş T1 ise `attest_blocker="ORG_NOT_VERIFIED"` (yalnız bilgi).
   - `can_add_task`: `ACTIVE` ve (`is_org_member` veya `is_coordinator`) — `engagement.py:555` ile aynı.
   - `can_add_deliverable`: `ACTIVE` ve `is_subject` — `engagement.py:679` ile aynı.
3. `api/engagements.py`: `EngagementViewerResponse` Pydantic modeli; `EngagementDetailResponse.viewer`.
4. `/me`: `get_me_context` organizasyon/kurum üyeliklerini **rol ve birimle** döndürsün (üyelik tablolarıyla
   join; `scoped_organizations`/`scoped_institutions` sonucu üzerinden, çıplak select yok). `me.py` şemalarına
   `role`, `unit` (yalnız org). Alanlar **ekleme**; mevcut istemci kırılmaz.

#### Frontend adımları
1. `lib/session/types.ts`: `OrganizationRef {id,name,role,unit}`, `InstitutionRef {id,name,role}`; `isMeResponse` gevşek kalır.
2. `lib/api/engagements.ts`: `EngagementDetail.viewer` tipi. `availableTransitions` ve "BACKEND GAP" notu kaldırılır;
   `isReasonRequired` yerine `viewer.reason_required`.
3. `transition-actions.tsx`: adaylar = `viewer.allowed_transitions`. Liste boşsa bileşen hiç render olmaz.
4. `attestation-form.tsx` yalnız `viewer.can_attest`; `attest_blocker` varsa açıklama metni (tr.json `calismalar` ad alanına **ekle**).
5. `task-form.tsx` → `can_add_task`; `deliverable-form.tsx` → `can_add_deliverable`; değerlendirme bağlantısı → `can_evaluate`.
6. İlgili `*.test.tsx` dosyalarını viewer'a göre güncelle; "öğrenci Onayla düğmesini görmez" ve
   "koordinatör PENDING_APPROVAL'da Onayla/Reddet görür" testleri zorunlu.

**Kabul (AC):**
- AC-1 Çok üyelikli kullanıcıda `/me` her üyeliği doğru rolle döner.
- AC-2 **Değişmez:** 6 aktör (talent-sahibi, org admin, org member, koordinatör, kurum admini, ilgisiz org üyesi)
  × her durum için: `to ∈ viewer.allowed_transitions` ⇔ `POST /transitions` 2xx. Parametrik test:
  `tests/authorization/test_engagement_viewer_capabilities.py`.
- AC-3 `can_evaluate`/`can_attest` true ⇔ ilgili uç 2xx (aynı dosyada).
- AC-4 Detay ekranında 403 üretecek hiçbir düğme render edilmez (vitest).
- AC-S1 Kişi aynı zamanda kuruluş üyesiyse `relation=SUBJECT`, org eylemleri `false` (self-dealing maskesi).
- AC-S2 Kapsam dışı çalışma için yine 404; `viewer` alanı başka hiçbir bilgi sızdırmaz.
- AC-S3 `/me` başka kiracının rolünü/birimini döndürmez.

**Doğrulama:** `TEST_DB_SUFFIX=a pytest tests/authorization -q` (tamamı) + `tests/test_engagement*.py tests/test_evaluation.py tests/test_attestation.py -q`;
frontend `npm run typecheck && npm run lint && npx vitest run app/calismalar lib/api lib/session`.

**Skill:** `threat-model` (soru: viewer alanı bir saldırgana ne öğretir?) → uygula → `authz-test` (AC-2 matrisi) → `verify` → `red-team`.

**Demo etkisi:** Koordinatör detayda yalnız Onayla/Reddet görür; öğrenci yalnız kendi düğmelerini.

---

### D1 — Onaylayıcı atama: çalışma tarafı (Y4, Y14)

**Hat 1 · Opus · Boyut M · Bağımlılık: A (aynı dosyalar)** · Frontend seçici D2'nin `approvers` ucunu kullanır (sözleşme aşağıda; D2 birleşmemişse mock'la yaz).

**Okunacak yerler:** `services/engagement.py:103-237` (`create_engagement`), `872-920` (`list_engagements`),
`921-987` (`get_engagement_detail`); `api/engagements.py:57-70`, `225-249`, `284-436`;
`frontend/app/calismalar/olustur/page.tsx:61-118`.

#### API sözleşmesi
- `POST /engagements` gövdesine: `"supervisor_user_id": "uuid|null"` (opsiyonel).
- `GET /engagements?assigned=me&organization_id=<uuid>` — iki filtre de opsiyonel; **kapsamı asla genişletmez**
  (`scoped_engagements` üzerine `WHERE` eklenir).
- `EngagementSummaryResponse`'a ekle: `institution_name|null`, `supervisor_user_id|null`.
  (`talent_id`, `talent_name` #60 ile **zaten var** — tekrar ekleme.)
- **#61 ile ilişki:** #61 kurum tarafında onay bildirimini e-postayla koordinatöre yönlendiriyor (`notify_emails`).
  D1 **kuruluş tarafı** için kişi atar (`supervisor_user_id`). İkisi ayrı; #61'in davranışını değiştirme.
- `EngagementDetailResponse`'a ekle: `"supervisor": {"user_id","display_name","unit"} | null`.
  `display_name` = onaylayıcının `TalentProfile.full_name`'i (her kullanıcıda var). **E-posta yok.**

#### Backend adımları
1. `create_engagement(..., supervisor_user_id: str | None = None)`: verildiyse
   aktif `OrganizationMember` (aynı `organization_id`, `status='ACTIVE'`) + `User.status='ACTIVE'` olmalı,
   ve **çalışmanın sahibi olamaz** (`talent.user_id != supervisor`). Aksi hâlde `OrganizationNotFoundError`
   (→ uçta genel 404, mevcut GUV-08 kalıbı). Audit metadata'sına yalnız `"has_supervisor": true/false`.
2. `list_engagements(..., assigned_to_me: bool, organization_id: UUID | None)` + talent adı / kurum adı join'i.
3. `get_engagement_detail` → supervisor özetini döndür.
4. Uç: `assigned: Literal["me"] | None = Query(None)`, `organization_id: uuid.UUID | None = Query(None)`.

#### Frontend adımları
1. `lib/api/engagements.ts`: `listEngagements({assigned?, organizationId?, limit?})`, yeni alan tipleri, `createEngagement` gövdesine `supervisor_user_id`.
2. `calismalar/olustur/page.tsx`: kuruluş seçiliyken `GET /organizations/{id}/approvers` (D2) ile
   "Kime gönderilsin? (isteğe bağlı)" seçimi. Seçenek etiketi `Ad Soyad · Birim`; varsayılan
   "Kuruluş yöneticisine (genel)" = `null`. Liste boşsa alan gizlenir. Metinler `calismaOlustur` ad alanına eklenir.
3. `calismalar/[id]/page.tsx` başlığında: "Onaylayıcı: Mehmet Kaya · Yazılım" (yalnız `supervisor` varsa).

**Kabul:**
- AC-1 Onaylayıcıyla oluşturulan çalışma detayda onaylayıcıyı gösterir.
- AC-2 `assigned=me` yalnız bana atanmışları, `organization_id` yalnız o kuruluşunkileri döner.
- AC-S1 Başka kuruluşun üyesi onaylayıcı → 404, kayıt oluşmaz.
- AC-S2 Onaylayıcı = çalışmanın sahibi (kişi aynı zamanda kuruluş üyesi) → 404.
- AC-S3 Pasif üye / askıdaki kullanıcı → 404.
- AC-S4 `assigned=me` + `organization_id=<üyesi olmadığım kuruluş>` → boş liste (404 değil, 200 `[]`; kapsam genişlemez).
- AC-S5 Liste ve detayda e-posta yok.

**Doğrulama:** `TEST_DB_SUFFIX=d1 pytest tests/authorization -q` + `tests/test_engagement.py -q`; frontend typecheck + `npx vitest run app/calismalar`.

**Skill:** `threat-model` → uygula → `authz-test` → `verify` → `red-team`.

---

### D2 — Ekip, birim, onaylayıcı listesi, vitrin ayarı (Y9; "alt hesap" fikri)

**Hat 2 · Opus · Boyut M · Bağımlılık: M0**

**Fikrin karşılığı:** "Kurum alt mail oluşturur" → mail kutusu oluşturmayız. Yönetici, **zaten kayıtlı**
çalışanını davet eder ve ona **birim** verir (Y11: bilinmeyen e-posta sessizce düşer; demoda kayıtlı hesap kullanılır).
Onay talepleri kişiye gider; yönetici her şeyi görür. Tek seviye birim; ağaç yok, birime özel yetki yok.

**Okunacak yerler:** `api/organizations.py` (tamamı ~600 satır, şemalar 39-110, PATCH 274-330, davet 333-457),
`services/organization.py:240-310` (`invite_org_member`), `services/rate_limit.py` (keşfet limiter'ı),
`tests/authorization/test_organization_authorization.py` (kalıp).

#### API sözleşmesi (F ve D1 buna göre yazar)

| Uç | Kim | Dönen |
|---|---|---|
| `GET /organizations/{id}/members` | o kuruluşun **herhangi** üyesi | `[{user_id, display_name, role, unit, open_assigned_count, email}]` — `email` **yalnız çağıran ADMIN ise** dolu, değilse `null` |
| `PATCH /organizations/{id}/members/{user_id}` gövde `{"unit": "Yazılım" \| null}` | yalnız ADMIN | güncel üye satırı |
| `POST /organizations/{id}/members` gövdeye ek `"unit"` | yalnız ADMIN | (mevcut 202 davranışı) |
| `GET /organizations/{id}/approvers` | e-postası doğrulanmış her kullanıcı | `[{user_id, display_name, unit}]` — e-posta **yok**, rol yok |
| `PATCH /organizations/{id}` gövde artık `{"domain"?: str, "showcase_public"?: bool}` (en az biri) | yalnız ADMIN | `OrganizationResponse` (+`showcase_public`) |

`open_assigned_count` = `supervisor_user_id = üye` ve durumu `ACTIVE|PENDING_EVALUATION|EVALUATED` olan çalışma sayısı.

#### Adımlar
1. Servis fonksiyonları `services/organization.py`'de; router'da iş mantığı yok.
2. `approvers`: kuruluş `ACTIVE` ve silinmemiş olmalı, yoksa 404. Yalnız `ACTIVE` üyeler, `ACTIVE` kullanıcılar.
   Sıralama: birim (null sona), ad. Keşfet rate limit'ini paylaş (60/dk/kullanıcı) → 429 `RATE_LIMITED`.
3. `unit` doğrulama: `strip()`, 1-60 karakter, boş → `null`. DB CHECK zaten var (M0).
4. Audit: `ORG_MEMBER_UNIT_CHANGED`, `ORGANIZATION_SHOWCASE_CHANGED` (metadata'da ad/e-posta yok).
5. `PATCH /organizations/{id}`: mevcut alan adı mantığı aynen korunur; `showcase_public` ayrı dal.
   Mevcut testler (`test_org_domain_change_l02.py` vb.) değişmeden geçmeli.
6. Frontend `lib/api/organizations.ts`: `listOrgMembers`, `updateMemberUnit`, `listApprovers`,
   `updateOrganization({showcase_public})`, `inviteOrgMember(..., unit?)` + `organizations.test.ts`.
7. **Opsiyonel (Ö1, vakit varsa):** T2+ kuruluşta davet yalnız doğrulanmış alan adındaki e-postalara
   (`@lale.com.tr`). Farklı alan → mevcut 202 kalıbıyla sessiz (sayım sızdırmaz) + audit `reason=domain_mismatch`.

**Kabul:**
- AC-1 Admin üyeleri e-postalarıyla, üye e-postasız görür.
- AC-2 Admin birim atar/temizler; panel ve onaylayıcı listesi güncellenir.
- AC-3 `showcase_public` admin tarafından açılıp kapanır.
- AC-S1 Üye olmayan → `members` 404; MEMBER → `PATCH members` 404; A kuruluşunun admini B'nin üyesine → 404.
- AC-S2 `approvers` yanıtında e-posta/rol yok; olmayan veya silinmiş kuruluş → 404 (ikisi aynı gövde).
- AC-S3 MEMBER `showcase_public` değiştiremez → 404.
- AC-S4 `unit` 61 karakter → 422; HTML/script metni olduğu gibi saklanır, arayüz düz metin basar.

**Doğrulama:** `TEST_DB_SUFFIX=d2 pytest tests/authorization -q` + `tests/test_organization.py -q`; frontend `npx vitest run lib/api`.

**Skill:** `threat-model` (personel adı numaralandırma riskini değerlendir) → uygula → `authz-test` → `verify` → `red-team`.

---

### C — Terimler ve anlatı metinleri (Y8, Y12'nin metin kısmı)

**Hat 2 · Sonnet · Boyut S · Bağımlılık: yok · İlk birleşen paket olmalı**

**Sözlük (tek tip, her yerde):**
| Kod | Arayüzde | Asla |
|---|---|---|
| `TALENT` | **Bireysel** (kullanıcı / hesap) | ~~Öğrenci~~ — yalnız kurum bağlamında "öğrenciniz" kalır |
| `Organization` | **Kuruluş** | ~~Organizasyon~~, ~~Kurum~~ |
| `Institution` | **Kurum** (üniversite / bölüm) | ~~Kuruluş~~ |

**Sahip dosyalar:** `frontend/messages/tr.json`, `frontend/app/page.tsx`, `frontend/app/kayit/form.tsx` (yalnız alan etiketi seçimi).

**Adımlar:**
1. `grep -n "Organizasyon\|organizasyon" frontend/messages/tr.json` → hepsi "Kuruluş".
   Bilinenler: `kurulusPanel.noDomainMessage`, `kurulusPanel.domainAlreadyVerifiedError`, `kurulusOlustur.title`.
2. `kurulusPanel.orgNextStep.PENDING_APPROVAL` → "Üniversite onayı bekleniyor".
3. `kayit`: `accountKindTalent` → "Bireysel", hint → "Staj, proje ve iş deneyimlerinizi kanıtlayın".
   `entityNameLabel` yerine iki anahtar: `entityNameOrganization` "Kuruluş adı", `entityNameInstitution` "Kurum (üniversite/bölüm) adı";
   `kayit/form.tsx` seçilen hesap türüne göre doğru etiketi göstersin. `accountKindOrganizationHint` →
   "Başvuranları doğrulayın, stajyerlerinize mühür verin".
4. `shell.roleStudent` → "Bireysel".
5. Ana sayfa (`home.personas` + `app/page.tsx` sırası): **Kuruluş ilk**, sonra Bireysel, sonra Kurum.
   - Kuruluş: başlık "Kuruluş", açıklama "Başvuranın deneyimini saniyeler içinde doğrulayın; kendi stajyerlerinize mühür verin."
     maddeler: "Adayın bağlantısını yapıştırın, imzalı kaydı görün" · "Ekibinizdeki mentorlar kendi stajyerini değerlendirsin" · "Vitrininizde gerçek işleri gösterin".
   - Bireysel: "Staj, proje ve işlerinizi kanıtla belgeleyin." maddeler korunur, "Mentorunuzdan" → "Mentorunuzdan ve üniversitenizden".
   - Kurum: "Öğrencilerinizin doğrulanmış deneyimlerini izleyin" · "Hangi kuruluşla kaç öğrenci çalıştı, tek ekranda" · "Akreditasyon için tek tıkla rapor".
   - `home.demo.steps.attestation.actor` → "Kuruluş değerlendirir, üniversite mühürler" (K1-A anlatısı; K1-B seçilirse "Mentor mühürler").
6. `kayit.documentDemoNote` → "Otomatik belge kontrolü yol haritasında; şimdilik başvurunuz platform ekibince incelenir."
7. `tr.json` geri kalanında "Öğrenci" geçen yerleri tek tek değerlendir: kurum paneli ve kurum bağlamı **kalır**;
   genel/kuruluş bağlamı "kişi/aday/bireysel" olur. Keşfet sekme adı "Öğrenciler" → "Kişiler".
8. Testlerde metin eşleşmesi varsa (vitest `getByText`) güncelle.

**Kabul:** "Organizasyon" kelimesi arayüzde yok; ana sayfada kuruluş ilk sırada; kayıt formunda doğru etiket.
**Doğrulama:** `npm run lint && npm run typecheck && npx vitest run app/kayit app/page components`.
**Skill:** `fast-track` (commit adımını §3.5'e göre yap).
**Not:** I, F, G kesilirse buradaki ilgili vaadi geri al (kesme listesi).

---

### B — Rol bazlı yönlendirme ve menü (Y12)

**Hat 2 · Sonnet · Boyut M · Bağımlılık: C** · A'ya **bağımlı değil** (yalnız üyelik listelerinin doluluğuna bakar).

**Sorun:** Her kullanıcıda `talent_profile` var (`backend/app/services/auth.py:211`); koordinatör girişte
`/calismalar`'a düşüyor ve "Yeni Çalışma", "Onaya gönderin" görüyor (ekran görüntüsü 10 Ekim).

**Okunacak yerler:** `frontend/app/giris/form.tsx:40-80` (`DEFAULT_AFTER_LOGIN`, `ADMIN_AFTER_LOGIN`),
`frontend/components/app-shell.tsx:250-300` (`PRIMARY_LINKS`, `contextGroups`) ve `780-830` (`navData`),
`frontend/app/calismalar/page.tsx`, `frontend/lib/session/use-session.ts`.

**Adımlar:**
1. Yeni `frontend/lib/session/roles.ts`:
   - `isOrgSide(me)`: `organizations.length > 0 || institutions.length > 0`.
   - `homePathFor(me)`: platform admini → `ADMIN_AFTER_LOGIN`; ilk kuruluş → `/kurulus/{id}/panel`;
     yoksa ilk kurum → `/kurum/{id}/panel`; yoksa `/calismalar`.
   - Birim testleri `roles.test.ts`.
2. `giris/form.tsx`: giriş sonrası `/me` alınır (zaten oturum sorgusu geçersizleniyor), `next` yoksa
   `homePathFor(me)`. Open-redirect temizliği (`sanitizeNext`) aynen kalır.
3. `app-shell.tsx`: `isOrgSide` ise üst menü = [aktif panel(ler), İşlemler (`/calismalar`), Keşfet]; "Profil" üst
   menüden çıkar, kullanıcı menüsüne **"Bireysel profilim"** olarak taşınır (kişi hem çalışan hem öğrenci olabilir).
   "Paneller" seçici aynı kalır. Alt başlıkta rol yazısı (A birleştiyse `role`'den: "Koordinatör", "Yönetici", "Üye · Yazılım").
4. ~~`calismalar/page.tsx` yönlendirmesi~~ **İPTAL (10 Ekim gece):** #60 bu sayfada kurum/kuruluş için zaten
   "Sizden işlem bekleyenler" görünümünü açıyor ve hem öğrenci hem üye olan kullanıcıya görünüm değiştirici veriyor.
   Bu sayfaya yönlendirme ekleme. Yalnız: `isOrgSide` kullanıcının üst menüsünde bu bağlantının etiketi
   "Çalışmalarım" yerine **"İşlemler"** olsun (aynı `/calismalar`); "Yeni Çalışma" düğmesinin #60'taki görünürlük
   kuralını koru.
5. Metinler `shell` ad alanına eklenir.

**Kabul:**
- AC-1 `kurum1-koordinator@seed.local` girişte kurum paneline, `org1-admin@seed.local` kuruluş paneline,
  `ogrenci1@seed.local` `/calismalar`'a, platform admini admin kuyruğuna gider.
- AC-2 `next=/p/...` verilirse oraya gider (temizlenmiş).
- AC-3 Kurum/kuruluş kullanıcısının üst menüsünde bağlantı "İşlemler" adıyla görünür; #60 görünümü bozulmaz (`app/calismalar/page.test.tsx` geçer).
- AC-S1 Rol kontrolü yalnız UX; hiçbir sayfa erişimi frontend'de "yetki" diye kapatılmaz.

**Doğrulama:** `npm run typecheck && npm run lint && npx vitest run app/giris components lib/session app/calismalar`.
**Skill:** uygula → `verify`; birleştirmeden sonra ana klasörde 3 hesapla göz kontrolü.

---

### F — Kuruluş paneli yeniden

**Hat 2 · Sonnet · Boyut L · Bağımlılık: D2 (sert), A + D1 (sözleşmeyle erken başlar; testlerde mock)**

**Hedef:** Panel "bireysel çalışma listesi" değil, **kuruluşun iş masası**: kim bekliyor, ekipte kim neyle
ilgileniyor, hangi üniversitelerle çalışıyoruz, aday doğrulama, vitrin.

**Sahip dosyalar:** `frontend/app/kurulus/[id]/panel/` altında: `page.tsx` (iskelet), yeni `inbox.tsx`,
`team-card.tsx`, `candidate-verify-card.tsx`, `showcase-card.tsx`, `partners-section.tsx`, mevcut `DomainCard`
ve `InviteCard` ayrı dosyaya taşınabilir; `page.test.tsx` + yeni bileşen testleri; `tr.json` → `kurulusPanel` ad alanı.

**Rol:** `me.organizations[].role` (A). `MEMBER`: davet, birim düzenleme, vitrin anahtarı **görünmez**.

**Ana sütun:**
1. **Özet kutuları:** "Değerlendirmenizi bekleyen" (bana atanan / tümü), "Devam eden", "Mühürlenen",
   "Birlikte çalışılan üniversite".
2. **Onay kutusu** (`inbox.tsx`) — **#60'ın mantığını yeniden kullan:** hangi satırın kuruluştan aksiyon
   beklediğini `frontend/lib/ui/engagement-review.ts` (`reviewAction`, `isInReviewerScope`) belirler; aynı kuralı
   kopyalama, içe aktar. Panel kompakt liste gösterir, "Tümünü gör" → `/calismalar` (#60 görünümü).
   - Sekme: **Bana atananlar** (varsayılan, `listEngagements({assigned:'me', organizationId})`) | **Tümü** (`{organizationId, limit:200}`).
     Kullanıcıya atanmış hiç kayıt yoksa varsayılan "Tümü".
   - Gruplar: *Sizden aksiyon bekleyen* (`PENDING_EVALUATION`; kurumsuz `EVALUATED` + ADMIN) ·
     *Devam eden* (`ACTIVE`, `PENDING_APPROVAL`, `DRAFT`) · *Tamamlanan* (`VERIFIED`, `RESOLVED`; kapalı, açılır) ·
     `REJECTED`/`CANCELLED` gösterilmez.
   - Satır: kişi adı, çalışma başlığı, tür, üniversite (`institution_name` ya da "Bireysel"), onaylayıcı çipi (birim), zaman.
   - Satır eylemi:
     - `PENDING_EVALUATION` → "Değerlendir" (`/calismalar/{id}/degerlendirme`).
     - `ACTIVE` → "Değerlendirmeye al" (geçiş `PENDING_EVALUATION`, `version` ile). `PRECONDITION_FAILED` →
       "Kişi henüz teslim eklemedi"; 409 → listeyi yenile.
     - `EVALUATED` + kurumsuz + ADMIN → "Mühürle" (`/calismalar/{id}#tanıklık`).
     - `EVALUATED` + kurumlu → bilgi çipi "Üniversite mührü bekleniyor".
   - Boş durum: ne yapılacağını söyle ("Öğrenci bağlantısını paylaşın" + kopyala düğmesi).
3. **İş birlikleri** (`partners-section.tsx`): Tümü listesinden istemcide topla: üniversite adı → kişi sayısı,
   mühürlü sayısı; kurumsuzlar "Bireysel başvurular" satırı.

**Yan sütun:**
4. **Aday doğrula** (`candidate-verify-card.tsx`): "Başvuranın CV'sindeki Yetkin360 bağlantısını yapıştırın".
   Saf ayrıştırıcı `parseCandidateLink(input) -> {kind:'verification', token} | {kind:'profile', slug} | null`:
   herhangi bir host'tan `/v/<token>` veya `/p/<slug>` yolunu kabul et; **yalnız yolu kullan**, kendi origin'imizde aç
   (`window.open('/v/'+encodeURIComponent(token))`). Geçersizse hata metni. Birim testi zorunlu
   (`javascript:` ve dış host'a yönlendirme denemeleri reddedilir/yalnız yol alınır).
5. **Vitrin** (`showcase-card.tsx`): ADMIN için anahtar (`updateOrganization`), herkes için "Vitrini gör" → `/o/{id}`;
   açıklama: "Yalnız kişinin herkese açık yaptığı kayıtlar görünür."
6. **Ekip ve birimler** (`team-card.tsx`): `listOrgMembers`; birime göre grupla; her kişide açık atama sayısı.
   ADMIN satır içinde birim düzenler; davet formu (mevcut) + birim alanı.
7. **Alan adı** kartı (mevcut `DomainCard`): doğrulanmışsa küçük rozet hâline gelsin.

**Kabul:**
- AC-1 MEMBER rolünde yönetim kontrolleri yok; ADMIN'de var (vitest).
- AC-2 "Bana atananlar" yalnız bana atanmışları gösterir; boşsa "Tümü" açılır.
- AC-3 Satır eylemleri yukarıdaki tabloya uyar; hata metinleri `aria-live` ile duyurulur.
- AC-4 Aday doğrula ayrıştırıcısı testleri geçer.
- AC-5 Her bölümün boş durumu var; klavye ile gezilebilir.

**Doğrulama:** `npm run typecheck && npm run lint && npx vitest run app/kurulus lib/api`.
**Skill:** uygula → `verify`; birleştirmeden sonra `vision-test` (org1-admin ve org1-yazilim hesaplarıyla).

---

### I — Kurum backend: dashboard zenginleştirme, iş birlikleri, CSV (Y7, Y13)

**Hat 3 · Sonnet (authz-test zorunlu; Opus açıksa Opus) · Boyut M · Bağımlılık: S0**

**Okunacak yerler:** `services/engagement.py:749-870` (`get_coordinator_dashboard` — **yalnız bu fonksiyon senin**),
`api/institutions.py:562-650` (dashboard + students), `services/institution.py:400-470` (`list_institution_students`, kalıp),
`services/authorization.py:773-799` (`scoped_institution_students`), `tests/authorization/test_institution_students_authz.py` (kalıp).

#### API sözleşmesi (E buna göre yazar)
1. `GET /institutions/{id}/dashboard` satırlarına ekle: `talent_full_name`, `organization_name`, `kind`, `version`.
   Yeni liste `pending_attestation` (durum `EVALUATED`) + `summary.pending_attestation`.
2. `GET /institutions/{id}/partners` → `{"items":[{"organization_id","organization_name","verification_level","student_count","engagement_count","verified_count"}]}`.
   Kurumun **herhangi** üyesi (ADMIN, COORDINATOR) çağırabilir.
3. `GET /institutions/{id}/report.csv` → `text/csv; charset=utf-8`, UTF-8 BOM, ayraç `;` (Türkçe Excel),
   `Content-Disposition: attachment; filename="yetkin360-rapor-<YYYY-MM-DD>.csv"`.
   Sütunlar: Ad Soyad; Bölüm; Sınıf; Kuruluş; Çalışma; Tür; Durum; Başlangıç; Bitiş; Doğrulama tarihi; Doğrulama bağlantısı (yalnız PUBLIC deneyimde).
   Kapsam: `list_institution_students` ile **aynı** kural (onaylı bağlantı, `PRIVATE` olmayan) + bu kurumun çalışmaları.

#### Adımlar
1. Dashboard sorgularına join (kişi adı, kuruluş adı); `EVALUATED` listesi.
2. `partners` ve rapor servis fonksiyonları `services/institution.py`'de; `scoped_engagements` +
   `scoped_institution_students` üzerinden. Çıplak select yok.
3. **CSV enjeksiyonu:** `=`, `+`, `-`, `@`, `\t`, `\r` ile başlayan her hücrenin başına `'` ekle. Python `csv` modülü.
4. Audit: `INSTITUTION_REPORT_EXPORTED` (metadata: satır sayısı; ad/e-posta yok).
5. Frontend `lib/api/institutions.ts`: tip güncellemesi + `listInstitutionPartners`, `reportCsvUrl(id)`; testleri.

**Kabul:**
- AC-1 Dashboard satırları kişi ve kuruluş adını taşır; `pending_attestation` doğru.
- AC-2 Partners sayıları seed verisiyle tutarlı.
- AC-3 CSV Excel'de Türkçe karakterlerle açılır (BOM).
- AC-S1 Başka kurumun koordinatörü, kuruluş üyesi, bireysel kullanıcı → partners ve CSV için 404.
- AC-S2 `PRIVATE` profilli öğrencinin satırı CSV'de yok.
- AC-S3 `=HYPERLINK(...)` başlıklı çalışma CSV'de `'=HYPERLINK(...)` olarak çıkar.
- AC-S4 Kimlik doğrulamasız → 401.

**Doğrulama:** `TEST_DB_SUFFIX=i pytest tests/authorization -q` + `tests/test_coordinator_dashboard.py tests/test_institution.py -q`; `npx vitest run lib/api`.
**Skill:** `threat-model` (CSV) → uygula → `authz-test` → `verify` → `red-team`.

---

### E — Kurum paneli yeniden (Y7, Y12)

**Hat 3 · Sonnet · Boyut M · Bağımlılık: I (sert), A (sözleşmeyle erken başlar)**

**Sahip dosyalar:** `frontend/app/kurum/[id]/panel/*` (gerekirse `approval-queue.tsx`, `partners-section.tsx`
olarak böl), `page.test.tsx`, `tr.json` → `kurumPanel` ad alanı.

**Rol farkı (A'dan `me.institutions[].role`):**
| Rol | Görür | Yapar |
|---|---|---|
| ADMIN ("Yönetici") | Her şey (salt okunur onay listesi) | Üye davet, rapor indir. **Onay veremez** — panelde açıkça yazar: "Onayları koordinatörler verir." |
| COORDINATOR ("Koordinatör") | Her şey | Onayla/Reddet, hatırlatma, mühürle, rapor indir. Davet formu görünmez |

**Adımlar:**
0. **#60'ı yeniden kullan:** aksiyon belirleme `frontend/lib/ui/engagement-review.ts`'ten (`reviewAction`:
   `approve` / `verify`). Panelde "Tümünü gör" → `/calismalar`.
1. Başlıkta rol rozeti + tek satır rol açıklaması.
2. **Onay bekleyen** bölümü: satır = kişi adı · kuruluş adı · başlık · başlangıç. Koordinatörde satır içi
   **Onayla** (`ACTIVE`, satırdaki `version`) ve **Reddet** (satır içi açılan gerekçe alanı, boş gönderilemez → `REJECTED`).
   Başarıda listeler yenilenir; 409 → "Kayıt değişti, liste yenilendi".
3. **Değerlendirme bekleyen**: mevcut hatırlatma akışı + kişi ve kuruluş adları.
4. **Mühür bekleyen** (yeni, `pending_attestation`): koordinatörde "Mühürle" → `/calismalar/{id}#tanıklık`.
   Açıklama: "Kuruluş değerlendirdi; mühürünüzle kayıt çift imzalı olur." (K1-A anlatısı.)
5. **İş birlikleri** (yeni): `listInstitutionPartners` → kuruluş adı, güven seviyesi, öğrenci, çalışma, mühürlü sayıları.
6. **Rapor indir (CSV)** düğmesi: başlık eylemlerine (`<a href={reportCsvUrl} download>`).
7. Öğrenciler ve üyeler bölümleri kalır; üye listesinde rol rozetleri.

**Kabul:**
- AC-1 ADMIN'de onay düğmeleri yok + açıklama var; COORDINATOR'da var (vitest).
- AC-2 Reddet gerekçesiz gönderilemez.
- AC-3 İş birlikleri ve CSV görünür; boş durumları var.
**Doğrulama:** `npm run typecheck && npm run lint && npx vitest run app/kurum lib/api`.
**Skill:** uygula → `verify`; birleştirmeden sonra `vision-test` (kurum1-admin ve kurum1-koordinator).

---

### G — Kuruluş vitrini (herkese açık) + Keşfet bağlantısı

**Hat 3 · Backend Opus, frontend Sonnet (aynı oturumda yapılacaksa Opus) · Boyut M · Bağımlılık: M0**

**Hedef:** Keşfet'te kuruluşa tıklayınca o kuruluşta yapılmış, **çift rızalı** (kuruluş vitrini açık + kişi
kaydı herkese açık) doğrulanmış işler görünsün. Keşfet kartındaki "Çalışma başlat" kalkar (aynı düğme
profilde ve Çalışmalarım'da zaten var).

**Okunacak yerler:** `api/public.py` (tamamı), `services/public_profile.py`, `services/authorization.py:453-620`
(`scoped_public_*` kalıpları, GUV-05 iptal filtresi 482-522), `services/discover.py:195-244`,
`frontend/app/kesfet/discover-ui.tsx:343-400`, `frontend/app/kesfet/page.tsx` (`canStartEngagement`),
`frontend/app/p/[slug]/page.tsx` (görsel referans), `frontend/lib/auth/should-redirect.ts:55-90`.

#### API sözleşmesi
`GET /public/organizations/{organization_id}` (kimlik doğrulamasız):
```json
{
  "id": "uuid", "name": "Lale Yazılım A.Ş.", "verification_level": "T3",
  "domain": "lale.com.tr|null (yalnız T2+)",
  "showcase_enabled": true,
  "stats": { "verified_public_count": 7, "institution_count": 3 },
  "experiences": [{
    "role_snapshot": "Mobil Uygulama Stajı", "started_on": "2026-07-01", "ended_on": "2026-09-01",
    "talent_display_name": "Ayşe Yılmaz", "talent_public_slug": "ayse-yilmaz",
    "institution_name": "Galata Teknik Üniversitesi|null",
    "public_token": "…", "skills": ["React Native", "Test yazımı"]
  }]
}
```
- Kuruluş yok / silinmiş / `ACTIVE` değil → 404 `ORGANIZATION_NOT_FOUND` (tek gövde).
- `showcase_public=false` → 200, `showcase_enabled=false`, `experiences=[]`, `stats` sıfır (kart bilgisi zaten Keşfet'te açık).

#### Backend adımları
1. `services/authorization.py`'ye **yeni** `scoped_public_org_showcase_experiences(session, organization_id) -> Select`:
   `VerifiedExperience` ⋈ `Engagement` (org eşleşir) ⋈ `TalentProfile`; koşullar: `ve.visibility='PUBLIC'`,
   `talent.visibility='PUBLIC'`, `talent.deleted_at IS NULL`, `talent.public_slug IS NOT NULL`,
   GUV-05 (en az bir aktif tanıklık veya hiç tanıklık yok — `scoped_public_verified_experiences` ile aynı ifade; ortak yardımcıya çıkar).
2. Yeni `services/organization_showcase.py`: `build_org_showcase(session, organization_id)`; en yeni 50 kayıt;
   beceriler `scoped_attestations_for_engagement` üzerinden (N+1'den kaçın: tek sorguda topla).
3. `api/public.py`'ye uç + Pydantic şemaları. İç id sızmaz (yalnız org id, public token, slug).

#### Frontend adımları
1. `should-redirect.ts`: `/o` ve `/o/` herkese açık yollar (+ `middleware.test.ts`).
2. Yeni `frontend/app/o/[id]/page.tsx`: başlık (ad, güven göstergesi, doğrulanmış alan adı), istatistik şeridi,
   kayıt kartları (rol, tarih, kişi → `/p/{slug}`, "Kaydı doğrula" → `/v/{token}`, beceri çipleri, üniversite).
   Vitrin kapalıysa boş durum: "Bu kuruluş vitrinini henüz açmadı." Metinler yeni `orgShowcase` ad alanı.
   `lib/api/public.ts`'e `getOrganizationShowcase(id)`.
3. `kesfet/discover-ui.tsx` `OrganizationCard`: `canStartEngagement` ve bağlantısı kaldırılır; kartın tamamı `/o/{id}`'ye
   gider ("Vitrini gör"). `kesfet/page.tsx`'te prop kaldırılır; testler güncellenir; `kesfet.startEngagement*` anahtarları silinmez (C kuralı), kullanılmaz.

**Kabul:**
- AC-1 Vitrin açık kuruluşta yalnız çift rızalı kayıtlar listelenir.
- AC-S1 `PRIVATE` / `INSTITUTION` / `ORGANIZATIONS` deneyim asla görünmez.
- AC-S2 Profili `PUBLIC` olmayan kişinin deneyimi görünmez (deneyim `PUBLIC` olsa bile).
- AC-S3 Tüm tanıklıkları iptal edilmiş kayıt görünmez.
- AC-S4 Vitrin kapalı → kayıt yok; silinmiş kuruluş → 404.
- AC-S5 Yanıtta e-posta, talent id, engagement id yok.
- AC-2 Keşfet kartında "Çalışma başlat" yok; kart vitrine gider.

**Doğrulama:** `TEST_DB_SUFFIX=g pytest tests/authorization -q` + `tests/test_public_profile.py tests/test_public_verification.py -q`;
`npm run typecheck && npm run lint && npx vitest run app/kesfet app/o lib middleware.test.ts`.
**Skill:** `threat-model` → uygula → `authz-test` → `verify` → `red-team`.

---

### H — "Kuruluşlar görebilir" görünürlüğü (K2 → evet) · H-0 (K2 → hayır)

**Hat 1 · Opus · Boyut M · Bağımlılık: A, G (`api/public.py` ve `authorization.py` sırası)**
**K2 cevabı gelmeden başlanmaz. Cevap gelmezse H-0 uygulanır.**

#### H (gerçek yap)
- `GET /public/talents/{slug}` **isteğe bağlı oturum** alır (yeni bağımlılık `get_optional_principal`:
  çerez yoksa/geçersizse `None`, hata fırlatmaz).
- Görünürlük kuralı (tek `scoped_*` fonksiyonunda): profil `PUBLIC` → herkes. Profil `ORGANIZATIONS` →
  yalnız oturum sahibi **en az bir `ACTIVE` üyeliği olan ve `verification_level ∈ (T2,T3,T4)` kuruluşun** üyesiyse.
  Diğer herkese **aynı 404**.
- Deneyimler: `ORGANIZATIONS` erişiminde `visibility IN ('ORGANIZATIONS','PUBLIC')`; herkese açık erişimde yalnız `PUBLIC`.
- Yanıt başlığı: oturuma bağlı yanıtlarda `Cache-Control: private, no-store` (paylaşılan önbellek sızıntısı).
- Audit: `PROFILE_VIEWED_BY_ORGANIZATION` (metadata: organization_id; talent id subject). → Ö4 için temel.
- Frontend `p/[slug]/page.tsx`: istek çerezle gider; `ORGANIZATIONS` erişiminde üstte bant:
  "Bu profil yalnız doğrulanmış kuruluşlara açık." Profil ayarındaki seçeneğin yardım metni bunu anlatır.
- **AC-S:** anonim → 404; bireysel kullanıcı → 404; T1 kuruluş üyesi → 404; T2 kuruluş üyesi → 200;
  kurum koordinatörü → 404; `PRIVATE` → herkese 404; `INSTITUTION` deneyim hiçbir kuruluşa görünmez;
  pasif üyelik → 404; yanıtta `Cache-Control: private, no-store`.
- **Doğrulama:** `pytest tests/authorization -q` tamamı + `tests/test_public_profile.py`. **Skill:** `threat-model` → `authz-test` → `verify` → `red-team`.

#### H-0 (kaldır, Sonnet, 15 dk)
- `frontend/app/profil/profile-form.tsx` ve `evidence-section.tsx`'te `ORGANIZATIONS` seçeneği listeden çıkar
  (backend değeri kabul etmeye devam eder; mevcut kayıtlar bozulmaz). Seçili olanlara uyarı: "Bu seçenek yakında; şu an profiliniz gizli."
- Doğrulama: `npx vitest run app/profil`.

---

### K — Çift imza rozeti + değerlendiren adı (Y6; K1-A'ya bağlı)

**Hat 3 · Sonnet · Boyut S · Bağımlılık: G (aynı dosya). K1-B seçilirse bu paket yeniden yazılır.**

**Kural:** Bir doğrulanmış deneyim **çift imzalı** sayılır ⇔ çalışmanın kuruluş üyesince yapılmış
`ORG_TO_TALENT` değerlendirmesi var **ve** kurum adına verilmiş (`attestor_org_id IS NULL`, `engagement.institution_id` dolu),
iptal edilmemiş tanıklık var. Admin'in elle verdiği T4 seviyesiyle karışmaz; ayrı alan.

**Adımlar:**
1. `api/public.py` `/public/v/{token}` yanıtına: `co_signed: bool`, `evaluator: {"display_name": "Mehmet K.", "unit": "Yazılım"} | null`.
   `display_name` = değerlendirenin adı + soyadının baş harfi (gizlilik; tam ad yok). Birim `OrganizationMember.unit`.
2. `services/public_profile.py` deneyim kartlarına aynı iki alan.
3. Frontend `v/[token]/page.tsx`: rozet "Çift imzalı · Kuruluş değerlendirdi, üniversite mühürledi" + satır
   "Değerlendiren: Mehmet K. · Lale Yazılım, Yazılım". `p/[slug]` kartında küçük rozet. Metin `publicVerification` ad alanına eklenir.

**Kabul:** AC-1 Seed'deki çift imzalı kayıtta rozet var, tek imzalıda yok. AC-S1 Tam soyad ve e-posta yanıtta yok.
AC-S2 İptal edilmiş tanıklıkta rozet yok.
**Doğrulama:** `pytest tests/test_public_verification.py tests/test_public_profile.py tests/authorization/test_public_verification_authz.py -q`; `npx vitest run app/v app/p`.

---

### J — Demo seed'i

**Son · Sonnet · Boyut M · Bağımlılık: D1, D2, G birleşmiş olmalı**

**Okunacak yerler:** `backend/scripts/seed.py:300-420` (veri), `640-760` (kurum/kuruluş ekleme), `840-870` (çalışma üretimi),
`tests/test_seed.py`, `backend/scripts/reset_demo.py`. **Şifreleri çıktıya yazma.**

**Eklenecek veri (idempotent — iki kez çalışınca kopya yok):**
| Ne | Değer |
|---|---|
| Lale Yazılım (ORG1) üyeleri | Murat Demirci (ADMIN, birim "Yönetim"), **Mehmet Kaya** `org1-yazilim@seed.local` (MEMBER, "Yazılım"), **Zeynep Arı** `org1-tasarim@seed.local` (MEMBER, "Tasarım") |
| Kuzey Enerji (ORG3) | **Elif Çınar** `org3-ik@seed.local` (MEMBER, "İnsan Kaynakları") — "Aday doğrula" aktörü |
| Vitrin | ORG1 ve ORG4 `showcase_public=true` |
| Ayşe Yılmaz (`ogrenci1`, Galata) | (a) Lale ile **VERIFIED**, onaylayıcı Mehmet, Mehmet değerlendirmiş + Kerem mühürlemiş (çift imza), deneyim `PUBLIC`; (b) Lale ile **PENDING_EVALUATION**, onaylayıcı Mehmet (canlı demo); (c) Galata bağlı **PENDING_APPROVAL** (Kerem canlı onaylar) |
| Profil | Ayşe `PUBLIC`; başka bir öğrenci `ORGANIZATIONS` (H yapıldıysa demosu) |

- Mevcut ekran görüntüsündeki "eg" taslakları el ile girilmiş test verisi → `python -m scripts.reset_demo --yes --reseed` ile temizlenir.
- `tests/test_seed.py`'ye yeni hesap ve atama kontrolleri.

**Kabul:** `reset_demo --yes --reseed` sonrası §0 senaryosu adım adım yürür; seed iki kez çalışınca sayılar değişmez.
**Doğrulama:** `TEST_DB_SUFFIX=j pytest tests/test_seed.py tests/test_reset_demo.py -q`; ana klasörde `reset_demo` + 4 hesapla giriş.

---

### R — Prova ve son kalite kapısı

**Son · Opus · Boyut S · Bağımlılık: hepsi birleşmiş**

**Hatlardan devreden işler (yönetici notu, 10 Ekim 21:45):**
- **Çapa:** E ve F'nin "Mühürle" bağlantısı `/calismalar/{id}`'ye gidiyor; detay sayfasında `#tanıklık` çapası yok.
  Detay sayfasındaki tanıklık bölümüne `id="taniklik"` ekle, E/F bağlantılarını `#taniklik` yap (ASCII çapa).
- **Aralıklı kırılan testler (paralel yük kaynaklı):** `tests/test_auth_rate_limit.py::test_hits_survive_the_request_rollback_with_real_get_session`
  (sabit IP + paylaşılan DB), `app/kayit` ve `app/giris` vitest'leri (zaman aşımı). Kapıyı **tek başına, seri** koş;
  yine kırılırsa düzelt, geçerse "paralel yük kaynaklı" diye not et.
- **Görsel kontrol (ana klasörde, sunucular açıkken):** E — `kurum1-admin`, `kurum1-koordinator`; F — `org1-admin`, `org1-yazilim`;
  G — `/o/<ORG1 id>`; B — üç hesapla giriş yönlendirmesi. 390px ve masaüstü.
- **Dev DB migration:** `alembic upgrade head` (M0 dahil) R'de uygulanır; kullanıcı onayı plan kapsamında verildi, yine tek satır haber ver.
- **Şikayet PR'ı (`feat/admin-eksikler-ve-sikayet`) tabana birleşmişse:** `alembic heads` tek değilse **DUR** ve
  bildir (PR'ın migration'ı `e7b1d9a3c604`'e bağlı; M0 ile iki head oluşabilir → merge migration gerekir).

1. Taban dalda tam kapı: `pytest -q` · `pytest tests/authorization -q` · `ruff check . && mypy app` ·
   `npm run lint && npm run typecheck && npm test` · `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.
2. `python -m scripts.reset_demo --yes --reseed`; §0 senaryosunu **jüri telefonu genişliğinde** (390px) yürü.
3. Her adımın ekran görüntüsünü al (yedek: canlı demo çökerse slayttan göster).
4. Hata listesi → yalnız kırık olan düzeltilir (yeni özellik yok).
5. Taban dal push; `main`'e birleştirme **kullanıcı kararı** (ayrı onay).

---

## 6. Öneriler (paket dışı; vakit/karar durumuna göre)

| # | Öneri | Değer | Maliyet | Durum |
|---|---|---|---|---|
| Ö1 | Doğrulanmış alan adına bağlı davet (T2+ kuruluş yalnız `@alanadi` e-postalarını davet eder) | "Alt mail" fikrinin güvenlik karşılığı; sahte çalışan eklenemez | S, Opus | D2 içinde opsiyonel adım |
| Ö2 | Kuruluş katılım onayı (Y10): kurumsuz çalışma `ACTIVE` olmadan kuruluş "evet bizde" der | Sahte çalışma itirazını kapatır | L (durum makinesi) | **Yol haritası** — sunumda: "Kuruluş imzası olmadan hiçbir şey mühürlenmez" |
| Ö3 | Atanan kişiye e-posta bildirimi (outbox konusu + işleyici) | Gerçek kullanımda şart | M | Yol haritası (demoda görünmez) |
| Ö4 | "Profilimi görüntüleyen kuruluşlar" listesi (H'nin audit kaydından) | KVKK/şeffaflık sorusuna güçlü cevap | S (H varsa) | H yapılırsa önerilir |
| Ö5 | Kurum paneli dönem/kohort filtresi | Koordinatörün asıl ihtiyacı | M | Yol haritası (Faz 6.1) |
| Ö6 | Akademisyen (SUPERVISOR) daveti + TÜBİTAK/proje akışı | Kullanıcının fikri; kurum içi kişiye doğrudan onay | M-L: SUPERVISOR'ın dashboard erişimi tanımsız, çalışma bir kuruluş zorunlu tutuyor | Yol haritası |
| Ö7 | Vitrin "işveren markası" sayaçları (kaç üniversiteden kaç kişi) | Kuruluşa hesapta kalma sebebi | — | G'nin `stats` alanında var |
| Ö8 | Bilinmeyen e-postaya davet → kayıt bağlantılı davet (Y11) | "Davet gönderildi" yalanını kaldırır | M | Yol haritası; demoda kayıtlı hesap kullan |

---

## 7. Sunum anlatısı (R paketi ve sunucu için)

- **Açılış:** "Bir şirket stajyerini onaylamak için hesap açmaz. Başvuranın söylediğini doğrulamak için açar."
- **Kuruluş döngüsü:** doğrulayıcı olarak gelir (Aday doğrula) → ihraççıya dönüşür (kendi stajyerine mühür) →
  vitrinle işveren markası kazanır. Her yeni kuruluş ağdaki tüm kayıtların değerini artırır.
- **Kurum:** öğrencisini öne çıkaran taraf; iş birliklerini ve akreditasyon raporunu tek yerden alır;
  mührü onun vermesi kaydı **çift imzalı** yapar.
- **Ekip içi düzen (kullanıcının fikri):** onay doğru kişiye gider (mentor/birim), yönetici her şeyi görür;
  karmaşa yok çünkü birim tek seviye, yetki kuralı tek.
- **Güven:** yetkisiz erişimde 404, çift rıza (kuruluş vitrini + kişi izni), iptal edilen tanıklık kayıttan düşer.
- **Yol haritası slaytı:** Ö2, Ö3, Ö5, Ö6, Ö8 + T3 belge doğrulaması.
