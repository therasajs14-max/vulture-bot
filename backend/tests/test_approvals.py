"""Vulture Bot - Unit and Integration Tests for Approval and Email Automation."""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.session import Base
from app.database.models.user import User
from app.database.models.file import Dataset, DatasetRecord
from app.database.models.email import EmailDraft, ApprovalRecord
from app.approvals.service import ApprovalService
from app.email.service import PersonalizationEngine, MockEmailProvider


@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


def test_personalization_engine():
    template = "Dear {name}, your register number is {register_number} in {department} department."
    student = {
        "name": "Aarav Sharma",
        "register_number": "REG2021001",
        "department": "AI & DS",
    }
    rendered = PersonalizationEngine.render(template, student)
    assert rendered == "Dear Aarav Sharma, your register number is REG2021001 in AI & DS department."

    # Test missing fields fallback cleanly without error
    rendered_fallback = PersonalizationEngine.render("Hello {name}, welcome!", {})
    assert rendered_fallback == "Hello Student, welcome!"


@pytest.mark.asyncio
async def test_mock_email_provider():
    provider = MockEmailProvider()
    assert provider.name == "mock"

    res = await provider.send_email(
        to_email="test@college.edu",
        subject="Project Guidelines",
        body_text="Please submit by Friday.",
        recipient_name="Test Student",
    )
    assert res.success is True
    assert res.provider_message_id is not None
    assert len(provider.sent_messages) == 1
    assert provider.sent_messages[0]["to_email"] == "test@college.edu"


@pytest.mark.asyncio
async def test_admin_approval_and_invalidation(test_db: AsyncSession):
    # 1. Create admin and standard user
    admin = User(
        id=str(uuid.uuid4()),
        email="admin@vulture.local",
        name="Administrator",
        is_admin=True,
    )
    regular_user = User(
        id=str(uuid.uuid4()),
        email="student@vulture.local",
        name="Student User",
        is_admin=False,
    )
    test_db.add_all([admin, regular_user])

    # 2. Create sample dataset and records
    dataset = Dataset(
        id=str(uuid.uuid4()),
        file_id="dummy-file-id",
        user_id=admin.id,
        name="Final Year AI & DS",
        columns_json='["Name", "Email", "Department"]',
        total_rows=2,
        valid_rows=2,
        status="imported",
    )
    test_db.add(dataset)
    await test_db.flush()

    rec1 = DatasetRecord(
        dataset_id=dataset.id,
        row_number=1,
        data_json='{}',
        name="Aarav Sharma",
        email="aarav@college.edu",
        department="AI & DS",
        is_valid=True,
    )
    rec2 = DatasetRecord(
        dataset_id=dataset.id,
        row_number=2,
        data_json='{}',
        name="Diya Patel",
        email="diya@college.edu",
        department="AI & DS",
        is_valid=True,
    )
    test_db.add_all([rec1, rec2])

    # 3. Create Draft
    draft = EmailDraft(
        id=str(uuid.uuid4()),
        user_id=admin.id,
        dataset_id=dataset.id,
        task_name="Project Review Task",
        subject="Important Review Submission Guidelines",
        body_template="Dear {name}, please submit your final year project by Friday.",
        is_personalized=True,
        status="draft",
    )
    test_db.add(draft)
    await test_db.commit()

    # 4. Standard user cannot approve
    with pytest.raises(PermissionError):
        await ApprovalService.approve_draft(test_db, draft.id, regular_user)

    # 5. Admin can approve
    approval = await ApprovalService.approve_draft(test_db, draft.id, admin, "Approved for dispatch.")
    assert approval.status == "approved"
    assert approval.approved_recipient_count == 2
    assert approval.approved_content_hash is not None

    # 6. Execute batch successfully
    batch = await ApprovalService.execute_batch(test_db, draft.id, admin)
    assert batch.status == "completed"
    assert batch.sent_count == 2
    assert batch.failed_count == 0
