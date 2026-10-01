# refactor — yet-187-coklu-rol
Ön koşul: verify yeşildi (backend 940/0/5, authz 455/4). Testlere dokunulmadı.

## Yapılan (2 değişiklik, davranış korunur)
1. `backend/app/services/engagement.py`, `evaluation.py`: `engagement_relation` 4 kez fonksiyon içinde import ediliyordu (3 engagement.py, 1 evaluation.py); aynı modül zaten dosya başında `authorization`'dan import yapıyor → import dosya başına taşındı, 4 satır-içi import silindi. Ölçüt: 4 tekrar, gereksiz.
2. `engagement.py` `create_engagement_task`: ilk "Talent cannot create tasks" bloğu (`is_subject and not has_org_side_link`) ikinci bloğun mantıksal alt kümesi (bu durumda is_org_member ve is_coordinator False, ikinci blok aynı hatayı veriyor) → kopya blok silindi.

## Sonuç
ruff temiz; mypy 4 hata (hepsi önceden var: `rowcount`); backend 940 geçti/0 kırık/5 atlandı; tests/authorization 455 geçti/4 atlandı.

## Denenip geri alınan
Yok.

## Dokunulmayıp not düşülenler
- `engagement_relation` içindeki iki zincirli `... is not None and ... in ...` kontrolü ve `Principal.coordinator_institution_ids` her çağrıda liste üretiyor (küçük listeler; ölçülebilir sorun yok, dokunulmadı).
- mypy `rowcount` 4 hatası (evaluation.py:226, engagement.py:372, attestation.py:353/496): bu işten değil, ayrı takip.
- `attestation.py` içindeki ikinci self-attestation kontrolü (≈satır 244) savunma derinliği olarak bırakıldı.
