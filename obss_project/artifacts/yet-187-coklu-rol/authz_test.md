# authz-test — yet-187-coklu-rol
_Durum: matris tanımlandı (test-copilot'a extra_instructions olarak verilecek). Canlı sonda henüz atılmadı: uygulama kodu yok; koddan sonra, verify aşamasında ve yalnız geliştirme/test DB'sinde atılacak. Aşağıdaki sütunlar o zaman doldurulur._

Kural: testler **mock'suz**, gerçek `get_current_principal` + gerçek test DB (üyelikler DB'de kurulur, `Principal(...)` elle kurulmaz; tek istisna `test_principal_roles_unit.py` saf birim). En az iki farklı kiracı/aktör. Boş liste tek başına "PASS" sayılmaz: sızıntı testlerinde sızması beklenen kaydın DB'de var olduğu önce doğrulanır. Yazma testlerinde son durum DB'den yeniden okunur.

## Aktör kurulumu (fixture önerisi, hepsi gerçek kullanıcı + üyelik)
| Kod | Kullanıcı | Üyelikler |
|---|---|---|
| M1 | çoklu rol | talent profili + Org O1 ADMIN + Kurum K1 COORDINATOR |
| M2 | çoklu rol | Kurum K1 ADMIN + Kurum K2 COORDINATOR (+ talent) |
| M3 | çoklu rol | Org O1 MEMBER + Org O2 ADMIN (+ talent) |
| T1 | talent | yalnız talent profili (talent_a), engagement E1 (O1, K1) sahibi |
| X | dış kiracı | Org O3 ADMIN + Kurum K3 COORDINATOR, O1/K1/O2/K2 ile bağı yok |
| P | saf talent | yalnız talent |
| A | platform admin | `is_platform_admin` |
| S | self-dealing | talent sahibi olduğu engagement E2'nin org'unda (O1) ADMIN, ayrıca K1 COORDINATOR |

