# film_synopsis — 영화 기획실 (Writers' Room)

**제1회 대한민국 AI창작문학상 영화 부문** 응모작(A4 11pt 3~5매 기획안 + 프롬프트 노트)을 준비하는 저장소다.
전략과 요강은 `기획전략.md`를 따른다. 접수 2026-10-01 ~ 11-30 자정, **목표 제출일 2026-11-25**, 발표 2027-02-15.

`heekeunlee/fairy_tale`(동화 공방)의 서브에이전트 파이프라인을 영화 공모전에 맞게 옮겨 확장했다.
동화 공방과 가장 크게 다른 점은 **사람 작가가 쇼러너**라는 것이다. 이 공모전은 "AI 활용의 독창성 및
협업 과정"을 30% 반영하고, 판권 협의에는 인간 창작 기여가 필요하다. 그래서 크루는 제안·초안·비평·기록을
맡고, **로그라인 선택, 방향 결정, 최종 문장은 작가가 한다.**

## 크루 구성 (9명 + 작가)

| 역할 | 에이전트 | 정의 파일 | 트리거 | 모델 | 산출물 |
|---|---|---|---|---|---|
| **쇼러너 (사람)** | 작가 본인 | - | - | - | 결정, 최종 문장 |
| 리서처 | researcher | `.claude/agents/researcher.md` | `/research [주제]` | sonnet(기본) | `research/` |
| 기획 PD | planner | `.claude/agents/planner.md` | `/plan <아이디어 또는 "발굴">` | opus | `ideas/`, `planning/` |
| 시나리오 작가 | writer | `.claude/agents/writer.md` | `/write [기획서 경로]` | opus | `drafts/` |
| 심사위원 | critic | `.claude/agents/critic.md` | `/review [원고 경로]` | opus | `reviews/` |
| 고문 (프로듀서) | advisor | `.claude/agents/advisor.md` | `/consult [작품]` | opus | `advisory/` |
| 비주얼 디렉터 | designer | `.claude/agents/designer.md` | `/visual [작품]` | sonnet(기본) | `visual/`, `assets/`, `video/` |
| 피칭 담당 | pitcher | `.claude/agents/pitcher.md` | `/pitch [작품]` | sonnet(기본) | `pitch/` |
| 라인 PD (총무) | admin | `.claude/agents/admin.md` | `/audit` | sonnet(기본) | `admin/` |
| 메이킹 기록자 | recorder | `.claude/agents/recorder.md` | `/log`, `/promptnote` | sonnet(기본) | `journal/`, `submission/` |

발상(기획)·비평(심사)·시장 판단(고문)·완성도가 점수의 50%인 집필은 opus, 형식이 정해진 실행 업무는 기본 모델.
사람 이름과 설정(`site/crew.json`)은 오피스 화면 연출이고, 실제로는 전부 Claude Code 서브에이전트다.

### 심사위원과 고문의 차이
- **critic**: "공모전 심사위원이 이걸 읽으면 몇 점인가". 요강 규격과 심사 기준(완성도 50 / AI 협업 30 / 확장성 20)으로 모의 채점한다.
- **advisor**: "피칭 데이에서 제작사가 이걸 사고 싶어 하는가". 현업 프로듀서 관점에서 시장성, 제작 현실성, 비교작, 시리즈 확장을 본다.

## 워크플로우 (반자동)

```
/research → /plan 발굴 → [작가: 로그라인 선택] → /plan <선택안> → [작가: 기획서 확정]
  → /write → /review ⇄ /write (수정 필요 시 반복)
  → [작가: 직접 퇴고 → drafts/{slug}-vN-author.md] → /review → /consult
  → /visual, /pitch → /promptnote → [작가: 프롬프트 노트 확정] → /audit → [작가: 제출]
/log 는 매 세션 끝에, /audit 은 수시로
```

1. (선택) `/research`로 영화·드라마·OTT 동향과 유사작을 조사한다.
2. `/plan 발굴`로 로그라인 후보를 뽑는다 → **작가가 고른다.**
3. `/plan <고른 로그라인>`으로 기획서를 만든다 → 작가가 검토·수정한다.
4. `/write`로 제출 규격 기획안 초고(AI 초안)를 쓴다.
5. `/review`로 모의 심사를 받는다. "수정 필요"면 `/write`로 v2를 만들고 반복한다.
6. **작가가 직접 퇴고한 버전**을 `drafts/{slug}-vN-author.md`로 저장한다. 제출본은 반드시 작가 버전이다.
7. `/consult`로 프로듀서 검토, `/visual`로 포스터·키 비주얼 프롬프트, `/pitch`로 피칭 자료를 만든다.
8. `/promptnote`로 일지와 결정로그를 프롬프트 노트 초안으로 엮는다 → 작가가 확정한다.
9. `/audit`으로 규격(실제 PDF 매수)과 제출 체크리스트를 점검한 뒤 작가가 이메일로 제출한다.

