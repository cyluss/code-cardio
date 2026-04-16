# code-cardio

Claude Code 사용량을 측정하고, 요일과 공휴일에 따라 모델을 자동 전환하는 도구 모음.

## 배경

Claude Code는 모델별 토큰 단가 차이가 크다.

| 모델 | 특징 | 적합한 상황 |
|------|------|-------------|
| Opus | 1M 컨텍스트, 높은 추론 능력, 높은 단가 | 장시간 심층 작업 (설계, 문서 작성, 대규모 리팩토링) |
| Sonnet | 200k 컨텍스트, 빠른 응답, 낮은 단가 | 단발성 작업 (스크립트, 설정, 간단한 수정) |

주말과 공휴일은 장시간 집중 작업이 가능하므로 Opus를 쓰고, 평일은 짧은 작업 위주이므로 Sonnet을 쓰면 비용 대비 효과가 높다.

## 구성

이 저장소는 두 가지 독립된 스크립트로 구성된다.

### 1. switch_model.py (모델 자동 전환)

로그온 시 실행되어 `~/.claude/settings.json`의 `model` 값을 변경한다.

**전환 규칙**

| 조건 | 모델 |
|------|------|
| 토요일, 일요일 | Opus |
| 한국 공휴일 (ICS 기반) | Opus |
| 그 외 평일 | Sonnet |

**공휴일 지원 범위**

- 법정 공휴일: officeholidays.com ICS 파일에서 자동 반영
- 대체공휴일: ICS 파일에 포함됨
- 비정기 공휴일 (지방선거, 대선, 보궐선거 등): ICS 파일에 수동 추가 필요

**사전 준비**

1. 공휴일 ICS 파일 다운로드

```bash
curl -L -o ~/.claude/south-korea-holidays.ics \
  https://www.officeholidays.com/ics/south-korea
```

2. 비정기 공휴일이 있으면 ICS 파일 끝의 `END:VCALENDAR` 앞에 VEVENT 블록을 추가

```
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260603
DTEND;VALUE=DATE:20260604
SUMMARY:Local Election Day
END:VEVENT
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
<summary>macOS (LaunchAgent)</summary>

`~/Library/LaunchAgents/com.claude.switch-model.plist` 생성:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.switch-model</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOU/bin/uv</string>
        <string>run</string>
        <string>/Users/YOU/claude_home/code-cardio/switch_model.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/claude-switch-model.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/claude-switch-model.err</string>
</dict>
</plist>
```

```bash
# 등록
launchctl load -w ~/Library/LaunchAgents/com.claude.switch-model.plist

# 해제
launchctl unload ~/Library/LaunchAgents/com.claude.switch-model.plist

# 수동 실행
launchctl start com.claude.switch-model
```

</details>

<details>
<summary>Windows (Task Scheduler)</summary>

```powershell
$action = New-ScheduledTaskAction `
  -Execute "uv.exe" `
  -Argument "run $env:USERPROFILE\.claude\switch_model.py"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask `
  -TaskName "ClaudeModelSwitch" `
  -Action $action -Trigger $trigger -Settings $settings `
  -Description "Claude Code model: Sonnet on weekdays, Opus on weekends/holidays" `
  -Force
```

</details>

### 2. toktrack_daily_sku.py (사용량 리포트)

