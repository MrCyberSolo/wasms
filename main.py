import requests
import time
import random
import os
import sys
import io
from datetime import datetime, timedelta

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ============================================================
#                    CONFIGURATION
# ============================================================
API_URL       = "https://wa.geniusdevel.com/api/send"
INSTANCE_ID   = "6A1E80DDA0116"
ACCESS_TOKEN  = "6a1e80ce3e27d"

DELAY_MIN        = 60       # seconds (min wait between messages)
DELAY_MAX        = 600      # seconds (max wait between messages)
SHUFFLE_NUMBERS  = True
RETRY_COUNT      = 2        # retries on failure
RETRY_DELAY      = 10       # seconds between retries
MSG_SEPARATOR    = "────────────────────────────────────"
# ============================================================

# ── ANSI Colors ──────────────────────────────────────────────
R  = "\033[0m"          # reset
B  = "\033[1m"          # bold
GR = "\033[38;5;82m"    # green
RD = "\033[38;5;196m"   # red
YL = "\033[38;5;220m"   # yellow
CY = "\033[38;5;51m"    # cyan
MG = "\033[38;5;201m"   # magenta
DM = "\033[38;5;240m"   # dim grey
WH = "\033[97m"         # white

def clr(text, color): return f"{color}{text}{R}"

def enable_ansi():
    """Enable ANSI escape codes on Windows terminal."""
    if sys.platform == "win32":
        os.system("")   # triggers VT processing via conhost

# ── Helpers ──────────────────────────────────────────────────
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fmt_seconds(secs):
    m, s = divmod(int(secs), 60)
    return f"{m:02d}m {s:02d}s" if m else f"{s:02d}s"

def progress_bar(done, total, width=30):
    filled = int(width * done / total) if total else 0
    bar    = "█" * filled + "░" * (width - filled)
    pct    = int(100 * done / total) if total else 0
    return f"[{GR}{bar}{R}] {B}{pct}%{R}"

def header_banner():
    line = "=" * 56
    print(f"""
{CY}+{line}+
|      {B}WhatsApp Bulk Sender  --  Advanced Edition{R}{CY}       |
+{line}+{R}
""")

def divider():
    print(clr("─" * 56, DM))

# ── File I/O ─────────────────────────────────────────────────
def load_numbers(path="number.txt"):
    if not os.path.exists(path):
        print(clr(f"❌  {path} not found!", RD))
        return []
    with open(path, "r", encoding="utf-8") as f:
        nums = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    if SHUFFLE_NUMBERS:
        random.shuffle(nums)
    return nums

def save_remaining(numbers, path="number.txt"):
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(f"{n}\n" for n in numbers)

def append_sent(number, path="send.txt"):
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{number} | {now_str()}\n")

def load_messages(path="msg.txt"):
    if not os.path.exists(path):
        print(clr(f"❌  {path} not found!", RD))
        return []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    msgs = [m.strip() for m in content.split(MSG_SEPARATOR) if m.strip()]
    return msgs

# ── Send with retry ──────────────────────────────────────────
def send_message(number, message):
    payload = {
        "number":       number,
        "type":         "text",
        "message":      message,
        "instance_id":  INSTANCE_ID,
        "access_token": ACCESS_TOKEN,
    }
    for attempt in range(1, RETRY_COUNT + 2):
        try:
            resp = requests.post(API_URL, json=payload, timeout=15)
            if resp.status_code == 200:
                return True, resp.status_code, ""
            else:
                reason = resp.text[:120]
                if attempt <= RETRY_COUNT:
                    print(clr(f"   ⚠  Attempt {attempt} failed (HTTP {resp.status_code}). Retrying in {RETRY_DELAY}s…", YL))
                    time.sleep(RETRY_DELAY)
                else:
                    return False, resp.status_code, reason
        except requests.exceptions.Timeout:
            reason = "Request timed out"
            if attempt <= RETRY_COUNT:
                print(clr(f"   ⚠  Timeout on attempt {attempt}. Retrying…", YL))
                time.sleep(RETRY_DELAY)
            else:
                return False, 0, reason
        except Exception as e:
            return False, 0, str(e)
    return False, 0, "Max retries exceeded"

