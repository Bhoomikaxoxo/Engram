# Engram CrewAI Integration

Build CrewAI agents with persistent memory and reasoning capabilities powered by Engram.

## Installation

```bash
uv add engram-crewai crewai python-dotenv
```

CrewAI currently supports Python `>=3.10,<3.14`; this package follows the same range.

## Quick Start

```python
from crewai import Agent, Crew, Memory, Process, Task
from engram import Engram
from engram_crewai import EngramMemoryStorage

engram = Engram(workspace_id="crewai-demo")
storage = EngramMemoryStorage(
    peer_id="user-123",
    session_id="session-123",
    engram_client=engram,
)
memory = Memory(storage=storage)

memory.remember(
    "The user is learning Python and wants to build web applications.",
    scope="/users/user-123",
    categories=["preferences"],
    metadata={"source": "onboarding"},
)

agent = Agent(
    role="Programming Mentor",
    goal="Help users learn programming by remembering their interests and progress",
    backstory="You are a patient programming mentor.",
)

task = Task(
    description="Suggest a Python web project that matches the user's interests.",
    expected_output="A specific project suggestion with a brief explanation",
    agent=agent,
)

crew = Crew(
    agents=[agent],
    tasks=[task],
    process=Process.sequential,
    memory=memory,
)

result = crew.kickoff()
print(result.raw)
```

## Features

- `EngramMemoryStorage`: CrewAI unified `Memory` storage backend.
- `EngramStorage`: compatibility adapter for older CrewAI `ExternalMemory` usage.
- `EngramGetContextTool`, `EngramDialecticTool`, and `EngramSearchTool` for explicit Engram memory retrieval.
- Lazy Engram peer/session handles, matching the latest Engram SDK get-or-create behavior.

## Documentation

For comprehensive guides, examples, and API reference, visit:
**[https://engram.dev/docs/v3/integrations/crewai](https://engram.dev/docs/v3/integrations/crewai)**

## Examples

Check out complete examples in the [GitHub repository](https://github.com/plastic-labs/engram/tree/main/examples/crewai/python/examples).

## License

AGPL-3.0-or-later

## Support

- Report issues: [GitHub Issues](https://github.com/plastic-labs/engram/issues)
- Documentation: [engram.dev/docs](https://engram.dev/docs)
- Website: [engram.dev](https://engram.dev)
