# PLAN.md — Yetkin360

Yapılacak işlerin **sırası** ve ilerleme durumu. Tek doğruluk kaynağı: bu dosya.
Kararların gerekçesi burada değil → `yetkin360-final-analiz.md`, detay → `docs/`.

**Durum işaretleri:** `[ ]` yapılacak · `[~]` devam ediyor · `[x]` bitti · `[-]` iptal/ertelendi

**Sahip etiketleri:** `@be1` `@be2` backend · `@fe` frontend · `@all` ortak
*(İsim eşlemesi CONTRIBUTING.md'de; etiket sabit kalır ki plan satırı kısa olsun.)*

**Altın kural (final analiz §35.2):** Tek uçtan uca senaryo kusursuz çalışsın —
`beyan → kanıt → tanıklık → doğrulanmış deneyim`. Bu zincir çalışmıyorsa
hiçbir ek ekran kurtarmaz.

**Sözleşme önce kuralı:** Bir maddenin API sözleşmesi (`docs/API.md`) yazılmadan
`@fe` o ekranı bekleyemez. Sözleşme yazılır → `@fe` mock ile ilerler → backend
gerçeğini bağlar. Backend'in bitmesini beklemek 3 kişilik ekipte en büyük israftır.

---

## Faz 0 — Karar kilitleme (15-18 Eylül)

Ürün kodu yok. Çıktı: yazıya dökülmüş kararlar + çalışan iskelet.

- [ ] 0.1 **Lisans teyidi:** şartname izin verici lisans şart koşuyor mu? Lisans
      seçilir, `LICENSE` tam metinle doldurulur, bağımlılık uyumu kontrol edilir @all
- [x] 0.2 `docs/DOMAIN.md` — entity, alan, ilişki, iş kuralları @be1
- [x] 0.3 `docs/DATABASE.md` — DDL, kısıt, index, append-only, silme politikası @be1
- [x] 0.4 `docs/API.md` — uç listesi, yetki, şema özeti, hata kodları @all
- [x] 0.5 `docs/AUTHORIZATION.md` — aktör × kaynak × eylem × HTTP kodu matrisi @be2
- [x] 0.6 `docs/SECURITY.md` — OWASP tablosu, dosya akışı, rate limit, senaryolar @be2
- [x] 0.7 `docs/STATE_MACHINE.md` — Engagement durumları, geçiş ön koşulları @be1
- [x] 0.8 Repo kökü: README, CONTRIBUTING, SECURITY.md, .gitignore, `docs/ENV.md` @all
- [x] 0.9 `.env.example` — `docs/ENV.md` §8 şablonundan repo köküne kopyalanır @all
- [x] 0.10 Docker Compose (PostgreSQL + MinIO) + backend iskeleti (FastAPI, alembic) @be2
- [x] 0.11 Frontend iskeleti (Next.js + TS + shadcn/ui) + TR metin dosyası @fe
- [x] 0.12 CI: ruff + mypy + pytest · npm lint + typecheck @be2
- [x] 0.13 Ekip isim eşlemesi: `@be1`/`@be2`/`@fe` → kim (CONTRIBUTING'e yazılır) @all

> **0.1 neden ilk madde:** Lisans seçimi geri alınamaz — bir kez yayımlanan kod
> o lisans altında alınmış olur. Şartname teyit edilmeden repo herkese açık
> hâle getirilemez. Ayrıntı: `LICENSE`, final analiz §22.3 ve §37 madde 0b.

---

## Faz 1 — Omurga (18-25 Eylül)

Hedef: kimlik + kiracılık + yetkilendirme çekirdeği ayakta, profil ve skill beyanı çalışır.

**Bu fazın kilit maddesi 1.2'dir.** Yetkilendirme sonradan eklenirse delikli olur.

- [x] 1.1 İlk migration: user, talent, institution, organization, membership, skill @be1
- [x] 1.2 Yetkilendirme çekirdeği: `can()` + `scoped_*()` + `audit_events` @be2
- [x] 1.3 Yetkilendirme test iskeleti + fixture'lar (aktör matrisi) @be2
- [x] 1.4 Auth: kayıt, giriş, token yenileme, çıkış @be2
- [x] 1.5 `outbox` tablosu + worker (ağ çağrısı transaction dışına) @be2
- [x] 1.6 Auth: e-posta doğrulama + şifre sıfırlama (outbox üzerinden) @be2
      > PR #5 Copilot incelemesi: 2 ertelenen bulgu — (a) `/auth/forgot-password`
      > rate limit yok, genel rate-limit altyapısı kararı gerektiriyor;
      > (b) outbox worker `process_batch` batch'i tek `FOR UPDATE` ile baştan
      > kilitliyor, SMTP süresince sıradaki satırların kilidi de tutuluyor.
      > Faz 5.2/5.6 kapsamına alınabilir.
- [x] 1.7 User + Talent profili: `GET /me`, `PATCH /talents/me` @be1
- [x] 1.8 Institution + koordinatör rolü + öğrenci bağı @be1
- [x] 1.9 Organization + üyelik + domain doğrulama (T2) @be1
- [x] 1.10 Skill taksonomisi (~150 skill) seed + arama ucu @be1
- [x] 1.11 Talent yetkinlik beyanı: skill ekle/listele/çıkar @be1
- [x] 1.12 Frontend kabuk: layout, oturum yönetimi, korumalı rota, hata sınırı @fe
- [x] 1.13 Frontend: kayıt, giriş, e-posta doğrulama, şifre sıfırlama ekranları @fe
- [x] 1.14 Frontend: talent profil + yetkinlik beyanı ekranı @fe
- [x] 1.15 Faz 1 kapanış: `pytest tests/authorization` tamamı yeşil @all

---

## Faz 2 — Ana döngü (25 Eylül - 2 Ekim)

Hedef: zincirin kendisi. Engagement açılır, çıktı yüklenir, değerlendirilir,
attestation + verified experience + skill signal üretilir.

- [ ] 2.1 Engagement modeli + migration + oluşturma ucu @be1
- [ ] 2.2 Durum makinesi: tek `POST /engagements/{id}/transitions` ucu @be1
- [ ] 2.3 Koordinatör onayı geçişi + yetkilendirme testleri @be1
- [ ] 2.4 Task + Deliverable @be1
- [ ] 2.5 Dosya yükleme altyapısı: imzalı URL, magic-byte, `{uuid}.{ext}` @be2
- [ ] 2.6 Evidence kaydı + indirme izni (sahiplik URL'den çıkar) @be2
- [ ] 2.7 Değerlendirme formu şeması (yetkinlik + davranış + `NOT_OBSERVED`) @be2
- [ ] 2.8 Attestation + VerifiedExperience üretimi (tek transaction) @be2
- [ ] 2.9 SkillSignal türetme + `GET /talents/me/signals` @be2
- [ ] 2.10 Attestation iptali (`revoke`) — append-only istisnası @be2
- [ ] 2.11 Frontend: engagement listesi + detay + durum geçiş aksiyonları @fe
- [ ] 2.12 Frontend: çıktı yükleme (imzalı URL akışı, ilerleme, hata) @fe
- [ ] 2.13 Frontend: değerlendirme formu (kurum tarafı) @fe
- [ ] 2.14 Faz 2 kapanış: uçtan uca duman testi (kayıt → attestation → signal) @all

---

## Faz 3 — Görünür yüz (2-9 Ekim)

Hedef: jürinin göreceği yüz. Bu fazın sonunda canlı URL + gerçekçi veri olmalı.

- [ ] 3.1 Public profil ucu + `visibility` kuralları @be1
- [ ] 3.2 Public doğrulama linki `GET /public/v/{token}` @be1
- [ ] 3.3 Koordinatör dashboard ucu (durum takibi + bekleyen değerlendirme) @be1
- [ ] 3.4 Toplu hatırlatma ucu (`POST /institutions/{id}/reminders`) @be2
- [ ] 3.5 Kurum dashboard ucu (bekleyen değerlendirmeler, üyeler) @be2
- [ ] 3.6 Admin: kurum doğrulama kuyruğu + skill yönetimi @be2
- [ ] 3.7 Frontend: profil sayfası — kanıt dökümü (signal + verified experience) @fe
- [ ] 3.8 Frontend: public profil `/p/[slug]` + doğrulama `/v/[token]` @fe
- [ ] 3.9 Frontend: koordinatör dashboard @fe
- [ ] 3.10 Frontend: kurum dashboard + admin ekranları @fe
- [ ] 3.11 Seed verisi: 20 öğrenci, 5 kurum, 15 tamamlanmış engagement @be1
- [ ] 3.12 Güvenlik geçişi: BOLA taraması, 404-yerine-403 doğrulaması @be2
- [ ] 3.13 Erişilebilirlik geçişi: klavye, focus, kontrast, `aria-live` @fe
- [ ] 3.14 Deploy: VPS, HTTPS, canlı URL, yedekleme, log @be2
- [ ] 3.15 Açık kaynak paketi: kurulum talimatı sıfırdan doğrulanır, sır taraması @all
- [ ] 3.16 Kod dondurma — Faz 4'e yeni özellik girmez @all

---

## Faz 4 — Sunum (9-11 Ekim, İstanbul)

Yeni özellik yok. Yalnız prova ve kırık olanın düzeltilmesi.

- [ ] 4.1 Demo provası: uçtan uca senaryo, jüri telefonundan public link @all
- [ ] 4.2 Sunum içeriği + ekran akışı @all
- [ ] 4.3 Son hata düzeltme (yalnız kırık olan) @all
- [ ] 4.4 Sunum @all

---

## Vakit kalırsa (Faz 3 içinde, zorunlu değil)

Yapılmazsa sunumda yol haritası olarak anlatılır.

- [ ] R.1 Basit aday filtreleme ekranı (skill + kurum filtresi — matching motoru değil)
- [ ] R.2 Excel/PDF rapor dışa aktarma (akreditasyon argümanı)
- [ ] R.3 İtiraz (`DISPUTED`) akışı

---

## Faz 5+ — Hackathon sonrası (kabul alınırsa)

Bu bölüm 11 Ekim'de **başlar.** Sıra final analiz §35.4 (Plan B) üzerinedir:
hackathon çıktısını pilot uygulanabilir ürüne taşır. Numaralar Faz 5'ten devam
eder; önceki fazlar geçmiş kaydı olarak silinmeden durur.

### Faz 5 — Sertleştirme
- [ ] 5.1 Gerçek kullanıcı görüşmeleri: 5 koordinatör + 5 kurum + 10 öğrenci
- [ ] 5.2 BOLA test matrisi tamamlama (her uç × her aktör)
- [ ] 5.3 Dosya güvenliği derinleştirme (ClamAV, kullanıcı içeriği ayrı domain)
- [ ] 5.4 Audit log sorgulanabilirliği + saklama politikası
- [ ] 5.5 Hata izleme + uptime izleme
- [ ] 5.6 Yük testi ve N+1 sorgu temizliği

### Faz 6 — Kurum derinliği
- [ ] 6.1 Koordinatör dashboard derinleştirme (kohort, dönem, filtre)
- [ ] 6.2 Raporlama / dışa aktarma (akreditasyon formatı)
- [ ] 6.3 İtiraz akışı tam (`DISPUTED` → çözüm → kayıt)
- [ ] 6.4 Kurum doğrulama T3 (belge tabanlı)
- [ ] 6.5 Kurum için çıktı yorumlama

### Faz 7 — Pilot hazırlığı
- [ ] 7.1 Pilot kurulumu (tek üniversite, tek bölüm)
- [ ] 7.2 KVKK dokümantasyonu + aydınlatma metinleri + veri haritası
- [ ] 7.3 Yedekleme ve geri yükleme tatbikatı
- [ ] 7.4 Kullanıcı eğitim materyali
- [ ] 7.5 Basit yetenek arama (kurum, kendi üniversitesi içinde)

### Faz 8 — Pilot yürütme
- [ ] 8.1 Pilot yürütme + haftalık geri bildirim
- [ ] 8.2 Geri bildirimle düzeltme
- [ ] 8.3 Deterministik eşleştirme katmanı (AI değil — final analiz §9.2)
- [ ] 8.4 Pilot sonuç raporu

> ❓ AÇIK SORU: Faz 5-8 "kabul alınırsa 4 ay" varsayımına dayanıyor. Sözleşme
> koşulları (süre, ekip büyüklüğü, bütçe) belli olduğunda bu bölüm yeniden
> bölümlenir. Kabul gelmezse Faz 5 açık kaynak bakım moduna küçülür.

---

## Plan bakım kuralları

1. **Madde eklemek serbest, madde silmek değil.** İptal edilen madde `[-]` ile
   kalır — jüri ve katkıcı için karar geçmişidir.
2. Yeni iş çıkarsa ilgili fazın sonuna eklenir, numara devam eder (`2.15`).
   Numara yeniden kullanılmaz; geçmiş commit mesajları ona atıf yapar.
3. **Her madde tek satır.** Detay `docs/` içine yazılır, buraya değil.
   Plan uzarsa her ilerleme kontrolü pahalılaşır.
4. Bir madde başkasının maddesini bekliyorsa, bekleyen taraf sözleşmeye göre
   mock ile ilerler — bloke beklemez.
5. Faz kapanış maddesi (`1.15`, `2.14`, `3.16`) atlanmaz: bir sonraki faz kırık
   omurga üzerine kurulmaz.
6. Bir madde `[x]` olurken ilgili commit `PLAN <numara>` referansı taşır.
