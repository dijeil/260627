# -*- coding: utf-8 -*-
"""
폰에서 대시보드가 안 뜰 때 원인을 찾아주는 진단 도구.

'집 컴퓨터'와 '회사 컴퓨터'를 구분해서, 지금 이 컴퓨터에서 써야 할
주소를 알려줍니다. (컴퓨터가 바뀌면 주소도 바뀝니다!)

사용법 (대시보드를 켜 둔 상태로):
    python tools/mobile_check.py            # 기본 포트 8100
    python tools/mobile_check.py 8501       # 포트 지정
    python tools/mobile_check.py --rename   # 이 컴퓨터의 이름표 다시 정하기

표준 라이브러리만 사용합니다. 설치할 것 없습니다.
"""

import os
import platform
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.host_label import (  # noqa: E402
    HOSTS_FILE,
    current_ips,
    get_host_label,
    known_hosts,
    machine_id,
    register_current,
)

OK = "[OK]"
NG = "[문제]"
TIP = "  ->"
LINE = "=" * 64


def _run(cmd):
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, timeout=15).stdout
        return out.decode("utf-8", errors="replace")
    except Exception:
        return ""


def find_port(port):
    """해당 포트를 듣고 있는 주소 목록."""
    if platform.system() == "Windows":
        text = _run("netstat -ano -p TCP")
        pat = re.compile(r"^\s*TCP\s+(\S+)\s+\S+\s+LISTENING\s+\d+", re.M)
    else:
        text = _run("ss -ltn 2>/dev/null") or _run("netstat -ltn 2>/dev/null")
        pat = re.compile(r"LISTEN\s+\d+\s+\d+\s+(\S+)", re.M)

    found = []
    for m in pat.finditer(text):
        addr = m.group(1)
        if addr.rsplit(":", 1)[-1] == str(port):
            found.append(addr)
    return found


# ------------------------------------------------------- 0. 어느 컴퓨터인가
def show_which_computer(port, ask=True):
    label = get_host_label(ask=ask)
    register_current(label if label != "등록 안 된 컴퓨터" else None, port)

    print(LINE)
    print(f"  ■ 지금 이 컴퓨터 : {label}   (이름: {machine_id()})")
    print(LINE)

    others = [h for h in known_hosts() if not h["is_current"]]
    if others:
        print("\n  [다른 컴퓨터에 저장된 주소] — 지금은 이 주소로 들어가면 안 됩니다")
        for h in others:
            addrs = (h.get("lan") or []) + (h.get("tailscale") or [])
            p = h.get("port", port)
            shown = ", ".join(f"http://{a}:{p}" for a in addrs) or "기록 없음"
            print(f"    · {h.get('label', '?')} ({h['hostname']}) : {shown}")
            if h.get("last_seen"):
                print(f"      마지막 사용 {h['last_seen']}")
        print(f"\n{TIP} 폰 즐겨찾기에 위 주소가 저장돼 있으면 지금은 열리지 않습니다.")
        print("     아래 [2]번의 '지금 이 컴퓨터 주소'로 바꿔서 접속하세요.")
    return label


# ------------------------------------------------------- 1. 서버 바인딩
def check_bind(port):
    print("\n[1] 대시보드가 켜져 있고, 바깥에서 접속 가능한가")
    addrs = find_port(port)
    if not addrs:
        print(f" {NG} {port} 포트를 듣고 있는 프로그램이 없습니다. 대시보드가 꺼져 있습니다.")
        print(f"{TIP} 대시보드를 먼저 실행한 뒤 다시 돌리세요.")
        return False

    for a in addrs:
        print(f"      듣는 중: {a}")

    open_to_all = any(
        a.startswith("0.0.0.0") or a.startswith("*") or a.startswith("[::]")
        for a in addrs
    )
    if open_to_all:
        print(f" {OK} 0.0.0.0 으로 열려 있어 폰에서 접속 가능한 상태입니다.")
        return True

    print(f" {NG} 127.0.0.1(이 PC 전용)로만 열려 있습니다.")
    print(f"{TIP} 실행할 때 호스트를 0.0.0.0 으로 지정하세요:")
    print(f"       Streamlit : streamlit run app.py --server.address 0.0.0.0 --server.port {port}")
    print(f"       FastAPI   : uvicorn main:app --host 0.0.0.0 --port {port}")
    print(f"       Flask/Dash: app.run(host='0.0.0.0', port={port})")
    return False


