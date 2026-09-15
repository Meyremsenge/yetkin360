# STATE_MACHINE.md — Engagement Durum Makinesi

Engagement'ın durumları, geçişleri, her geçişin ön koşulu ve kimin yetkili olduğu.

**Kaynak:** `yetkin360-final-analiz.md` §10.1–10.4.

> Durum geçişleri **tek bir uçtan** yapılır: `POST /engagements/{id}/transitions`.
> Bu, durum makinesini tek yerde tutar ve her geçişe ayrı uç yazmaktan daha
> güvenlidir — her uçta yetkilendirmeyi tekrar yazma riski ortadan kalkar.

**İlgili dosyalar:**
- Uç sözleşmesi ve hata kodları → [API.md](API.md) §2.6
- `engagements.status` CHECK kısıtı, `version` kolonu → [DATABASE.md](DATABASE.md) §2.3
- Aktör tanımları → [AUTHORIZATION.md](AUTHORIZATION.md) §2
- Üretilen entity'ler → [DOMAIN.md](DOMAIN.md)

---

## 1. Kapsam sınırı: Jira'ya dönüşmeme kuralı

Durum makinesini tasarlarken en büyük risk, proje yönetimi aracına dönüşmektir.
Somut sınır:

| ✅ Var | ❌ Yok |
|---|---|
| Görev (`EngagementTask`) | Alt görev, bağımlılık, sprint, board, etiket, tahmini süre |
| 3 görev durumu: `PLANNED` \| `IN_PROGRESS` \| `DONE` | Zaman takibi, iş yükü, burndown, Gantt |
| Görevin tek amacı: **bir çıktıya ve bir yetkinliğe bağlanmak** | Bağlanamayan görev |

> **Test sorusu:** "Bu özellik olmadan, tamamlanmış bir stajdan geçerli bir
> doğrulanmış deneyim üretilebilir mi?" Cevap **evet** ise özellik **eklenmez**.

**İsimlendirme:** `Collaboration` değil **`Engagement`** — "collaboration" eşit
ortaklık ima ediyor; staj/proje ilişkisi asimetriktir (bir taraf değerlendirir).
Türkçe arayüzde "Çalışma" / "Staj".

---

## 2. Durum diyagramı

```
DRAFT ──────────► PENDING_APPROVAL ──────► ACTIVE
  │                      │                    │
  │                      ├──► REJECTED        ├──► CANCELLED (gerekçeli)
  │                      │                    │
  └──► (silinebilir)     │                    ▼
                         │              PENDING_EVALUATION
                         │                    │
                         │                    ▼
                         │                EVALUATED
                         │                    │
                         │                    ▼
                         │                VERIFIED ──► (VerifiedExperience üretilir)
                         │                    │
                         │                    └──► DISPUTED ──► RESOLVED
```

---

## 3. Durumlar

