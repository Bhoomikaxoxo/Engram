import json
from datetime import UTC

import pytest

from sdks.python.src.engram.client import Engram


@pytest.mark.asyncio
async def test_session_upload_file(
    client_fixture: tuple[Engram, str],
):
    """
    Tests uploading a single file to a session.
    """
    engram_client, client_type = client_fixture

    # Create test file
    text_content = (
        "This is a test text file.\nIt has multiple lines.\nFor testing purposes."
    )

    # Create file object for testing the flexible interface
    from io import BytesIO

    text_file = BytesIO(text_content.encode("utf-8"))
    text_file.name = "test.txt"

    # Handle sync and async clients separately
    if client_type == "async":
        session = await engram_client.aio.session(id="test-session-upload")
        user = await engram_client.aio.peer(id="user-upload")
        messages = await session.aio.upload_file(
            file=text_file,
            peer=user.id,
        )
    else:
        session = engram_client.session(id="test-session-upload")
        user = engram_client.peer(id="user-upload")
        messages = session.upload_file(
            file=text_file,
            peer=user.id,
        )

    # Verify messages were created
    assert len(messages) >= 1

    # Check first message (text file)
    assert text_content in messages[0].content
    assert messages[0].peer_id == user.id
    assert messages[0].session_id == session.id


@pytest.mark.asyncio
async def test_large_file_chunking(
    client_fixture: tuple[Engram, str],
):
    """
    Tests that large files get split into multiple messages automatically.
    """
    engram_client, client_type = client_fixture

    # Create a large text file that will require chunking
    large_content = "This is a test line.\n" * 3000  # Should exceed 49500 chars

    # Create file object for testing the flexible interface
    from io import BytesIO

    large_file = BytesIO(large_content.encode("utf-8"))
    large_file.name = "large_test.txt"

    # Handle sync and async clients separately
    if client_type == "async":
        session = await engram_client.aio.session(id="test-session-chunking")
        user = await engram_client.aio.peer(id="user-chunking")
        messages = await session.aio.upload_file(
            file=large_file,
            peer=user.id,
        )
    else:
        session = engram_client.session(id="test-session-chunking")
        user = engram_client.peer(id="user-chunking")
        messages = session.upload_file(
            file=large_file,
            peer=user.id,
        )

    # Should be multiple messages due to chunking
    assert len(messages) > 1

    # All messages should have the same peer_id and session_id
    for message in messages:
        assert message.peer_id == user.id
        assert message.session_id == session.id


@pytest.mark.asyncio
async def test_multiple_files_upload(
    client_fixture: tuple[Engram, str],
):
    """
    Tests uploading multiple files one by one.
    """
    engram_client, client_type = client_fixture

    # Create multiple files
    file1_content = "Content of first file"
    file2_content = "Content of second file"
    file3_content = "Content of third file"

    # Create file objects for testing the flexible interface
    from io import BytesIO

    file1 = BytesIO(file1_content.encode("utf-8"))
    file1.name = "file1.txt"

    file2 = BytesIO(file2_content.encode("utf-8"))
    file2.name = "file2.txt"

    file3 = BytesIO(file3_content.encode("utf-8"))
    file3.name = "file3.txt"

    # Handle sync and async clients separately
    if client_type == "async":
        session = await engram_client.aio.session(id="test-session-multiple")
        user = await engram_client.aio.peer(id="user-multiple")
        messages1 = await session.aio.upload_file(file=file1, peer=user.id)
        messages2 = await session.aio.upload_file(file=file2, peer=user.id)
        messages3 = await session.aio.upload_file(file=file3, peer=user.id)
    else:
        session = engram_client.session(id="test-session-multiple")
        user = engram_client.peer(id="user-multiple")
        messages1 = session.upload_file(file=file1, peer=user.id)
        messages2 = session.upload_file(file=file2, peer=user.id)
        messages3 = session.upload_file(file=file3, peer=user.id)

    # Should be at least one message per file
    assert len(messages1) >= 1
    assert len(messages2) >= 1
    assert len(messages3) >= 1

    # Check that all files were processed
    assert file1_content in messages1[0].content
    assert file2_content in messages2[0].content
    assert file3_content in messages3[0].content

    # All messages should have correct peer_id and session_id
    for messages in [messages1, messages2, messages3]:
        for message in messages:
            assert message.peer_id == user.id
            assert message.session_id == session.id


