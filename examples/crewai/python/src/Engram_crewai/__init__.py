"""
Engram CrewAI Integration

This package provides seamless integration between Engram and CrewAI,
enabling AI agents to maintain persistent memory across conversations.

Example:
    ```python
    from engram_crewai import EngramMemoryStorage, EngramSearchTool, EngramGetContextTool, EngramDialecticTool
    from crewai import Agent, Task, Crew, Memory
    from engram import Engram

    # Initialize Engram client and CrewAI memory
    engram = Engram()
    storage = EngramMemoryStorage(
        peer_id="user123",
        session_id="session123",
        engram_client=engram,
    )
    memory = Memory(storage=storage)

    # Create tools for agents
    search_tool = EngramSearchTool(engram=engram, session_id=storage.session_id)
    context_tool = EngramGetContextTool(engram=engram, session_id=storage.session_id, peer_id="user123")
    dialectic_tool = EngramDialecticTool(engram=engram, session_id=storage.session_id, peer_id="user123")

    # Create agent with memory and tools
    agent = Agent(
        role="AI Assistant",
        goal="Help users with persistent memory",
        backstory="You remember past conversations.",
        tools=[search_tool, context_tool, dialectic_tool],
    )

    # Define a task for the crew
    task = Task(
        description="Help the user with their request",
        expected_output="A helpful response",
        agent=agent,
    )

    # Create crew with unified memory
    crew = Crew(
        agents=[agent],
        tasks=[task],
        memory=memory
    )
    ```
"""

from engram_crewai.exceptions import EngramDependencyError
from engram_crewai.storage import EngramMemoryStorage, EngramStorage
from engram_crewai.tools import (
    EngramDialecticTool,
    EngramGetContextTool,
    EngramSearchTool,
)

__version__ = "0.3.0"
__all__ = [
    "EngramDependencyError",
    "EngramDialecticTool",
    "EngramGetContextTool",
    "EngramMemoryStorage",
    "EngramSearchTool",
    "EngramStorage",
]
