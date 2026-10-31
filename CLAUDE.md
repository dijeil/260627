# 프로젝트 규칙 (Claude 영구 기억)

## 1. CSV 저장 규칙 — 반드시 지킬 것 ⚠️

**모든 프로젝트·모든 코드에서 CSV를 저장할 때는 항상 `utf-8-sig` 인코딩을 사용한다.**

이유: 구매자가 CSV 파일을 **더블클릭만 해도** 엑셀에서 한글이 깨지지 않아야 한다.
(`utf-8`로 저장하면 엑셀이 BOM을 못 읽어서 한글이 깨진다. `utf-8-sig`는 BOM을 붙여준다.)

### pandas
```python
df.to_csv("파일명.csv", index=False, encoding="utf-8-sig")
```

### 파이썬 기본 csv 모듈
```python
with open("파일명.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
```

### 읽을 때
```python
pd.read_csv("파일명.csv", encoding="utf-8-sig")   # BOM 유무 모두 안전
```

### 절대 쓰지 말 것
```python
df.to_csv("파일명.csv")                            # ❌ 인코딩 미지정
df.to_csv("파일명.csv", encoding="utf-8")          # ❌ 엑셀에서 한글 깨짐
df.to_csv("파일명.csv", encoding="cp949")          # ❌ 일부 문자 저장 실패(㈜, ♥ 등)
```

## 2. 앞자리 0이 중요한 열(종목코드 등)

종목코드 `005930`처럼 앞자리 0이 있는 값은 CSV로 주면 엑셀이 `5930`으로 바꿔버린다.
→ **이런 열이 있으면 CSV 대신 xlsx로 제공한다.**

```python
with pd.ExcelWriter("파일명.xlsx", engine="openpyxl") as w:
    df.to_excel(w, index=False, sheet_name="데이터")
```

xlsx는 인코딩 문제도 없고 숫자 형식 변환 문제도 없어서 구매자에게 전달할 때 가장 안전하다.

## 3. 구매자 전달용 파일 원칙

| 상황 | 권장 포맷 |
|---|---|
| 한글이 들어간 일반 데이터 | CSV (`utf-8-sig`) 또는 xlsx |
| 종목코드·우편번호 등 앞자리 0 포함 | **xlsx 필수** |
| 날짜·금액 서식이 중요한 리포트 | **xlsx** |

구매자가 **가장 쉽고 편하게** 열어볼 수 있는 것이 최우선이다.
추가 설정 없이 더블클릭 한 번으로 바로 보이게 만든다.