[toktrack](https://github.com/mag123c/toktrack)의 JSON 출력을 모델별 일간 비용/토큰 표로 정리한다.

**출력 예시**

```
=== COST (USD) ===
date           claude-haiku-4-5    claude-opus-4-6              TOTAL
--------------------------------------------------------------------
2026-04-15  $              0.28$              1.99$              2.27
2026-04-16  $              1.03$             17.82$             18.85
2026-04 sub $              1.31$             19.81$             21.12
--------------------------------------------------------------------
TOTAL       $              1.31$             19.81$             21.12
```

**사전 준비**

1. toktrack 바이너리 설치

```bash
# macOS (Apple Silicon)
curl -L -o ~/bin/toktrack \
  https://github.com/mag123c/toktrack/releases/download/v2.4.0/toktrack-darwin-arm64
chmod +x ~/bin/toktrack
xattr -d com.apple.quarantine ~/bin/toktrack  # Gatekeeper 해제

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

**자동 리포트 생성**

로그인 시 + 매일 09:00에 리포트를 생성한다. 당일 리포트가 이미 존재하면 중복 생성하지 않는다.

<details>
<summary>macOS (LaunchAgent)</summary>

래퍼 스크립트 `~/bin/toktrack-receipt.sh` 생성:

```bash
#!/bin/zsh
set -e
OUT_DIR="$HOME/Documents/toktrack-receipts"
mkdir -p "$OUT_DIR"
TODAY="$(date +%Y-%m-%d)"
if ls "$OUT_DIR"/${TODAY}_*.txt >/dev/null 2>&1; then
    exit 0
fi
STAMP="${TODAY}_$(date +%H%M%S)"
"$HOME/bin/toktrack" report --month > "$OUT_DIR/$STAMP.txt"
PATH="$HOME/bin:$PATH" /usr/bin/python3 \
    "$HOME/claude_home/code-cardio/toktrack_daily_sku.py" > "$OUT_DIR/${STAMP}_daily.txt"
```

```bash
chmod +x ~/bin/toktrack-receipt.sh
```

`~/Library/LaunchAgents/com.claude.toktrack-receipt.plist` 생성:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.toktrack-receipt</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOU/bin/toktrack-receipt.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/YOU/Documents/toktrack-receipts/.launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOU/Documents/toktrack-receipts/.launchd.err.log</string>
</dict>
</plist>
```

```bash
# 등록 (로그인 시 + 매일 09:00 실행)
launchctl load -w ~/Library/LaunchAgents/com.claude.toktrack-receipt.plist

# 해제
launchctl unload ~/Library/LaunchAgents/com.claude.toktrack-receipt.plist

# 수동 실행
launchctl start com.claude.toktrack-receipt
```

리포트는 `~/Documents/toktrack-receipts/` 에 저장된다:
- `YYYY-MM-DD_HHMMSS.txt` — 월간 텍스트 영수증
- `YYYY-MM-DD_HHMMSS_daily.txt` — 모델별 일간 비용/토큰 표

</details>

<details>
<summary>Windows (NSSM 서비스)</summary>

별도의 래퍼 스크립트가 필요하다. NSSM 서비스로 등록하면 부팅 시 자동 시작되고, 매일 09:00에 리포트를 생성하여 `reports/toktrack-YYYY-MM-DD.txt`에 저장한다.

래퍼 스크립트 예시는 [toktrack-service.ps1 gist](toktrack-service.ps1)를 참고한다.

</details>

## 의존성

| 항목 | 용도 |
|------|------|
| Python 3.10 이상 | 스크립트 실행 |
| [uv](https://github.com/astral-sh/uv) | PEP 723 스크립트 실행 |
| [toktrack](https://github.com/mag123c/toktrack) | Claude Code 사용량 수집 (toktrack_daily_sku.py 전용) |
| [NSSM](https://nssm.cc) | Windows 서비스 등록 (toktrack 자동 실행 전용, 선택) |

## macOS launchd 참고

macOS는 systemd 대신 **launchd**를 사용한다.

| 개념 | systemd (Linux) | launchd (macOS) |
|------|-----------------|-----------------|
| 사용자 서비스 | `~/.config/systemd/user/` | `~/Library/LaunchAgents/` |
| 시스템 서비스 | `/etc/systemd/system/` | `/Library/LaunchDaemons/` |
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

## 파일 구조

```
code-cardio/
  switch_model.py         # 모델 자동 전환 스크립트
  toktrack_daily_sku.py   # 사용량 리포트 스크립트
  README.md
```

설치 위치 (참고)

```
~/.claude/
  settings.json                # Claude Code 설정 (model 키를 switch_model.py가 갱신)
  south-korea-holidays.ics     # 공휴일 캘린더
```

## 라이선스

MIT
