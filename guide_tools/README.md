# 도감 업데이트 도구와 작업 메모

장비 도감 HTML을 새 표본·새 시세로 다시 만들 때 쓰는 스크립트입니다. 작업 공간이 바뀌어도 이 폴더와
**가장 최근 도감 HTML 파일 하나**만 있으면 이어서 업데이트할 수 있습니다. 도감 HTML 자체는 이 저장소에 넣지 않습니다.

마지막 업데이트: 2026.11.19판 (표본 11/13 00:00–11/19 00:00, 시세 11/6–11/19). 그 다음 판의 표본은 `2026-11-19T00:00`부터입니다.

## 파일

| 파일 | 하는 일 |
| --- | --- |
| `../tools/aggregate.py` | 순위 표본 집계(장착 횟수·비중·순위·같이 쓰는 장비 TOP 3·수집 상태) |
| `recount.py` | 위 집계와 따로 짠 코드로 원본 기록을 다시 세어, 집계 결과(.json)나 완성된 HTML과 비교 |
| `fetch_market.py` | Albion Online Data Project 아시아 서버에서 시세 원자료(일별 시장 이력·현재 판매 요청서)를 받음. 2초에 한 번 요청 |
| `build_market.py` | 받은 원자료로 도감의 시세 칸(4.0–8.0 여덟 단계 + 참고 티어)과 본문에 쓰는 수치를 계산 |
| `verify_market.py` | 시세 칸을 정수 계산·다른 구현으로 전부 다시 계산해 HTML 안의 값과 비교 |
| `build_v1119.py` | 11/13판을 바탕으로 11/19판을 만든 스크립트(다음 판을 만들 때 복사해서 날짜·문구를 바꿔 씀) |
| `final_checks.py` | 완성본 정적 점검(지난 판 문구 잔존, 새 외부 주소, 스크립트 안전성, 개인 정보) |
| `qa_browser_1119.py` | Chromium으로 모든 화면·342종 상세·7가지 화면 폭·어두운 테마 점검(Playwright 필요) |

## 업데이트 순서

```sh
git pull
# 0) 새 패치 확인: 게임 데이터 추출본 최신 커밋과 공식 공지
git ls-remote https://github.com/ao-data/ao-bin-dumps.git HEAD      # 2026.11.19 기준 0483dd9 (11/2 패치 4)
# 1) 순위 표본 (한국 시간, 끝 시각은 포함하지 않음. 보통 하루 단위로 자름)
python3 tools/aggregate.py . <최신 도감 HTML> 2026-11-19T00:00 <이번 끝 시각> agg.json
python3 guide_tools/recount.py . <최신 도감 HTML> 2026-11-19T00:00 <이번 끝 시각> agg.json     # 0 problems 여야 함
# 2) 시세: 도감 HTML에서 아이템 ID 목록(2,253개)과 ID 표를 뽑은 뒤
python3 guide_tools/fetch_market.py ids.json market_raw <M-D-YYYY 시작> <M-D-YYYY 끝>
python3 guide_tools/build_market.py market_raw idmap.json <최신 도감 HTML> <since> <until> market.json
# 3) 새 판 만들기: build_v1119.py를 복사해 날짜·문구를 고친 뒤 실행 → 4) 점검 → 5) 쓴 기록 지우기
python3 tools/prune.py <이번 끝 시각> --dry-run && python3 tools/prune.py <이번 끝 시각>
```

### 규칙

- **순위 표본**: 직전 판 끝 시각부터 이번 끝 시각까지. 밸런스 패치가 그 사이에 있으면 패치 이후 기록만 씁니다(11/05판 예).
- **시세 기간**: 수집한 날(UTC)까지 최근 14일. 그 안에 밸런스 패치가 있으면 패치 날부터. `until`은 수집한 UTC 날짜여야 합니다.
  본문의 “최근 N일” 문구(앱 스크립트 9곳, 정적 본문 몇 곳)는 빌드할 때 바꿉니다.
- **시세 계산**: 품질 1–3, 기간 안 일별 기록, 같은 칸의 거래량 가중 중앙값 1/3 미만·3배 초과 기록 제외(도시 묶음과 암시장 따로),
  거래량 가중 평균. 판매 요청서는 수집 24시간 안에 보인 도시 최저가. 거래 10개 미만이거나 마지막 거래가 `until - 7일`보다 이르면 흐린 숫자.
- **같이 쓰는 장비**: 한 기록의 한쪽(승자 또는 패자) 장비 구성 기준, 가방 칸은 도감에서 뺌, 동률은 아이템 코드 순.
- **Q·W 순위**: 공식 킬 기록의 `ActiveSpells`가 늘 비어 있어 만들 수 없음(11/19에도 장비 4,910개 모두 빈 값).
- `logs/`의 `"gap": true`는 겹쳐 읽는 여유분(3분)까지 다시 읽지 못했다는 뜻입니다. 읽은 범위가 직전 확인의 최신 기록보다
  앞까지 닿았는지(`oldest` ≤ 직전 `newest`) 확인하고, 분당 기록 수에 빈틈이 없는지 봅니다(11/17 0시 31–39분 3건은 끊김 없음).

### 점검(전부 통과해야 전달)

```sh
python3 guide_tools/recount.py . <이전 도감 HTML> <시작> <끝> <새 HTML>                 # 순위·비중·TOP 3
python3 guide_tools/verify_market.py market_raw <새 HTML> idmap.json <ao-bin-dumps>/formatted/items.txt
GUIDE_PRIVATE_TOKENS="<계정 이름 등>" python3 guide_tools/final_checks.py <새 HTML> <이전 HTML> --final
python3 guide_tools/qa_browser_1119.py <새 HTML> shots agg.json report.json            # 기대 문자열은 판마다 고침
```

게임 데이터가 바뀌지 않은 판에서는 스킬·장비 정적 자료(`spells`, `images`, 각 장비의 고정 항목)가 이전 판과 한 글자도
다르지 않은지 비교합니다. 패치가 있으면 새 추출본과 스킬 수치를 다시 대조해야 합니다.

## 개인 정보

이 폴더와 도감 HTML에는 플레이어 이름·길드·ID, 계정 이름, 이메일을 넣지 않습니다. 시세 요청의 User-Agent도 일반 문구입니다.
