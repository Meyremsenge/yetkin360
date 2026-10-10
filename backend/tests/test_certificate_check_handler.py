"""
PLAN 3.55: evidence.certificate_check_requested outbox handler. AI never
decides authenticity here — it only transcribes printed text (transformation,
not judgment, final-analiz §11.4.2/§39); name-match is computed by plain
string comparison in the handler, never by the model. Decision stays PENDING
until a coordinator resolves it (tests/authorization/test_certificate_check_authz.py).

Runs the real handler against the rolled-back test transaction (same pattern
as tests/test_evidence_scan.py) with fake storage + fake httpx.post — no real
network/S3.
"""

import uuid

import cv2
import numpy as np
import pytest
import sqlalchemy
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CertificateCheck, Evidence, Organization, TalentProfile, User
from app.services.storage import StoredObject
from app.workers import outbox_worker


def _blank_png() -> bytes:
    image = np.zeros((50, 50, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", image)
    assert ok
    return bytes(buf)


class _FakeHttpError(Exception):
    pass


def _install_fake_openrouter(monkeypatch, body: dict | None = None, status_code: int = 200, exc: Exception | None = None):
    calls: list[dict] = []

    class _Response:
        def __init__(self, status_code, body):
            self.status_code = status_code
            self._body = body

        def raise_for_status(self):
            if self.status_code >= 400:
                raise _FakeHttpError(f"status={self.status_code}")

        def json(self):
            return self._body

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "json": json})
        if exc is not None:
            raise exc
        return _Response(status_code, body)

    monkeypatch.setattr("httpx.post", fake_post)
    return calls


def _chat_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


@pytest.fixture
def handler_env(session, monkeypatch):
    class _Engine:
        def dispose(self) -> None:
            pass

    bind = session.get_bind()
    monkeypatch.setattr(sqlalchemy, "create_engine", lambda *a, **k: _Engine())
    monkeypatch.setattr(
        outbox_worker,
        "Session",
        lambda engine: Session(bind=bind, join_transaction_mode="create_savepoint"),
    )
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "openrouter_model", "anthropic/claude-haiku-4.5")

    reads: list[tuple[str, str]] = []

    def install_storage(data, etag="etag-1"):
        def fake_fetch(bucket, key, max_bytes):
            reads.append((bucket, key))
            if isinstance(data, Exception):
                raise data
            return None if data is None else StoredObject(data=data, etag=etag)

        monkeypatch.setattr("app.services.storage.fetch_object", fake_fetch)

    return install_storage


