# Engram Python SDK

The official Python library for the [Engram](https://github.com/plastic-labs/engram) conversational memory platform. Engram provides tools for managing peers, sessions, and conversation context across multi-party interactions, enabling advanced conversational AI applications with persistent memory and theory-of-mind capabilities.

## Installation

```bash
pip install engram-ai
```

## Quick Start

```python
from engram import Engram

# Initialize client
client = Engram(api_key="your-api-key")

# Create peers (participants in conversations)
alice = client.peer("alice")
bob = client.peer("bob")

# Create a session for group conversations
session = client.session("conversation-1")

# Add messages to the session
session.add_messages([
    alice.message("Hello, Bob!"),
    bob.message("Hi Alice, how are you?")
])

# Query conversation context
response = alice.chat("What did Bob say to the user?")
print(response)
```

## Core Concepts

### Peers

Peers represent participants in conversations.

```python
# Create peers
assistant = client.peer("assistant")
user = client.peer("user-123")

# Chat with global context
response = user.chat("What did I talk about yesterday?")

# Chat with perspective of another peer
response = user.chat("Does the assistant know my preferences?", target=assistant)
```

### Sessions

Sessions group related conversations and messages:

```python
# Create a session
session = client.session("project-discussion")

# Add peers to session
session.add_peers([alice, bob])

# Add messages
session.add_messages([
    alice.message("Let's discuss the project timeline"),
    bob.message("I think we need two more weeks")
])

# Get conversation context
context = session.context()
```

### Messages and Context

Retrieve and use conversation history:

```python
# Get messages from a session
messages = session.messages()

# Convert to OpenAI format for further prompting
openai_messages = context.to_openai(assistant="assistant")

# Convert to Anthropic format for further prompting
anthropic_messages = context.to_anthropic(assistant="assistant")
```

### Async Support

The SDK provides async access via the `.aio` accessor on any instance:

```python
from engram import Engram

async def main():
    client = Engram(api_key="your-api-key")

    # Async peer and session creation
    peer = await client.aio.peer("user-123")
    session = await client.aio.session("conversation-1")

    # Async chat
    response = await peer.aio.chat("What does this user prefer?")

    # Async iteration
    async for p in client.aio.peers():
        print(p.id)
```

### Metadata Management

```python
# Set peer metadata
user.set_metadata({"location": "San Francisco", "preferences": {"theme": "dark"}})

# Session metadata
session.set_metadata({"topic": "project-planning", "priority": "high"})
```

### Multi-Perspective Queries

```python
# Alice's view of what Bob knows
response = alice.chat("Does Bob remember our discussion about the budget?", target=bob)

# Session-specific perspective
response = alice.chat("What does Bob think about this project?",
                     target=bob,
                     session=session)
```

## Configuration

### Environment Variables

```bash
export ENGRAM_API_KEY="your-api-key"
export ENGRAM_BASE_URL="https://api.engram.dev"  # Optional
export ENGRAM_WORKSPACE_ID="your-workspace"  # Optional
```

### Client Options

```python
client = Engram(
    api_key="your-api-key",
    environment="production",  # or "local"
    workspace_id="custom-workspace",
    base_url="https://api.engram.dev"
)
```

## License

Apache 2.0 - see [LICENSE](../../LICENSE) for details.

## Support

- [Documentation](https://engram.dev/docs)
- [GitHub Issues](https://github.com/plastic-labs/engram/issues)
- [Discord Community](https://discord.gg/engram)
