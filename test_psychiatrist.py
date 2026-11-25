"""Tests for the psychiatrist dashboard backend.

These never touch data/aegismind_persistent.db or Supabase: every test points the
local store at a temporary SQLite file and removes the Supabase settings first.
"""
import sqlite3

import pytest

PATIENT_TOKEN = "PATIENTTOKEN0001"
OTHER_TOKEN = "PATIENTTOKEN0002"


@pytest.fixture()
def clinician_app(tmp_path, monkeypatch):
    # Set to empty (not deleted): app.py loads the real .env on import and never overrides a variable that already exists
    for name in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY", "COUNSELOR_API_KEY", "GROQ_API_KEY", "CLINICIAN_EMAILS"):
        monkeypatch.setenv(name, "")

    import database
    monkeypatch.setattr(database, "SQLITE_PATH", str(tmp_path / "psychiatrist_test.db"))
    database.init_sqlite_tables()

    # If app.py is imported for the first time here it initialises the temporary database
    import app as aegis_app
    monkeypatch.setattr(database, "_supabase_client", None)
    monkeypatch.setattr(aegis_app.Config, "COUNSELOR_API_KEY", "")
    monkeypatch.setattr(aegis_app.Config, "CLINICIAN_EMAILS", frozenset())
    monkeypatch.setattr(aegis_app.Config, "IS_PRODUCTION", False)
    monkeypatch.setattr(aegis_app.Config, "GROQ_API_KEY", "")  # keeps chat tests off the network
    aegis_app.rate_limiter._requests.clear()
    return aegis_app


def add_case(db, case_id, token, alias, sev, risk_level, source="checkin", triggers=None):
    db.upsert_profile(user_id=token, alias=alias, consent=True)
    return db.save_counselor_case({
        "id": case_id, "token": token, "alias": alias, "sev": sev, "risk_level": risk_level,
        "source": source, "dpi": 0.8, "delta_dpi": 0.1, "triggers": triggers or ["low_valence"],
        "text_fragment": "sample text", "reviewed": False,
    })


