import random
import uuid

from engram import Engram, MessageCreateParams

# Create a Engram client with the default workspace
engram = Engram(environment="local")

peers = [
    engram.peer("alice"),
    engram.peer("bob"),
    engram.peer("charlie"),
]

# Create a new session
session = engram.session("chat_test_" + str(uuid.uuid4()))

# Generate some random messages from alice, bob, and charlie and add them to the session
messages: list[MessageCreateParams] = []
for i in range(10):
    random_peer = random.choice(peers)
    messages.append(
        random_peer.message(f"Hello from {random_peer}! This is message {i}.")
    )

session.add_messages(messages)

# Chat with alice
alice = peers[0]
response = alice.chat("what did alice have for breakfast today?")
print("response returned:", response)

# Chat with alice in the session
response = alice.chat("what did alice have for breakfast today?", session=session)
print("response returned:", response)

# Chat with alice in the session with a target
# This means you are querying alice's theory-of-mind representation of bob
bob = peers[1]
response = alice.chat("what did bob have for breakfast today?", target=bob)
print("response returned:", response)
