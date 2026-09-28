# Code Diff — acik-kaynak-paketi-dogrulama

## Değiştirilen dosyalar
- `README.md` — satır 138-139'daki stale blockquote silindi:
  ```
  > **Not:** `.env.example` henüz repoda yok ([PLAN.md](PLAN.md) 0.9).
  > O zamana kadar [docs/ENV.md](docs/ENV.md) §8'deki şablonu kopyalayın.
  ```
  Kurulum kod bloğu (`git clone` / `cp .env.example .env` / `docker compose up -d`) ve devamı değiştirilmedi. `git status --short README.md` ile doğrulandı (`M README.md`), `Read` ile satır 128-142 kontrol edildi — yalnızca stale not kaldırılmış.

## AC Eşlemesi
| AC | Sonuç |
|---|---|
| AC-1 (happy path kurulum) | Kurulum adımları artık yanıltıcı ek adıma yönlendirmiyor. |
| AC-3 (stale/yanlış adım tespiti) | Çözüldü — `test_readme_does_not_claim_env_example_missing` artık geçmeli (stale ifade README'de yok). |

## Kalan sınırlamalar
Yok — bu görevin diğer kısımları (AC-1'in fiili sıfırdan kurulum denemesi, AC-2/AC-7'nin gerçek `security-scan`/detect-secrets çalıştırması) implementasyon değil, `verify` aşamasında fiilen yapılacak doğrulama adımları.

## Varsayımlar
- `.env.example` dosyasının repo kökünde gerçekten var olduğu plan.md'deki keşifle zaten doğrulanmıştı; bu adım yalnızca README metnini o gerçeğe uydurdu.

## CAVEMAN self-review
Yeni dosya yok, yeni soyutlama/yardımcı fonksiyon yok — tek değişiklik iki satırlık bir metin silme. Test dosyasına dokunulmadı (`backend/tests/test_repo_packaging.py` — `git status` çıktısında hâlâ `??` yani izlenmemiş/değiştirilmemiş).
