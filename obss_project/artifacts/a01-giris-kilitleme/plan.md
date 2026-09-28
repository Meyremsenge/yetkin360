# Plan — a01-giris-kilitleme
_Reference: atdd.md_

## Files to Modify

| File | Why | Risk |
|------|-----|------|
| `backend/app/services/auth.py` | `authenticate()`: (1) kilitli hesap yolunda (`AccountLocked` fırlatmadan önce) DENIED audit + `session.commit()` ekle (AC-3, AC-S1); (2) kilit süresi dolmuşsa (`locked_until <= now`) sayacı/`locked_until`'i proaktif sıfırla (AC-4, AC-8); (3) yanlış parola / kullanıcı yok yolunda mevcut `session.flush()`'ı `session.commit()` yap, istisna öncesi (AC-1, AC-2, AC-3); (4) L-03: kullanıcı bulunduktan hemen sonra `status in ('SUSPENDED','DELETED')` ise `InvalidCredentials` fırlat — parola kontrolünden ÖNCE (timing/mesaj ayrımı olmasın, AC-5, AC-S2); (5) `refresh_tokens()`: token'ın kullanıcısının `status` alanı ACTIVE/PENDING değilse `InvalidRefreshToken` fırlat (AC-7). Her yeni `commit()` çağrısına `refresh_tokens()`'taki "Commit it now, before raising" yorum tarzıyla açıklama eklenecek. | medium |
| `backend/tests/authorization/test_auth_endpoints.py` | Var olan `TestLogin.test_login_locks_account_after_repeated_failures` testi savepoint fixture'ı kullandığı için (HATA.md TEST-02) yanıltıcı geçiyor — gerçek rollback'i sınamıyor. Bu test AYNEN KALIR (regresyon için hâlâ değerli, davranışı savepoint dünyasında da doğruluyor); yeni AC'ler (AC-2 sınır durumu: 10. deneme 401 döner ama kilitler, AC-3 audit metadata AC-S1, AC-5 L-03, AC-8 kilit-süresi-dolmuş-yanlış-parola) için ek test sınıfı/metodları buraya eklenir — bu dosya zaten override'lı `session` fixture'ını kullanıyor, davranışsal (flush-görünür) doğrulama için yeterli. | low |
## New Files

| File | Purpose |
|------|---------|
| `backend/tests/authorization/test_auth_login_real_session.py` | AC-9 (rollback semantiğini gerçekten sınayan test) ve AC-1/AC-2/AC-3/AC-5/AC-8/AC-S1/AC-S2'nin gerçek-commit doğrulaması. `test_auth_refresh_real_session.py`'nin desenini birebir takip eder: ayrı `create_engine`/`sessionmaker`, `TestClient(app)` **override'sız** (gerçek `get_session`), `finally` bloğunda temizlik (oluşturulan kullanıcı/audit satırlarının silinmesi). |

## Dependencies