## Matris
| # | AC | Aktör → eylem | Beklenen | Kanıt (doldurulacak) |
|---|---|---|---|---|
| 1 | AC-1 | M1 → `POST /organizations/{O1}/members`, `POST /organizations/{O1}/verify-domain` | 2xx (bugün 404) | |
| 2 | AC-1 | M1 → `POST /engagements/{E1}/transitions` PENDING_APPROVAL→ACTIVE (E1 K1'de, M1 E1'in talent'ı DEĞİL) | 2xx | |
| 3 | AC-2 | M1 (talent + org + kurum) → GET kendi evidence/skill-claim/signal/verified-experience uçları | 200 + yalnız kendi kayıtları (kayıt DB'de var) | |
| 4 | AC-3 | M2 → K2'nin PENDING_APPROVAL engagement'ını onayla | 2xx | |
| 5 | AC-S5 | M2 → K1'in (yalnız ADMIN olduğu) engagement'ını onayla | bugünkü gibi reddedilir (404/403 mevcut tür); DB değişmez | |
| 6 | AC-S5 | yalnız INST_ADMIN kullanıcı → geçiş | reddedilir, DB değişmez | |
| 7 | AC-5 | M1 → `GET /engagements` | liste = {kendi talent engagement'ları} ∪ {O1} ∪ {K1}; kopya yok; O3/K3 engagement'ı yok | |
| 8 | AC-7/S2 | X → `GET /engagements/{E1}` ve E1 üzerinde her yazma eylemi | 404, gövdede E1 alanı yok | |
| 9 | AC-S2 | M3 (O1 MEMBER) → body'de `organization_id=O2` vererek O1 adına işlem; M3 → O3 kaynağı | O1/O2 dışı: 404; ID oturumdan | |
| 10 | AC-S4 | M3 → `POST /organizations/{O1}/members` (MEMBER olduğu org, ADMIN-only uç) | 404 (403 değil), üye eklenmemiş (DB) | |
| 11 | AC-S4 | M3 → `POST /organizations/{O2}/members` (ADMIN olduğu org) | 2xx | |
| 12 | AC-S4 | M2 → K2 ADMIN-only/COORDINATOR-only eylem ayrımı: K1'de yalnız ADMIN yetkisi, K2'de yalnız COORDINATOR yetkisi sızmaz | roller kurum bazlı | |
| 13 | AC-S3 | M1 (O1 üyesi) → T1'in PRIVATE kanıtına `download-url` | 404; kanıt DB'de var | |
| 14 | AC-S3 | A (platform admin) → T1'in PRIVATE kanıtı | 403 (mevcut sözleşme: AC-S3 "admin da hayır", test_admin_downloads_private_evidence_returns_403) | |
| 15 | AC-S3 | M1 → `GET` kanıt/claim uçları: T1'in kayıtları yanıtta yok | yalnız M1'in talent kayıtları | |
| 16 | AC-S1 | S → kendi E2'sini attest et (ORG_ADMIN/COORDINATOR yoluyla) | 409 SELF_ATTESTATION_FORBIDDEN (mevcut sözleşme), attestation satırı oluşmaz | |
| 17 | AC-S1 | S → E2'ye `ORG_TO_TALENT` evaluation | 403 (mevcut TransitionForbidden), evaluation satırı oluşmaz | |
| 18 | AC-S1 | S → E2 PENDING_APPROVAL→ACTIVE/REJECTED (K1 koordinatörü olarak) | reddedilir, status/version değişmez | |
| 19 | AC-S1 | S → E2 ACTIVE→CANCELLED (O1 admin olarak) ve ACTIVE→PENDING_EVALUATION, `POST /tasks` | reddedilir, DB değişmez | |
| 20 | AC-S1 | S → E2: DRAFT→PENDING_APPROVAL, deliverable, `TALENT_TO_ORG` evaluation (talent-tarafı) | 2xx (çalışmaya devam) | |
| 21 | AC-S1 | S → E3 (başka talent'ın engagement'ı, O1/K1 kapsamında) org/koordinatör eylemleri | 2xx (self-dealing maskesi yalnız kendi engagement'ında) | |
| 22 | AC-S1 | S org MEMBER (ADMIN değil) varyantı: kendi engagement'ında task / PENDING_EVALUATION | reddedilir | |
| 23 | AC-S1 | S → kendi adına engagement oluştur (talent_id=kendi) | mevcut davranış korunur (2xx) | |
| 24 | AC-S1 | Saf T1 → attest | 403 (mevcut S6 istisnası) | |
| 25 | AC-4 | P, T1 (tek rol) → mevcut uçlar | bugünkü kodlar aynı (mevcut 360 authz testi değişmeden yeşil) | |
| 26 | AC-8 | M1'in O1 üyeliği silinir → sonraki istek `POST /organizations/{O1}/members` | 404; token yenilenmeden | |
| 27 | AC-S2 | Kimliksiz istek → tüm yukarıdaki uçlar | 401, boş liste değil | |
| 28 | AC-S2 | Bozuk/süresi geçmiş cookie | 401 | |
| 29 | AC-S2 | İstekte `kind`/`role`/`org_admin_ids`/`is_platform_admin` alanı (body/query/header) | yok sayılır, sunucu DB'ye bakar | |
| 30 | AC-6 | Statik: `principal.kind` services/ ve api/ içinde okunmaz | test yeşil | |
| 31 | tüm yazma | Reddedilen her yazma sonrası ilgili satırlar yeniden okunur | değişmemiş | |

## Kapsam notu
- Satır 5-6 INST_ADMIN davranışının **değişmediğini** sabitler (YET-190 kapsamı).
- Satır 16-24 AC-S1 için; mevcut testlerde org ADMIN+talent self-attest'i bekleyen bir test varsa kırılır → kod/test ayrımı yapılıp kullanıcıya sorulur.
- Dashboard (`GET /institutions/{id}/dashboard`) için M2: K2 → 200, K1 (yalnız ADMIN) → mevcut davranış, X → 404. (Satır 7'ye ek senaryo.)
- Mock'lanan test: yok (matris mock yasaklı).
- Kapsanmayan: üyelik `status=PENDING` davranışı (kapsam dışı, atdd Risks).

## Canlı sonda planı (kod sonrası, verify aşamasında)
Geliştirme ortamında (Docker postgres 55433, test DB) iki gerçek hesapla satır 2/8/10/13/27 gerçek HTTP ile atılır; çıktı bu dosyaya eklenir. Üretime sonda atılmaz.