@pytest.fixture
def talent_cc(session):
    user = User(email="cert-talent@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    profile = TalentProfile(user_id=user.id, full_name="Ahmet Yılmaz", visibility="PRIVATE")
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def org_cc(session):
    org = Organization(name="Cert Org", verification_level="T2")
    session.add(org)
    session.flush()
    return org


def _evidence(session, talent, status="CLEAN", mime="image/png") -> Evidence:
    ev = Evidence(
        owner_talent_id=talent.id,
        kind="CERTIFICATE",
        storage_key=f"evidence/{talent.id}/{uuid.uuid4()}.png",
        mime_type=mime,
        size_bytes=100,
        scan_status=status,
    )
    session.add(ev)
    session.flush()
    return ev


def _pending_check(session, evidence) -> CertificateCheck:
    check = CertificateCheck(evidence_id=evidence.id)
    session.add(check)
    session.flush()
    return check


class TestHandlerRegistration:
    def test_handler_is_registered_for_the_topic(self):
        assert (
            outbox_worker.DEFAULT_HANDLERS["evidence.certificate_check_requested"]
            is outbox_worker.certificate_check_requested_handler
        )


class TestNamesMatch:
    """Transcription noise (dropped Turkish letters, I/l/1, rn/m, word order)
    must not flip a real match to False; a different person must stay False."""

    @pytest.mark.parametrize(
        ("extracted", "profile"),
        [
            ("Ahmet Yılmaz", "Ahmet Yılmaz"),
            ("AYSE KILIC", "Ayşe Kılıç"),  # certificate printed without Turkish letters
            ("Ayse KiIic", "Ayşe Kılıç"),  # capital I read where l is printed
            ("AIi Su", "Ali Su"),  # short name, one confusable glyph
            ("A1i Su", "Ali Su"),  # digit read for a letter
            ("Ahrnet Yilrnaz", "Ahmet Yılmaz"),  # m read as rn
            ("YILMAZ Ahmet", "Ahmet Yılmaz"),  # surname-first layout
            ("Işıl Kır", "ISIL KIR"),
            ("Jean-Luc O'Brien", "Jean Luc OBrien"),
        ],
    )
    def test_transcription_noise_still_matches(self, extracted, profile):
        assert outbox_worker._names_match(extracted, profile) is True

    @pytest.mark.parametrize(
        ("extracted", "profile"),
        [
            ("Mehmet Demir", "Ahmet Yılmaz"),
            ("Ahmet Kaya", "Ahmet Yılmaz"),
            ("Ayşe Yılmaz", "Ahmet Yılmaz"),
            ("", "Ahmet Yılmaz"),
            ("...", "Ahmet Yılmaz"),
        ],
    )
    def test_different_person_does_not_match(self, extracted, profile):
        assert outbox_worker._names_match(extracted, profile) is False

    def test_dotless_i_is_folded_not_dropped(self):
        assert outbox_worker._normalize_name("  Ayşe   KILIÇ ") == "ayse kilic"
        assert outbox_worker._normalize_name("Işıl Kır") == "isil kir"


class TestExtractionConsensus:
    """A credential id is only trusted when independent readings of different
    renderings agree — a misread character must never become the verify link."""

    GOOD = "UC-a677fedf-70be-4a21-a039-ad09955d4e18"
    BAD = "UC-a677fedf-70be-4a21-a039-ad0995544e18"  # the misread seen live: d -> 4

    @staticmethod
    def _install_readings(monkeypatch, credential_ids):
        calls = []

        def fake_extract(view, api_key, model):
            calls.append(view)
            credential_id = credential_ids[len(calls) - 1]
            if credential_id == "MALFORMED":
                return None
            return {
                "provider": "UDEMY",
                "credential_id": credential_id,
                "extracted_name": "Ahmet Yılmaz",
                "course_name": "Kurs",
                "verify_url": f"ude.my/{credential_id}" if credential_id else None,
            }

        monkeypatch.setattr(outbox_worker, "_extract_certificate_fields", fake_extract)
        return calls

    def test_two_agreeing_readings_are_accepted_without_a_third_call(self, monkeypatch):
        calls = self._install_readings(monkeypatch, [self.GOOD, self.GOOD, self.BAD])

        fields = outbox_worker._extract_with_consensus([b"v1", b"v2", b"v3"], "key", "model")

        assert fields["credential_id"] == self.GOOD
        assert calls == [b"v1", b"v2"]

    @pytest.mark.parametrize("order", [("BAD", "GOOD", "GOOD"), ("GOOD", "BAD", "GOOD")])
    def test_disagreement_is_settled_by_majority_of_three(self, monkeypatch, order):
        self._install_readings(monkeypatch, [getattr(self, name) for name in order])

        fields = outbox_worker._extract_with_consensus([b"v1", b"v2", b"v3"], "key", "model")

        assert fields["credential_id"] == self.GOOD
        assert fields["verify_url"] == f"ude.my/{self.GOOD}"
        assert fields["extracted_name"] == "Ahmet Yılmaz"

    def test_no_majority_leaves_the_id_unknown_instead_of_guessing(self, monkeypatch):
        self._install_readings(monkeypatch, [self.GOOD, self.BAD, "UC-something-else-entirely"])

        fields = outbox_worker._extract_with_consensus([b"v1", b"v2", b"v3"], "key", "model")

        assert fields["credential_id"] is None
        assert fields["verify_url"] is None
        assert fields["extracted_name"] == "Ahmet Yılmaz"  # fuzzy-compared fields are kept

    def test_two_views_that_disagree_leave_the_id_unknown(self, monkeypatch):
        self._install_readings(monkeypatch, [self.GOOD, self.BAD])

        assert outbox_worker._extract_with_consensus([b"v1", b"v2"], "key", "model")["credential_id"] is None

    def test_malformed_second_reading_falls_through_to_the_third(self, monkeypatch):
        calls = self._install_readings(monkeypatch, [self.GOOD, "MALFORMED", self.GOOD])

        fields = outbox_worker._extract_with_consensus([b"v1", b"v2", b"v3"], "key", "model")

        assert fields["credential_id"] == self.GOOD
        assert len(calls) == 3

    def test_malformed_first_reading_fails_like_before(self, monkeypatch):
        calls = self._install_readings(monkeypatch, ["MALFORMED", self.GOOD])

        assert outbox_worker._extract_with_consensus([b"v1", b"v2"], "key", "model") is None
        assert len(calls) == 1

    def test_single_view_is_one_call(self, monkeypatch):
        calls = self._install_readings(monkeypatch, [self.GOOD])

        assert outbox_worker._extract_with_consensus([b"v1"], "key", "model")["credential_id"] == self.GOOD
        assert len(calls) == 1


class TestCertificateViews:
    @staticmethod
    def _long_edges(views):
        return [max(cv2.imdecode(np.frombuffer(v, dtype=np.uint8), cv2.IMREAD_COLOR).shape[:2]) for v in views]

    def test_small_image_yields_a_single_view(self):
        assert len(outbox_worker._certificate_views(_blank_png(), "image/png")) == 1

    def test_large_image_yields_distinct_resolutions_smallest_first(self):
        ok, buf = cv2.imencode(".jpg", np.full((2400, 3600, 3), 200, dtype=np.uint8))
        assert ok

        views = outbox_worker._certificate_views(bytes(buf), "image/jpeg")

        assert self._long_edges(views) == [1568, 2200, 3000]
        assert all(v.startswith(b"\x89PNG") for v in views)  # always real PNG bytes

    def test_undecodable_image_yields_no_views(self):
        assert outbox_worker._certificate_views(b"not an image", "image/png") == []

    def test_pdf_first_page_is_rendered_at_several_resolutions(self):
        import fitz

        doc = fitz.open()
        doc.new_page(width=842, height=595)
        pdf_bytes = doc.tobytes()
        doc.close()

        views = outbox_worker._certificate_views(pdf_bytes, "application/pdf")

        edges = self._long_edges(views)
        assert len(edges) == 3 and edges == sorted(edges)
        assert all(v.startswith(b"\x89PNG") for v in views)


class TestCertificateCheckHandler:
    def test_coursera_page_fields_html_entities_are_unescaped(self, monkeypatch):
        class _Page:
            status_code = 200
            text = (
                '<meta data-rh="true" property="og:title" '
                'content="Completion Certificate for Data &amp; AI: Foundations"/>'
                "<p>Completed by <strong>Sean O&#x27;Brien</strong></p>"
            )

        monkeypatch.setattr("httpx.get", lambda *a, **k: _Page())

        assert outbox_worker._fetch_official_page(
            "https://www.coursera.org/account/accomplishments/verify/ABC"
        ) == ("Sean O'Brien", "Data & AI: Foundations")

    @pytest.mark.parametrize(
        ("certificate_course", "expected_match"),
        [
            ("Introduction to Front-End Development", True),
            ("lntroduction to Front-End Developrnent", True),  # transcription noise
            ("Advanced Machine Learning", False),
        ],
    )
    def test_coursera_course_name_is_compared_with_official_page(
        self, session, talent_cc, handler_env, monkeypatch, certificate_course, expected_match
    ):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "ABC123", "extracted_name": "Ahmet Yılmaz", '
                f'"course_name": "{certificate_course}", "verify_url": "https://coursera.org/verify/ABC123"}}'
            ),
        )

        class _Page:
            status_code = 200
            text = (
                '<meta data-rh="true" property="og:title" '
                'content="Completion Certificate for Introduction to Front-End Development"/>'
                "<h3><span>Completed by <strong>Ahmet Yılmaz</strong></span></h3>"
            )

        monkeypatch.setattr("httpx.get", lambda *a, **k: _Page())

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.extracted_course_name == certificate_course
        assert check.page_course_name == "Introduction to Front-End Development"
        assert check.course_match is expected_match
        assert check.page_match is True
        assert check.decision == "PENDING"  # AI never decides

    @staticmethod
    def _btk_page(name: str, course: str) -> str:
        """Same shape as the live validate page: certificate HTML as a JSON string."""
        import json

        certificate_html = (
            '<html><div class="icerik"><h1>KATILIM SERTİFİKASI</h1> '
            f'<h3>{name}</h3> <p class="course-name"><strong>"{course}"</strong> '
            "<br>çevrim içi eğitimini tamamlayarak</p></div></html>"
        )
        next_data = {"props": {"pageProps": {"certificateId": "rKjhGX9nYp", "certificate": certificate_html}}}
        return (
            '<html><body><div id="__next"></div><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(next_data)
            + "</script></body></html>"
        )

    def test_btk_page_is_fetched_and_name_and_course_compared(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "BTK", "credential_id": "rKjhGX9nYp", "extracted_name": "AHMET YILMAZ", '
                '"course_name": "Veri Bilimi için Python ve Tensorflow", "verify_url": null}'
            ),
        )
        page = self._btk_page("AHMET YILMAZ", "Veri Bilimi için Python ve Tensorflow")
        page_calls = []

        class _Page:
            status_code = 200
            text = page

        def fake_get(url, **kwargs):
            page_calls.append(url)
            return _Page()

        monkeypatch.setattr("httpx.get", fake_get)

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        # No QR in the blank image -> link is built from the certificate number.
        assert page_calls == ["https://www.btkakademi.gov.tr/portal/certificate/validate?certificateId=rKjhGX9nYp"]
        session.refresh(check)
        assert check.status == "DONE"
        assert check.provider == "BTK"
        assert check.verify_url == page_calls[0]
        assert check.name_match is True  # profile: "Ahmet Yılmaz"
        assert check.page_name == "AHMET YILMAZ"
        assert check.page_match is True
        assert check.page_course_name == "Veri Bilimi için Python ve Tensorflow"
        assert check.course_match is True
        assert check.decision == "PENDING"  # AI never decides

    def test_btk_page_with_different_person_and_course_is_flagged_false(
        self, session, talent_cc, handler_env, monkeypatch
    ):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "BTK", "credential_id": "rKjhGX9nYp", "extracted_name": "Ahmet Yılmaz", '
                '"course_name": "Veri Bilimi için Python ve Tensorflow", "verify_url": null}'
            ),
        )
        page = self._btk_page("MEHMET DEMİR", "Siber Güvenliğe Giriş")

        class _Page:
            status_code = 200
            text = page

        monkeypatch.setattr("httpx.get", lambda *a, **k: _Page())

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.page_match is False
        assert check.course_match is False

    @pytest.mark.parametrize(
        "page_html",
        [
            "<html><body>no data</body></html>",
            '<script id="__NEXT_DATA__" type="application/json">{not json</script>',
            '<script id="__NEXT_DATA__" type="application/json">{"props": {"pageProps": {"certificate": null}}}</script>',
        ],
    )
    def test_btk_page_without_certificate_is_unknown_not_mismatch(self, page_html):
        assert outbox_worker._parse_btk_certificate_page(page_html) == (None, None)

    @pytest.mark.parametrize("credential_id", [None, 42, "", "abc", "rKjh GX9nYp", "rKjhGX9nYp&x=1", "../etc/passwd"])
    def test_btk_verify_url_rejects_ids_without_btk_shape(self, credential_id):
        assert outbox_worker._btk_verify_url(credential_id) is None

    def test_udemy_course_name_is_stored_but_never_auto_compared(self, session, talent_cc, handler_env, monkeypatch):
        """Udemy's page can't be fetched — the course name is kept for the
        coordinator's manual check; course_match stays unknown, not False."""
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "UDEMY", "credential_id": "UC-a677fedf-70be-4a21-a039-ad09955d4e18", '
                '"extracted_name": "Ahmet Yılmaz", "course_name": "Photoshop ile Mimari illüstrasyon ve kolaj", '
                '"verify_url": null}'
            ),
        )
        monkeypatch.setattr(
            "httpx.get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not fetch"))
        )

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "DONE"
        assert check.extracted_course_name == "Photoshop ile Mimari illüstrasyon ve kolaj"
        assert check.page_course_name is None
        assert check.course_match is None

    def test_missing_api_key_is_noop(self, session, talent_cc, handler_env, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "")
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response("{}"))
        install_storage = handler_env
        install_storage(_blank_png())

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert calls == []
        session.refresh(check)
        assert check.status == "PENDING"

    def test_successful_extraction_with_matching_name(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "UDEMY", "credential_id": "UC-123", '
                '"extracted_name": "Ahmet Yılmaz", "verify_url": "https://udemy.com/cert/UC-123"}'
            ),
        )

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "DONE"
        assert check.provider == "UDEMY"
        assert check.credential_id == "UC-123"
        assert check.extracted_name == "Ahmet Yılmaz"
        assert check.name_match is True
        assert check.decision == "PENDING"  # AI never decides
        assert check.verify_url == "https://udemy.com/cert/UC-123"
        assert check.page_name is None  # udemy.com allowlist'te değil — otomatik çekilmedi
        assert check.page_match is None

    def test_coursera_verify_page_is_fetched_and_compared(self, session, talent_cc, handler_env, monkeypatch):
        """PLAN 3.55b: coursera.org allowlist'te — resmi sayfadan ad çekilip
        sertifikadaki adla DETERMİNİSTİK karşılaştırılır (AI kararı değil)."""
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "ABC123", '
                '"extracted_name": "Ahmet Yılmaz", "verify_url": "https://coursera.org/verify/ABC123"}'
            ),
        )

        class _PageResponse:
            status_code = 200
            text = "<div>Completed by <strong>Ahmet Yılmaz</strong></div>"

        page_calls = []

        def fake_get(url, timeout=None, follow_redirects=None, headers=None):
            page_calls.append(url)
            return _PageResponse()

        monkeypatch.setattr("httpx.get", fake_get)

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert page_calls == ["https://coursera.org/verify/ABC123"]
        session.refresh(check)
        assert check.page_name == "Ahmet Yılmaz"
        assert check.page_match is True
        assert check.course_match is None  # model output had no course_name -> unknown

    def test_coursera_page_name_mismatch_is_flagged_false(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "ABC123", '
                '"extracted_name": "Ahmet Yılmaz", "verify_url": "https://coursera.org/verify/ABC123"}'
            ),
        )

        class _PageResponse:
            status_code = 200
            text = "<div>Completed by <strong>Başka Bir İsim</strong></div>"

        monkeypatch.setattr("httpx.get", lambda *a, **k: _PageResponse())

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.page_name == "Başka Bir İsim"
        assert check.page_match is False

    def test_arbitrary_host_is_never_fetched_ssrf_guard(self, session, talent_cc, handler_env, monkeypatch):
        """AI'nin ürettiği verify_url'e kör güvenilmez — allowlist dışı hiçbir
        host'a istek atılmaz (SSRF/keyfi URL savunması)."""
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "UNKNOWN", "credential_id": null, "extracted_name": "Ahmet Yılmaz", '
                '"verify_url": "https://internal.attacker.example/steal?x=1"}'
            ),
        )
        calls = []
        monkeypatch.setattr("httpx.get", lambda *a, **k: calls.append(a) or (_ for _ in ()).throw(AssertionError("should not fetch")))

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert calls == []
        session.refresh(check)
        assert check.page_name is None
        assert check.page_match is None

    def test_coursera_page_fetch_failure_does_not_fail_the_handler(self, session, talent_cc, handler_env, monkeypatch):
        """Doğrulama sayfası çekimi opsiyonel bir ek öneri — başarısız olursa
        ana çıkarım (provider/isim/kimlik no) yine DONE olarak kaydedilir."""
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "ABC123", '
                '"extracted_name": "Ahmet Yılmaz", "verify_url": "https://coursera.org/verify/ABC123"}'
            ),
        )

        def failing_get(*a, **k):
            raise _FakeHttpError("network down")

        monkeypatch.setattr("httpx.get", failing_get)

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "DONE"
        assert check.page_name is None
        assert check.page_match is None

    def test_name_mismatch_is_flagged_false_not_rejected(self, session, talent_cc, handler_env, monkeypatch):
        """Ad uyuşmazlığı AI'nin kararı değil — sadece name_match=False, decision PENDING kalır."""
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "XYZ", '
                '"extracted_name": "Başka Bir İsim", "verify_url": null}'
            ),
        )

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "DONE"
        assert check.name_match is False
        assert check.decision == "PENDING"

    def test_qr_data_used_as_verify_url_over_model_text(self, session, talent_cc, handler_env, monkeypatch):
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        ok, qr_buf = cv2.imencode(".png", image)
        assert ok
        handler_env(bytes(qr_buf))
        monkeypatch.setattr(outbox_worker, "_decode_qr", lambda img: "https://coursera.org/verify/ABC123")
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "ABC123", '
                '"extracted_name": null, "verify_url": "https://wrong.example.com"}'
            ),
        )

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.qr_raw_data == "https://coursera.org/verify/ABC123"
        assert check.verify_url == "https://coursera.org/verify/ABC123"
        assert check.name_match is None  # extracted_name null -> unknown, not False

    def test_udemy_verify_url_is_built_from_credential_id_not_model_text(
        self, session, talent_cc, handler_env, monkeypatch
    ):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        credential_id = "UC-a677fedf-70be-4a21-a039-ad09955d4e18"
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                f'{{"provider": "UDEMY", "credential_id": "{credential_id}", '
                '"extracted_name": "Ahmet Yılmaz", "verify_url": "ude.rny/UC-a677fedf-70be-4a2l-a039"}'
            ),
        )

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "DONE"
        assert check.verify_url == f"https://ude.my/{credential_id}"
        assert check.page_name is None  # ude.my allowlist'te değil — otomatik çekilmedi

    @pytest.mark.parametrize(
        "credential_id",
        [None, 12345, "", "UC-123", "ABC123", "UC-abc/../../evil", "UC-12345678?x=1", "https://evil.example/UC-12345678"],
    )
    def test_udemy_verify_url_rejects_ids_without_udemy_shape(self, credential_id):
        assert outbox_worker._udemy_verify_url(credential_id) is None

    def test_udemy_verify_url_accepts_short_legacy_id(self):
        assert outbox_worker._udemy_verify_url(" UC-4X6T2Q1Z ") == "https://ude.my/UC-4X6T2Q1Z"

    def test_coursera_credential_id_never_produces_udemy_link(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        monkeypatch.setattr(outbox_worker, "_fetch_official_page", lambda url: (None, None))
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "UC-ABCDEFGH", '
                '"extracted_name": null, "verify_url": "https://coursera.org/verify/UC-ABCDEFGH"}'
            ),
        )

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.verify_url == "https://coursera.org/verify/UC-ABCDEFGH"

    def test_malformed_model_output_marks_failed_not_error(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(monkeypatch, body=_chat_response("bu bir sertifika gibi görünüyor"))

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "FAILED"
        assert check.decision == "PENDING"

    def test_http_error_propagates_so_outbox_retries(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(monkeypatch, status_code=500, body=_chat_response(""))

        with pytest.raises(Exception):
            outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "PENDING"

    def test_missing_object_marks_failed(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(None)
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response("{}"))

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "FAILED"
        assert calls == []  # never reaches the model if the object is missing

    def test_redelivery_of_already_processed_row_is_noop(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        check.status = "DONE"
        session.flush()
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response("{}"))
        handler_env(_blank_png())

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert calls == []

    def test_unknown_check_id_is_noop(self, handler_env, monkeypatch):
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response("{}"))
        handler_env(_blank_png())

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(uuid.uuid4())}, 1)

        assert calls == []

    def test_jpeg_upload_is_reencoded_to_real_png_before_sending(self, session, talent_cc, handler_env, monkeypatch):
        """Canlı bulgu: JPEG bytes'ı ham haliyle 'image/png' etiketiyle gönderirsek
        sağlayıcı (Anthropic) 400 ile reddediyor ('declared png but is jpeg').
        Her upload gerçek PNG'ye yeniden encode edilmeli — hangi mime_type ile
        yüklendiği fark etmeksizin."""
        import base64

        image = np.full((40, 40, 3), 128, dtype=np.uint8)
        ok, jpeg_buf = cv2.imencode(".jpg", image)
        assert ok
        jpeg_bytes = bytes(jpeg_buf)

        ev = _evidence(session, talent_cc, mime="image/jpeg")
        check = _pending_check(session, ev)
        handler_env(jpeg_bytes)
        calls = _install_fake_openrouter(
            monkeypatch, body=_chat_response('{"provider": "UDEMY", "credential_id": null, "extracted_name": null, "verify_url": null}')
        )

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert len(calls) == 1
        content_blocks = calls[0]["json"]["messages"][0]["content"]
        image_block = next(b for b in content_blocks if b["type"] == "image_url")
        data_url = image_block["image_url"]["url"]
        assert data_url.startswith("data:image/png;base64,")
        decoded = base64.b64decode(data_url.split(",", 1)[1])
        assert decoded.startswith(b"\x89PNG\r\n\x1a\n"), "gönderilen bytes gerçek PNG imzasıyla başlamalı"

        session.refresh(check)
        assert check.status == "DONE"

    def test_undecodable_image_marks_failed_without_calling_model(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc, mime="image/png")
        check = _pending_check(session, ev)
        handler_env(b"not a real image")
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response("{}"))

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert calls == []
        session.refresh(check)
        assert check.status == "FAILED"
