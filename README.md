# code-cardio

Claude Code 사용량을 측정하고, 요일과 공휴일에 따라 모델을 자동 전환하는 도구 모음.

## 배경

Claude Code는 모델별 토큰 단가 차이가 크다.

| 모델 | 특징 | 적합한 상황 |
|------|------|-------------|
| Opus 4.7 | 1M 컨텍스트, 최고 추론 능력, 높은 단가 | 토요일 / 평일 공휴일 — 장시간 심층 작업 (설계, 문서, 대규모 리팩토링) |
| Sonnet 4.6 | 200k 컨텍스트, 빠른 응답, 중간 단가 | 평일 / 일요일 — 일상 작업 (스크립트, 설정, 간단한 수정) |

## 구성

이 저장소는 세 가지 독립된 스크립트로 구성된다.

### 1. switch_model.py — 모델 자동 전환

로그온 시 실행되어 `~/.claude/settings.json`의 `model` 값을 변경한다.

**전환 규칙**

| 조건 | 모델 |
|------|------|
| 토요일 | Opus 4.7 (`claude-opus-4-7`) |
| 평일 공휴일 (월–금, ICS 기반) | Opus 4.7 (`claude-opus-4-7`) |
| 그 외 (평일 + 일요일) | Sonnet 4.6 (`claude-sonnet-4-6`) |

> 일요일은 공휴일이어도 Sonnet을 사용한다 — 일요일에는 무리하지 않는다.

**공휴일 지원 범위**

| 유형 | 처리 방식 |
|------|-----------|
| 법정 공휴일 / 대체공휴일 | officeholidays.com ICS 파일에서 자동 반영 |
| 비정기 공휴일 (선거일 등) | ICS 파일 끝 `END:VCALENDAR` 앞에 수동 추가 |

비정기 공휴일 추가 예시:

```
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260603
DTEND;VALUE=DATE:20260604
SUMMARY:Local Election Day
END:VEVENT
```

**사전 준비**

```bash
curl -L -o ~/.claude/south-korea-holidays.ics \
  https://www.officeholidays.com/ics/south-korea
```

**실행 방법**

```bash
# 오늘 기준 전환
uv run switch_model.py

# 특정 날짜 시뮬레이션
uv run switch_model.py 2026-05-01
```

**자동 실행 등록**

<details>
<summary>Windows</summary>

```bash
uv run add_startup_task.py
```

`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\switch-model.bat` 을 생성한다. 관리자 권한 불필요.

</details>

<details>
<summary>macOS (LaunchAgent)</summary>

```bash
uv run add_startup_task.py
```

`~/Library/LaunchAgents/com.claude.switch-model.plist` 을 생성하고 `launchctl load -w` 로 즉시 등록한다. 재실행하면 덮어쓰고 재등록한다.

> `uv` 경로는 `~/bin/uv` 로 고정된다. 다른 위치에 설치한 경우 `setup_macos()` 내 `uv` 변수를 수정한다.

</details>

<details>
<summary>Rocky 9 (systemd user service + timer)</summary>

```bash
uv run add_startup_task.py
```

`~/.config/systemd/user/` 아래에 systemd user 단위 파일을 생성한다.

- `claude-switch-model.service` — 로그인 시 실행 (`WantedBy=default.target`)
- `claude-switch-model.timer` — 매일 한 번씩 실행 (`OnCalendar=daily`, `Persistent=true`)

> `uv` 경로는 `~/.local/bin/uv` 로 고정된다. 다른 위치에 설치한 경우 `setup_linux()` 내 `uv` 변수를 수정한다.

**상태 확인 및 로그 보기**

```bash
systemctl --user status claude-switch-model.service
systemctl --user status claude-switch-model.timer
systemctl --user list-timers

# 로그 파일 확인
tail /tmp/claude-switch-model.log
tail /tmp/claude-switch-model.err

# 또는 journal에서 확인
journalctl --user-unit=claude-switch-model.service -n 20
```

</details>

### 2. add_startup_task.py — 시작 프로그램 등록 (Windows / macOS / Rocky 9)

