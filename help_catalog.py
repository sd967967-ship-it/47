"""
47 command catalog — the single source of truth for what 47 can do and the
exact words that trigger it. Served to the dashboard overlay via
/api/commands and spoken/sent by the `help` command. Every entry mirrors
a real handle_command branch — no aspirational commands allowed.
"""
GROUPS = [
    {"title": "Talk", "items": [
        {"triggers": "hi 47 … (voice)", "example": "hi 47, remind me to call mom"},
        {"triggers": "type anything", "example": "just type, no wake word needed"},
        {"triggers": "help", "example": "help"},
        {"triggers": "brain status", "example": "brain status"},
    ]},
    {"title": "Play & search", "items": [
        {"triggers": "play <song>", "example": "play tera zikr"},
        {"triggers": "youtube <query>", "example": "youtube lofi beats"},
        {"triggers": "google <query>", "example": "google taj mahal history"},
        {"triggers": "search for <topic>", "example": "search for black holes"},
        {"triggers": "research <topic>", "example": "research electric cars"},
        {"triggers": "fetch <url>", "example": "fetch https://example.com"},
    ]},
    {"title": "Photos & data", "items": [
        {"triggers": "image of … / picture of … / photo of …", "example": "image of red fort"},
        {"triggers": "convert <n> <from> to <to>", "example": "convert 100 usd to inr"},
        {"triggers": "<coin> price", "example": "bitcoin price"},
        {"triggers": "holiday in <place>", "example": "holiday in usa"},
        {"triggers": "country info <name>", "example": "country info japan"},
        {"triggers": "weather in <city>", "example": "weather in delhi"},
    ]},
    {"title": "Files & study", "items": [
        {"triggers": "find file <name>", "example": "find file gravitation"},
        {"triggers": "read file <path>", "example": "read file notes.txt"},
        {"triggers": "list files / recent files", "example": "recent files"},
        {"triggers": "open folder / open documents", "example": "open documents"},
        {"triggers": "preview document <name>", "example": "preview document physics"},
        {"triggers": "summarize document <name>", "example": "summarize document physics"},
        {"triggers": "quiz me on <name>", "example": "quiz me on gravitation"},
        {"triggers": "index my files", "example": "index my files"},
    ]},
    {"title": "Computer", "items": [
        {"triggers": "open / start / launch <app>", "example": "open notepad"},
        {"triggers": "run command <cmd>", "example": "run command ipconfig"},
        {"triggers": "move mouse / click / type …", "example": "move mouse to 500 300"},
        {"triggers": "screenshot", "example": "take a screenshot"},
        {"triggers": "list apps / list windows", "example": "list apps"},
        {"triggers": "top processes / system status / disk drives", "example": "system status"},
        {"triggers": "lock pc", "example": "lock pc"},
        {"triggers": "browse <url>", "example": "browse https://example.com"},
        {"triggers": "scan wifi / wifi status", "example": "scan wifi networks"},
    ]},
    {"title": "Tasks & briefings", "items": [
        {"triggers": "remind me …", "example": "remind me to call mom in 20 minutes"},
        {"triggers": "what are my tasks", "example": "what are my tasks"},
        {"triggers": "done with … / delete task …", "example": "done with report"},
        {"triggers": "tomorrow", "example": "what is my routine tomorrow"},
        {"triggers": "briefing / headlines", "example": "briefing"},
        {"triggers": "audit log", "example": "show audit log"},
    ]},
    {"title": "3D & confirm words", "items": [
        {"triggers": "generate <thing> 3d model", "example": "generate a building 3d model"},
        {"triggers": "make 3d of <thing>", "example": "make 3d of boombox"},
        {"triggers": "what does <x> look like", "example": "what does a wrench look like"},
        {"triggers": "confirm", "example": "say confirm to approve a staged action"},
        {"triggers": "anything else", "example": "cancels a staged action"},
    ]},
]


def as_text() -> str:
    lines = ["What I can do — say or type these:"]
    for group in GROUPS:
        lines.append("")
        lines.append(group["title"] + ":")
        for item in group["items"]:
            lines.append(f"- {item['triggers']}  (e.g. {item['example']})")
    return "\n".join(lines)
