# CLAUDE.md — Yetkin360

Zemin360 Hackathon projesi (GİRVAK × İSTKA × Bilgi Üni.). Kanıta dayalı yetkinlik platformu: beyan → kanıt → tanıklık → doğrulanmış deneyim.
**Teslim: 9-11 Ekim 2026, İstanbul.** Geliştirme: 18 Eylül – 9 Ekim. Platform **açık kaynak** olacak.

Stack: FastAPI + PostgreSQL + Next.js (TypeScript). Modüler monolit, tek VPS.

---

## Dil

- Kullanıcıyla **Türkçe** konuş — açıklama, ilerleme notu, soru, hata yorumu dahil.
- Kod İngilizce: tanımlayıcılar, kod yorumları, commit mesajları, API alan adları.
- UI metni Türkçe; koda gömülmez (sabit metin dosyasından).
- İngilizce teknik terim/komut/log çıktısı olduğu gibi alıntılanır, açıklama cümlesi Türkçe kalır.
- **Bu kural bağlam özetlemesi (compaction) sonrasında da geçerlidir.** Uzun oturumda İngilizceye kayma yok.

---

## Tek doğruluk kaynağı

| Dosya | Ne için | Ne zaman okunur |
|---|---|---|
| **`docs/PLAN.md`** | Yapılacak işlerin **sırası** ve ilerleme durumu | Her iş başlangıcında |
| **`docs/yetkin360-final-analiz.md`** | Tüm mühendislik ve ürün kararları (39 bölüm) | İlgili bölüm, ihtiyaç anında |
| `docs/` | Detaylı şema, API, güvenlik, mimari | İlgili bölüm, ihtiyaç anında |

**Kritik kural: Dokümanların tamamını okuma.** Final analiz ~2200 satır. İhtiyacın olan bölümü `grep` ile bul, sadece onu oku.

Mimari kararlar verilmiştir. **Yeni mimari önerme; uygula.** Ancak uygulama sırasında bir karara aykırı somut kanıt görürsen (başarısız test, ölçüm, çelişen kısıt) sessizce sapma — kısa bir not düş ve sor. Sessizce sapmak da, itiraz etmeden yanlış uygulamak da hatadır.

Bu dosyada `@import` **bilinçli olarak yok**: import edilen dosyalar her oturumda yüklenir. Dokümanlar ihtiyaç anında okunur.

---

## Komutlar

