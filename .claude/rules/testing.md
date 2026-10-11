---
name: Test kuralları
paths:
  - "tests/**"
  - "**/*_test.py"
  - "**/test_*.py"
  - "**/*.test.ts"
  - "**/*.spec.ts"
---

# Test

Detay: `docs/yetkin360-final-analiz.md` §21.

## Öncelik sırası

1. **Yetkilendirme testleri** — en yüksek öncelik
2. Domain kuralları (durum geçişleri, sinyal hesabı, doğrulama kuralları)
3. Integration (gerçek PostgreSQL, testcontainers)
4. API sözleşmesi
5. E2E — yalnız 2 senaryo

Neden yetkilendirme birinci: BOLA uygulama mantığı hatasıdır, otomatik tarayıcılar yakalayamaz. Tek savunma sistematik testtir.

## Yetkilendirme testleri parametrik yazılır

Her uç × her aktör kombinasyonu elle yazılmaz — tablo ile üretilir. Yeni endpoint eklendiğinde tabloya satır eklenir.

Beklenen sonuçlar:
- Başka kiracının kaynağı → **404** (403 değil)
- Sahibi olmayan kaynağı güncelleme → **404**
- `private_note` → talent'a **asla** dönmez
- Askıya alınmış kullanıcı yazma → **403**
- İptal edilmiş doğrulama linki → **410**

## Kurallar

- Test gerçek davranışı doğrular. Sadece geçsin diye mock'lama, assert'i gevşetme.
- Bir test kırıldıysa **testi değiştirme** — önce kodun mu testin mi yanlış olduğunu anla, sonra sor.
- Integration testlerinde gerçek PostgreSQL kullan (SQLite ile PostgreSQL davranışı farklı — CHECK, RLS, tip sistemi).
- Her test kendi verisini kurar, birbirine bağımlı test yazma.

## Yasak

- Testi silerek "düzeltmek"
- `skip`/`xfail` ile geçici gizlemek (gerçekten geçiciyse sebebini yaz ve kullanıcıya söyle)
- Yetkilendirme testi olmadan endpoint commit etmek