# ── Live countdown ────────────────────────────────────────────
def live_countdown(seconds, sent, failed, remaining):
    end_time = datetime.now() + timedelta(seconds=seconds)
    while True:
        left = (end_time - datetime.now()).total_seconds()
        if left <= 0:
            break

        eta_str   = end_time.strftime("%I:%M:%S %p")
        bar_width = 28
        elapsed   = seconds - left
        filled    = int(bar_width * elapsed / seconds)
        bar       = "█" * filled + "░" * (bar_width - filled)
        pct       = int(100 * elapsed / seconds)

        line = (
            f"  {YL}⏳ Next in {fmt_seconds(left):>9}{R}  "
            f"[{CY}{bar}{R}] {B}{pct:>3}%{R}  "
            f"ETA {DM}{eta_str}{R}  "
            f"│ {GR}✓{sent}{R}  {RD}✗{failed}{R}  {WH}⋯{remaining}{R}"
        )
        # overwrite same line
        sys.stdout.write(f"\r{line}")
        sys.stdout.flush()
        time.sleep(0.5)

    sys.stdout.write("\r" + " " * 100 + "\r")   # clear the line
    sys.stdout.flush()

# ── Main ─────────────────────────────────────────────────────
if __name__ == "__main__":
    enable_ansi()
    header_banner()

    numbers  = load_numbers("number.txt")
    messages = load_messages("msg.txt")
    total    = len(numbers)

    if total == 0:
        print(clr("⚠  No numbers found in number.txt. Exiting.", YL))
        sys.exit(0)
    if not messages:
        print(clr("⚠  No messages found in msg.txt. Exiting.", YL))
        sys.exit(0)

    print(f"  {CY}Numbers loaded   :{R} {B}{total}{R}")
    print(f"  {CY}Message templates:{R} {B}{len(messages)}{R}")
    print(f"  {CY}Delay range      :{R} {B}{DELAY_MIN}s – {DELAY_MAX}s{R}")
    print(f"  {CY}Retries per send :{R} {B}{RETRY_COUNT}{R}")
    print(f"  {CY}Session started  :{R} {B}{now_str()}{R}")
    divider()

    remaining_numbers = numbers.copy()
    sent_count   = 0
    failed_count = 0
    session_start = time.time()

    try:
        for i, number in enumerate(numbers, 1):
            # ── Pick & personalise message ──────────────────
            msg = random.choice(messages)
            msg = msg.replace("{number}", number)
            msg = msg.replace("{time}", datetime.now().strftime("%I:%M %p"))
            msg = msg.replace("{date}", datetime.now().strftime("%d %b %Y"))

            # ── Progress header ─────────────────────────────
            print(f"\n  {progress_bar(i - 1, total)}  {DM}[{i}/{total}]{R}")
            print(f"  {B}📤 Sending to :{R} {CY}{number}{R}  {DM}({now_str()}){R}")

            # ── Send ────────────────────────────────────────
            ok, code, err = send_message(number, msg)

            if ok:
                sent_count += 1
                remaining_numbers.remove(number)
                append_sent(number)
                save_remaining(remaining_numbers)
                print(f"  {GR}{B}✅ Success!{R}  Saved → send.txt  │  Remaining: {len(remaining_numbers)}")
            else:
                failed_count += 1
                print(f"  {RD}{B}❌ Failed!{R}  HTTP {code}  │  {err[:80]}")

            # ── Delay (skip after last number) ──────────────
            if i < total:
                delay = random.randint(DELAY_MIN, DELAY_MAX)
                print(f"  {DM}Waiting {delay}s before next send…{R}")
                live_countdown(delay, sent_count, failed_count, len(remaining_numbers))

    except KeyboardInterrupt:
        print(f"\n\n  {YL}{B}⚠  Interrupted by user.{R}")
        save_remaining(remaining_numbers)
        print(f"  {DM}Remaining numbers saved to number.txt{R}")

    # ── Session summary ──────────────────────────────────────
    elapsed = fmt_seconds(time.time() - session_start)
    divider()
    print(f"""
  {B}SESSION SUMMARY{R}
  +--------------------------------+
  |  {GR}Sent     : {sent_count:<5}{R}              |
  |  {RD}Failed   : {failed_count:<5}{R}              |
  |  {CY}Total    : {total:<5}{R}              |
  |  {YL}Duration : {elapsed:<10}{R}         |
  +--------------------------------+
  {DM}Log saved in send.txt{R}
""")