# Code Diff — kurum-dashboard-uyeler
_Reference: atdd.md, plan.md, test_diff.md_

## Değiştirilen Dosyalar
- `backend/app/services/engagement.py` — `get_coordinator_dashboard()` (satır 640-753)
  içine `InstitutionMember` + `User` join sorgusu eklendi. **AC-S1 kritik güvenlik filtresi
  doğrulandı:** `InstitutionMember.institution_id == inst_uuid` WHERE koşulu var (satır 712) —
  çapraz-kurum sızıntısı riski kapatılmış.
- `backend/app/api/institutions.py` — `DashboardMemberItem` şeması (satır 96-102, mevcut
  `DashboardEngagementItem` deseniyle birebir tutarlı), `DashboardResponse`'a `members` alanı
  (satır 119), endpoint'te `members=[DashboardMemberItem(**item) for item in ...]` eklendi.

Test dosyasına (`test_coordinator_dashboard.py`) dokunulmadı — `git diff` ile doğrulandı, sadece
`engagement.py`/`institutions.py` değişti.

## AC Karşılanması (Read ile doğrulandı, alt-ajan özetine güvenilmedi)
| AC | Karşılandı mı | Not |
|---|---|---|
| AC-1 (happy path, tek/çoklu üye) | ✅ | `InstitutionMember`+`User` join, `user_id/email/role/joined_at` doğru eşleniyor |
| AC-2 (kurumda üye yok) | ⚠️ Kısmen | Implementasyon doğru (`members: []` boş listeyi doğru şekilde döner), ama BU AC'yi test eden fonksiyon (`test_ac2_members_empty_when_no_other_members`, test-copilot aşamasından kalma) gövdesi `pass` — hiçbir assert çalıştırmıyor, "PASSED" görünmesi yanıltıcı. Bu bir implementasyon hatası DEĞİL, önceden bilinen bir test-kalite notu (`test_diff.md`'de zaten işaretlenmişti). |
| AC-S1 (çapraz-kurum sızıntısı) | ✅ | `institution_id` WHERE filtresi kodda var, 2 test (`test_acs1_cross_tenant_member_isolation`, `test_acs1_members_email_not_exposed_across_institutions`) gerçekten geçiyor (gerçek assert'lerle, boş gövde değil) |

## Bağımsız Doğrulama (alt-ajanın özetine ek olarak, ben de çalıştırdım)
- `ruff check app/services/engagement.py app/api/institutions.py` → **All checks passed!**
- `mypy app` → **Success: no issues found in 63 source files**
- `pytest tests/test_coordinator_dashboard.py -v` → **11 passed** (6 mevcut test + 5 yeni test, hiç regresyon yok — dosyanın TAMAMI çalıştırıldı, sadece yeni class değil)

## CAVEMAN Değerlendirmesi
Yeni dosya yok, yeni soyutlama/yardımcı fonksiyon yok — mevcut desenle (join + dict comprehension)
birebir tutarlı. Sayfalama/üye yönetimi/öğrenci listesi gibi kapsam dışı hiçbir şey eklenmemiş.

## Kalan Not (engelleyici değil, red-team'e taşınıyor)
`test_ac2_members_empty_when_no_other_members`'ın boş (`pass`) gövdesi — `pytest.skip("...")`
olarak değiştirilmesi daha dürüst olurdu (şu an yanıltıcı şekilde "PASSED" gösteriyor). Bu, test
dosyasında bir değişiklik gerektirdiği için code-copilot'un kapsamı dışında bırakıldı — `verify`/
`red-team` aşamasında ele alınabilir.

## Sub-agent Raporu Hakkında Not
Alt-ajanın kendi özeti kısmen Endonezce/Malayca karışık yazılmıştı (ör. "Berkas yang Diubah",
"Hasil Testing") — içerik doğru ve tutarlı çıktı ama format tuhaftı, bu yüzden özete güvenilmedi,
her iddia yukarıdaki gibi bağımsız olarak `Read`/gerçek komut çalıştırmayla doğrulandı.

## Sıradaki Adım
`verify` — tüm gate'ler (lint/mypy zaten yukarıda geçti ama `verify` resmi olarak tekrar
çalıştırılacak) + `pytest tests/authorization -q` tam paket.
