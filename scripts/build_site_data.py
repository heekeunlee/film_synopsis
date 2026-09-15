#!/usr/bin/env python3
"""저장소의 실제 파일과 git 이력을 읽어 오피스 화면용 site/data.json을 만든다.

    python3 scripts/build_site_data.py

크루 통계를 손으로 고치지 않기 위한 스크립트다. GitHub Actions가 push마다 실행한다.
없는 활동은 만들지 않는다. 파일이 없으면 0, 커밋이 없으면 null이다.
"""
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "heekeunlee/film_synopsis"
DATES = {
    "open": "2026-10-01",
    "target": "2026-11-25",
    "deadline": "2026-11-30",
    "result": "2027-02-15",
}
JOURNAL_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d+)_(.+)\.md$")


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def work_files(folder):
    d = ROOT / folder
    if not d.is_dir():
        return []
    return sorted(p for p in d.rglob("*.md") if p.name != "README.md" and not p.name.startswith("_"))


def journal_entries():
    entries = []
    for p in work_files("journal"):
        m = JOURNAL_RE.match(p.name)
        if not m:
            continue
        first = next((l for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("# ")), "")
        title = re.sub(r"^#\s*(\[[^\]]*\]\s*)?(#\d+\s*)?", "", first).strip() or m.group(3).replace("-", " ")
        entries.append({"date": m.group(1), "session": int(m.group(2)), "title": title,
                        "path": p.relative_to(ROOT).as_posix()})
    return sorted(entries, key=lambda e: (e["date"], e["session"]), reverse=True)


def table_rows(path, heading=None):
    """문서의 (heading이 있으면 그 절 아래) 첫 번째 표의 데이터 행 수."""
    p = ROOT / path
    if not p.exists():
        return 0
    text = p.read_text(encoding="utf-8")
    if heading:
        start = text.find(heading)
        if start < 0:
            return 0
        text = text[start:]
    rows = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            rows.append(line)
        elif rows:
            break
    return max(0, len(rows) - 2)  # 머리글 줄과 구분선 제외


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    return dict(re.findall(r"^(\w+):\s*(.+)$", m.group(1), re.M)) if m else {}


def latest_verdict(folder, label):
    files = sorted(work_files(folder), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files:
        text = p.read_text(encoding="utf-8")
        verdict = re.search(rf"\*\*{label}:\*\*\s*(.+)", text)
        score = re.search(r"\*\*모의 점수:\*\*\s*(\d+)\s*/\s*100", text)
        if verdict:
            return {"path": p.relative_to(ROOT).as_posix(), "verdict": verdict.group(1).strip(),
                    "score": int(score.group(1)) if score else None}
    return None


def progress():
    readme = ROOT / "README.md"
    if not readme.exists():
        return []
    plain = lambda s: re.sub(r"\s*→?\s*\[([^\]]+)\]\([^)]*\)", "", s).replace("`", "").strip()
    return [{"label": plain(m.group(2)), "done": m.group(1).lower() == "x"}
            for m in re.finditer(r"^- \[( |x|X)\] (.+)$", readme.read_text(encoding="utf-8"), re.M)]


def main():
    crew_cfg = json.loads((ROOT / "site/crew.json").read_text(encoding="utf-8"))
    crew = []
    for member in crew_cfg["crew"]:
        agent_file = ROOT / ".claude/agents" / f"{member['agent']}.md"
        fm = frontmatter(agent_file) if agent_file.exists() else {}
        if member["agent"] == "recorder":
            count = len(journal_entries())
        else:
            count = sum(len(work_files(f)) for f in member["outputs"])
        # 빈 폴더용 .gitkeep, 템플릿, README 커밋은 작업으로 치지 않는다
        pathspecs = [f":(glob){f}/**/*.md" for f in member["outputs"]]
        last = git("log", "-1", "--format=%cs", "--", *pathspecs,
                   ":(exclude,glob)**/_*.md", ":(exclude,glob)**/README.md") or None
        crew.append({**member, "active": agent_file.exists(), "model": fm.get("model", "기본"),
                     "count": count, "last_activity": last})

    drafts = work_files("drafts")
    commits = []
    for line in git("log", "-12", "--format=%cs\t%s").splitlines():
        date, _, msg = line.partition("\t")
        commits.append({"date": date, "message": msg})

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": REPO,
        "dates": DATES,
        "showrunner": crew_cfg["showrunner"],
        "crew": crew,
        "progress": progress(),
        "counts": {
            "ideas": len(work_files("ideas")),
            "planning": len(work_files("planning")),
            "drafts_ai": sum(1 for p in drafts if not p.stem.endswith("-author")),
            "drafts_author": sum(1 for p in drafts if p.stem.endswith("-author")),
            "reviews": len(work_files("reviews")),
            "journal": len(journal_entries()),
            "decisions": table_rows("journal/결정로그.md"),
            "scenes": table_rows("video/장면후보.md", "## 장면 후보 목록"),
            "commits": int(git("rev-list", "--count", "HEAD") or 0),
        },
        "latest_review": latest_verdict("reviews", "종합 판정"),
        "latest_advisory": latest_verdict("advisory", "종합 의견"),
        "journal": journal_entries()[:10],
        "commits": commits,
    }
    out = ROOT / "site/data.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"site/data.json 갱신: 크루 {len(crew)}명, 일지 {data['counts']['journal']}편, "
          f"결정 {data['counts']['decisions']}건, 커밋 {data['counts']['commits']}개")


if __name__ == "__main__":
    main()
