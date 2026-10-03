Frontend-pipeline: tetikleyici yok (backend-only/dokümantasyon görevi — `.tsx`/`.jsx`/`.css` dosyası değişmiyor, "Görsel/UI kriteri" atdd.md'de boş).

# Plan — acik-kaynak-paketi-dogrulama
_Reference: atdd.md_

## Keşif Bulguları (atdd.md'yi güncelleyen gerçek repo durumu)

- **Repo kökü proje klasörüyle aynı** (`git rev-parse --show-toplevel` doğrulandı) — arama kapsamı güvenli, atdd.md'nin "doğrulanmadı" notu artık çözüldü.
- **PLAN.md madde 0.9 zaten `[x]` işaretli**: ".env.example — docs/ENV.md §8 şablonundan repo köküne kopyalanır" — tamamlanmış görünüyor.
- **Ama README.md:138 hâlâ şunu söylüyor**: "`.env.example` henüz repoda yok (PLAN.md 0.9). O zamana kadar docs/ENV.md §8'deki şablonu kopyalayın." Bu **stale/yanlış bir talimat** — gerçekte kök dizinde `.env.example` dosyası mevcut (bugün tarihli). Bu README'yi sıfırdan izleyen biri gereksiz bir ekstra adıma yönlendirilir, yani AC-3'ün ("kurulum talimatı eksik/yanlış adım") tam karşılığı — bu görev başlar başlamaz bulunan somut bir bulgu.
- **`.env` kök dizinde mevcut ve `.gitignore`'da** (satır 2), `git ls-files` ile tracked değil — sızıntı riski yok, ama AC-2 taramasında yine de kontrol edilecek.
- **`.secrets.baseline` zaten repoda var** — detect-secrets bu projede daha önce en az bir kez çalıştırılmış; `security-scan` skill'i muhtemelen bu baseline'ı kullanacak (atdd.md'nin "Unknowns" bölümündeki "baseline var mı" sorusu böylece cevaplandı).
- `backend/app/` şu an yalnız `__init__.py` + `main.py` içeriyor — backend iskeleti minimal ama PLAN.md 0.10'a göre tamamlanmış sayılıyor; bu görevin kapsamına backend kodu girmiyor, sadece kurulum talimatının çalışırlığı.
- `.env.example` içeriği bu oturumda **okunamadı** — sandbox izinleri dotfile okumayı engelliyor (CLAUDE.md'nin ".env okunmaz" kuralıyla tutarlı, `.env.example` da aynı korumaya takılıyor). İçeriğin gerçek sır içerip içermediği ancak `security-scan`/detect-secrets aracıyla (Claude'un doğrudan Read'i değil) doğrulanabilir — bu zaten AC-2'nin işi.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| README.md:138 | ".env.example henüz repoda yok" cümlesi yanlış — dosya zaten kökte mevcut (PLAN.md 0.9 tamamlanmış). AC-3 kapsamında bu stale talimat düzeltilmeli, aksi halde "sıfırdan kurulum" adımı gereksiz bir sapmayla başarısız/karmaşık olur. | low |

## New Files
(Yok — bu görev yeni dosya oluşturmuyor, mevcut dosyaların doğruluğunu denetliyor.)

## Dependencies
- `security-scan` skill'i (detect-secrets, mevcut `.secrets.baseline` dosyasıyla) — AC-2, AC-4, AC-7 (sır taraması) için kullanılacak.
- README.md'nin geri kalanı (Kurulum bölümü satır 121-190) — 138. satır dışında adımlar (`docker compose up -d`, backend/frontend kurulum komutları) şimdilik tutarlı görünüyor; sıfırdan kurulum denemesinde (AC-1) yine de baştan sona doğrulanacak.

## Migration Required?
Hayır — bu görev şema/veri değişikliği içermiyor, yalnızca dokümantasyon metni ve repo/sır durumu denetimi.

## Risks
- (atdd.md'den taşındı) Git geçmişi taraması büyük repo geçmişinde RAM/performans sorunu yaratabilir.
- (atdd.md'den taşındı) README'nin "sıfırdan" doğrulanması manuel olduğu için insan hatasına açık.
- (yeni) README.md:138'deki stale talimat şu ana kadar fark edilmemiş — bu, dokümantasyonun kod/PLAN.md ile senkron tutulmadığının bir işareti; benzer başka stale referanslar da olabilir (örn. diğer "henüz yok" notları), `test-copilot`/manuel doğrulama sırasında README'nin tamamı taranmalı, sadece 138. satırla sınırlı kalınmamalı.

## Open Questions
(Boş — atdd.md'nin Unknowns'ındaki iki soru (repo kökü, baseline varlığı) bu keşifte çözüldü. Kalan tek somut iş README.md:138 düzeltmesi + AC-1/AC-2'nin fiilen çalıştırılması, bunlar `test-copilot`/`code-copilot` aşamasına geçebilir.)