def test_old_database_gets_the_new_case_columns(tmp_path, monkeypatch):
    import database
    old_db_path = tmp_path / "old.db"
    with sqlite3.connect(old_db_path) as conn:
        conn.execute("CREATE TABLE counselor_cases (id TEXT PRIMARY KEY, user_id TEXT, alias TEXT, dpi REAL NOT NULL, "
                     "delta_dpi REAL NOT NULL, risk_level TEXT NOT NULL, triggers TEXT, text_fragment TEXT, "
                     "jitsi_room TEXT, reviewed INTEGER DEFAULT 0, reviewed_at TEXT, sev TEXT DEFAULT 'SEV-2', flagged_at TEXT)")
    monkeypatch.setattr(database, "SQLITE_PATH", str(old_db_path))

    database.init_sqlite_tables()

    with sqlite3.connect(old_db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(counselor_cases)")}
    assert {"source", "status", "notes", "acknowledged_at"} <= columns


def test_alerts_list_sev1_first_and_counts_match(clinician_app):
    db = clinician_app.db
    add_case(db, "CASE0001", PATIENT_TOKEN, "GentleEmber77", "SEV-2", "moderate")
    add_case(db, "CASE0002", OTHER_TOKEN, "QuietWillow42", "SEV-1", "critical", source="chat")

    alerts = db.get_psychiatrist_alerts()
    counts = db.get_psychiatrist_counts()

    assert [alert["id"] for alert in alerts] == ["CASE0002", "CASE0001"]
    assert alerts[0]["source"] == "chat"
    assert counts["open_sev1"] == 1 and counts["open_sev2"] == 1 and counts["unacknowledged"] == 2


def test_clinician_never_sees_the_real_user_id(clinician_app):
    db = clinician_app.db
    add_case(db, "CASE0003", PATIENT_TOKEN, "SteadyRiver18", "SEV-1", "critical")
    db.save_checkin(PATIENT_TOKEN, "I feel awful", 3, 8, 0.4, {"fp_density": 0.2}, 0.8, 0.1, "critical")

    patient = db.get_psychiatrist_patients()[0]
    detail = db.get_psychiatrist_patient_detail(patient["patient_ref"])

    assert PATIENT_TOKEN not in str(db.get_psychiatrist_alerts())
    assert PATIENT_TOKEN not in str(patient)
    assert PATIENT_TOKEN not in str(detail)
    assert detail["alias"] == "SteadyRiver18" and detail["risk_level"] == "critical"
    assert detail["checkins"][0]["nlp"] == {"fp_density": 0.2}
    assert db.get_psychiatrist_patient_detail("doesnotexist0000") is None


def test_patients_with_open_emergencies_are_listed_first(clinician_app):
    db = clinician_app.db
    db.upsert_profile(user_id=OTHER_TOKEN, alias="CalmPatient11", consent=True)
    db.save_checkin(OTHER_TOKEN, "all good", 8, 5, 0.9, {}, 0.1, 0.0, "low")
    add_case(db, "CASE0004", PATIENT_TOKEN, "UrgentPatient22", "SEV-1", "critical")

    aliases = [patient["alias"] for patient in db.get_psychiatrist_patients()]

    assert aliases == ["UrgentPatient22", "CalmPatient11"]


def test_open_access_in_local_development_without_a_code(clinician_app):
    client = clinician_app.app.test_client()

    assert client.get("/api/psychiatrist/alerts").status_code == 200
    assert client.get("/api/psychiatrist/session").get_json()["authenticated"] is True


def test_patient_session_cannot_read_clinician_data_when_a_code_is_set(clinician_app, monkeypatch):
    monkeypatch.setattr(clinician_app.Config, "COUNSELOR_API_KEY", "clinic-secret-code")
    client = clinician_app.app.test_client()
    with client.session_transaction() as flask_session:
        flask_session["user_id"] = PATIENT_TOKEN  # a normal signed-in patient

    assert client.get("/api/psychiatrist/alerts").status_code == 401
    assert client.get("/api/psychiatrist/patients").status_code == 401
    assert client.post("/api/psychiatrist/cases/X", json={"status": "resolved"}).status_code == 401
    assert client.get("/api/psychiatrist/alerts", headers={"X-Counselor-Key": "wrong"}).status_code == 401
    assert client.get("/api/psychiatrist/alerts", headers={"X-Counselor-Key": "clinic-secret-code"}).status_code == 200


def test_clinician_login_with_the_access_code(clinician_app, monkeypatch):
    monkeypatch.setattr(clinician_app.Config, "COUNSELOR_API_KEY", "clinic-secret-code")
    client = clinician_app.app.test_client()

    assert client.post("/api/psychiatrist/login", json={"access_code": "nope"}).status_code == 401
    assert client.get("/api/psychiatrist/alerts").status_code == 401
    assert client.post("/api/psychiatrist/login", json={"access_code": "clinic-secret-code"}).status_code == 200
    assert client.get("/api/psychiatrist/alerts").status_code == 200
    client.post("/api/psychiatrist/logout")
    assert client.get("/api/psychiatrist/alerts").status_code == 401


def test_production_without_an_access_code_stays_locked(clinician_app, monkeypatch):
    monkeypatch.setattr(clinician_app.Config, "IS_PRODUCTION", True)
    client = clinician_app.app.test_client()

    assert client.get("/api/psychiatrist/alerts").status_code == 401


def test_crisis_phrase_in_chat_raises_a_sev1_case_for_the_psychiatrist(clinician_app):
    db = clinician_app.db
    db.upsert_profile(user_id=PATIENT_TOKEN, alias="QuietWillow42", consent=True)
    client = clinician_app.app.test_client()

    chat_response = client.post("/api/chat", json={"token": PATIENT_TOKEN, "message": "i want to die", "lang": "en"})
    alerts = client.get("/api/psychiatrist/alerts").get_json()["alerts"]
    detail = client.get(f"/api/psychiatrist/patients/{alerts[0]['patient_ref']}").get_json()

    assert chat_response.get_json()["is_crisis"] is True
    assert len(alerts) == 1
    assert alerts[0]["sev"] == "SEV-1" and alerts[0]["source"] == "chat" and alerts[0]["alias"] == "QuietWillow42"
    assert [turn["crisis"] for turn in detail["chat"]] == [True, False]


def test_a_calm_chat_message_does_not_raise_a_case(clinician_app):
    client = clinician_app.app.test_client()

    client.post("/api/chat", json={"token": PATIENT_TOKEN, "message": "thanks, that helped", "lang": "en"})

    assert client.get("/api/psychiatrist/alerts").get_json()["alerts"] == []


def test_case_goes_from_new_to_acknowledged_to_resolved_with_a_note(clinician_app):
    db = clinician_app.db
    add_case(db, "CASE0005", PATIENT_TOKEN, "WarmHarbor31", "SEV-1", "critical")
    client = clinician_app.app.test_client()

    acknowledged = client.post("/api/psychiatrist/cases/CASE0005", json={"status": "acknowledged"}).get_json()
    noted = client.post("/api/psychiatrist/cases/CASE0005", json={"notes": "  Called the family.  "}).get_json()
    still_open = client.get("/api/psychiatrist/alerts").get_json()
    resolved = client.post("/api/psychiatrist/cases/CASE0005", json={"status": "resolved"}).get_json()
    after_resolve = client.get("/api/psychiatrist/alerts").get_json()

    assert acknowledged["status"] == "acknowledged" and acknowledged["acknowledged_at"]
    assert noted["notes"] == "Called the family." and noted["status"] == "acknowledged"
    assert still_open["counts"]["unacknowledged"] == 0 and len(still_open["alerts"]) == 1
    assert resolved["status"] == "resolved" and resolved["reviewed"] is True
    assert after_resolve["alerts"] == [] and after_resolve["counts"]["resolved_today"] == 1


def test_case_update_rejects_bad_input(clinician_app):
    add_case(clinician_app.db, "CASE0006", PATIENT_TOKEN, "SoftCompass53", "SEV-2", "moderate")
    client = clinician_app.app.test_client()

    assert client.post("/api/psychiatrist/cases/CASE0006", json={"status": "deleted"}).status_code == 400
    assert client.post("/api/psychiatrist/cases/CASE0006", json={"notes": "x" * 2001}).status_code == 400
    assert client.post("/api/psychiatrist/cases/CASE0006", json={}).status_code == 400
    assert client.post("/api/psychiatrist/cases/NOSUCHCASE", json={"status": "acknowledged"}).status_code == 404
    assert client.get("/api/psychiatrist/patients/doesnotexist0000").status_code == 404


def test_dashboard_page_renders(clinician_app):
    response = clinician_app.app.test_client().get("/psychiatrist")

    assert response.status_code == 200
    assert "Clinician Console" in response.text
    assert "psychiatrist.js" in response.text
    assert "panel-alerts" in response.text and "panel-patient" in response.text


class RecordingSupabase:
    """Stands in for the Supabase client: remembers what would be sent, never touches the network."""

    def __init__(self):
        self.sent = []  # (action, table, payload, filters)

    def from_(self, table):
        return _RecordingQuery(self, table)


class _RecordingQuery:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.action, self.payload, self.filters = None, None, []

    def insert(self, payload):
        self.action, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.action, self.payload = "update", payload
        return self

    def upsert(self, payload, **_):
        self.action, self.payload = "upsert", payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def execute(self):
        self.client.sent.append((self.action, self.table, self.payload, self.filters))
        return type("Result", (), {"data": []})()


def test_new_case_is_sent_to_supabase_with_its_source(clinician_app, monkeypatch):
    fake_supabase = RecordingSupabase()
    monkeypatch.setattr(clinician_app.db, "_supabase_client", fake_supabase)

    add_case(clinician_app.db, "CASE0007", PATIENT_TOKEN, "WarmHarbor31", "SEV-1", "critical", source="chat")

    case_inserts = [sent for sent in fake_supabase.sent if sent[0] == "insert" and sent[1] == "counselor_cases"]
    assert len(case_inserts) == 1
    assert case_inserts[0][2]["source"] == "chat" and case_inserts[0][2]["sev"] == "SEV-1"


def test_case_progress_is_sent_to_supabase(clinician_app, monkeypatch):
    add_case(clinician_app.db, "CASE0008", PATIENT_TOKEN, "GentleEmber77", "SEV-2", "moderate")
    fake_supabase = RecordingSupabase()
    monkeypatch.setattr(clinician_app.db, "_supabase_client", fake_supabase)

    clinician_app.db.update_psychiatrist_case("CASE0008", status="acknowledged", notes="Called the family.")

    progress_updates = [sent for sent in fake_supabase.sent if sent[0] == "update" and "status" in sent[2]]
    assert len(progress_updates) == 1
    payload, filters = progress_updates[0][2], progress_updates[0][3]
    assert payload["status"] == "acknowledged" and payload["notes"] == "Called the family."
    assert payload["acknowledged_at"]
    assert filters == [("id", "CASE0008")]


# ---------------------------------------------------------------------------
# Personal clinician accounts (email + password, approved by CLINICIAN_EMAILS)
# ---------------------------------------------------------------------------

APPROVED_EMAIL = "dr.rao@clinic.org"


@pytest.fixture()
def clinician_accounts(clinician_app, monkeypatch):
    """Approved clinician emails plus a stand-in for Supabase's password check (no network)."""
    monkeypatch.setattr(clinician_app.Config, "CLINICIAN_EMAILS", frozenset({APPROVED_EMAIL}))
    accounts_in_supabase = {APPROVED_EMAIL: "right-password", "patient@gmail.com": "patient-pass"}
    monkeypatch.setattr(
        clinician_app, "check_clinician_account",
        lambda email, password: email if accounts_in_supabase.get(email) == password else None,
    )
    return clinician_app


def test_approved_clinician_signs_in_with_email_and_password(clinician_accounts):
    client = clinician_accounts.app.test_client()
    assert client.get("/api/psychiatrist/session").get_json()["authenticated"] is False
    assert client.get("/api/psychiatrist/alerts").status_code == 401

    response = client.post("/api/psychiatrist/login", json={"email": "  Dr.Rao@Clinic.org ", "password": "right-password"})

    assert response.status_code == 200 and response.get_json()["clinician_email"] == APPROVED_EMAIL
    assert client.get("/api/psychiatrist/alerts").status_code == 200
    session_info = client.get("/api/psychiatrist/session").get_json()
    assert session_info["authenticated"] is True and session_info["clinician_email"] == APPROVED_EMAIL
    assert session_info["sign_in_methods"]["account"] is True

    client.post("/api/psychiatrist/logout")
    assert client.get("/api/psychiatrist/alerts").status_code == 401
    assert client.get("/api/psychiatrist/session").get_json()["clinician_email"] == ""


def test_wrong_password_and_unapproved_account_get_the_same_refusal(clinician_accounts):
    client = clinician_accounts.app.test_client()

    wrong_password = client.post("/api/psychiatrist/login", json={"email": APPROVED_EMAIL, "password": "nope"})
    real_account_not_approved = client.post("/api/psychiatrist/login", json={"email": "patient@gmail.com", "password": "patient-pass"})

    assert wrong_password.status_code == real_account_not_approved.status_code == 401
    assert wrong_password.get_json() == real_account_not_approved.get_json()
    assert client.get("/api/psychiatrist/alerts").status_code == 401


def test_email_sign_in_says_so_when_no_clinician_emails_are_configured(clinician_app):
    response = clinician_app.app.test_client().post("/api/psychiatrist/login", json={"email": APPROVED_EMAIL, "password": "x"})

    assert response.status_code == 503
    assert response.get_json()["error"] == "clinician_accounts_not_set_up"


def test_configuring_clinician_emails_closes_open_development_access(clinician_accounts):
    # No access code is set here, yet the dashboard is no longer open to anyone
    client = clinician_accounts.app.test_client()

    assert client.get("/api/psychiatrist/session").get_json()["development_open_access"] is False
    assert client.get("/api/psychiatrist/patients").status_code == 401


def test_production_accepts_accounts_but_not_the_shared_access_code(clinician_accounts, monkeypatch):
    monkeypatch.setattr(clinician_accounts.Config, "IS_PRODUCTION", True)
    monkeypatch.setattr(clinician_accounts.Config, "COUNSELOR_API_KEY", "clinic-secret-code")
    client = clinician_accounts.app.test_client()

    by_code = client.post("/api/psychiatrist/login", json={"access_code": "clinic-secret-code"})
    assert by_code.status_code == 401
    assert client.get("/api/psychiatrist/session").get_json()["sign_in_methods"]["access_code"] is False

    by_account = client.post("/api/psychiatrist/login", json={"email": APPROVED_EMAIL, "password": "right-password"})
    assert by_account.status_code == 200
    assert client.get("/api/psychiatrist/alerts").status_code == 200


def test_password_check_is_refused_when_supabase_is_not_configured(clinician_app, monkeypatch):
    monkeypatch.setattr(clinician_app, "supabase_url", "")
    monkeypatch.setattr(clinician_app, "supabase_anon_key", "")

    assert clinician_app.check_clinician_account(APPROVED_EMAIL, "right-password") is None


# ---------------------------------------------------------------------------
# Clinician self-registration (approved email + setup code, no patient profile)
# ---------------------------------------------------------------------------

SETUP_CODE = "clinic-setup-code"


@pytest.fixture()
def clinician_registration(clinician_accounts, monkeypatch):
    """Registration switched on, with a stand-in for creating the Supabase login (no network)."""
    monkeypatch.setattr(clinician_accounts.Config, "COUNSELOR_API_KEY", SETUP_CODE)
    monkeypatch.setattr(clinician_accounts, "supabase", object())  # only needs to be "connected"
    created_logins = []

    def fake_create(email, password):
        if email == "already.there@clinic.org":
            return "already_exists"
        created_logins.append((email, password))
        return "created"

    monkeypatch.setattr(clinician_accounts, "create_clinician_account", fake_create)
    clinician_accounts.created_logins = created_logins
    return clinician_accounts


def register_clinician(client, **overrides):
    details = {"email": APPROVED_EMAIL, "password": "a-good-password", "setup_code": SETUP_CODE, **overrides}
    return client.post("/api/psychiatrist/register", json=details)


def test_approved_clinician_can_create_their_account(clinician_registration):
    client = clinician_registration.app.test_client()
    assert client.get("/api/psychiatrist/session").get_json()["sign_in_methods"]["registration"] is True

    response = register_clinician(client, email="  Dr.Rao@Clinic.org ")

    assert response.status_code == 201
    assert clinician_registration.created_logins == [(APPROVED_EMAIL, "a-good-password")]
    # Creating the login does not sign anyone in or open patient data
    assert client.get("/api/psychiatrist/alerts").status_code == 401


def test_registration_refuses_wrong_setup_code_and_unapproved_email_alike(clinician_registration):
    client = clinician_registration.app.test_client()

    wrong_code = register_clinician(client, setup_code="guess")
    not_approved = register_clinician(client, email="someone.else@gmail.com")

    assert wrong_code.status_code == not_approved.status_code == 403
    assert wrong_code.get_json() == not_approved.get_json()
    assert clinician_registration.created_logins == []


def test_registration_rejects_short_passwords_and_existing_accounts(clinician_registration, monkeypatch):
    client = clinician_registration.app.test_client()
    assert register_clinician(client, password="short").status_code == 400

    monkeypatch.setattr(clinician_registration.Config, "CLINICIAN_EMAILS", frozenset({"already.there@clinic.org"}))
    existing = register_clinician(client, email="already.there@clinic.org")
    assert existing.status_code == 409 and existing.get_json()["error"] == "account_exists"


def test_registration_is_off_without_a_setup_code_or_supabase(clinician_accounts, monkeypatch):
    client = clinician_accounts.app.test_client()
    # clinician_accounts has approved emails but no setup code and no Supabase connection
    assert register_clinician(client).status_code == 503
    assert client.get("/api/psychiatrist/session").get_json()["sign_in_methods"]["registration"] is False

    monkeypatch.setattr(clinician_accounts.Config, "COUNSELOR_API_KEY", SETUP_CODE)
    assert register_clinician(client).status_code == 503  # still no Supabase


def test_creating_a_clinician_login_makes_no_patient_profile(clinician_app, monkeypatch):
    created_users = []

    class FakeAdmin:
        def create_user(self, attributes):
            created_users.append(attributes)

    fake_supabase = type("FakeSupabase", (), {"auth": type("FakeAuth", (), {"admin": FakeAdmin()})()})()
    monkeypatch.setattr(clinician_app, "supabase", fake_supabase)
    profiles_before = clinician_app.db.get_profile_by_id(APPROVED_EMAIL)

    outcome = clinician_app.create_clinician_account(APPROVED_EMAIL, "a-good-password")

    assert outcome == "created" and profiles_before is None
    assert created_users[0]["email_confirm"] is True and created_users[0]["user_metadata"] == {"role": "clinician"}
    assert clinician_app.db.get_profile_by_id(APPROVED_EMAIL) is None
