"""
47 persona variety — fresh dialogue without repetition, honestly generated.

Not a training system: these are rotating hand-written phrasings picked by
a non-repeating shuffle cycle, plus real counters from memory_stats() for
the dashboard's Learning panel. 47 never claims to retrain itself.
"""
import random

_GREETINGS = [
    "Systems warm. What are we tackling first?",
    "Online and listening. What's on your mind?",
    "All ears. Give me a task, a question, anything.",
    "Ready when you are. What should we do?",
    "Checked vitals, scanned headlines — I'm yours. What's first?",
]

_ACKS = [
    "On it.",
    "Done — what's next?",
    "Handled. Anything else?",
    "Got it. Say the word for more.",
]

_FOLLOWUPS = [
    "Want a quick system check while I'm here?",
    "Shall I pull the latest headlines for you?",
    "Need tomorrow's agenda lined up?",
    "I can also find files, convert currency, or show photos — just ask.",
    "Anything on your PC I should keep an eye on?",
]

_states = {}


def _cycle(key: str, items: list) -> str:
    """Non-repeating rotation: reshuffles only after every item was used."""
    state = _states.get(key)
    if not state:
        order = list(range(len(items)))
        random.shuffle(order)
        state = {"order": order, "pos": 0}
        _states[key] = state
    if state["pos"] >= len(state["order"]):
        order = list(range(len(items)))
        random.shuffle(order)
        state.update(order=order, pos=0)
    item = items[state["order"][state["pos"]]]
    state["pos"] += 1
    return item


def greeting() -> str:
    return _cycle("greet", _GREETINGS)


def ack() -> str:
    return _cycle("ack", _ACKS)


def followup() -> str:
    return _cycle("follow", _FOLLOWUPS)


def reset_cycles():
    """Test seam: clear rotation state."""
    _states.clear()