각 단계 결과는 작가가 확인하고 다음 단계로 넘길지 정한다. 무인 자동 파이프라인은 도입하지 않는다.

## 기록 규칙 (가장 중요)

이 저장소의 기록은 **프롬프트 노트(심사 30%)의 원재료**이자 **과정 영상의 재료**다.

1. 세션마다 `journal/_TEMPLATE_창작일지.md`를 복사해 `journal/YYYY-MM-DD_NN_제목.md`를 만든다.
2. 크루 커맨드를 실행할 때마다 메인 세션이 그날 일지의 **"크루 호출 기록"** 표에 한 줄 추가한다: 커맨드 원문, 담당, 산출물 경로, 작가 결정이 필요한 항목.
3. **사용자 프롬프트는 원문 그대로** 남긴다.
4. 채택·수정·기각의 **판단과 이유는 작가가 실제로 말한 것만** 적는다. AI가 판단이나 이유를 지어내지 않는다. 결정이 안 났으면 `보류`, 이유를 모르면 `-`로 둔다. 서브에이전트의 추천은 "추천"이지 결정이 아니다.
5. 결정은 `journal/결정로그.md`에도 한 줄씩 추가한다 (제안 주체: 작가 / 에이전트 이름).
6. 영상에 쓸 순간은 일지의 "🎬 영상화 메모"와 `video/장면후보.md`에 추가한다.
7. 단계가 넘어가면 `README.md` 진행 현황 체크박스를 갱신한다 (오피스 화면이 이걸 읽는다).
8. 세션 끝에 커밋하고 `main`에 push한다.

서브에이전트는 메인 대화를 보지 못한다. `/log`를 부를 때는 메인 세션이 이번 세션의 사용자 프롬프트 원문, 실행한 커맨드, 산출물, 작가가 말한 결정을 정리해 recorder에게 넘긴다.

## 파일 명명 규칙

제목슬러그(한글 가능, 공백은 `-`)로 같은 작품의 파일을 연결한다.

| 종류 | 경로 |
|---|---|
| 트렌드 조사 | `research/{YYYY-MM-DD}-{주제}.md` |
| 유사작·저작권 점검 | `research/{YYYY-MM-DD}-유사작점검-{슬러그}.md` |
| 로그라인 후보 | `ideas/{YYYY-MM-DD}-로그라인후보.md` |
| 기획서 | `planning/{YYYY-MM-DD}-{슬러그}.md` |
| AI 초안 | `drafts/{슬러그}-v{N}.md` |
| **작가 수정본** | `drafts/{슬러그}-v{N}-author.md` (에이전트는 절대 덮어쓰지 않는다) |
| 모의 심사 | `reviews/{원고 파일명}-review.md` |
| 프로듀서 검토 | `advisory/{원고 파일명}-advisory.md` |
| 비주얼 기획 | `visual/{슬러그}-v{N}.md`, 이미지는 `assets/` |
| 피칭 자료 | `pitch/{슬러그}.md` |
| 프롬프트 노트 | `submission/{슬러그}-프롬프트노트.md` |
| 라인 PD 점검 | `admin/{YYYY-MM-DD}-점검.md` |
| 창작 일지 | `journal/{YYYY-MM-DD}_{NN}_{제목}.md` |

## 도구

- `python3 scripts/build_pdf.py <원고.md>`: A4·11pt·줄간격 160%·여백 20mm로 PDF를 만들고 **실제 매수**를 출력한다 (Chrome headless, `build/`에 저장). 여백 가정은 `--margin`으로 바꿀 수 있다.
- `python3 scripts/build_site_data.py`: 저장소 파일을 읽어 `site/data.json`을 만든다. GitHub Actions가 push 때마다 실행하므로 오피스 통계는 손으로 고치지 않는다.

## 오피스 화면

`site/`는 GitHub Pages로 배포되는 오피스 화면이다 (https://heekeunlee.github.io/film_synopsis/).
동화 공방은 크루 통계를 손으로 갱신했지만, 여기서는 `build_site_data.py`가 실제 파일과 git 이력에서 숫자를 뽑는다.
**없는 활동을 지어내지 않는다.** 활동이 없으면 0이나 "아직 없음"으로 보인다.

## 주의

- 저장소는 **PUBLIC**이다. 작가가 2026-09-15에 스토리 본문 공개를 포함해 공개 유지를 결정했다.
- 퇴고할 때 AI 특유의 과장된 수사를 경계한다. 최종 문장은 작가가 쓴다.
- 실존 인물을 닮은 이미지나 특정 IP의 화풍 모방은 쓰지 않는다.
- 새 에이전트를 추가할 때는 `.claude/agents/`에 정의 파일, `.claude/commands/`에 커맨드, `site/crew.json`에 설정을 추가하고 이 문서의 구성 표를 갱신한다.
