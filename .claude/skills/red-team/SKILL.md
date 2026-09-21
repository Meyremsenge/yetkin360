---
name: red-team
description: ATDD pipeline'ının commit'ten önceki son bağımsız inceleme adımı. atdd.md + code_diff.md + test_report.md'yi okur; security/correctness/architecture/maintainability/performance/reliability/readability + CAVEMAN karmaşıklık incelemesi + scope review + risk review yapar. Sadece CLI ajanı tarafından çalıştırılır, hiçbir dış modele (Gemma vb.) bağımlı değildir. Gerçek kodu asla değiştirmez — sadece red_team.json bulgu raporu üretir ve commit'e hazır olup olmadığına dair bir "Ready To Commit" değerlendirmesiyle biter.
---

# Red-Team Skill

## Kullanılacak destek skiller
- `caveman`, `ponytail` (full) — her zaman aktif.
- `superpowers:requesting-code-review` — ek/tamamlayıcı bakış açısı gerekiyorsa; çakışırsa `red-team` verdict'i esastır.

Red-team, commit'ten önceki son bağımsız incelemedir.

- Gerçek kod ASLA yazmaz.
- Gerçek kod ASLA düzenlemez.
- Sadece inceler ve bulgu raporlar.

## Kritik kural: sadece CLI ajanı çalıştırır
Bu adım **her koşulda CLI ajanı tarafından** yürütülür, hiçbir dış modele (Gemma vb.) bağımlı değildir.

- **CLI ajanında çağrıldıysa:** aşağıdaki adımları uygula. Mümkünse `obss-red-team` subagent'ını (Agent tool, `subagent_type: obss-red-team`) kullan — gerçek kodu değiştirmez, sadece bulgu raporu döner.
- **Copilot'ta çağrıldıysa:** review YAPMA. Bunun yerine kullanıcıya şunu söyle: "Red-team adımı sadece CLI ajanında çalışır. Lütfen CLI ajanında `/red-team <task-slug>` çalıştır." ve dur.

