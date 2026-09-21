---
name: postmortem
description: Closes the pipeline's learning loop — aggregates red_team.json findings AND security_scan.md/verify_report.md gate results across finished tasks, finds categories/gates that repeat, and turns them into concrete checks for the next atdd.md. Use after a task's commit, or when the user asks what keeps going wrong, which files are fragile, whether a tool/gate keeps failing, or whether the process is improving. Reports patterns and proposes checklist items; never rewrites past work.
---

# postmortem — aynı hatayı ikinci kez yapmamak

## Kullanılacak destek skiller
- `caveman`, `ponytail` (full) — her zaman aktif.

## Neden var
Boru hattında öğrenme döngüsü yoktu. `red-team` her görevin sonunda bulgu
üretiyor, bulgular `red_team.json`'a yazılıyor ve **orada kalıyordu**. Bir
sonraki görevin `atdd`'si onlardan habersiz başlıyor, dolayısıyla aynı hata
tekrar edebiliyordu. Tek görevin incelemesi "bu sefer ne oldu"yu söyler;
görevler arası toplam "**neyi sistematik olarak yanlış yapıyoruz**"u söyler.
İkincisi süreç kusurudur ve kontrol listesine yazılarak çözülür.

## Ne zaman çalışır
Bir görev `commit`'lendikten sonra (zincirin parçası değil, ayrı çağrılır), ya
da kullanıcı "ne sık patlıyor / hangi dosya kırılgan / süreç iyileşiyor mu"
diye sorduğunda.

## Nasıl çalıştırılır

```bash
"$HOME/.claude/security-tools/venv/Scripts/python.exe" "$HOME/.claude/skills/postmortem/aggregate.py" <docs_dizini>
```

`<docs_dizini>` her görev için bir alt dizin içerir (her birinde `red_team.json`) —
örn. `your-repo/docs`. Son N göreve bakmak için `--since-tasks N`,
makine-okunur çıktı için `--json`.

Script aynı `<docs_dizini>` taramasında, her görev alt klasöründe varsa
`security_scan.md` ve `verify_report.md`'yi de otomatik okur (ayrı bir flag
gerekmez) — bu iki dosyanın "Gate | Sonuç/Result | ..." formatındaki
markdown tablosunu parse edip her (gate, sonuç) çiftini çıkarır. Format
tabloya uymuyorsa (başlık satırı bulunamazsa) o görev sessizce
"OKUNAMAYAN" listesine düşer, script çökmez.

## Çıktıyı nasıl okumalı

- **Tekrar eden kategori** = süreç kusuru adayı. Tek görevde çıkan bulgu şanssızlık,
  üç görevde çıkan aynı kategori kontrol listesi eksikliğidir.
- **Sıcak dosya** = mimari sinyal. Aynı dosya görev görev bulgu alıyorsa sorun
  o görevlerde değil, o dosyadadır (muhtemelen çok fazla sorumluluk taşıyor).
- **Şiddet dağılımı** = trend. Zamanla `medium`/`high` oranı düşmüyorsa süreç
  değişikliğin işe yaramamış demektir.
- **`security_scan.md`/`verify_report.md` tekrar eden gate sonuçları** = araç/
  süreç kusuru adayı. `PASS`/`N/A` ilgi çekici değildir (elenir); bir gate'in
  aynı sonuçla (`FAIL`/`MISSING`/`INCONCLUSIVE`/`PENDING`/`ERROR`/`TIMEOUT`)
  2+ farklı görevde tekrarlaması, o gate'in araç/kurulum/kapsam sorunuyla
  kronik olarak karşılaştığı anlamına gelir. Örnek (canlı, bu skill'e bu
  özellik eklenirken keşfedildi): `detect-secrets (araç) -> MISSING` — araç
  repo-dışı dosyaları desteklemiyor; bu 2+ görevde tekrarlarsa `security-scan`
  skill'ine "repo dışı dosyalar için manuel inceleme akışı" maddesi eklenmeli,
  her seferinde elle iş üretmek yerine.

> **Az veriyle kalıp uydurma.** Script 5 görevin altında uyarı basar. 2 görevde
> 2 kez çıkan bir kategori kalıp değildir; 10 görevde 7 kez çıkan kalıptır.
> Emin değilsen "henüz veri yetersiz" de — uydurulmuş kalıp, kalıp olmamasından
> kötüdür çünkü yanlış yere kontrol ekletir.

## Bulgudan eyleme

Her tekrar eden kategori için **tek bir somut şey** üret. Genel öğüt yasak.