| İş | Komut |
|---|---|
| Ortam | `docker compose up -d` (PostgreSQL + MinIO) |
| Backend | `uvicorn app.main:app --reload` (backend/ içinde) |
| Frontend | `npm run dev` (frontend/ içinde) |
| Test (hepsi) | `pytest -q` |
| Test (yetkilendirme) | `pytest tests/authorization -q` |
| Lint + tip | `ruff check . && mypy app` · frontend: `npm run lint && npm run typecheck` |
| Migration | `alembic revision --autogenerate -m "..."` · uygula: `alembic upgrade head` |
| Seed verisi | `python -m scripts.seed` |
| Demo sıfırla | `python -m scripts.reset_demo --yes [--reseed]` (skills hariç tüm tabloları TRUNCATE; prod'da çalışmaz) |

*(Komutlar proje kurulduğunda kesinleşecek; değişirse bu tablo güncellenir.)*

---

## Değişmez kurallar (ihlal = değişiklik reddedilir)

### Mimari
- Katman: `api/ → services/ → models/`. İş mantığı **yalnız** `services/` içinde; router'da iş mantığı yazılmaz.
- **Repository katmanı yok.** SQLAlchemy doğrudan servis içinde kullanılır (gereksiz soyutlama — final analiz §13.2).
- Pydantic şemaları ile ORM modelleri **asla aynı sınıf değildir**. ORM modeli doğrudan response olarak dönülmez.
- Modüller birbirinin iç dosyalarını import etmez.

### Veri
- Tüm veri erişimi **merkezî yetkilendirmeden** geçer: `can()` ve `scoped_*()`. Çıplak `select(Model)` yasak.
- Append-only tablolar — `UPDATE`/`DELETE` yasak: `attestations`, `skill_signals`, `evaluations`, `audit_events`, `verified_experiences`. (Tek istisna: `attestations.revoked_at` ve `verified_experiences.visibility`.)
- Kısıtlar veritabanında olur (FK, CHECK, UNIQUE) — sadece uygulama kontrolü yetmez.
- Zaman: `timestamptz`/UTC. ID: UUIDv7. Fiziksel `DELETE` yalnız değeri olmayan tablolarda.
- Ağ çağrısı (e-posta, S3, AI) **asla açık transaction içinde** yapılmaz → `outbox` tablosu.

### Güvenlik
- **Yetkisiz erişimde 403 değil 404 dön.** 403 kaynağın varlığını sızdırır.
- Yeni endpoint = aynı commit'te yetkilendirme testi. Testsiz endpoint commit edilmez.
- `.env` okunmaz, içeriği çıktıya/commit'e taşınmaz. Sır sabitleri koda yazılmaz → `.env.example`'a placeholder.
- Loglara PII yazılmaz: şifre, token, CV içeriği, `private_note`, tam e-posta.
- Ham SQL yalnız migration dosyalarında.
- Dosya yükleme: uzantıya güvenilmez (magic-byte), dosya adı korunmaz (`{uuid}.{ext}`), kullanıcı içeriği ana domainden servis edilmez.

### Kapsam
- **MVP dışı özellik yazma.** Yasaklılar: AI, matching motoru, chat, gamification, blockchain, trust score, assessment, Redis, Elasticsearch, Celery, pgvector, Kubernetes, RLS. (Gerekçeler: final analiz §39.)
- Bir özellik eklemeden önce sor: "Bu olmadan `beyan → kanıt → tanıklık → doğrulanmış deneyim` zinciri çalışır mı?" Evet ise ekleme.

---

## İzin ve onay sınırları

**Var olan dosyayı değiştirmeden önce:** ne değişeceğini tek cümleyle söyle, sonra değiştir. Yeni dosya oluşturmak serbest.

**Aşağıdakiler için önce açık onay al** (token tasarrufu bu sınırları kaldırmaz):

- Migration oluşturma veya uygulama
- Dosya/klasör silme, toplu yeniden adlandırma
- 3+ dosyayı etkileyen refactor
- Bağımlılık ekleme veya sürüm yükseltme
- Yetkilendirme, kimlik doğrulama veya izin mantığı değişikliği
- `settings.json`, `docker-compose`, CI yapılandırması değişikliği
- `git push`, deploy, dış servise veri gönderen herhangi bir işlem

**Kesin yasaklar:**
- `docker compose down -v` — volume = veritabanı
- Uygulanmış migration'ı düzenleme/silme — düzeltme = **yeni** migration
- `git add -A` / `git add .` — dosyaları adıyla ekle
- `git push --force` — yalnız açık onayla
- `.env`, `secrets/` okuma veya commit'leme

---

## Çalışma döngüsü

```
ANLA → PLANLA → HEDEFLİ OKU → UYGULA → HEDEFLİ DOĞRULA → KISA RAPOR
```

- **Repoyu baştan sona okuma.** Önce yapıyı keşfet, sonra yalnız ilgili modülü + çağıranlarını + testini oku.
- Aynı dosyayı iki kez okuma — bir kez oku, aklında tut.
- `grep`/`glob` ile hedefle; geniş `find`/recursive listeleme yapma.
- Okuma listesi: ilgili modül → ilgili test → gerekirse ilgili doküman bölümü. Bu kadar.
- Belirsizlik varsa: bağımsız işleri bitir, kalan için **sor** — tahmin edip yanlış yazma.

---

## Doğrulama matrisi

Değişiklik türüne göre **minimum güvenli** doğrulama. Az test çalıştırmak tasarruf değil, risktir — bu tablo hangi testin gerçekten gerektiğini söyler.

| Değişiklik | Çalıştırılacak |
|---|---|
| Sadece doküman/markdown | Hiçbiri |
| Frontend stil/görsel | `npm run lint` |
| Frontend mantık | `npm run typecheck` + ilgili bileşen testi |
| Backend servis | İlgili unit + integration testi |
| Yeni endpoint | İlgili test + **yetkilendirme testi (zorunlu)** |
| **Yetkilendirme / kimlik doğrulama** | **`pytest tests/authorization -q` tamamı + ilgili testler** |
| Veritabanı şeması / migration | `alembic upgrade head` + `alembic downgrade -1` + ilgili testler |
| Dosya yükleme / kanıt | İlgili testler + güvenlik testleri |
| Bağımlılık değişikliği | Tüm test paketi |
| Deploy öncesi | Tüm test paketi + lint + typecheck |

**Asla yapma:** "Token tasarrufu için testi atlayayım." Testi atlamak tasarruf değil, gizlenmiş hata.

---

## Çıktı formatı

**Normal işlerde kısa tut:**

```
Değişen: app/services/engagement.py — durum geçişi doğrulaması eklendi
Doğrulanan: pytest tests/test_engagement.py (7 geçti)
Kalan: —
```

**Uzun açıklama yalnız şu durumlarda:** güvenlik değişikliği, veritabanı şeması, mimari karar, kırıcı değişiklik, veya bir kararı sorguluyorsan.

- Yaptığın işi tekrar tekrar özetleme; son mesajda bir kez söyle.
- Kod bloklarını cevaba kopyalama — dosya yolu + satır numarası ver.
- Başarılıysa düz söyle. Test kırıldıysa çıktısıyla birlikte söyle, gizleme.

---

## Commit

- Her mantıklı birim ayrı commit. Mesaj Türkçe, tek satır özet + gerekirse gövde.
- `docs/PLAN.md` maddesiyle ilgiliyse gövdeye madde numarasını yaz (ör. `PLAN 2.3`).
- **Commit'i sen atmazsın — kullanıcı söyleyince atarsın.** İstisna: `/bitir` komutu çalıştığında.
- Sonunda: `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`

---

## Açık kaynak

Repo herkese açık olacak. Bunun sonucu: **bir yetkilendirme açığı herkes tarafından okunabilir.** Güvenlik kuralları gevşetilmez, sıkılaştırılır.

- `LICENSE`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `.env.example` her zaman güncel.
- Sır repoda olmaz — commit öncesi kontrol et.
- Commit geçmişi temiz tutulur (jüri repoya bakabilir).
