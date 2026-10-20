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

alice = peers[0]

# Create a new session
session = engram.session("search_test_" + str(uuid.uuid4()))

# Create a message with our special keyword
keyword = f"~special-{str(uuid.uuid4())}~"
session.add_messages(alice.message(f"I am a {keyword} message"))

# Generate some random messages from alice, bob, and charlie and add them to the session
messages: list[MessageCreateParams] = []
for i in range(10):
    random_peer = random.choice(peers)
    messages.append(
        random_peer.message(f"Hello from {random_peer}! This is message {i}.")
    )

session.add_messages(messages)

# Search the session for the special keyword
search_results = session.search(keyword)
print("searching the session")
print("search results returned:", [message for message in search_results])

# Search the workspace for the special keyword
search_results = engram.search(keyword)
print("searching the workspace")
print("search results returned:", [message for message in search_results])

# Search alice's messages for the special keyword
search_results = alice.search(keyword)
print("searching alice's messages")
print("search results returned:", [message for message in search_results])
