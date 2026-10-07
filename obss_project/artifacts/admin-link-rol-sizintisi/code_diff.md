# Code Diff — admin-link-rol-sizintisi
_Reference: atdd.md, plan.md, test_diff.md_

## Değiştirilen Dosyalar
- `backend/app/api/me.py` — `UserResponse` şemasına `is_platform_admin: bool` eklendi; `get_me()` içinde `user.is_platform_admin` değeri geçiriliyor.
- `frontend/lib/session/types.ts` — `MeResponse.user`'a `is_platform_admin?: boolean` eklendi (opsiyonel, `isMeResponse` guard'ı değişmedi).
- `frontend/components/app-shell.tsx` — Yeni üst bar (logo "Yetkin360" + Çalışmalarım + Profil + koşullu admin linkleri + Çıkış), eski `border-t` footer kaldırıldı. Admin linkleri `session.data.user.is_platform_admin === true` (kesin eşitlik, fail-closed) koşuluna bağlandı.

## Oluşturulan Dosyalar
Yok.

## AC → Implementasyon eşleşmesi
| AC | Karşılandığı yer |
|---|---|
| AC-1 | app-shell.tsx üst bar, admin true iken tüm linkler |
| AC-2 | `=== true` koşulu false'ta admin linkini gizler |
| AC-3 | Mevcut `session.isPending` early-return'ü (dokunulmadı) zaten admin linkini göstermiyor |
| AC-4 | `=== true` kesin eşitliği undefined/null'da da gizler (fail-closed) |
| AC-5 | Çalışmalarım/Profil linkleri üst bar'da, eski footer silindi |
| AC-S1 | `backend/app/api/admin.py`'ye hiç dokunulmadı — mevcut 404 regresyon koruması bozulmadı |
| AC-S2 | `UserResponse`'a sadece `is_platform_admin` eklendi, başka rol alanı eklenmedi |

## Dokunulmayan Dosyalar (bilinçli)
- `backend/app/services/authorization.py`, `backend/app/api/admin.py`, `frontend/components/ui/button.tsx` — kapsam dışı, değiştirilmedi.
- Test dosyaları (`test_talent.py`, `app-shell.test.tsx`) ve `tr.json` — test-copilot adımından, bu adımda dokunulmadı.

## Orkestratör Doğrulaması
`git status --short` ile 3 dosyanın değiştiği, yasaklı dosyaların değişmediği doğrulandı; `Read` ile içerikler satır satır incelendi — TODO/placeholder/kapsam dışı değişiklik yok, fail-closed (`=== true`) garantisi kodda birebir var.

## Görsel/UI Kriteri
Bu görev `.tsx` dosyalarına dokunuyor, nav yerleşimi değişti — `verify` adımında gate 11 (`vision-test`) N/A değil, AKTİF çalışmalı.
