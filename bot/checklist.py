import re
from dataclasses import dataclass, field


@dataclass
class Question:
    id: str
    text: str


@dataclass
class Checklist:
    name: str
    questions: list[Question] = field(default_factory=list)


def load_checklist(path: str) -> Checklist:
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    name = ""
    questions: list[Question] = []
    current_id: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_id, current_lines
        if current_id:
            text = "\n".join(current_lines).strip()
            if text:
                questions.append(Question(id=current_id, text=text))
        current_id = None
        current_lines = []

    for line in lines:
        if line.startswith("# ") and not name:
            name = line[2:].strip()
        elif line.startswith("## "):
            flush()
            current_id = re.sub(r"\s+", "_", line[3:].strip().lower())
        elif current_id is not None:
            current_lines.append(line)

    flush()
    return Checklist(name=name or "Checklist", questions=questions)
