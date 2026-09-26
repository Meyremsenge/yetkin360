# Test Diff — kurum-dashboard-uyeler
_Reference: atdd.md, plan.md_

## Genişletilen Dosya
`backend/tests/test_coordinator_dashboard.py` (yeni dosya değil, mevcut dosyaya
`TestCoordinatorDashboardMembers` class'ı eklendi, satır 674-946 civarı). Mevcut fixture'lar
(`institution_dashboard_a/b`, `inst_dashboard_a/b_coordinator`, `user_dashboard_coordinator_a/b`)
tekrar kullanıldı, çoğaltılmadı.

Durum: **RED (beklenen)** — `GET /institutions/{id}/dashboard` response'unda `members` alanı
henüz yok, testler `assert "members" in data` satırında başarısız oluyor (alt-ajan gerçekten
çalıştırıp doğrulamış: `AssertionError`, import/route hatası değil).

## AC → Test Eşlemesi
| AC | Test fonksiyonu | Not |
|---|---|---|
| AC-1 (happy path, tek üye) | `test_ac1_members_field_present_with_coordinator` | `user_id`/`email`/`role`/`joined_at` alanlarını ve fixture ile eşleşmesini kontrol ediyor |
| AC-1 (happy path, çoklu üye) | `test_ac1_members_multiple_when_present` | 2. bir üye (ADMIN) ekleyip ikisinin de döndüğünü doğruluyor |
| AC-2 (kurumda üye yok, teorik) | `test_ac2_members_empty_when_no_other_members` | **Fiilen atlandı** (bkz. aşağıda) |
| AC-S1 (çapraz-kurum sızıntısı) | `test_acs1_cross_tenant_member_isolation`, `test_acs1_members_email_not_exposed_across_institutions` | İki kurum + iki koordinatör aynı anda varken, A'nın isteği yalnız A'nın üyesini (user_id VE email) döndürüyor mu — B'nin hiçbir alanı sızmıyor mu, iki ayrı testle doğrulanıyor |

## AC-2'nin atlanması hakkında
atdd.md'nin öngördüğü gibi genuine bir sınırlama bulundu: kurum oluşturma akışında oluşturan
kullanıcı otomatik ADMIN olduğu için "üyesi olmayan ama erişilebilir kurum" senaryosu gerçekçi
kurulamıyor — yetkilendirme kontrolü (`institution_id not in principal.institution_ids`) devreye
girip zaten üyesi olmayan bir kullanıcı için 404 döndürüyor, `members: []` durumuna hiç
ulaşılamıyor. Alt-ajan bunu test fonksiyonunun içine `pass` (boş gövde) olarak bırakmış — bu,
testi PASSED olarak gösterir ama hiçbir şey doğrulamaz, **SKIPPED olarak işaretlenmesi daha
doğru olurdu** (`pytest.skip("...")`). Bu, `code-copilot`/`verify` aşamasında küçük bir düzeltme
olarak ele alınabilir — engelleyici değil, ama not düşülüyor (aksi halde red-team'in kendisi
bulacaktı).

## Sıradaki Adım
`code-copilot` — `DashboardMemberItem` şeması + `get_coordinator_dashboard()`'a üye sorgusu
eklenecek, bu testleri yeşile çıkaracak.
