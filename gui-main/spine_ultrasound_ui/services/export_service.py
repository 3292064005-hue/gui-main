from pathlib import Path


def export_text_report(target: Path, title: str, lines: list[str]):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(title + "\n\n" + "\n".join(lines), encoding="utf-8")
