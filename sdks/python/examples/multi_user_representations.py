import time
import uuid

from engram import Engram, MessageCreateParams
from engram.session import SessionPeerConfig

# Create a Engram client with the default workspace
engram = Engram(environment="local")

alice = engram.peer("alice")
bob = engram.peer("bob")

# Create a new session
session = engram.session("chat_test_" + str(uuid.uuid4()))

session.add_peers(
    [
        (alice, SessionPeerConfig(observe_me=True, observe_others=True)),
        (bob, SessionPeerConfig(observe_me=True, observe_others=True)),
    ]
)

# Generate messages with personal information
messages: list[MessageCreateParams] = []
messages.append(alice.message("I had a great breakfast today!"))
messages.append(bob.message("What did you eat?"))
messages.append(alice.message("I had pancakes and eggs and bacon."))

session.add_messages(messages)

# sleep to get later timestamps on these "future" messages
time.sleep(5)

# Create a separate session
session2 = engram.session("chat_test_" + str(uuid.uuid4()))
session2.add_peers(
    [
        (alice, SessionPeerConfig(observe_me=True, observe_others=True)),
        (bob, SessionPeerConfig(observe_me=True, observe_others=True)),
    ]
)
session2.add_messages(
    [
        alice.message(
            "Hey remember when I told you I had a great breakfast today? I lied. I actually skipped breakfast."
        ),
        bob.message("WTF is wrong with you??"),
    ]
)

# # Chat with alice's engram-level representation
print(
    "\n\n\033[1m asking alice's engram-level representation what she had for breakfast \033[0m"
)
response = alice.chat("what did alice have for breakfast today?", session=session)
print("response:", response)

# Chat with bob's internal representation of alice
print(
    "\n\n\033[1m asking bob what alice had for breakfast -- scoped to session 1 \033[0m"
)
response = bob.chat(
    "what did alice have for breakfast today?", target=alice, session=session
)
print("response:", response)

print(
    "\n\n\033[1m asking bob what alice had for breakfast -- scoped to session 2 \033[0m"
)
response = bob.chat(
    "what did alice have for breakfast today?", target=alice, session=session2
)
print("response:", response)

print("\n\n\033[1m asking bob what alice had for breakfast -- global scope \033[0m")
response = bob.chat("what did alice have for breakfast today?", target=alice)
print("response:", response)