| Durum | Anlamı | Terminal mi |
|---|---|---|
| `DRAFT` | Oluşturuldu, henüz onaya sunulmadı. **Silinebilir** | Hayır |
| `PENDING_APPROVAL` | Koordinatör onayı bekliyor | Hayır |
| `REJECTED` | Koordinatör reddetti | **Evet** |
| `ACTIVE` | Çalışma sürüyor. Görev ve çıktı girilir | Hayır |
| `CANCELLED` | Gerekçeli iptal | **Evet** |
| `PENDING_EVALUATION` | İş bitti, **değerlendirme bekleniyor** | Hayır |
| `EVALUATED` | Değerlendirme formu dolduruldu | Hayır |
| `VERIFIED` | Onaylandı, **`VerifiedExperience` üretildi** | Evet (yalnız `DISPUTED`'a gider) |
| `DISPUTED` | İtiraz edildi | Hayır |
| `RESOLVED` | İtiraz çözüldü | **Evet** |

### 3.1 Neden bu durumlar

Ön araştırma dokümanı `PROPOSED → ACCEPTED → ACTIVE → PAUSED → COMPLETED → CANCELLED`
öneriyordu. Farklar ve gerekçeleri:

| Değişiklik | Gerekçe |
|---|---|
| **`PENDING_APPROVAL` eklendi** | Üniversite koordinatörünün onay noktası. **Sahte staj saldırısına karşı en güçlü savunma** |
| **`PENDING_EVALUATION` eklendi** | "İş bitti ama değerlendirme gelmedi" gerçek hayatta çok yaygın ve koordinatörün en çok kovaladığı durum. Ayrı bir hâl olmazsa **takip edilemez** |
| **`VERIFIED` ayrıldı** | `EVALUATED` (form dolduruldu) ile `VERIFIED` (onaylandı, deneyim üretildi) **farklıdır** |
| **`DISPUTED` eklendi** | İtiraz mekanizması olmadan değerlendirme sistemi kötüye kullanıma açıktır |
| **`PAUSED` çıkarıldı** | Gerçek bir iş ihtiyacı değil; `ACTIVE` içinde bir tarih boşluğu olarak temsil edilebilir |

> **`PENDING_EVALUATION` ürünün en kritik operasyonel ekranıdır.** Koordinatör
> dashboard'unun ana listesi budur ve `(status) PARTIAL WHERE status =
> 'PENDING_EVALUATION'` index'i bunun içindir ([DATABASE.md](DATABASE.md) §2.3).

---

## 4. Geçiş tablosu

> **Bu tablo test edilebilir sözleşmedir.** Tabloda olmayan her geçiş
> `422 ILLEGAL_TRANSITION` döner.

| # | Geçiş | Yetkili aktör | Ön koşul | Yan etki |
|---|---|---|---|---|
| T1 | `DRAFT` → `PENDING_APPROVAL` | Kurum (`ORG:MEMBER`) veya `TALENT` | `institution_id` dolu; `title`, `kind` dolu | `AuditEvent`, koordinatöre bildirim |
| T2 | `PENDING_APPROVAL` → `ACTIVE` | **`INST:COORD`** (kendi kurumu) | Talent, koordinatörün kurumuna bağlı | `AuditEvent`, taraflara bildirim |
| T3 | `PENDING_APPROVAL` → `REJECTED` | **`INST:COORD`** (kendi kurumu) | `reason` **zorunlu** | `AuditEvent`, bildirim |
| T4 | `DRAFT` → `ACTIVE` | Kurum (`ORG:MEMBER`) | **`institution_id` NULL** (platform dışı işbirliği) | `AuditEvent` |
| T5 | `ACTIVE` → `PENDING_EVALUATION` | `TALENT` veya `ORG:SUPERVISOR` | **En az 1 `Deliverable` olmalı** | `AuditEvent`, kuruma bildirim |
| T6 | `ACTIVE` → `CANCELLED` | `ORG:ADMIN` veya `INST:COORD` | `reason` **zorunlu** | `AuditEvent`, bildirim |
| T7 | `PENDING_EVALUATION` → `EVALUATED` | **Sistem** (otomatik) | `ORG_TO_TALENT` yönünde `Evaluation` gönderildi | `AuditEvent` |
| T8 | `EVALUATED` → `VERIFIED` | **`INST:COORD`**; `institution_id` NULL ise `ORG:SUPERVISOR` | Kurum tanıklığı **ve** (kurumsal bağlamda) koordinatör onayı | **§5 — tek transaction** |
| T9 | `VERIFIED` → `DISPUTED` | `TALENT` veya `ORG:MEMBER` | `reason` **zorunlu** | `AuditEvent`, bildirim |
| T10 | `DISPUTED` → `RESOLVED` | `INST:COORD` veya `ADMIN` | `reason` **zorunlu** | `AuditEvent` |

### 4.1 Geçiş kuralları

| Kural | |
|---|---|
| **`VERIFIED` terminal ve değişmezdir** | Yalnız `DISPUTED`'a gidebilir, **geri dönemez** |
| **Her geçiş `AuditEvent` üretir** | İstisnasız (Definition of Done madde 4) |
| **Geçişler DB seviyesinde zorlanır** | `status` CHECK kısıtı + `version` optimistic locking |
| **`DRAFT` silinebilir** | Tek silinebilir durum; diğerleri `CANCELLED`/`REJECTED` ile kapanır |
| **`REJECTED`, `CANCELLED`, `RESOLVED` terminaldir** | Çıkış geçişi yoktur |

### 4.2 Eşzamanlılık

Her geçiş isteği `version` taşır ([API.md](API.md) §2.6):

```sql
UPDATE engagements
   SET status = :new_status, version = version + 1
 WHERE id = :id AND status = :expected_status AND version = :expected_version;
```

0 satır dönerse → **`409 CONFLICT`**. İstemci kaydı yeniden okur ve kullanıcıya
"bu kayıt başkası tarafından değiştirildi" der.

### 4.3 Hata kodlarının ayrımı

Üç farklı başarısızlık, üç farklı kod — istemcinin doğru mesajı gösterebilmesi için:

| Durum | Kod |
|---|---|
| Geçiş tabloda **yok** | `422 ILLEGAL_TRANSITION` |
| Geçiş var, **ön koşul** sağlanmıyor | `422 PRECONDITION_FAILED` |
| Geçiş var, ön koşul tamam, **aktör yetkisiz** | `403 FORBIDDEN` |
| Kaynak kapsam dışı | `404` |
| `version` eski | `409 CONFLICT` |

`GET /engagements/{id}` cevabındaki `available_transitions[]` alanı, **bu
kullanıcının şu anda yapabileceği** geçişleri listeler. Frontend butonları
bundan üretir; durum makinesini kendisi hesaplamaz.

> ❓ AÇIK SORU: T4 (`DRAFT → ACTIVE`, koordinatörsüz yol) §10.2 diyagramında
> açıkça çizilmemiş; §7.7'deki "`Engagement n──1 Institution` (nullable —
> platform dışı işbirliği için)" ifadesinden türetildi. Platform dışı engagement
> gerçekten koordinatör onayını atlayabilir mi, yoksa `institution_id` her zaman
> zorunlu mu? Hackathon demosu üniversite bağlamı üzerinden gittiği için T4
> MVP'de gerçeklenmeyebilir.

> ❓ AÇIK SORU: T7 (`PENDING_EVALUATION → EVALUATED`) tetikleyicisi —
> değerlendirme gönderilir gönderilmez otomatik mi geçiliyor, yoksa `TALENT_TO_ORG`
> yönündeki karşılıklı değerlendirme de bekleniyor mu? Final analiz `evaluations`
> tablosunda iki yön tanımlıyor ama hangisinin geçişi tetiklediğini söylemiyor.
> Bu dosya tek yönü (`ORG_TO_TALENT`) varsayıyor.

---

## 5. `VERIFIED` geçişi — tek transaction

> Ürünün tüm zincirinin tamamlandığı an. **1–5 atomik olmalıdır.**
> Yarım kalırsa tutarsız kanıt zinciri oluşur: deneyim var ama sinyali yok,
> ya da tam tersi.

| # | Adım | Transaction |
|---|---|---|
| 1 | `Engagement.status = VERIFIED` | **İçinde** |
| 2 | `VerifiedExperience` oluştur — kurum adı, tarih, rol **kopyalanarak** (snapshot) | **İçinde** |
| 3 | Her onaylanmış yetkinlik için `SkillSignal` ekle (`source_type = ATTESTATION`) | **İçinde** |
| 4 | `Attestation` kayıtlarını final olarak işaretle | **İçinde** |
| 5 | `AuditEvent` yaz | **İçinde** |
| 6 | Bildirim kuyruğuna ekle | **DIŞINDA** — `outbox` |

> **Kritik: Adım 6 asla transaction içinde yapılmaz.** E-posta gönderimi
> transaction'ı kilitler. Transaction içinde `outbox` tablosuna satır yazılır;
> ayrı bir süreç okur ve gönderir ([DATABASE.md](DATABASE.md) §5).

**Adım 2'nin snapshot olması kritiktir:** kurum hesabını silerse, adını
değiştirirse veya platformdan ayrılırsa öğrencinin doğrulanmış deneyimi
bozulmamalıdır ([DOMAIN.md](DOMAIN.md) §3.13).

**Adım 3'te `COMPETENCE` kontrolü:** [DOMAIN.md](DOMAIN.md) §3.11'deki 6 ön
koşuldan biri eksikse ilgili tanıklık `PARTICIPATION`'a düşürülür ve sinyal
buna göre üretilir. Geçiş **reddedilmez**.

---

## 6. Geri alma: silinemez, geri çekilebilir

> **Hayır, silinemez. Ama geri çekilebilir (revoke).**

| Eylem | Sonuç |
|---|---|
| Kurum tanıklığını geri çeker | `Attestation.revoked_at` + **zorunlu gerekçe**. Orijinal kayıt kalır |
| Profilde gösterim | Deneyim **görünür kalır**, "doğrulama geri çekildi" notuyla |
| `SkillSignal` | `superseded` olur, **silinmez** |
| Öğrenci | Deneyimi **gizleyebilir** (`visibility = PRIVATE`) ama **silemez** |

**Gerekçe:**

> **Silinebilir doğrulama, doğrulama değildir.** Öğrenci kötü değerlendirmeleri
> silebiliyorsa, iyi değerlendirmelerin de bir anlamı kalmaz.

Bu, Upwork'ün iş geçmişini silmeye izin vermemesiyle aynı mantıktır.

**Revoke, bir durum geçişi değildir.** `engagements.status` `VERIFIED` kalır;
değişen `attestations` tablosudur. Uç: `POST /attestations/{id}/revoke`
([API.md](API.md) §2.8). Yalnız tanıklığı **yapan kişi** geri çekebilir.

---

## 7. MVP kapsamı

Hackathon fazlarına dağılım — [PLAN.md](../PLAN.md):

| Geçiş | Faz | Durum |
|---|---|---|
| T1, T2, T3 | 2.2, 2.3 | ✅ MVP'de |
| T5 | 2.2 | ✅ MVP'de |
| T7 | 2.7 | ✅ MVP'de |
| T8 | **2.8** | ✅ MVP'de — **zincirin kilit taşı** |
| T6 (`CANCELLED`) | 2.2 | ✅ MVP'de |
| T4 (koordinatörsüz) | — | ⚠️ Açık soru (§4.3) |
| T9, T10 (`DISPUTED`) | **R.3** | ⚠️ "Vakit kalırsa" — gerçeklenmeyebilir |

> **Altın kural hatırlatması ([PLAN.md](../PLAN.md)):** Tek uçtan uca senaryo
> kusursuz çalışsın. Bu durum makinesinde o senaryo **T1 → T2 → T5 → T7 → T8**
> yoludur. Bu yol çalışmıyorsa `DISPUTED` akışı hiçbir şey kurtarmaz.

---

## 8. Test kontrol listesi

Her satır bir test vakasıdır. Yetkilendirme testleriyle birlikte çalışır
([AUTHORIZATION.md](AUTHORIZATION.md) §5.4 D1, D2, E4).

| # | Test | Beklenen |
|---|---|---|
| S1 | Tabloda olmayan geçiş (`DRAFT → VERIFIED`) | `422 ILLEGAL_TRANSITION` |
| S2 | `ACTIVE → PENDING_EVALUATION`, deliverable **yok** | `422 PRECONDITION_FAILED` |
| S3 | `ACTIVE → PENDING_EVALUATION`, 1 deliverable **var** | `200` |
| S4 | `PENDING_APPROVAL → ACTIVE`, başka üniversitenin koordinatörü | `404` |
| S5 | `PENDING_APPROVAL → ACTIVE`, kendi üniversitesinin koordinatörü | `200` |
| S6 | `EVALUATED → VERIFIED`, talent dener | `403` |
| S7 | `EVALUATED → VERIFIED`, koordinatör dener | `200` |
| S8 | `VERIFIED → ACTIVE` (geri dönüş) | `422 ILLEGAL_TRANSITION` |
| S9 | Eski `version` ile geçiş | `409 CONFLICT` |
| S10 | `REJECTED`'dan herhangi bir geçiş | `422 ILLEGAL_TRANSITION` |
| S11 | `T3`/`T6`/`T9`/`T10` `reason` olmadan | `400 VALIDATION_ERROR` |
| S12 | `VERIFIED` sonrası: `VerifiedExperience` **ve** `SkillSignal` var mı | Her ikisi de var |
| S13 | `VERIFIED` transaction'ı ortada kırılırsa | **Hiçbiri** yazılmamış (atomiklik) |
| S14 | Her geçiş sonrası `AuditEvent` | Var |
| S15 | Attestation revoke → `SkillSignal` `superseded`, deneyim duruyor | Doğrulandı |
