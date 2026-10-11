# Verify Report — yeni-calisma-akisi
_Reference: atdd.md/code_diff.md yok (görev pipeline dışında, sohbetle yürütüldü); kapsam git diff'ten alındı._

Kapsam: öğrencinin "Yeni çalışma" akışı — kuruluş seçimi, tek adımda oluştur + gönder,
okul onayı (koordinatör seçimi, maskeli e-posta), türe göre okul onayı (staj/bitirme okula bağlı),
görev formu, detay sayfası düzeltmeleri.

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short`: 21 değişen + 2 yeni dosya, hepsi diskte |
| 2 | Build/derleme | PARTIAL | Backend: tüm paket import edilip test edildi. Frontend `npm run build` çalıştırılmadı — açık `npm run dev` ile aynı `.next` dizinini kullanıyor; CI'da koşacak. `tsc --noEmit` temiz |
| 3 | Supabase şema/canlı doğrulama | N/A | Proje Supabase kullanmıyor (FastAPI + PostgreSQL); migration yok |
| 4 | Lint | PASS | `ruff check .` → All checks passed; `npm run lint` → 0 error (7 eski uyarı, değişen dosyalarda değil). `ruff format`: repo genelinde kullanılmıyor (228 dosya biçimsiz, CI denetlemiyor); yalnız yeni test dosyası biçimlendi |
| 5 | Type check | PASS | `npm run typecheck` temiz; `mypy app` 4 hata — değişiklik öncesi de aynı 4 `rowcount` hatası (stash ile karşılaştırıldı), yeni hata yok |
| 6 | Unit testler | PASS | Backend `pytest` (e2e ve cv2 gerektiren `test_certificate_check_handler.py` hariç): 2640 geçti, 10 atlandı; `pytest tests/authorization`: 1705 geçti. Frontend `npm run test`: 1745/1745 |
| 7 | E2E testler | PASS (elle) | Playwright (Edge) ile gerçek uygulamada: giriş → kuruluş seç → onaylayıcılar → oluştur → detay/görev formu; 1280px ve 375px |
| 8 | Lighthouse (performans) | N/A | Lighthouse MCP bu oturumda yok |
| 9 | Erişilebilirlik | PARTIAL | Lighthouse yok; elle: fieldset/legend, native radio, label, aria-live hata/başarı, görünür odak, aria-expanded |
| 10 | Güvenlik taraması | PASS | `security-scan` (değişen 12 dosya): secrets PASS, python_sast PASS, deps N/A. Tarayıcılar iş mantığını görmez → yetkilendirme testleri ayrıca yazıldı (`test_approval_recipients_authz.py`, 30 test) |
| 11 | AI code review | PENDING (red-team) | Çalıştırılmadı |
| 12 | Görsel regresyon | PASS (elle) | Ekran görüntüleri incelendi; mobilde adım göstergesi ve kuruluş adı kırpılması düzeltildi |
| 13 | DAST (ZAP) | N/A | threat-model AC-S üretilmedi; ZAP bu oturumda yok |
| 14 | İnsan onayı | PENDING | Kullanıcı commit+push istedi; ürün onayı kullanıcıda |

## Davranış → Test eşlemesi
1. Onaylayıcı listesi maskeli e-posta, tam adres sızmaz → `test_org_team_authz.py::TestApprovers::test_any_verified_user_lists_name_unit_and_masked_email_only`, `test_short_local_part_is_never_shown_whole` → PASS
2. Taslağın okul koordinatörleri yalnız gönderebilene, diğer herkese 404 → `TestApprovalRecipientsList` → PASS
3. Kendi okulunun koordinatörleri; okulsuz/profilsiz 404 → `TestOwnSchoolRecipients` → PASS
4. `notify_user_ids` yalnız o okulun koordinatörlerine daraltır; diğerleri sessizce yok sayılır; alıcı opsiyonel → `TestNotifyUserIds`, `test_without_a_recipient_every_coordinator_is_notified` → PASS
5. Staj/bitirme okulu atlayıp kendi kendine aktifleşemez; yarı zamanlı okulsuz hemen başlar → `TestSchoolBoundKinds` → PASS
6. Arayüz: tek adımda gönder / başlat / taslak, gönderim hatasında ikinci oluşturma yok → `olustur/page.test.tsx` → PASS
7. Arayüz: detayda koordinatör seçimi → `transition-actions.test.tsx` → PASS

## Coverage / Quality Notes
- Davranış değişikliği (onaylı): `notify_emails` artık zorunlu değil (ekip arkadaşının #61 kararı); eski "zorunlu" testi yeni davranışa çevrildi.
- `frontend/lib/ui/notify-emails.ts` + testi ve `calismalar.notifyEmails*` metinleri artık kullanılmıyor; silme kullanıcı onayı bekliyor.
- `docs/STATE_MACHINE.md` T4 aktörünü yalnız `ORG:MEMBER` yazıyor; kod öğrencinin okulsuz çalışmayı başlatmasına da izin veriyor (yeni akış buna dayanıyor) — belge ya da kural netleştirilmeli.
