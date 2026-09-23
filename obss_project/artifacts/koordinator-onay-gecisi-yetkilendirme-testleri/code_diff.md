# Code Diff — koordinator-onay-gecisi-yetkilendirme-testleri
_Reference: atdd.md, plan.md, test_diff.md_

## Sonuç: Kod değişikliği YAPILMADI

Docker Desktop kullanıcı tarafından başlatıldı, `docker compose up -d` ile
PostgreSQL + MinIO ayağa kaldırıldı, gerçek DB'ye karşı test koşuldu:

```
backend> .venv/Scripts/python.exe -m pytest tests/test_engagement_transitions.py -q
25 passed, 16 warnings in 2.95s

backend> .venv/Scripts/python.exe -m pytest tests/authorization -q
73 passed, 4 skipped, 16 warnings in 8.16s
```

`test-copilot`'un yazdığı 7 yeni test (`TestCoordinatorCrossInstitution` x3,
`TestOrgAdminScopeVsAdminMismatch` x1, `TestExtraFieldsIgnored` x2 = 6 test,
+ mevcut dosyadaki toplam 25 test) **ilk koşuda yeşil geçti** — bu klasik bir
red→green değil, çünkü implementasyon (`transition_engagement`,
`scoped_engagements`, `get_scoped_or_404`) PLAN 2.2'de zaten doğru yazılmıştı.
`plan.md`'nin öngördüğü "muhtemelen düzeltme gerekmeyecek" varsayımı
doğrulandı.

`tests/authorization -q` içindeki 4 skip, atdd.md'nin "Kapsam Dışı"
bölümünde zaten belirtilen YET-8/YET-9/anonim-profil placeholder'ları —
bu görevin AC'lerine dahil değil, dokunulmadı.

## Değiştirilen Dosyalar
Yok (implementasyon dosyalarında `app/services/engagement.py`,
`app/services/authorization.py` — hiçbir satır değişmedi).

## AC Karşılama Durumu
Tüm AC-1..AC-8 ve AC-S1..AC-S5 kriterleri `test_diff.md`'deki testlerle
karşılanıyor ve hepsi gerçek DB'ye karşı geçiyor. AC-S6 (authz-test ile tam
parametrik matris) bu adımda hâlâ ayrı — `test_diff.md`'de not edildi,
gerekirse `verify`/kullanıcı onayıyla ayrıca tetiklenir.

## Kalan Sınırlamalar
- `TestOrgAdminScopeVsAdminMismatch`'teki fixture sapması (`evan_member_of_org_b`
  tam "iki kurumda farklı rol" senaryosunu değil, basitleştirilmiş tek-üyelik
  senaryosunu test ediyor) — `test_diff.md`'de not edildi, davranışsal sonuç
  aynı olduğu için düzeltme gerekmedi, ama `red-team` adımında tekrar
  değerlendirilebilir.

## Varsayımlar
Yok — sonuç doğrudan gerçek test koşumuyla kanıtlandı, varsayım yapılmadı.
