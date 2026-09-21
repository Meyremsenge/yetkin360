---
name: refactor
description: The missing third step of red→green→refactor — improves the structure of code that already passes its tests, without changing behavior. Runs between `verify` (green) and `red-team`. Use when tests pass but the implementation is rough, or when `postmortem` flags a file that keeps collecting findings. Behavior-preserving only; if a test has to change, it is not a refactor.
---

# refactor — yeşilden sonra, temizlik

## Kullanılacak destek skiller
- `ponytail` (full) — **bu skill'in belkemiği**. En tembel, en az değişiklik.
- `caveman` (full) — her zaman aktif.
- `superpowers:systematic-debugging` — refactor testi kırdıysa kör deneme yerine bunu izle.

## Neden var
Boru hattı `red → green → refactor` diyordu ama üçüncü adım fiilen yoktu.
`verify` kendini "refactor gate" diye tanıtıyor, oysa yaptığı iş **kontrol
koşmak**; hiçbir adım kodu iyileştirmiyordu. Sonuç: testler geçtiği an iş
bitmiş sayılıyor ve `code-copilot`'ın ilk çalışan hali kalıcı hale geliyordu.
`postmortem`'in "sıcak dosya" sinyali (aynı dosya görev görev bulgu alıyor)
tam olarak bunun birikmiş halidir.

## Ön koşul — pazarlıksız
**Tüm testler yeşil olmalı.** Refactor'ün tek güvencesi testlerdir; kırmızı
testin üstüne refactor yapmak, ağı olmadan ip cambazlığıdır. `verify` FAIL
verdiyse bu skill çalışmaz — önce yeşile dön.

## Tanım: neyi değiştirebilirsin
Refactor **davranışı korur**. Ölçüt tek ve nettir:

> Testleri değiştirmen gerekiyorsa, yaptığın şey refactor değildir.

Test dosyasına dokunma ihtiyacı duyuyorsan dur ve bunu bildir — o iş yeni bir
`atdd` gerektirir, buranın kapsamı değil.

İzin verilen: isimlendirme, fonksiyon çıkarma/birleştirme, tekrarın kaldırılması,
ölü kodun silinmesi, iç içe geçmenin (nesting) düşürülmesi, sihirli sayının
sabite çevrilmesi, uzun parametre listesinin toplanması.

İzin verilmeyen: yeni özellik, API/imza değişikliği (çağıran kodu bozar),
performans "iyileştirmesi" için davranış değişimi, bağımlılık ekleme.

## Kapsam sınırı
`code_diff.md`'deki **bu görevde değişen dosyalarla** sınırlı kal. Projenin
geri kalanını "yoldan geçerken" temizlemek diff'i incelenemez hale getirir ve
`red-team`'in işini imkânsızlaştırır. Başka yerde gördüğün sorunu rapora not
düş, dokunma.

## Yöntem — küçük adım, sık doğrulama

1. **Aday listele.** `code_diff.md`'yi ve dokunulan dosyaları oku. En fazla
   **3 iyileştirme** seç; hepsini birden yapma.
2. **Gerekçelendir.** Her aday için "neden şimdi" yaz. Gerekçe "daha temiz
   olur" ise `ponytail` gereği **yapma** — okunabilirlik iddiası ölçülebilir
   bir şeye dayanmalı (tekrar sayısı, iç içe derinlik, fonksiyon uzunluğu).
3. **Tek tek uygula, her adımda testi koştur.** Bir değişiklik → test → yeşil →
   sonraki. Toplu değişiklikte hangi adımın kırdığı bulunamaz.
4. **Kırdıysan geri al.** Refactor'ün maliyeti düşük olmalı; ısrar etme,
   o adayı "denendi, kırdı" diye rapora yaz ve geç.
5. **Bitince `verify`'ı tam koştur.** Ara koşumlar sadece ilgili testlerdi.

## Ne zaman hiç yapmamalı
- Test yoksa veya kapsam zayıfsa (güvence yok → refactor kumar).
- Görev acil bir düzeltmeyse (hotfix); temizlik ayrı işe bırakılır.
- Kod yakında silinecekse.
- İyileştirme gerekçesi yalnızca kişisel tercihse.

`ponytail` burada varsayılan cevabın **"dokunma"** olduğunu söyler. Refactor'ün
kendisi de bir değişikliktir ve her değişiklik risk taşır.

## Raporlama
`artifacts/<task-slug>/refactor.md`: yapılan her değişiklik
(dosya + ne + neden), test sonucu, **denenip geri alınanlar**, ve dokunulmayıp
not düşülen sorunlar. Sonra `red-team`'e devret.

## Yapmayacakların
- Test dosyası yazmaz/değiştirmez (`test-copilot`'ın işi).
- Yeni davranış eklemez.
- Kapsam dışı dosyaya dokunmaz.
- Testler kırmızıyken çalışmaz.
