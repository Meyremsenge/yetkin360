# Entegrasyon Notu — Kuruluş kaydında kurumsal kimlik (PLAN 3.57)

## Gerçek olan (backend'e bağlı)

| Parça | Nerede | Durum |
|---|---|---|
| Kurumsal e-posta zorunluluğu | `POST /auth/register` (`app/services/auth.py`) | Gerçek. `ORGANIZATION` kaydında ücretsiz sağlayıcı adresi `422` (`fields.email`). Form aynı listeyle erken uyarı verir; asıl kontrol sunucudadır. |
| Doğrulama e-postası | mevcut `email.verify_email` outbox akışı | Gerçek. Kayıt e-postasına gider; kural sayesinde kuruluşta bu her zaman kurumsal adrestir. |
| MERSİS numarası | `RegisterRequest.legal_id` → `organizations.legal_id` | Gerçek. Yalnız biçim (16 hane) doğrulanır; başka kuruluşa aitse `409 LEGAL_ID_TAKEN`. Şirketin gerçekliğini kanıtlamaz. |
| Belge türü/boyutu | `rejectDocument()` (`frontend/lib/api/organization-document.ts`) | Gerçek, yalnız istemci tarafı (PDF/PNG/JPEG, en fazla 5 MB). |

## MOCK olan

**Belge kontrolü ("kayıtla eşleşiyor / doğrulanamadı") tamamen mock'tur.**

- Backend'de bu iş için uç yok; `docs/API.md`'de sözleşmesi de yazılı değil.
- Belge hiçbir yere gönderilmez, saklanmaz; karekod/barkod ve metin **okunmaz**.
- Sonuç dosyanın içeriğine değil, formdaki beyana bağlıdır ve deterministiktir:
  kuruluş adı dolu **ve** MERSİS 16 haneliyse `MATCH`, değilse `UNVERIFIED` +
  "manuel incelemeye gönderilecek". Rastgelelik yoktur.
- Sonuç kaydı, yetkileri ve doğrulama seviyesini etkilemez; kuruluş `T1` açılır.
  "Manuel inceleme" bir kayıt oluşturmaz — T3 kararı mevcut admin doğrulama
  kuyruğundadır (`docs/DOMAIN.md`).
- Ekran, sonucun altında "Örnek sonuç: otomatik belge kontrolü henüz bağlı değil
  ve belge sunucuya gönderilmez." notunu gösterir (`USE_MOCK_DOCUMENT_CHECK`
  açıkken).

## Gerçeğe geçmek için gerekenler

1. Sözleşmeyi `docs/API.md`'ye yaz (uç, yetki, hız sınırı, hata kodları).
2. Backend: belge yükleme + karekod okuma (OpenCV — sertifika kontrolünde var),
   belge metninde kuruluş adı ve MERSİS'in deterministik aranması; sonucun admin
   doğrulama kuyruğunda görünmesi. Yetkilendirme ve güvenlik testleri zorunlu.
3. Resmi doğrulama sayfasının (Ticaret Sicili Gazetesi / e-Devlet) otomatik
   açılıp açılamadığı **denenmedi**; açılamıyorsa bağlantı admine gösterilir.
4. `checkOrganizationDocument()` içindeki `else` dalını gerçek çağrıyla doldur,
   `USE_MOCK_DOCUMENT_CHECK = false` yap; "örnek sonuç" notu kendiliğinden kalkar.

## Bu işte yapılmayanlar

- Kurumsal e-postaya ayrı bir **doğrulama kodu** (mevcut akış bağlantı gönderir).
- E-posta alan adı ile kuruluş alan adının eşleştirilmesi (kuruluş `domain`
  alanı kayıtta boş açılır; alan adı doğrulaması ayrı `verify-domain` ucundadır).
- HTML dosyasıyla alan adı doğrulama.
- MERSİS'in resmi kayıtla karşılaştırılması.
