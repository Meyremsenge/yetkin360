# Refactor — koordinator-dashboard-frontend

Ön koşul: tüm testler yeşil (bkz. verify_report.md gate 6, 21/21 PASS). Refactor çalıştırılabilir durumda.

## Aday Değerlendirmesi
`verify_report.md`'nin "Refactor Aday Kontrolü" bölümünde zaten yapılan tespit doğrulandı:
- `frontend/lib/api/institutions.ts` (33 satır, tek fonksiyon) — aday yok.
- `frontend/app/kurum/[id]/panel/page.tsx` (110 satır) — iki liste bloğu görsel olarak benzer ama farklı alan adları (`started_on`/`ended_on`) ve farklı empty-state mesajları taşıyor; ortak bir component'e çıkarmak şu an **spekülatif soyutlama** olur (`ponytail`: gerekçe "daha temiz olur" ise dokunma, ölçülebilir bir tekrar/karmaşıklık eşiği yok — 2 tekrar, kısa bloklar).
- Kullanılmayan `scripts` değişkeni (`page.test.tsx:379`, lint uyarısı) — bu bir test dosyası, refactor'ün kapsamı implementasyon dosyaları; test dosyasına dokunmak bu skill'in yasağı ("test dosyası yazmaz/değiştirmez").

## Karar
**Hiçbir değişiklik yapılmadı.** 3 adayın hiçbiri ölçülebilir bir eşiği (tekrar sayısı, iç içe derinlik, fonksiyon uzunluğu) geçmiyor — `ponytail` gereği varsayılan "dokunma" korundu.

## Sonraki adım
`red-team`.