- `app/services/audit.py::log_audit_event()` — zaten `metadata: dict | None` parametresi ve PII guard'ı (`password`, `password_hash`, `email`, `tc_kimlik_no` anahtarlarını reddeder) var; `{"reason": "locked"}` bu guard'dan sorunsuz geçer. Değişiklik gerekmiyor.
- `app/core/deps.py::get_session()` — DOKUNULMUYOR (atdd.md'de zaten kapsam dışı olarak işaretli); production davranışı (`yield` → commit / `except` → rollback+raise / `finally` → close) referans alınacak, test örneği bunu taklit edecek.
- `app/models/identity.py::User.status` CHECK constraint (`'PENDING','ACTIVE','SUSPENDED','DELETED'`) — zaten DB'de var, değişiklik yok.
- Emsal desen: `refresh_tokens()`'taki REUSE_DETECTED dalı (auth.py:432-458) — `session.commit()` + yorum + `raise` sıralaması birebir kopyalanacak.
- Emsal test deseni: `test_auth_refresh_real_session.py` (ayrı `create_engine`/`sessionmaker`, `TestClient(app)` override'sız, `finally` bloğunda temizlik) — yeni testler bunu takip edecek.

## Migration Required?

**Hayır.** Hiçbir yeni kolon/tablo gerekmiyor — `User.failed_login_count`, `User.locked_until`, `User.status`, `audit_events.event_metadata` zaten mevcut. Değişiklik yalnız uygulama katmanında (ne zaman commit edildiği, hangi durumda audit yazıldığı, status kontrolünün eklenmesi).

## Risks

(atdd.md Risks bölümünden taşındı + keşifte netleşenler)

- Erken `commit()` transaction'ı ikiye böler; `authenticate()`/`refresh_tokens()` içinde commit'ten sonra aynı istek içinde başka bir DB yazımı yok — risk yok, ama yorum satırıyla gelecekteki bir eklemeye karşı açıkça uyarılmalı (emsal `refresh_tokens()`'taki yorum gibi).
- Kilitli hesap yolunda commit eklenmesi, `authenticate()`'in şu anki tek-`flush`-tek-`commit`-en-sonunda-yapısını bozuyor — dikkatle, yalnızca `AccountLocked`/`InvalidCredentials` dallarına commit eklenecek, başarılı girişteki mevcut akış (sayaç sıfırlama + token issue + SUCCESS audit + tek commit `get_session` tarafından) **değişmeyecek** (AC-6).
- L-03 status kontrolünün **parola doğrulamasından önce mi sonra mı** yapılacağı kritik: AC-S2 (byte-byte aynı yanıt) için SUSPENDED kullanıcı parolası doğru olsa bile hash karşılaştırması hiç yapılmadan mı reddedilecek, yoksa hash karşılaştırması yapılıp (timing tutarlılığı için) sonra mı reddedilecek? Plan önerisi: **kullanıcı bulunduktan hemen sonra, parola kontrolünden ÖNCE** reddet (basitlik + `verify_password`'ın zaten pahalı olduğu düşünülürse timing farkı averaj kullanıcı için gözlemlenebilir değil) — ama bu görevin "SUSPENDED kullanıcı + DOĞRU parola" AC'sini (AC-5) sağladığı sürece hangi sırayla yapıldığı testleri etkilemiyor. **Basit ve mevcut deseni bozmayan yol seçildi; kullanıcı onayı bekleniyor (aşağıda).**
- Test dosyası seçimi (var olan `test_auth_refresh_real_session.py`'ye ekleme vs. yeni `test_auth_login_real_session.py`) — **Open Question, kullanıcıya sorulacak.**

## Kararlar

1. **Yeni rollback-testi hangi dosyaya gitsin?** → **Yeni dosya:
   `backend/tests/authorization/test_auth_login_real_session.py`.**
   (Sonnet 5 low alt-ajanı tarafından yanıtlandı: 40-50 satırlık yeni test
   sınıfı "küçük, kaçınılmaz dokunuş" eşiğini aşıyor; `test_auth_refresh_real_session.py`
   adı "refresh" ile sınırlı, login testini oraya eklemek dosya adını
   yanıltıcı yapar ve A-13'ün gelecekteki genellemesinde karışıklığa yol
   açar; setup/teardown tekrarı kabul edilebilir maliyet, YAGNI gereği ortak
   fixture'a çıkarma bu görevin kapsamında değil.)
2. **L-03 kontrolünün parola doğrulamasına göre sırası** → **Parola
   kontrolünden ÖNCE** (kullanıcı bulunduktan hemen sonra `status` kontrolü).
   (Sonnet 5 low alt-ajanı tarafından yanıtlandı: AC-5/AC-S2 hangi sırayla
   üretildiğini önemsemiyor, yalnız sonucun byte-byte aynı olmasını istiyor;
   basit erken-çıkış deseni mevcut kodu bozmuyor; timing-attack karşı önlemi
   açıkça A-10'un kapsamı, bu görevin değil.)