- Kötü: "correctness'a daha çok dikkat edilmeli"
- İyi: `atdd` şablonuna madde — "Girdi formatı varsayımı: parse edilen dosyanın
  beklenmedik bir ayraç/başlık içermesi durumunda davranış AC olarak yazıldı mı?"
  (gerekçe: correctness bulgularının 3'ü de sabit-format varsayımından çıktı)

Eylem üç yerden birine gider:
1. **`atdd` kontrol listesi** — gereksinim aşamasında yakalanabilecekse (en ucuz).
2. **`plan` / `verify` gate'i** — ancak kodu görünce anlaşılabiliyorsa.
3. **Refactor görevi** — sıcak dosya sinyaliyse, `refactor` skill'i ile ayrı iş.

Tekrar eden gate sonuçları (`security_scan.md`/`verify_report.md`) için dördüncü
hedef: **ilgili aracı çalıştıran skill'in kendisi** (`security-scan`, `verify`,
`supabase-check` vb.) — gate her seferinde aynı sebeple MISSING/FAIL oluyorsa
kök neden görevde değil, o skill'in aracı çağırma şeklindedir; düzeltme oraya
yazılır, her göreve tekrar tekrar manuel iş yükletilmez.

## Raporlama
`<docs_dizini>/POSTMORTEM.md` dosyasına yaz ve **üzerine ekle, silme** — geçmiş
ölçüm silinirse trend kaybolur. Her koşumda: tarih, görev sayısı, kategori
tablosu, tekrar edenler, ve önerilen somut eylemler + nereye gittiği.

Kullanıcı onaylarsa eylemi ilgili skill'e gerçekten uygula; onaysız skill
değiştirme.

## Yapmayacakların
- Geçmiş görevlerin kodunu veya raporunu değiştirmez.
- Kişi/araç suçlamaz — çıktı süreç hakkındadır, "Copilot kötü yazdı" değil.
- Az veriden kalıp uydurmaz.
- Kontrol listesini şişirmez: her koşumda en fazla 2-3 yeni madde önerir,
  yoksa kimse listeyi okumaz.

## Agentic karşılığı — `agentic_judge/*.json` üzerinden

`red_team.json` kod görevlerini kapsıyor; agentic görevlerde (`agentic-judge`
skill'inin ürettiği tekil transkript değerlendirmeleri) aynı öğrenme
döngüsü ayrı bir script ile çalışır — şemalar farklı olduğu için `aggregate.py`
bunları okuyamaz.

```bash
"$HOME/.claude/security-tools/venv/Scripts/python.exe" "$HOME/.claude/skills/postmortem/aggregate_agentic.py" <docs_dizini>
```

`<docs_dizini>` altında her task-slug kendi `agentic_judge/<conversation_id>.json`
dosyalarını taşır (bkz. `agentic-judge` skill'inin 4. adımı — append-only,
her transkript kendi dosyasında).

### Çıktıyı nasıl okumalı (trajectory_review/response_review/scope_review'a göre)

- **`top_extra_calls` / `top_missing_calls`** — bir `(agent, tool)` çifti
  tekrar ediyorsa bu prompt/tool-description sorunudur: fazladan çağrılan
  tool'un tetikleme koşulu çok geniş, eksik çağrılanın description'ı zayıf
  veya few-shot örneği eksik.
- **`order_error_rate`** — bir agent için %15'i aşıyorsa, o agent'ın
  planlama/orchestration talimatına açık sıra kuralı eklenmeli.
- **`criteria_avg_per_agent`** — bir kriterin (faithfulness/completeness/
  tone_fit/actionability) haftadan haftaya düşen trendi, sessiz bir
  regression sinyalidir — hata log'u olmadan bile yakalanır.
- **`scope_creep_rate`** — diğer metriklerden daha sert bir eşiğe tabidir
  (script'te %3). `sensitive_tool_hits` doluysa bu satır sadece süreç
  notu değil, **anında** ilgili tool'un izin kapsamının daraltılmasını
  gerektiren bir bulgudur — `authz-test` skill'ine yönlendir.
- **`judge_user_disagreement`** — judge yüksek puan verirken kullanıcı
  retry/edit/thumbs_down verdiyse, sorun agent'ta değil **judge rubric'inde**
  olabilir. Bu liste büyüyorsa (`>%5` tur) `agentic-judge` subagent
  prompt'unun ilgili kriterinin tanımı gözden geçirilmeli, agent değil.

### Bulgudan eyleme (agentic sürüm)
Aynı "genel öğüt yasak" kuralı geçerli — her tekrar eden sinyal için tek
somut değişiklik:
- Kötü: "tool seçimine daha dikkat edilmeli"
- İyi: `search_jobs` agent'ı 8 turda 6 kez `get_company_data`'yı gereksiz
  çağırdı → tool description'ına "yalnızca kullanıcı şirket hakkında soru
  sorarsa çağır" notu eklendi.

Eylem üç yerden birine gider:
1. **`atdd.md`'nin "Agentic Değerlendirme Kriterleri" bölümü** — beklenen
   trajectory veya hassas tool listesi eksikse (en ucuz).
2. **Agent/tool prompt revizyonu** — trajectory/response driftiyse.
3. **`agentic-judge` subagent'ının rubric'i** — judge-kullanıcı uyuşmazlığı
   sinyaliyse.

`POSTMORTEM.md`'ye aynı dosyaya, ayrı bir "Agentic" başlığı altında eklenir
— üzerine yazılmaz, mevcut kod-görevi geçmişiyle karışmaz.
