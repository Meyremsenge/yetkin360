---
name: sprint
description: SPRINT.md'deki kuruluş odaklı son sprint paketlerini paralel oturumlarda yürütür. "/sprint durum" hangi paketin boşta olduğunu gösterir, "/sprint <ID>" paketi kendi worktree'sinde başlatıp bitirir (uygula, doğrula, commit+push kendi dalına), "/sprint birlestir <ID>" bitmiş paketi taban dala alır. Kullanıcı /sprint yazdığında çalışır.
disable-model-invocation: true
argument-hint: "durum | <ID: S0 M0 A D1 H H-0 C B D2 F I E G K J R> | birlestir <ID>"
---

# Sprint — paralel paket yürütücü

Tek doğruluk kaynağı: kökteki `SPRINT.md`. **Dosyanın tamamını okuma.** Yalnız §3 (ortak kurallar),
§4 (paket tablosu) ve hedef paketin bölümünü oku. Satır aralığını `grep -n "^### <ID> "` ve bir sonraki
`^### ` başlığıyla bul, sadece o aralığı oku.

Sabitler:
- Ana klasör: `C:/Users/Meyrem/Desktop/P/yetkin360`
- Taban dal: `feat/kurum-kurulus-panelleri`
- Paket dalı: `sprint/<id>` (id küçük harf, `H-0` → `h0`)
- Worktree: `<ana>/.claude/worktrees/sprint-<id>`
- Venv python: `<ana>/backend/.venv/Scripts/python.exe`

Dil: kullanıcıyla Türkçe. Kod, kod yorumu, tanımlayıcı İngilizce. Commit mesajı Türkçe.

---

## Mod 1 — `/sprint durum`

Kod yazma, dosya değiştirme yok. Yalnız rapor.

1. `git fetch --quiet` (ağ yoksa geç).
2. `git branch -a --list "*sprint/*"` ve `git branch --merged feat/kurum-kurulus-panelleri --list "sprint/*"`.
3. SPRINT.md §4'teki `<!-- sprint-tablosu -->` tablosunu oku.
4. Her paket için durum:
   - **Birleşti** — dal tabana birleşmiş.
   - **Sürüyor/bekliyor** — dal var, birleşmemiş (son commit tarihi + başlığı: `git log -1 --format="%cr %s" sprint/<id>`).
   - **Hazır** — dal yok, sert bağımlılıkların hepsi birleşmiş.
   - **Erken başlanabilir** — dal yok, sert bağımlılık birleşmiş, "sözleşmeyle erken başlar" bağımlılıkları eksik.
   - **Bloklu** — sert bağımlılık birleşmemiş (hangisi).
   - **Karar bekliyor** — H/H-0 (K2) ve K (K1): SPRINT.md §1'de karar yazılı değilse.
5. Çıktı: tek tablo (ID | Başlık | Hat | Model | Durum) + "Şimdi açılabilecek oturumlar" listesi:
   her hat için sıradaki **Hazır** paket ve önerilen model. Başka yorum yok.

---

## Mod 2 — `/sprint <ID>`

### 2.1 Ön kontrol (kod yazmadan önce)
1. SPRINT.md'den §3, §4 ve paket bölümünü oku.
2. Model kontrolü: paketin "Model" sütunu bu oturumun modeliyle uyuşmuyorsa tek satır uyar
   ("Bu paket Opus için planlandı, Sonnet'tesin — devam ediyorum / `/model opus` önerilir") ve devam et.
   Opus paketi Sonnet'te çalışıyorsa yetki testlerinde ekstra titiz ol; atlamak yok.
3. Bağımlılık kontrolü: sert bağımlılıklar `git branch --merged feat/kurum-kurulus-panelleri` içinde mi?
   - Eksikse **DUR**: hangi paketin beklendiğini söyle. İstisna: paket "sözleşmeyle erken başlar" diyorsa,
     eksik paketin API sözleşmesine göre yaz, testlerde mock kullan ve bunu commit gövdesine not et.
4. Karar kontrolü: H, H-0, K için SPRINT.md §1'de karar yazılı değilse **DUR** ve kullanıcıya §1'deki
   ilgili sorunun kısa hâlini sor. H ve H-0 birbirinin alternatifidir; ikisi birden yapılmaz.
5. Dal zaten varsa (`sprint/<id>`) ve bu oturum o dalda değilse: başka bir oturum çalışıyor olabilir →
   kullanıcıya sor ("devam mı, yeniden mi?"). Kendi kendine silme/sıfırlama yapma.

