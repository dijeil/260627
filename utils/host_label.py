# -*- coding: utf-8 -*-
"""
이 코드가 지금 '집 컴퓨터'에서 돌고 있는지 '회사 컴퓨터'에서 돌고 있는지
구분해서 알려주는 모듈.

컴퓨터가 바뀌면 접속 주소(IP)도 바뀝니다.
집에서 쓰던 주소를 회사에서 그대로 쓰면 폰에서 안 열립니다.
그래서 "지금 이 컴퓨터가 어디인지"와 "지금 써야 할 주소"를 같이 보여줍니다.

대시보드 안에서 쓰는 법 (한 줄이면 됩니다):

    from utils.host_label import banner
    print(banner(8100))                 # 콘솔
    st.caption(banner(8100))            # Streamlit

등록 정보는 프로젝트 폴더의 hosts.json 에 저장되므로,
폴더를 통째로 옮기면 등록 내용도 같이 따라갑니다.
"""

import json
import os
import socket
import sys
from datetime import datetime

__all__ = [
    "get_host_label",
    "register_current",
    "known_hosts",
    "current_ips",
    "best_url",
    "banner",
    "HOSTS_FILE",
]

# 프로젝트 루트 (utils/ 의 부모)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOSTS_FILE = os.path.join(_ROOT, "hosts.json")

HOME = "집 컴퓨터"
WORK = "회사 컴퓨터"
UNKNOWN = "등록 안 된 컴퓨터"

# 호스트 이름에 이런 단어가 있으면 자동으로 추측한다
_HOME_HINTS = ("home", "house", "집", "myp", "personal")
_WORK_HINTS = ("work", "office", "corp", "company", "회사", "사무")


# ----------------------------------------------------------------- 저장/읽기
def _load():
    try:
        with open(HOSTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data):
    try:
        with open(HOSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def machine_id():
    """이 컴퓨터를 식별하는 이름."""
    try:
        return socket.gethostname()
    except Exception:
        return "unknown-pc"


# --------------------------------------------------------------------- IP
def current_ips():
    """이 컴퓨터의 IP를 종류별로 돌려준다. (와이파이용, Tailscale용)"""
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ":" not in ip:
                ips.add(ip)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass

    lan, tailscale = [], []
    for ip in sorted(ips):
        parts = ip.split(".")
        if len(parts) != 4 or ip.startswith("127."):
            continue
        try:
            a, b = parts[0], int(parts[1])
        except ValueError:
            continue
        if a == "100" and 64 <= b <= 127:
            tailscale.append(ip)
        elif ip.startswith("192.168.") or ip.startswith("10.") or (
            a == "172" and 16 <= b <= 31
        ):
            lan.append(ip)
    return lan, tailscale


def best_url(port=8100):
    """폰 브라우저에 넣을 주소. 같은 와이파이 주소를 우선한다."""
    lan, tailscale = current_ips()
    if lan:
        return f"http://{lan[0]}:{port}", "같은 와이파이"
    if tailscale:
        return f"http://{tailscale[0]}:{port}", "Tailscale 켜야 함"
    return f"http://localhost:{port}", "이 PC 전용 (폰에서 안 보임)"


# ------------------------------------------------------------------- 라벨
def _guess(name):
    low = name.lower()
    if any(h in low for h in _WORK_HINTS):
        return WORK
    if any(h in low for h in _HOME_HINTS):
        return HOME
    return None


def get_host_label(ask=True):
    """
    지금 이 컴퓨터의 이름표를 돌려준다. ('집 컴퓨터' / '회사 컴퓨터' / 직접 지은 이름)

    우선순위:
      1) 환경변수 DASHBOARD_HOST_LABEL
      2) hosts.json 에 저장된 값
      3) 컴퓨터 이름으로 추측
      4) (ask=True 이고 키보드 입력이 가능하면) 한 번만 물어보고 저장
    """
    env = os.environ.get("DASHBOARD_HOST_LABEL", "").strip()
    if env:
        return env

    mid = machine_id()
    data = _load()
    saved = data.get(mid, {}).get("label")
    if saved:
        return saved

    guessed = _guess(mid)
    if guessed:
        register_current(guessed)
        return guessed

    if ask and sys.stdin is not None and sys.stdin.isatty():
        print(f"\n이 컴퓨터({mid})는 어디인가요? 처음 한 번만 물어봅니다.")
        print("  1) 집 컴퓨터")
        print("  2) 회사 컴퓨터")
        print("  3) 직접 입력")
        try:
            choice = input("번호 선택 (엔터=건너뛰기): ").strip()
        except Exception:
            choice = ""
        label = None
        if choice == "1":
            label = HOME
        elif choice == "2":
            label = WORK
        elif choice == "3":
            try:
                typed = input("이름을 입력하세요: ").strip()
            except Exception:
                typed = ""
            label = typed or None
        if label:
            register_current(label)
            return label

    return UNKNOWN


def register_current(label=None, port=8100):
    """지금 이 컴퓨터의 이름표와 주소를 hosts.json 에 기록한다."""
    mid = machine_id()
    data = _load()
    entry = data.get(mid, {})
    if label:
        entry["label"] = label
    lan, tailscale = current_ips()
    entry["hostname"] = mid
    entry["lan"] = lan
    entry["tailscale"] = tailscale
    entry["port"] = port
    entry["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    data[mid] = entry
    _save(data)
    return entry


def known_hosts():
    """등록된 모든 컴퓨터를 (지금 이 컴퓨터인지 표시와 함께) 돌려준다."""
    mid = machine_id()
    out = []
    for name, e in _load().items():
        item = dict(e)
        item["hostname"] = name
        item["is_current"] = (name == mid)
        out.append(item)
    out.sort(key=lambda x: (not x["is_current"], x.get("label", "")))
    return out


# ------------------------------------------------------------------ 한 줄 표시
def banner(port=8100, ask=False):
    """대시보드 상단에 붙일 한 줄. 예) '회사 컴퓨터 (DESKTOP-ABC) · http://192.168.0.5:8100'"""
    label = get_host_label(ask=ask)
    url, _ = best_url(port)
    return f"{label} ({machine_id()}) · {url}"