# ------------------------------------------------------- 2. 지금 쓸 주소
def check_addresses(port, label):
    print(f"\n[2] 폰 브라우저에 넣을 주소  ({label} 기준)")
    lan, tailscale = current_ips()

    if lan:
        print(f" {OK} 같은 와이파이용 (가장 간단, 권장):")
        for ip in lan:
            print(f"       http://{ip}:{port}")
        print(f"{TIP} 폰도 같은 와이파이여야 합니다. LTE/5G면 안 됩니다.")
    else:
        print(f" {NG} 와이파이 IP(192.168.x.x 등)를 찾지 못했습니다. 유선/와이파이 연결을 확인하세요.")

    if tailscale:
        print(f"\n {OK} Tailscale(VPN)용:")
        for ip in tailscale:
            print(f"       http://{ip}:{port}")
        print(f"{TIP} 폰에도 Tailscale이 깔려 있고 켜져 있어야 열립니다.")
    else:
        print("\n      이 컴퓨터에는 Tailscale이 꺼져 있거나 설치돼 있지 않습니다.")
        print(f"{TIP} 100.x.x.x 로 시작하는 주소는 Tailscale 전용입니다.")
        print("       이 컴퓨터에서 Tailscale을 켜지 않으면 그 주소는 쓸 수 없습니다.")


# ------------------------------------------------------- 3. 방화벽
def check_firewall(port):
    print("\n[3] 방화벽")
    if platform.system() != "Windows":
        print("      (Windows가 아니므로 생략)")
        return
    rules = _run(f'netsh advfirewall firewall show rule name=all | findstr /C:"{port}"')
    if rules.strip():
        print(f" {OK} {port} 포트 관련 방화벽 규칙이 있습니다.")
    else:
        print(f" {NG} {port} 포트를 허용하는 규칙이 없습니다.")
        print(f"{TIP} 관리자 권한 명령 프롬프트에서 아래 한 줄:")
        print(f'       netsh advfirewall firewall add rule name="Dashboard {port}" '
              f"dir=in action=allow protocol=TCP localport={port}")
    print(f"{TIP} 회사 컴퓨터는 보안 정책으로 막혀 있을 수 있습니다.")
    print("       그럴 땐 폰 핫스팟을 켜고 PC를 거기에 연결한 뒤 다시 확인하세요.")


def rename():
    print(f"이 컴퓨터({machine_id()})의 이름표를 다시 정합니다.")
    print("  1) 집 컴퓨터")
    print("  2) 회사 컴퓨터")
    print("  3) 직접 입력")
    choice = input("번호 선택: ").strip()
    label = {"1": "집 컴퓨터", "2": "회사 컴퓨터"}.get(choice)
    if choice == "3":
        label = input("이름을 입력하세요: ").strip() or None
    if not label:
        print("변경하지 않았습니다.")
        return
    register_current(label)
    print(f"저장했습니다 -> {label}   ({HOSTS_FILE})")


def main():
    args = [a for a in sys.argv[1:]]
    if "--rename" in args:
        rename()
        return

    port = 8100
    for a in args:
        if a.isdigit():
            port = int(a)

    label = show_which_computer(port)
    check_bind(port)
    check_addresses(port, label)
    check_firewall(port)

    print("\n" + LINE)
    print("  폰에서 확인하는 순서")
    print(LINE)
    print("  1) 폰 즐겨찾기의 '옛날 컴퓨터 주소'를 지우고, 위 [2]번 주소를 쓴다")
    print("  2) PC가 켜져 있고 절전 모드가 아닌지")
    print("  3) 대시보드가 실행 중인지 ([1]번)")
    print("  4) 폰과 PC가 같은 와이파이인지")
    print("  5) 주소를 http:// 로 시작했는지 (https 아님)")
    print("  6) 그래도 안 되면 방화벽 ([3]번) 또는 폰 핫스팟 사용")
    print()


if __name__ == "__main__":
    main()