### 2.2 Worktree ve ortam
1. Worktree oluştur ve gir. Tercih: `EnterWorktree` aracı (ad: `sprint-<id>`). Araç yoksa:
   `git -C <ana> worktree add .claude/worktrees/sprint-<id> -b sprint/<id> feat/kurum-kurulus-panelleri`
   ve sonraki tüm komutları o klasörde mutlak yolla çalıştır.
   Dal adı `sprint/<id>` değilse: `git branch -m sprint/<id>`.
2. Ortam (SPRINT.md §3.2):
   - `.env`: **kopyalama** (izin kuralı yasaklıyor; aşmaya çalışma). `.env` repo kökünde. Backend komutlarına
     `YETKIN360_ENV_FILE=<ana>/.env` öneki ekle (S0 birleştikten sonra çalışır). İçeriği asla okuma/yazdırma.
   - Önce SPRINT.md'deki "⚠ Güncelleme" bölümünü oku.
   - Frontend paketi ise: `cmd //c mklink //J "<wt>\frontend\node_modules" "<ana>\frontend\node_modules"`;
     `npx vitest --version` çalışmazsa junction'ı kaldır (`cmd //c rmdir`) ve `npm ci`.
   - Backend testleri her zaman: `YETKIN360_ENV_FILE=<ana>/.env TEST_DB_SUFFIX=<id> <venv-python> -m pytest ...` (S0 paketinin kendisi hariç
     — S0 birleşmeden önce suffix desteği yoktur; S0 oturumu suffix'siz koşar ve aynı anda başka backend testi koşulmaz).
   - Sunucu açma (8000/3000 ana klasörün). Zorunluysa 8001/3001 (§3.2).
3. Tek satır bildir: `Başlıyorum: <ID> — <başlık> (dal sprint/<id>, worktree hazır)`.

### 2.3 Uygulama
1. Paket bölümündeki **"Okunacak yerler"**i oku — fazlasını değil. Repoyu tarama.
2. Paketin **Skill** satırındaki akışı izle:
   - `threat-model`: kısa yürüt; çıktı (kötüye kullanım senaryoları → ek AC-S maddeleri) **sohbette** kalsın,
     dosyaya yazma. Paketteki AC-S listesine eklenenleri commit gövdesine yaz.
   - **`test-copilot` ve `code-copilot` ÇAĞIRMA** (Haiku alt-ajanına devrediyorlar). Kodu ve testleri bu oturum yazar.
   - `authz-test`: matrisi çıkar, testleri **sen yaz** (`tests/authorization/test_<konu>_authz.py`), canlı yoklama gerekmez.
   - `verify`: paket bölümündeki "Doğrulama" komutlarını çalıştır; PASS/FAIL raporla.
   - `red-team`: commit öncesi son inceleme; "Ready To Commit" değilse bulguları düzelt, tekrar `verify`.
   - `fast-track`: yalnız C ve H-0 için; commit adımını aşağıdaki kurala göre yap (kullanıcıya sorma).
3. **Dosya sahipliği (SPRINT.md §3.3) kesindir.** Sahibi olmadığın dosyaya dokunman gerekiyorsa DUR, sor.
   `tr.json`: yalnız kendi ad alanına anahtar **ekle**; var olan anahtarı değiştirme (C paketi hariç).
4. API sözleşmesi paket bölümünde yazılıysa birebir uygula. Sapmak zorundaysan (somut sebep: test, kısıt)
   sessizce sapma — tek cümleyle bildir, commit gövdesine "SÖZLEŞME SAPMASI:" diye yaz.
5. CLAUDE.md değişmezleri geçerli: 404 (403 değil), `scoped_*()`, ayrı Pydantic şeması, PII'siz log,
   yeni uç = aynı commit'te pozitif + negatif yetki testi, UI metni `tr.json`'da.
6. Kapsam: paket bölümünde olmayanı ekleme. Gördüğün başka sorunları düzeltme; commit gövdesine "GÖZLEM:" diye yaz.

### 2.4 Doğrulama
- Paket bölümündeki "Doğrulama" komutlarının **hepsi**. Yetki dosyasına (`authorization.py`, `api/*`, `deps.py`,
  `services/*` içindeki yetki kontrolleri) dokunduysan `pytest tests/authorization -q` **tamamı** zorunlu.
- Kırık test varsa gizleme: çıktısıyla birlikte söyle. Senin değişikliğinle ilgisiz önceden kırık test ise
  `git stash` ile taban üzerinde koşup kanıtla, commit gövdesine yaz.
- Migration (yalnız M0): `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` (dev DB'ye uygulamadan önce tek satır haber ver).

### 2.5 Commit ve push (sormadan — SPRINT.md §3.5)
1. `git status --short` → yalnız paketin dosyaları değişmiş olmalı. Beklenmeyen dosya varsa (ör. `.env`,
   `node_modules` junction'ı, `tsconfig.tsbuildinfo`) **ekleme**.
2. Commit öncesi sır kontrolü: `git diff --cached` içinde parola/token/`.env` değeri yok.
3. Dosyaları **adıyla** ekle. `git add -A` / `git add .` yasak.
4. Mesaj (Türkçe; **Co-Authored-By ve "Generated with" satırı YOK**):
   ```
   feat(<alan>): <tek satır özet> [SPRINT <ID>]

   Değişen: <dosya — ne>
   Sözleşme: <aynen | SÖZLEŞME SAPMASI: ...>
   Ek AC-S (threat-model): <varsa>
   Doğrulanan: <komut — sonuç>
   Açık kalan: <— | ...>
   GÖZLEM: <varsa>
   ```
5. `git push -u origin sprint/<id>`. **`main`'e push asla.** `--force` yok. PR açma.

### 2.6 Kapanış
Kısa çıktı (CLAUDE.md formatı):
```
Paket: <ID> — <başlık> (dal sprint/<id>, <commit kısa hash>)
Doğrulanan: <komut → sonuç>
Kalan: <— | ...>
Sıradaki: <bu hattaki sonraki paket ve modeli> · Birleştirme: /sprint birlestir <ID>
```
Worktree'yi silme (birleştirme sonrası kullanıcı karar verir).

---

## Mod 3 — `/sprint birlestir <ID>`

Ana klasörde (`<ana>`), taban dalda çalışır. Paket kodu yazmaz; yalnız birleştirir ve doğrular.

1. `git -C <ana> status --short` temiz olmalı ve dal `feat/kurum-kurulus-panelleri` olmalı. Değilse DUR.
2. `git fetch --quiet`; `git pull --ff-only` (taban dal). Çakışırsa DUR, sor.
3. Bağımlılık sırası: paketin sert bağımlılıkları zaten birleşmiş olmalı. Değilse DUR (yanlış sırayla birleştirme yok).
4. `git merge --no-ff sprint/<id> -m "merge: SPRINT <ID> — <başlık>"`.
   Çakışma çözümü kuralları:
   - `tr.json`: iki taraftaki anahtarları **birlikte tut**; aynı anahtar iki farklı değer aldıysa C'nin değeri kazanır, diğerini sor.
   - SPRINT.md §3.3'teki sahiplik tablosuna göre sahibi olan paketin hâli esas alınır.
   - Mantık çakışması (aynı fonksiyon) → DUR, `git merge --abort`, kullanıcıya iki dalın neyi değiştirdiğini anlat.
5. Paket M0 içeriyorsa (veya `backend/alembic/versions/` değiştiyse): dev DB'ye `alembic upgrade head` (tek satır haber ver).
6. Doğrulama (birleşmiş hâlde, suffix'siz ana test DB'si — başka oturum aynı anda suffix'siz test koşmamalı):
   - Backend değiştiyse: `pytest tests/authorization -q` + paketin doğrulama komutları.
   - Frontend değiştiyse: `npm run lint && npm run typecheck` + paketin vitest kapsamı.
   - Kırılırsa: `git reset --hard ORIG_HEAD` **önce kullanıcıya sorarak** (geri alınamaz işlem), kırığı paketin dalına bildir.
7. Başarılıysa `git push origin feat/kurum-kurulus-panelleri` (main değil).
8. Bu paketi bekleyen paketleri söyle: "Artık açılabilir: …" ve devam eden dallara not:
   "Kendi dalında `git merge feat/kurum-kurulus-panelleri` yap."
9. Çıktı: tek blok — birleşen, doğrulanan, açılan paketler.

---

## Durdurma kuralları (her modda)

- `.env`, `secrets/` okuma/yazdırma — yalnız `cp`.
- `docker compose down -v`, uygulanmış migration düzenleme, `git push --force`, `main`'e push: **asla**.
- Dosya/klasör silme, worktree kaldırma, `reset --hard`: önce kullanıcıya sor.
- Sahibi olmadığın dosya, sözleşmede olmayan uç, kapsam dışı özellik: DUR, sor.
- Belirsizlikte tahmin etme: bağımsız işleri bitir, kalan için tek soru sor.
