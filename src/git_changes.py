import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"

ACTION_LABELS = {
    "A": "NEW",
    "M": "UPDATE",
    "D": "DELETE",
}


def run_git_status():
    result = subprocess.run(
        [
            "git",
            "-C",
            str(PROJECT_ROOT),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            "knowledge",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def parse_status_line(line):
    status = line[:2]
    raw_path = line[3:]

    # Porcelain can show renames as "old -> new". For this lab we treat the
    # new path as the relevant candidate and let hash/PostgreSQL validation
    # decide what action is really needed.
    if " -> " in raw_path:
        raw_path = raw_path.split(" -> ", 1)[1]

    if not raw_path.startswith("knowledge/") or not raw_path.endswith(".md"):
        return None

    source = Path(raw_path).relative_to("knowledge").as_posix()
    index_status = status[0]
    working_tree_status = status[1]

    if status == "??" or index_status == "A" or working_tree_status == "A":
        action = "A"
    elif index_status == "D" or working_tree_status == "D":
        action = "D"
    elif index_status == "M" or working_tree_status == "M":
        action = "M"
    else:
        return None

    return {
        "git_status": action,
        "action": ACTION_LABELS[action],
        "source": source,
    }


def get_git_changes():
    changes = []

    for line in run_git_status():
        parsed = parse_status_line(line)
        if parsed is not None:
            changes.append(parsed)

    # If a file appears more than once, keep the strongest action. DELETE wins
    # over UPDATE, UPDATE wins over NEW for this educational detector.
    priority = {"D": 3, "M": 2, "A": 1}
    by_source = {}
    for change in changes:
        existing = by_source.get(change["source"])
        if existing is None or priority[change["git_status"]] > priority[existing["git_status"]]:
            by_source[change["source"]] = change

    return sorted(by_source.values(), key=lambda item: item["source"])


def main():
    print("=== GIT CHANGES ===")
    print()

    changes = get_git_changes()
    if not changes:
        print("No hay cambios Markdown en knowledge/.")
        return

    for change in changes:
        print(f"[{change['action']:<6}] {change['source']}")


if __name__ == "__main__":
    main()
