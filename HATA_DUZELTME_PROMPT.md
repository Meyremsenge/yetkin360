# HATA.md Düzeltme Promptu — sonraki oturumda /atdd ile başlamak için

Bu dosya, `HATA.md`'deki bulguları düzeltmeye başlarken kullanılacak hazır
prompt'u içerir. Kaybolmasın diye ayrı dosyaya yazıldı. Token bitmeden önce
hazırlandı, henüz uygulanmadı.

---

## Kullanım

Yeni bir oturumda, sırayla her bulgu için `/atdd` skill'ini şu prompt'la başlat
(her bulgu ayrı bir atdd.md üretmeli, hepsini aynı anda tek atdd.md'ye
sıkıştırma):

```
/atdd

HATA.md dosyasındaki [BULGU NUMARASI] numaralı bulguyu düzelt: [BULGU BAŞLIĞI].

ÖNEMLİ — önce bunu doğrula, düzeltmeye körü körüne başlama:
HATA.md 2026-09-27'de statik kod analiziyle (canlı backend+frontend ayağa
kaldırılmadan) yazıldı. Bulgunun hâlâ geçerli olduğunu, dosyanın hâlâ o
satırlarda o şekilde durduğunu VE backend'in gerçekten iddia edilen endpoint'e
sahip olduğunu kendi başına tekrar oku ve doğrula — HATA.md'nin kendisini
sorgusuz doğru kabul etme. Eğer bulgu artık geçersizse (biri zaten düzeltmiş,
ya da HATA.md'nin okuduğu kod farklı bir dalda/committe yazılmış, ya da benim
yorumum yanlışsa) bunu aynen söyle ve DÜZELTME YAPMA — bana neden geçersiz
olduğunu kısaca açıkla ve dur.

Doğrulama adımları (düzeltmeye başlamadan önce):
1. HATA.md'de referans verilen dosya:satır'ı gerçekten oku, hâlâ o davranışta mı bak.
2. Backend'de iddia edilen endpoint'in gerçekten var olduğunu grep ile teyit et
   (route path + HTTP metodu + request/response şeması).
3. Mevcut çalışma dalının `main`'in gerisinde olup olmadığını kontrol et
   (`git log HEAD..main --oneline`) — eğer geride ise önce main'e göre durumu
   netleştir, eski bir dalda "hata" diye rapor edilen şey main'de zaten
   düzeltilmiş olabilir.
4. Eğer gerçekten hataysa: atdd.md'yi normal akışta yaz (persona, acceptance
   criteria, behaviour-contract tablosu), sonra pipeline'ın geri kalanına
   (plan → test-copilot → code-copilot → verify → red-team → commit) geç.

Kapsam dışı: HATA.md'de bahsedilmeyen başka mock/eksik bulursan onu da not et
ama bu görevin kapsamına dahil etme — ayrı bir /atdd turu olarak işaretle.
```

---

## Sırayla işlenecek bulgular (HATA.md'deki numaralandırma)

Önerilen sıra — bağımlılık zincirine göre (1 ve 2 birbirinden bağımsız,
paralel de yapılabilir; 3 hepsinden önce/bağımsız yapılabilir çünkü sadece
config dosyası):

1. **HATA.md §3** — `.env.example` NEXT_PUBLIC_API_BASE_URL düzeltmesi
   (PLAN.md 3.20). En düşük riskli, tek satır, bağımlılığı yok. Önce bunu yap.

2. **HATA.md §1** — Evidence upload akışının mock'tan gerçek backend'e
   bağlanması (PLAN.md 3.17). `frontend/lib/api/evidence.ts`:
   `USE_MOCK_UPLOAD_URL`, `USE_MOCK_STORAGE_UPLOAD` bayraklarını kaldır,
   `recordEvidence()`'ı gerçek `POST /evidence` çağrısına çevir.
   **Bağımlılık:** Docker (Postgres+MinIO) ayakta olmalı, `baslat.bat`
   çalıştırılmış olmalı — gerçek MinIO'ya yükleme testi backend ayakta
   değilse doğrulanamaz.

3. **HATA.md §2** — Değerlendirme formunun mock'tan gerçek backend'e
   bağlanması (PLAN.md 3.18). `frontend/lib/api/evaluation.ts`:
   `submitEvaluation()`'ı gerçek `POST /engagements/{id}/evaluation`
   çağrısına çevir. **Dikkat:** mock 422/409 ayrımı yapıyor, backend'in
   gerçek davranışı (ikisi de 409 CONFLICT) `backend/app/api/engagements.py`
   satır ~598 docstring'inde yazıyor — bunu tekrar oku, backend değişmiş
   olabilir, response body'sindeki `code` alanına göre ayrım yapılabiliyor mu
   kontrol et.

4. **HATA.md §4** — localStorage'a PII/hassas veri yazılmaması (PLAN.md
   3.19). 2 ve 3 tamamlandıktan SONRA yapılmalı — mock kod kaldırılınca
   localStorage kullanımı da otomatik gidecek, bu madde asıl "geriye kalan
   localStorage çağrısı kaldı mı" temizlik/doğrulama adımı.

5. **HATA.md §7** — `require_email_verified()` hiçbir router'da
   kullanılmıyor (PLAN.md 3.21). Bağımsız, backend-only. Önce bir ürün/güvenlik
   kararı gerekiyor: hangi uçlarda zorunlu olacak? Kod yazmadan önce bu soruyu
   /atdd aşamasında netleştir (Risks/Assumptions/Unknowns bölümüne yaz, tahmin
   etme).

6. **HATA.md §8** — `tests/test_seed.py` rollback izolasyonu bypass ediyor
   (PLAN.md 3.22). Bağımsız, backend-only, düşük risk.

7. **HATA.md §6 (PLAN.md 3.23)** — Son doğrulama: 1-6 bittikten sonra
   `grep -rn "USE_MOCK\|localStorage\." frontend/lib/api/` çalıştır, test
   dosyaları hariç sıfır sonuç dönmeli. Bu madde kapanmadan PLAN 2.14
   (uçtan uca duman testi) güvenilir sayılmaz.

---

## Genel hatırlatma (her /atdd turunda tekrar et)

- CLAUDE.md kuralı: yeni endpoint/değişiklik = aynı commit'te yetkilendirme
  testi. Evidence/evaluation mock→gerçek geçişinde YENİ endpoint açılmıyor
  (zaten var olan endpoint'e bağlanılıyor) ama var olan yetkilendirme
  testlerinin (`pytest tests/authorization -q`) hâlâ geçtiğini doğrula.
- Migration YOK bu değişikliklerde — sadece frontend dosyaları değişiyor
  (§1, §2, §3, §4) veya backend'de yeni `Depends()` bağlanıyor (§5) — hiçbiri
  şema değiştirmiyor, alembic'e dokunma.
- Doğrulama matrisi: "Frontend mantık" satırı → `npm run typecheck` +
  ilgili bileşen testi. Backend'e dokunulan maddelerde (§5, §6) ilgili
  unit+integration testi.
- Bulgunun geçersiz çıkması normal ve iyi bir sonuçtur — "araştırdım, hâlâ
  geçerli" ya da "araştırdım, artık geçersiz çünkü X" cevaplarının ikisi de
  kabul edilebilir. Amaç körü körüne HATA.md'yi uygulamak değil, gerçek
  durumu teyit etmek.
