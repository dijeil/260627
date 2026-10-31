"""엑셀에서 바로 열리는 파일 저장 유틸.

구매자가 **더블클릭 한 번**으로 열어도 한글이 깨지지 않고,
종목코드 앞자리 0도 사라지지 않게 저장한다.

사용법
------
    from utils.excel_safe import save_for_excel

    save_for_excel(df, "결과")          # 알아서 csv / xlsx 선택
    save_for_excel(df, "결과.csv")      # csv 고정 (utf-8-sig)
    save_for_excel(df, "결과.xlsx")     # xlsx 고정
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

import pandas as pd

__all__ = ["save_for_excel", "save_csv", "save_xlsx", "read_any", "find_text_cols"]

CSV_ENCODING = "utf-8-sig"          # 엑셀 한글 깨짐 방지 (BOM 포함)
_LEADING_ZERO = re.compile(r"^0\d+$")


# ---------------------------------------------------------------- 앞자리 0 탐지
def find_text_cols(df: pd.DataFrame) -> list[str]:
    """앞자리 0이 있어서 '텍스트'로 지켜야 하는 열 이름 목록을 돌려준다.

    예: 종목코드 '005930', 우편번호 '06236', 사업자번호 '0123456789'
    """
    found = []
    for col in df.columns:
        s = df[col]
        if s.dtype.kind not in ("O", "U", "S") and str(s.dtype) != "string":
            continue  # 이미 숫자형이면 0은 벌써 사라진 뒤다
        values = s.dropna().astype(str)
        if len(values) and values.map(lambda v: bool(_LEADING_ZERO.match(v))).any():
            found.append(col)
    return found


# ---------------------------------------------------------------------- CSV
def save_csv(df: pd.DataFrame, path: str | Path, **kwargs) -> Path:
    """CSV로 저장한다. 인코딩은 언제나 utf-8-sig."""
    path = _with_suffix(path, ".csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    kwargs.setdefault("index", False)
    kwargs.pop("encoding", None)                     # 다른 인코딩은 허용하지 않는다
    df.to_csv(path, encoding=CSV_ENCODING, **kwargs)
    return path


# --------------------------------------------------------------------- XLSX
def save_xlsx(
    data: pd.DataFrame | dict[str, pd.DataFrame],
    path: str | Path,
    text_cols: list[str] | None = None,
    sheet_name: str = "데이터",
) -> Path:
    """xlsx로 저장한다. 앞자리 0 보존 + 헤더 고정 + 열 너비 자동 조절.

    data에 {"시트이름": df, ...} 형태의 dict를 주면 여러 시트로 저장한다.
    """
    path = _with_suffix(path, ".xlsx")
    path.parent.mkdir(parents=True, exist_ok=True)

    sheets = data if isinstance(data, dict) else {sheet_name: data}

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            cols = text_cols if text_cols is not None else find_text_cols(df)
            out = df.copy()
            for col in cols:
                if col in out.columns:
                    out[col] = out[col].astype("string")
            out.to_excel(writer, index=False, sheet_name=_safe_sheet_name(name))
            _polish(writer.sheets[_safe_sheet_name(name)], out, cols)

    return path


# ----------------------------------------------------------------- 자동 선택
def save_for_excel(
    data: pd.DataFrame | dict[str, pd.DataFrame],
    path: str | Path,
    fmt: str = "auto",
    text_cols: list[str] | None = None,
    sheet_name: str = "데이터",
    quiet: bool = False,
) -> Path:
    """구매자가 바로 열 수 있는 형태로 저장한다.

    fmt="auto" (기본)
        · 앞자리 0이 있는 열이 있거나 시트가 여러 개면  -> xlsx
        · 그 외                                        -> csv (utf-8-sig)
        · 확장자(.csv / .xlsx)를 직접 쓰면 그 형식을 따른다

    돌려주는 값: 실제로 저장된 파일 경로
    """
    suffix = Path(path).suffix.lower()
    if fmt == "auto" and suffix in (".csv", ".xlsx"):
        fmt = suffix.lstrip(".")

    if fmt == "auto":
        if isinstance(data, dict):
            fmt = "xlsx"
        else:
            detected = text_cols if text_cols is not None else find_text_cols(data)
            fmt = "xlsx" if detected else "csv"

    if fmt == "csv":
        if isinstance(data, dict):
            raise ValueError("시트가 여러 개면 CSV로 저장할 수 없습니다. fmt='xlsx'를 쓰세요.")
        risky = text_cols if text_cols is not None else find_text_cols(data)
        if risky and not quiet:
            print(
                f"[주의] {', '.join(risky)} 열은 앞자리 0이 있습니다. "
                "CSV를 엑셀에서 열면 0이 사라집니다 — xlsx로 주는 것을 권합니다."
            )
        saved = save_csv(data, path)
        note = "엑셀에서 더블클릭해도 한글이 깨지지 않습니다 (utf-8-sig)"
    elif fmt == "xlsx":
        saved = save_xlsx(data, path, text_cols=text_cols, sheet_name=sheet_name)
        note = "앞자리 0과 한글이 그대로 보존됩니다"
    else:
        raise ValueError(f"fmt는 'auto' / 'csv' / 'xlsx' 중 하나여야 합니다 (받은 값: {fmt!r})")

    if not quiet:
        print(f"[저장 완료] {saved}  —  {note}")
    return saved


# ---------------------------------------------------------------------- 읽기
def read_any(path: str | Path, text_cols: list[str] | None = None, **kwargs) -> pd.DataFrame:
    """csv / xlsx를 가리지 않고 읽는다. BOM 유무와 상관없이 안전하다.

    text_cols에 열 이름을 주면 그 열의 앞자리 0을 유지한 채 문자열로 읽는다.
    """
    path = Path(path)
    dtype = {c: "string" for c in (text_cols or [])} or None
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, dtype=dtype, **kwargs)
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=dtype, **kwargs)


# -------------------------------------------------------------------- 내부용
def _with_suffix(path: str | Path, suffix: str) -> Path:
    path = Path(path)
    return path if path.suffix.lower() == suffix else path.with_suffix(suffix)


def _safe_sheet_name(name: str) -> str:
    """엑셀 시트 이름 제한(31자, 특수문자 불가)에 맞춘다."""
    cleaned = re.sub(r"[\\/*?:\[\]]", "-", str(name)).strip() or "Sheet1"
    return cleaned[:31]


def _display_width(text: str) -> int:
    """한글은 두 칸으로 세어 열 너비를 계산한다."""
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in str(text))


def _polish(ws, df: pd.DataFrame, text_cols: list[str]) -> None:
    """헤더 굵게 + 틀 고정 + 열 너비 자동 + 텍스트 열 서식."""
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    header_font = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="F2F2F2")

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    ws.freeze_panes = "A2"                       # 헤더 고정
    if ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions       # 필터 버튼

    for idx, col in enumerate(df.columns, start=1):
        letter = get_column_letter(idx)
        sample = df[col].dropna().astype(str).head(200)
        widest = max([_display_width(col)] + [_display_width(v) for v in sample] or [0])
        ws.column_dimensions[letter].width = min(max(widest + 3, 8), 50)

        if col in text_cols:                     # 앞자리 0 보존
            for row in range(2, ws.max_row + 1):
                ws.cell(row=row, column=idx).number_format = "@"


# ---------------------------------------------------------------------- 데모
if __name__ == "__main__":
    demo = pd.DataFrame(
        {
            "종목코드": ["005930", "000660", "035420"],
            "종목명": ["삼성전자", "SK하이닉스", "NAVER"],
            "현재가": [71500, 183000, 215000],
            "비고": ["㈜대표종목", "반도체 ♥", "플랫폼"],
        }
    )

    out_dir = Path(__file__).resolve().parent.parent / "sample_output"
    save_for_excel(demo, out_dir / "종목리스트")                 # -> 앞자리 0 있으니 xlsx
    save_for_excel(demo.drop(columns=["종목코드"]), out_dir / "시세")  # -> csv

    back = read_any(out_dir / "종목리스트.xlsx", text_cols=["종목코드"])
    print("\n[검증] 앞자리 0 유지:", back["종목코드"].tolist())
    print("[검증] 한글 유지:", back["비고"].tolist())
