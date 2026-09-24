# Entegrasyon Notu — YET-74/98/99 (PLAN 2.12) Kanıt Yükleme Frontend

**Durum: Backend'in bir kısmı gerçekten var ama bu oturumda backend+MinIO çalışmadığı için
üçünün de MOCK VERİYLE geliştirildi (kullanıcı onayıyla — bkz. konuşma geçmişi). Tam entegre DEĞİL.**

Jira'da bana atanmıştı: YET-74 (→ YET-98/99), PLAN 2.12 ("Frontend: çıktı yükleme —
imzalı URL akışı, ilerleme, hata").

## Backend uçlarının gerçek durumu

| Adım | Uç | Durum |
|---|---|---|
| 1) İmzalı URL alma | `POST /evidence/upload-url` | ✅ **Var** (`backend/app/api/evidence.py:31`, PLAN 2.5/YET-82-83) |
| 2) Depolamaya yükleme | MinIO'ya doğrudan istek | Backend bir **presigned POST** üretiyor (form alanları + `upload_url`), **PUT değil**. Jira ticket metni "upload-url → PUT → POST /evidence" diyor ama gerçek şekil bu değil. |
| 3) Kanıt kaydı | `POST /evidence` | ❌ **Yok** — `Evidence` modeli/tablosu backend'de henüz oluşturulmadı (PLAN 2.6 tamamlanmamış) |

Yani adım 1 gerçekten var, ama **bu geliştirme oturumunda backend (`uvicorn`) ve MinIO
(`docker compose up -d`) çalışmıyordu** — kullanıcıya soruldu, "sadece frontend dev server
çalışıyor" cevabı alındı. Bu yüzden 3 adımın **üçü de** `frontend/lib/api/evidence.ts`
içinde mock'landı, ikisi gerçek backend ayaktayken kolayca gerçek hale getirilebilecek
şekilde (adım 1 ve 2), biri (adım 3) backend PLAN 2.6/2.7'yi tamamlayana kadar zorunlu mock.

## Ne yapıldı

`frontend/lib/api/evidence.ts` — üç ayrı bayrak, üç ayrı gerçek/mock ayrımı:

- `USE_MOCK_UPLOAD_URL` (adım 1) — backend+MinIO ayaktayken `false` yapılabilir,
  gerçek çağrı kodu zaten yazılı (`apiFetch("/evidence/upload-url", ...)`).
- `USE_MOCK_STORAGE_UPLOAD` (adım 2) — aynı şekilde, gerçek kod bir `FormData` ile
  presigned POST yapıyor (**PUT değil** — yukarıdaki not).
- Adım 3 (`recordEvidence`) — **her koşulda mock**, backend gap kapanana kadar kaldırılamaz.
  `localStorage`'da tutuluyor (`yetkin360_mock_evidence_v1`), `deliverable_id`'ye göre filtreleniyor.

`scan_status` (PENDING/CLEAN/INFECTED/FAILED) gerçek sistemde bir arka plan worker +
outbox ile asenkron sonuçlanır (bkz. `.claude/rules/security.md`). Burada manuel testte
"tarama bekleniyor" durumunun gözlenebilmesi için ~4 saniye sonra CLEAN'e dönen bir
`setTimeout` simülasyonu var — sadece o tarayıcı sekmesinde çalışır, gerçek davranış
değildir. **Not:** ilk sürümde bu %85 CLEAN / %15 INFECTED rastgele dönüyordu; dosya
içeriğiyle ilgisi olmayan bu rastgelelik manuel testte kafa karıştırdığı için (kullanıcı
geri bildirimi) deterministik CLEAN'e sabitlendi. INFECTED rozetinin doğru render olduğu
artık sabit mock veriyle otomatik testte doğrulanıyor (`evidence-upload-form.test.tsx`).

UI: `frontend/app/calismalar/[id]/evidence-upload-form.tsx` — her çıktının (deliverable)
altına gömülü, dosya seçilince 3 adımı sırayla yürütür, ilerleme metni gösterir
("1/3 → 2/3 → 3/3"), yüklenmiş kanıtları tarama durumu rozetiyle listeler.

## Kapsam dışı bırakılanlar (bilinçli)

- Sunucu tarafı 422/429/403/503 hata simülasyonu **eklenmedi** — client-side `validateFile()`
  zaten aynı içerik-türü/boyut kurallarını (backend/app/services/storage.py ile birebir)
  uyguladığı için "dosya reddi" senaryosu ağa gitmeden yakalanıyor. Gerçek backend
  bağlandığında bu hata kodları zaten `ApiError` olarak fırlayacak; ek bir UI değişikliği
  gerekmez (aynı `catch` bloğu `messages.errors.generic` gösteriyor — backend spesifik
  kod eklenmek istenirse `TransitionActions`'daki gibi `error.code` dallanması eklenebilir).
- 403 (`TALENT_PROFILE_REQUIRED`/`ACCOUNT_SUSPENDED`) manuel test edilemiyor — mock rol
  kontrolü yapmıyor (YET-73'teki aynı sınırlama).

## Backend uçları eklendiğinde/ayaktayken yapılacaklar

1. `USE_MOCK_UPLOAD_URL` ve `USE_MOCK_STORAGE_UPLOAD`'ı `false` yap (backend+MinIO çalışıyorsa
   bu ikisi hemen gerçek olur, adım 3'ü beklemeye gerek yok).
2. Backend `POST /evidence` eklenince: `recordEvidence()`'i gerçek `apiFetch` çağrısına
   çevir, `localStorage` mock store'unu (`EVIDENCE_STORAGE_KEY`, `loadEvidenceStore`,
   `saveEvidenceStore`, `scheduleMockScanResolution`) sil.
3. Gerçek `Evidence` response şemasının burada tanımlı `EvidenceRecord` tipiyle eşleştiğini
   doğrula — özellikle `kind`/`provenance` enum değerleri final-analiz §7.6 ile aynı olmalı.

## Test durumu

- `lib/api/evidence.test.ts`: `validateFile` (allowlist/boyut), 3 adımın mock akışı,
  localStorage kalıcılığı, tarama simülasyonunun PENDING'den çıkması.
- `app/calismalar/[id]/evidence-upload-form.test.tsx`: dosya reddi (yanlış tür/boyut),
  başarılı akışta 3 adımın sırayla ve doğru argümanlarla çağrıldığı, hata durumunda genel
  hata mesajı.
- **Uçtan uca (gerçek backend+MinIO ile) entegrasyon testi YAPILMADI.**