`switch_model.py`를 로그온 시작 프로그램으로 등록한다.

```bash
uv run add_startup_task.py
```

| 플랫폼 | 등록 방식 | 관리자 권한 |
|--------|-----------|-------------|
| Windows | Startup 폴더에 `.bat` 생성 | 불필요 |
| macOS | LaunchAgent plist 생성 + `launchctl load -w` | 불필요 |
| Rocky 9 | systemd user service + timer 생성 | 불필요 |

재실행하면 덮어쓰고 재등록한다.

### 3. toktrack_daily_sku.py — 사용량 리포트

[toktrack](https://github.com/mag123c/toktrack)의 JSON 출력을 모델별 일간 비용/토큰 표로 정리한다.

**출력 예시**

```
=== COST (USD) ===
date           claude-haiku-4-5    claude-opus-4-7              TOTAL
--------------------------------------------------------------------
2026-04-15  $              0.28$              1.99$              2.27
2026-04-16  $              1.03$             17.82$             18.85
2026-04 sub $              1.31$             19.81$             21.12
--------------------------------------------------------------------
TOTAL       $              1.31$             19.81$             21.12
```

**사전 준비**

```bash
# macOS (Apple Silicon)
curl -L -o ~/bin/toktrack \
  https://github.com/mag123c/toktrack/releases/download/v2.4.0/toktrack-darwin-arm64
chmod +x ~/bin/toktrack
xattr -d com.apple.quarantine ~/bin/toktrack

# macOS (Intel)
curl -L -o ~/bin/toktrack \
  https://github.com/mag123c/toktrack/releases/download/v2.4.0/toktrack-darwin-x64
chmod +x ~/bin/toktrack
xattr -d com.apple.quarantine ~/bin/toktrack

# Windows
curl -L -o ~/bin/toktrack.exe \
  https://github.com/mag123c/toktrack/releases/download/v2.4.0/toktrack-win32-x64.exe
```

**실행 방법**

```bash
uv run toktrack_daily_sku.py
```

## 의존성

| 항목 | 필수 여부 | 용도 |
|------|-----------|------|
| Python 3.10+ | 필수 | 스크립트 실행 |
| [uv](https://github.com/astral-sh/uv) | 필수 | PEP 723 인라인 스크립트 실행 |
| [toktrack](https://github.com/mag123c/toktrack) | toktrack_daily_sku.py 전용 | Claude Code 사용량 수집 |

## 파일 구조

```
code-cardio/
  switch_model.py         # 모델 자동 전환
  add_startup_task.py     # Windows 시작 프로그램 등록
  toktrack_daily_sku.py   # 사용량 리포트
  README.md
```

설치 위치 (참고)

```
~/.claude/
  settings.json                # Claude Code 설정 (model 키를 switch_model.py가 갱신)
  south-korea-holidays.ics     # 공휴일 캘린더 (switch_model.py 전용)
```

## macOS launchd 참고

macOS는 systemd 대신 **launchd**를 사용한다.

| 개념 | systemd (Linux) | launchd (macOS) |
|------|-----------------|-----------------|
| 사용자 서비스 | `~/.config/systemd/user/` | `~/Library/LaunchAgents/` |
| 활성화 | `systemctl enable` | `launchctl load -w` |
| 시작 | `systemctl start` | `launchctl start` |
| 상태 확인 | `systemctl status` | `launchctl list \| grep` |
| 타이머 | `.timer` 유닛 파일 | plist 내 `StartCalendarInterval` |
| 로그 | `journalctl -u` | `StandardOutPath` / `StandardErrorPath` |

주요 plist 키:

| 키 | 설명 |
|---|---|
| `RunAtLoad` | 로그인(또는 load) 시 즉시 실행 |
| `StartCalendarInterval` | cron 스타일 스케줄 (Hour, Minute, Weekday 등) |
| `StartInterval` | N초마다 반복 실행 |
| `WatchPaths` | 지정 파일 변경 시 실행 |
| `KeepAlive` | 프로세스 종료 시 자동 재시작 (데몬용) |

## 라이선스

MIT