@pytest.mark.asyncio
async def test_json_file_upload(client_fixture: tuple[Engram, str]):
    """
    Tests uploading JSON files specifically.
    """
    engram_client, client_type = client_fixture

    # Create JSON file
    json_data = {
        "name": "test_json",
        "values": [1, 2, 3, 4, 5],
        "nested": {"key": "value", "array": ["a", "b", "c"]},
        "boolean": True,
        "null_value": None,
    }
    json_content = json.dumps(json_data)

    # Create file object for testing the flexible interface
    from io import BytesIO

    json_file = BytesIO(json_content.encode("utf-8"))
    json_file.name = "test.json"

    # Handle sync and async clients separately
    if client_type == "async":
        session = await engram_client.aio.session(id="test-session-json")
        user = await engram_client.aio.peer(id="user-json")
        messages = await session.aio.upload_file(
            file=json_file,
            peer=user.id,
        )
    else:
        session = engram_client.session(id="test-session-json")
        user = engram_client.peer(id="user-json")
        messages = session.upload_file(
            file=json_file,
            peer=user.id,
        )

    # Should create at least one message
    assert len(messages) >= 1

    # Check that JSON content is properly formatted in the message
    message_content = messages[0].content
    assert '"name": "test_json"' in message_content
    assert '"values": [1, 2, 3, 4, 5]' in message_content
    assert '"nested": {' in message_content
    assert '"key": "value"' in message_content
    assert '"array": ["a", "b", "c"]' in message_content
    assert '"boolean": true' in message_content
    assert '"null_value": null' in message_content

    assert messages[0].peer_id == user.id
    assert messages[0].session_id == session.id


@pytest.mark.asyncio
async def test_file_upload_with_tuple_input(
    client_fixture: tuple[Engram, str],
):
    """
    Tests uploading files using tuple input format.
    """
    engram_client, client_type = client_fixture

    # Create test content
    content = "This is test content for tuple input"
    filename = "tuple_test.txt"
    content_type = "text/plain"

    # Handle sync and async clients separately
    if client_type == "async":
        session = await engram_client.aio.session(id="test-session-tuple")
        user = await engram_client.aio.peer(id="user-tuple")
        messages = await session.aio.upload_file(
            file=(filename, content.encode("utf-8"), content_type),
            peer=user.id,
        )
    else:
        session = engram_client.session(id="test-session-tuple")
        user = engram_client.peer(id="user-tuple")
        messages = session.upload_file(
            file=(filename, content.encode("utf-8"), content_type),
            peer=user.id,
        )

    # Should create at least one message
    assert len(messages) >= 1
    assert content in messages[0].content
    assert messages[0].peer_id == user.id
    assert messages[0].session_id == session.id


@pytest.mark.asyncio
async def test_file_upload_with_metadata(
    client_fixture: tuple[Engram, str],
):
    """
    Tests uploading a file with metadata parameter.
    """
    engram_client, client_type = client_fixture

    text_content = "Test file with metadata"
    from io import BytesIO

    text_file = BytesIO(text_content.encode("utf-8"))
    text_file.name = "test_metadata.txt"

    metadata: dict[str, object] = {
        "source": "sdk_test",
        "category": "upload",
        "priority": 1,
    }

    if client_type == "async":
        session = await engram_client.aio.session(id="test-session-metadata")
        user = await engram_client.aio.peer(id="user-metadata")
        messages = await session.aio.upload_file(
            file=text_file,
            peer=user.id,
            metadata=metadata,
        )
    else:
        session = engram_client.session(id="test-session-metadata")
        user = engram_client.peer(id="user-metadata")
        messages = session.upload_file(
            file=text_file,
            peer=user.id,
            metadata=metadata,
        )

    assert len(messages) >= 1
    assert text_content in messages[0].content
    assert messages[0].peer_id == user.id
    assert messages[0].session_id == session.id
    # Check that metadata was applied
    assert messages[0].metadata == metadata


@pytest.mark.asyncio
async def test_file_upload_with_configuration(
    client_fixture: tuple[Engram, str],
):
    """
    Tests uploading a file with configuration parameter.
    """
    engram_client, client_type = client_fixture

    text_content = "Test file with configuration"
    from io import BytesIO

    text_file = BytesIO(text_content.encode("utf-8"))
    text_file.name = "test_config.txt"

    configuration = {"skip_deriver": True, "custom_flag": "test"}

    if client_type == "async":
        session = await engram_client.aio.session(id="test-session-config")
        user = await engram_client.aio.peer(id="user-config")
        messages = await session.aio.upload_file(
            file=text_file,
            peer=user.id,
            configuration=configuration,
        )
    else:
        session = engram_client.session(id="test-session-config")
        user = engram_client.peer(id="user-config")
        messages = session.upload_file(
            file=text_file,
            peer=user.id,
            configuration=configuration,
        )

    assert len(messages) >= 1
    assert text_content in messages[0].content
    assert messages[0].peer_id == user.id
    assert messages[0].session_id == session.id
    # Configuration is used during processing, not directly stored in message
    # This test confirms the endpoint accepts it without error