> **Şema uyuşmazlığı — canlı tespit edildi (2026-08-24).** `obss-red-team`
> ajanı KENDİ sabit çıktı şemasına sahip (`security_findings`/
> `alternative_approach`/`approved_points`/`overall_assessment` — OBSS
> bridge workflow'una özel, `.claude/agents/obss-red-team.md`de tanımlı).
> Bu, aşağıdaki 3. adımdaki ATDD şemasıyla (`findings`/`ready_to_commit`/
> `verdict` vb.) AYNI DEĞİL. Subagent'a dispatch ederken prompt'un SONUNA
> şunu MUTLAKA ekle, aksi halde subagent kendi varsayılan OBSS şemasında
> yanıt döner ve dönüşü elle yeniden yazman gerekir:
> "ÇIKTI ŞEMASI — kendi varsayılan formatını KULLANMA. Yanıtını TAM OLARAK
> şu JSON şemasıyla ver: [aşağıdaki 3. adımdaki tam şemayı buraya yapıştır].
> `severity` alanı SADECE critical/high/medium/low, `category` alanı
> SADECE security/correctness/architecture/maintainability/performance/
> reliability/readability/test-gap/caveman/scope/risk olabilir."
> Subagent yine de kendi OBSS şemasında dönerse (nadiren olabilir), CLI
> ajanı bunu SESSİZCE kabul ETMEZ — 3. adımdaki şemaya elle çevirip yazar,
> ama bunu her seferinde beklenmedik bir durum olarak görüp raporda not
> düşer (postmortem'in tekrar eden kalıbı yakalayabilmesi için).

## Ön Koşul
Aynı `<task-slug>` altında üçü de mevcut olmalı:
- `atdd.md`
- `code_diff.md`
- `test_report.md` (veya `verify_report.md` — hangisi varsa)

Biri eksikse dur, kullanıcıya hangi skill'in önce çalıştırılması gerektiğini söyle.

## İnceleme Alanları
1. **Security** — açık/gizli güvenlik zafiyeti, secrets sızıntısı, yetkilendirme boşluğu.
2. **Correctness** — kod ve testler atdd.md'deki Acceptance Criteria'yı gerçekten karşılıyor mu.
3. **Architecture** — proje deseniyle tutarlılık, katman ayrımı.
4. **Maintainability** — okunabilirlik, isimlendirme, tekrar.
5. **Performance** — atdd.md'nin benchmark hedefleriyle uyum.
6. **Reliability** — hata yönetimi, rollback davranışı, race condition.
   Buna **Davranış Sözleşmesi denetimi** dahildir: atdd.md'deki
   "Davranış Sözleşmesi" tablosunun her satırını kodda karşıla. Üç şeyi ayrı
   ayrı ara, çünkü en pahalı hatalar buradan çıkıyor:
   - **Sessiz başarı**: hiçbir şey yapmadan başarı bildiren yol var mı?
      Varsa şiddeti en az `medium`.
   - **Boş sonuç ↔ hata karışması**: "veri yok" ile "yetkin yok" aynı değeri
     mi dönüyor? Sözleşme ayrılmasını istiyorsa bu bir bulgudur.
   - **Kısmi başarı**: yarısı olup yarısı olmayan durumda sözleşmenin
     yazdığı şey mi dönüyor, yoksa tam başarı mı bildiriliyor?
   Sözleşmede olup kodda karşılığı olmayan satır = bulgu. atdd.md'de tablo
   hiç yoksa bunu `test-gap` kategorisiyle raporla.
7. **Readability** — kod kendini açıklıyor mu.
8. **CAVEMAN Review** — gereksiz karmaşıklık:
   - gereksiz soyutlamalar
   - gereksiz yardımcı fonksiyonlar
   - ölü kod
   - spekülatif mimari
   - kullanılmayan public API'ler
   - gereksiz dosyalar
   - gereksiz konfigürasyon
   - tekrar eden karmaşıklık

   Daha basit bir implementasyon mümkünse, bunu bulgu olarak raporla.

## Scope Review
Her uygulanan özelliğin atdd.md'de var olduğunu doğrula. atdd.md'nin dışında kalan her şeyi (kapsam genişlemesi) bulgu olarak raporla.

## Risk Review
Şunlara bak:
- breaking change'ler
- gizli varsayımlar
- eksik validasyon
- race condition
- hata yönetimi boşlukları
- güvenlik riskleri
- bakım riskleri

## Adımlar (CLI ajanı tarafında)
1. `atdd.md`, `code_diff.md`, `test_report.md`/`verify_report.md` dosyalarını (aynı `<task-slug>` altında) oku.
2. Yukarıdaki 8 inceleme alanı + Scope Review + Risk Review'u uygula. Gerçek kodu değiştirme — sadece bulgu üret. `obss-red-team`'e dispatch ediyorsan, yukarıdaki "Şema uyuşmazlığı" notundaki ÇIKTI ŞEMASI talimatını prompt'a MUTLAKA ekle.
3. Birleşik bulguları aşağıdaki JSON şemasıyla `artifacts/<task-slug>/red_team.json` dosyasına yaz:

```json
{
  "task": "<task-slug>",
  "reviewed_at": "<ISO tarih>",
  "summary": "<1-3 cümlelik genel değerlendirme>",
  "findings": [
    {
      "severity": "critical|high|medium|low",
      "category": "security|correctness|architecture|maintainability|performance|reliability|readability|test-gap|caveman|scope|risk",
      "file": "path/to/file",
      "issue": "sorunun kısa tanımı",
      "better_approach": "önerilen daha iyi çözüm (varsa)",
      "reason": "neden daha iyi — somut gerekçe, dosya/atdd referansıyla"
    }
  ],
  "strengths": ["<implementasyonun iyi yaptığı şeyler, varsa>"],
  "risks": ["<Risk Review'dan çıkan maddeler, varsa>"],
  "caveman_review": {
    "complexity": "low|medium|high",
    "unnecessary_files": 0,
    "unnecessary_helpers": 0,
    "unnecessary_abstractions": 0
  },
  "scope_review": {
    "matches_atdd": true,
    "scope_expansion": false
  },
  "ready_to_commit": {
    "atdd_satisfied": true,
    "tests_passed": true,
    "no_critical_findings": true,
    "scope_respected": true,
    "caveman_satisfied": true,
    "security_acceptable": true,
    "maintainability_acceptable": true,
    "no_blocking_risks": true
  },
  "verdict": "approve|approve-with-changes|block"
}
```

### `category` / `severity` — sabit kelime dağarcığı, pazarlıksız

Bu iki alan **yalnızca** yukarıdaki listedeki değerlerden birini alır:
küçük harf, tek değer, birleştirme yok.

- Doğru: `"correctness"`, `"security"`, `"test-gap"`
- Yanlış: `"Security"` (büyük harf), `"Correctness / Test Gap"` (birleşik)

Bu bir biçimsellik değil: `postmortem` skill'i görevler arası kalıbı bu alanı
sayarak buluyor. Serbest metin yazıldığında aynı kusur iki ayrı kategori gibi
görünür ve tekrar eden kalıp gizlenir — gerçek `red_team.json` dosyalarında
bunun olduğu ölçüldü . Hiçbiri uymuyorsa en yakınını seç ve
gerekçeyi `reason` alanına yaz; yeni kategori uydurma.

4. `findings`/`strengths`/`risks` boşsa boş dizi yaz, uydurma bulgu ekleme. Her bulgu somut kanıt, dosya referansı ve atdd.md referansıyla desteklenmeli.
5. Kullanıcıya `red_team.json` yolunu, `verdict`'i ve `ready_to_commit` özetini bildir. Sonraki adımın (varsa `commit` skill'i) kullanıcı isteğiyle tetiklendiğini hatırlat — otomatik geçme.

## Verdict Kuralları
- **approve** — önemli bulgu yok.
- **approve-with-changes** — küçük/orta önem seviyesinde sorunlar var, commit engellenmez ama kullanıcıya bildirilir.
- **block** — kritik correctness, security veya ATDD ihlali var. Kullanıcıyı commit'ten önce açıkça uyar.

## Ready To Commit
Red-team sadece hata bulmakla kalmaz, commit'e hazır olup olmadığını da değerlendirir (`ready_to_commit` alanı). Bu sayede `commit` skill'i kaliteyi yeniden değerlendirmek zorunda kalmaz — sadece bu sonucu okur, kullanıcı onayını alır ve Git işlemlerini yapar.

Sorumluluk ayrımı:
- **verify** → teknik doğrulama (build, test, lint, coverage vb.)
- **red-team** → bağımsız kalite ve mimari inceleme + commit'e hazır olma değerlendirmesi
- **commit** → güvenli commit ve push

## Kural
- Bu skill kod düzenlemez, yazmaz, yeniden yazmaz, düzeltmez (Edit/Write yasak, sadece Read/Grep + JSON çıktısı).
- Bulgu uydurma — her bulgu kanıt, dosya referansı ve gerekçe içermeli.
- "block" verdict'i varsa, kullanıcıyı commit'ten önce uyar.
