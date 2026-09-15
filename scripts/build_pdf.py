#!/usr/bin/env python3
"""원고 마크다운을 공모전 규격(A4, 11pt) PDF로 만들고 실제 매수를 센다.

    python3 scripts/build_pdf.py drafts/작품-v1.md
    python3 scripts/build_pdf.py drafts/작품-v1.md --margin 15mm --line-height 1.6

요강은 "A4 기준 11pt"만 정한다. 여백과 줄간격은 한글 워드프로세서 기본값에 가깝게
여백 20mm, 줄간격 160%로 가정한다. 외부 패키지 없이 표준 라이브러리와 Chrome만 쓴다.
"""
import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
    "chromium-browser",
]


def find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    return None


def inline(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # 인쇄본에는 링크 글자만 남김
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", text)
    return text


def md_to_html(md):
    """제출 원고에 쓰는 만큼만 지원하는 작은 마크다운 변환기."""
    md = re.sub(r"\A---\n.*?\n---\n", "", md, flags=re.S)  # 메타데이터 블록은 인쇄하지 않음
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    lines = md.split("\n")
    out, para, i = [], [], 0

    def flush():
        if para:
            out.append("<p>" + "<br>".join(inline(p) for p in para) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("```"):
            flush()
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(html.escape(lines[i]))
                i += 1
            out.append("<pre>" + "\n".join(code) + "</pre>")
        elif m := re.match(r"(#{1,6})\s+(.*)", s):
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif re.fullmatch(r"(-{3,}|\*{3,})", s):
            flush()
            out.append("<hr>")
        elif s.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(inline(lines[i].strip().lstrip(">").strip()))
                i += 1
            out.append("<blockquote>" + "<br>".join(quote) + "</blockquote>")
            continue
        elif s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                head = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
                body = "".join(
                    "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:]
                )
                out.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
            continue
        elif re.match(r"([-*]|\d+\.)\s+", s):
            flush()
            tag = "ol" if re.match(r"\d+\.", s) else "ul"
            items = []
            while i < len(lines) and re.match(r"\s*([-*]|\d+\.)\s+", lines[i]):
                items.append("<li>" + inline(re.sub(r"\s*([-*]|\d+\.)\s+", "", lines[i], count=1)) + "</li>")
                i += 1
            out.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue
        else:
            para.append(s)
        i += 1
    flush()
    return "\n".join(out)


def page_html(body, title, margin, line_height):
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
@page {{ size: A4; margin: {margin}; }}
html {{ font-size: 11pt; }}
body {{ margin: 0; font-family: "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", sans-serif;
       font-size: 11pt; line-height: {line_height}; color: #000; word-break: keep-all; }}
h1 {{ font-size: 16pt; margin: 0 0 4pt; }}
h2 {{ font-size: 12.5pt; margin: 12pt 0 4pt; }}
h3 {{ font-size: 11.5pt; margin: 8pt 0 2pt; }}
p {{ margin: 0 0 6pt; }}
ul, ol {{ margin: 0 0 6pt; padding-left: 16pt; }}
table {{ border-collapse: collapse; width: 100%; margin: 4pt 0 8pt; }}
th, td {{ border: 0.5pt solid #555; padding: 2pt 4pt; vertical-align: top; }}
blockquote {{ margin: 0 0 6pt; padding-left: 8pt; border-left: 2pt solid #999; }}
hr {{ border: 0; border-top: 0.5pt solid #999; margin: 8pt 0; }}
pre {{ font-size: 9pt; white-space: pre-wrap; }}
</style></head><body>{body}</body></html>"""


def count_pages(pdf_bytes):
    return len(re.findall(rb"/Type\s*/Page(?!s)", pdf_bytes))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="마크다운 원고 경로")
    ap.add_argument("--margin", default="20mm", help="페이지 여백 (기본 20mm)")
    ap.add_argument("--line-height", default="1.6", help="줄간격 (기본 1.6 = 160%%)")
    ap.add_argument("--out-dir", default=str(ROOT / "build"), help="출력 폴더 (기본 build/)")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.exists():
        sys.exit(f"원고를 찾을 수 없음: {src}")
    chrome = find_chrome()
    if not chrome:
        sys.exit("Chrome/Chromium을 찾을 수 없어 PDF를 만들 수 없음")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{src.stem}.html"
    pdf_path = out_dir / f"{src.stem}.pdf"
    html_path.write_text(
        page_html(md_to_html(src.read_text(encoding="utf-8")), src.stem, args.margin, args.line_height),
        encoding="utf-8",
    )

    pdf_path.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        # 환경에 따라 Chrome이 PDF를 다 쓴 뒤에도 종료하지 않아서, 완성된 PDF가 보이면 직접 닫는다.
        proc = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--user-data-dir={profile}", f"--print-to-pdf={pdf_path}", html_path.as_uri()],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and proc.poll() is None:
            if pdf_path.exists() and pdf_path.read_bytes().rstrip().endswith(b"%%EOF"):
                break
            time.sleep(0.3)
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    if not pdf_path.exists():
        sys.exit("PDF 생성 실패: Chrome이 60초 안에 PDF를 만들지 못함")

    pages = count_pages(pdf_path.read_bytes())
    verdict = "✅ 규격 안 (3~5매)" if 3 <= pages <= 5 else ("⚠️ 부족 (3매 미만)" if pages < 3 else "❌ 초과 (5매 넘음)")
    print(f"{src} → {pdf_path.relative_to(ROOT) if pdf_path.is_relative_to(ROOT) else pdf_path}")
    print(f"A4 {pages}매 · 11pt · 여백 {args.margin} · 줄간격 {args.line_height} · {verdict}")


if __name__ == "__main__":
    main()