@pytest.mark.asyncio
async def test_file_upload_with_created_at(
    client_fixture: tuple[Engram, str],
):
    """
    Tests uploading a file with created_at parameter.
    """
    engram_client, client_type = client_fixture

    text_content = "Test file with created_at"
    from datetime import datetime
    from io import BytesIO

    text_file = BytesIO(text_content.encode("utf-8"))
    text_file.name = "test_timestamp.txt"

    test_timestamp = datetime(2023, 1, 15, 10, 30, 45, tzinfo=UTC)
    created_at_str = test_timestamp.isoformat()

    if client_type == "async":
        session = await engram_client.aio.session(id="test-session-timestamp")
        user = await engram_client.aio.peer(id="user-timestamp")
        messages = await session.aio.upload_file(
            file=text_file,
            peer=user.id,
            created_at=created_at_str,
        )
    else:
        session = engram_client.session(id="test-session-timestamp")
        user = engram_client.peer(id="user-timestamp")
        messages = session.upload_file(
            file=text_file,
            peer=user.id,
            created_at=test_timestamp.isoformat(),
        )

    assert len(messages) >= 1
    assert text_content in messages[0].content
    assert messages[0].peer_id == user.id
    assert messages[0].session_id == session.id
    # Check that created_at was applied (compare timestamps, allowing for small differences)
    # Message.created_at from engram_core is a datetime object
    message_timestamp = messages[0].created_at
    assert abs((message_timestamp - test_timestamp).total_seconds()) < 1


@pytest.mark.asyncio
async def test_file_upload_with_all_parameters(
    client_fixture: tuple[Engram, str],
):
    """
    Tests uploading a file with metadata, configuration, and created_at all together.
    """
    engram_client, client_type = client_fixture

    text_content = "Test file with all parameters"
    from datetime import datetime
    from io import BytesIO

    text_file = BytesIO(text_content.encode("utf-8"))
    text_file.name = "test_all_params.txt"

    metadata: dict[str, object] = {"source": "comprehensive_test", "version": "1.0"}
    configuration = {"skip_deriver": False, "test_mode": True}
    test_timestamp = datetime(2023, 6, 20, 14, 15, 30, tzinfo=UTC)
    created_at_str = test_timestamp.isoformat()

    if client_type == "async":
        session = await engram_client.aio.session(id="test-session-all")
        user = await engram_client.aio.peer(id="user-all")
        messages = await session.aio.upload_file(
            file=text_file,
            peer=user.id,
            metadata=metadata,
            configuration=configuration,
            created_at=created_at_str,
        )
    else:
        session = engram_client.session(id="test-session-all")
        user = engram_client.peer(id="user-all")
        messages = session.upload_file(
            file=text_file,
            peer=user.id,
            metadata=metadata,
            configuration=configuration,
            created_at=created_at_str,
        )

    assert len(messages) >= 1
    assert text_content in messages[0].content
    assert messages[0].peer_id == user.id
    assert messages[0].session_id == session.id
    # Check metadata
    assert messages[0].metadata == metadata
    # Check created_at
    # Message.created_at from engram_core is a datetime object
    message_timestamp = messages[0].created_at
    assert abs((message_timestamp - test_timestamp).total_seconds()) < 1


@pytest.mark.asyncio
async def test_file_upload_with_datetime_object(
    client_fixture: tuple[Engram, str],
):
    """
    Tests uploading a file with created_at as a datetime object (Python only).
    """
    engram_client, client_type = client_fixture

    text_content = "Test file with datetime object"
    from datetime import datetime
    from io import BytesIO

    text_file = BytesIO(text_content.encode("utf-8"))
    text_file.name = "test_datetime.txt"

    test_timestamp = datetime(2023, 3, 10, 8, 45, 20, tzinfo=UTC)

    if client_type == "async":
        session = await engram_client.aio.session(id="test-session-datetime")
        user = await engram_client.aio.peer(id="user-datetime")
        messages = await session.aio.upload_file(
            file=text_file, peer=user.id, created_at=test_timestamp
        )
    else:
        session = engram_client.session(id="test-session-datetime")
        user = engram_client.peer(id="user-datetime")
        messages = session.upload_file(
            file=text_file, peer=user.id, created_at=test_timestamp
        )

    assert len(messages) >= 1
    assert text_content in messages[0].content
    assert messages[0].peer_id == user.id
    assert messages[0].session_id == session.id
    # Check that created_at was applied
    # Message.created_at from engram_core is a datetime object
    message_timestamp = messages[0].created_at
    assert abs((message_timestamp - test_timestamp).total_seconds()) < 1
