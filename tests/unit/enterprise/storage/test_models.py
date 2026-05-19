from qwenpaw.enterprise.storage.models import ChatRow, JobRow


def test_chat_row_columns():
    columns = ChatRow.__table__.columns
    assert "id" in columns
    assert "agent_id" in columns
    assert "session_id" in columns
    assert "payload" in columns


def test_job_row_columns():
    columns = JobRow.__table__.columns
    assert "id" in columns
    assert "agent_id" in columns
    assert "payload" in columns
    assert "updated_at" in columns
