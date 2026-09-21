---
name: security-scan
description: Deterministic security gate for the ATDD pipeline — runs real scanners (detect-secrets, bandit, pip-audit, npm audit) against the changed code and reports PASS/FAIL/N/A per gate with evidence. Use as a gate inside `verify`, or standalone when the user asks to check a project for leaked secrets, vulnerable dependencies, or insecure code patterns. Never authors or fixes code; it only reports. Pair with `red-team` (LLM reasoning about business-logic flaws) — this skill covers what tools can prove, red-team covers what they cannot.
---

# security-scan — deterministik güvenlik gate'i

## Kullanılacak destek skiller
- `caveman`, `ponytail` (full) — her zaman aktif.
- `superpowers:systematic-debugging` — bir gate kırıldığında kör deneme yerine bunu izle.

## Neden var
`red-team` skill'i bir LLM'in diff okuması. Şu üç şeyi **yapısal olarak** göremez:
zafiyetli transitive bağımlılık, git geçmişine sızmış anahtar, ve gözden kaçan
taint akışı. Bu skill onları deterministik araçlarla kanıtlar. Bölüşüm:

| Katman | Kim bakar | Örnek |
|---|---|---|
| Bilinen zafiyet imzası | bu skill (araçlar) | CVE'li paket, `shell=True`, sızmış token |
| İş mantığı açığı | `red-team` + `authz-test` | IDOR, tenant sızıntısı, eksik yetki |

Araç bulgusu olmaması **güvenli demek değildir** — sadece "bilinen imza yok" demektir.

## Ön koşul
`artifacts/<task-slug>/code_diff.md` varsa, değişen dosya listesini
oradan al ve taramayı o dosyalarla sınırla. Tüm repoyu taramak hem yavaştır hem
de göreve ait olmayan eski bulgularla gate'i kirletir.

## Nasıl çalıştırılır

Tek komut — parametreleri elle kurma, aşağıdaki tuzaklar yüzünden:

```bash
"$HOME/.claude/security-tools/venv/Scripts/python.exe" "$HOME/.claude/skills/security-scan/scan.py" <proje_dizini>
```

Değişen dosyalarla sınırlamak için (**tercih edilen**, proje kökene göre göreli yollar):

```bash
"$HOME/.claude/security-tools/venv/Scripts/python.exe" "$HOME/.claude/skills/security-scan/scan.py" <proje_dizini> --files src/auth.py src/api.py
```

Çıkış kodu: `0` = PASS, `1` = FAIL, `2` = koşucu hatası.
`--json` makine-okunur rapor verir; `verify` çağırırken bunu kullan.

## Araç ortamı
Araçlar **ayrı bir venv'de**: `~/.claude/security-tools/venv`
(bandit, detect-secrets, pip-audit). Global `pip install` yapma — kullanıcının
venv izolasyon kuralı bunu yasaklar, ve global kurulum diğer projeleri bozar.
Araç eksikse gate `MISSING` döner; bunu **PASS sayma**.

## Doğrulanmış tuzaklar 

1. **`PYTHONUTF8=1` zorunlu.** Yolda ASCII-dışı karakter varsa (bu makinede
   kullanıcı adındaki `Ç`) `pip-audit` daha tek satır basmadan
   `UnicodeDecodeError` ile çöküyor. `scan.py` bunu kendi set ediyor; aracı
   elle çağırırsan sen set etmelisin.

2. **`detect-secrets` mutlak yolla SESSİZCE 0 döner.** POSIX biçimli mutlak yol
   verildiğinde hata vermeden boş sonuç üretir — temiz repo ile ayırt edilemez.
   Proje dizinine `cd` edip **göreli** yol vermek şart. Bu tuzak yüzünden ilk
   ölçümümde "git geçmişinde 0 sızıntı" sonucu çıktı ve **yanlıştı**.

3. **Ayarsız `bandit` = gürültü.** `linkedin` projesinde ham koşum 149 bulgu
   verdi, hepsi test dosyalarındaki `assert` (B101). `-ll -ii` (MEDIUM+ severity
   ve confidence) + test dizini dışlaması ile 149 → 0 indi. Negatif kontrolde
   gerçek açıkların 3/3'ünü (`shell=True`, MD5, SQL injection) yakaladı.

4. **Baseline dosyası kendini taratır.** `.secrets.baseline` kabul edilen
   bulguların hash'lerini tutar; taranınca her hash yeni bir yüksek-entropi
   bulgusu olarak geri döner. Dışlama listesinde olması şart.

5. **Repo kökü sandığın yer olmayabilir.** Bu makinede `linkedin` projesinin
   git kökü **ev dizini**. `git log -p --all` devasa çıktı üretti ve tarama 5
   dakikada bitmedi. Kapsamı daima değişen dosyalarla sınırla (ölçüm: 5 dosya
   = 2 saniye).

## Yanlış pozitif yönetimi
Gerçek projede ilk koşum neredeyse her zaman yanlış pozitif verir (test
fixture'ı, cache dosyası). Kurt masalı anlatan gate okunmaz hale gelir.

**Her bulguyu tek tek incele**, gerçek sır olmadığından emin ol, sonra:

```bash
"$HOME/.claude/security-tools/venv/Scripts/python.exe" "$HOME/.claude/skills/security-scan/scan.py" <proje> --accept-secrets
```

Bu, mevcut bulguları `.secrets.baseline`'a yazar; sonraki koşumlarda sadece
**yeni** sızıntılar FAIL verir (regresyon testiyle doğrulandı).

> Gerçek bir sır asla baseline'a yazılmaz. Önce anahtar iptal edilir, sonra
> koddan silinir. Baseline "incelendi ve sır değil" demektir, "biliyoruz ama
> umursamıyoruz" değil.

## Kapsam sınırları — dürüstçe raporla
- `detect-secrets` her biçimi tanımaz. Testte Stripe anahtarını entropiyle
  yakaladı, biçimi bozuk bir `ghp_` token'ını kaçırdı. Tarayıcı geçti diye
  "sızıntı yok" deme; "bilinen imzalarda sızıntı yok" de.
- JavaScript/TypeScript için SAST yok (`semgrep` Windows'ta pip ile kurulmuyor).
  JS iş mantığı açıklarını `red-team` üstlenir — bunu raporda N/A olarak belirt.
- `npm audit` sadece `high`/`critical` seviyeyi FAIL sayar.

## Raporlama
`artifacts/<task-slug>/security_scan.md` dosyasına yaz:
gate tablosu (PASS/FAIL/N/A + gerekçe), bulgular, ve **hangi kapsamda**
tarandığı. Bir gate `ERROR`/`TIMEOUT` ise sonuç `INCONCLUSIVE`'dir — bunu
asla PASS diye raporlama.

## Yapmayacakların
- Kod yazmaz, açık düzeltmez (düzeltme `code-copilot`'ın işi).
- Bulguyu "önemsiz" diye kendi başına elemez — baseline kararı kullanıcınındır.
- Araç yokken gate'i atlamaz; `MISSING` der ve kurulum komutunu söyler.
