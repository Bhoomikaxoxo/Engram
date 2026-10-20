"""
Tests for Engram CrewAI tools.
"""

from engram_crewai import (
    EngramDialecticTool,
    EngramGetContextTool,
    EngramSearchTool,
)
from test_storage import FakeEngram


class TestGetContextTool:
    def test_initialization_is_lazy(self):
        engram = FakeEngram()

        tool = EngramGetContextTool(
            engram=engram,
            session_id="session-1",
            peer_id="user-1",
        )

        assert tool.name == "get_session_context"
        assert engram.session_calls == []

    def test_returns_formatted_context(self):
        engram = FakeEngram()
        peer = engram.peer("user-1")
        session = engram.session("session-1")
        session.add_messages([peer.message("Test message for context")])

        engram.session_calls.clear()
        tool = EngramGetContextTool(
            engram=engram,
            session_id="session-1",
            peer_id="user-1",
        )
        result = tool._run()

        assert "Messages (1)" in result
        assert "user-1: Test message for context" in result
        assert engram.session_calls == ["session-1"]


class TestDialecticTool:
    def test_initialization_is_lazy(self):
        engram = FakeEngram()

        tool = EngramDialecticTool(
            engram=engram,
            session_id="session-1",
            peer_id="user-1",
        )

        assert tool.name == "query_peer_knowledge"
        assert engram.peer_calls == []

    def test_returns_response(self):
        engram = FakeEngram()
        tool = EngramDialecticTool(
            engram=engram,
            session_id="session-1",
            peer_id="user-1",
        )

        result = tool._run(query="What does the user like?")

        assert "answer: What does the user like?" in result
        assert engram.peer_calls == ["user-1"]


class TestSearchTool:
    def test_initialization_is_lazy(self):
        engram = FakeEngram()

        tool = EngramSearchTool(engram=engram, session_id="session-1")

        assert tool.name == "search_session_messages"
        assert engram.session_calls == []

    def test_returns_formatted_results(self):
        engram = FakeEngram()
        peer = engram.peer("user-1")
        session = engram.session("session-1")
        session.add_messages([peer.message("I love pizza and pasta")])

        engram.session_calls.clear()
        tool = EngramSearchTool(engram=engram, session_id="session-1")
        result = tool._run(query="food", limit=5)

        assert "Search Results" in result
        assert "[user-1] I love pizza and pasta" in result
        assert engram.session_calls == ["session-1"]


class TestToolsWorkTogether:
    def test_all_tools_in_same_session(self):
        engram = FakeEngram()
        peer = engram.peer("user-1")
        session = engram.session("session-1")
        session.add_messages([peer.message("I enjoy coding in Python")])

        context_tool = EngramGetContextTool(
            engram=engram,
            session_id="session-1",
            peer_id="user-1",
        )
        dialectic_tool = EngramDialecticTool(
            engram=engram,
            session_id="session-1",
            peer_id="user-1",
        )
        search_tool = EngramSearchTool(engram=engram, session_id="session-1")

        assert context_tool._run()
        assert dialectic_tool._run(query="What does the user like?")
        assert search_tool._run(query="coding", limit=5)
