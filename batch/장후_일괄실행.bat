@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title 장후 일괄 실행 (오후 3시 30분 이후)
cd /d "%~dp0"

:: ============================================================
::  장후 일괄 실행  -  오후 3시 30분 장 마감 후 한 번만 더블클릭
:: ------------------------------------------------------------
::  이 파일 하나만 실행하면 아래 순서대로 자동으로 다 돌아갑니다.
::    1) 마감배치_실행.bat      (장 마감 정리)
::    2) 밤스캔_실행.bat        (KRX 전종목 스캔 -> 예측 장부)
::    3) 밤스캔_자정알림.bat    (자정 알림 예약)
::
::  * 이 파일은 package_v9 폴더 안에 두고 실행하세요.
::  * 순서를 바꾸거나 빼고 싶으면 아래 [실행 목록] 부분만 고치면 됩니다.
::    - 끄고 싶은 단계는 맨 앞에 :: 두 개를 붙이세요.
:: ============================================================

:: ----------------------- [실행 목록] ------------------------
set "STEP_COUNT=0"

call :ADD "마감배치"      BAT  "마감배치_실행.bat"
call :ADD "밤스캔"        BAT  "밤스캔_실행.bat"
call :ADD "자정 알림 예약" BAT  "밤스캔_자정알림.bat"

:: 장후 엔진을 따로 돌리고 싶을 때만 아래 :: 를 지우세요.
:: (마감배치_실행.bat 안에서 이미 돌고 있으면 두 번 돌게 되니 그대로 두세요)
::call :ADD "장후 엔진"     PY   "engine_postmarket.py"
:: ------------------------------------------------------------

echo.
echo ============================================================
echo   장후 일괄 실행
echo ============================================================
echo.

:: ---------- 지금 시각 / 요일 확인 ----------
set "NOW_YMD="
set "NOW_HM="
set "NOW_MIN="
set "NOW_DOW="
for /f "tokens=1-4 delims=|" %%A in ('powershell -NoProfile -Command "$d=Get-Date; '{0}|{1}|{2}|{3}' -f $d.ToString('yyyy-MM-dd'), $d.ToString('HH:mm'), ($d.Hour*60+$d.Minute), [int]$d.DayOfWeek" 2^>nul') do (
    set "NOW_YMD=%%A"
    set "NOW_HM=%%B"
    set "NOW_MIN=%%C"
    set "NOW_DOW=%%D"
)

if not defined NOW_HM (
    rem PowerShell 을 못 쓰는 경우 시계만 간단히 읽습니다
    set "NOW_YMD=%DATE%"
    set "NOW_HM=%TIME:~0,5%"
)

echo   오늘 날짜 : %NOW_YMD%
echo   지금 시각 : %NOW_HM%
echo.

:: 주말이면 알려만 주고 계속 진행 (휴장일에도 돌릴 수 있게)
if "%NOW_DOW%"=="0" echo   [안내] 오늘은 일요일입니다 (휴장).
if "%NOW_DOW%"=="6" echo   [안내] 오늘은 토요일입니다 (휴장).

:: 15:30 = 930분. 그 전이면 한 번 물어봅니다.
if defined NOW_MIN (
    if %NOW_MIN% LSS 930 (
        echo.
        echo   [주의] 아직 장이 끝나지 않았습니다. ^(마감 15:30^)
        echo          지금 돌리면 그날 데이터가 덜 들어갈 수 있습니다.
        echo.
        set /p "GO=  그래도 진행할까요? (Y 누르고 엔터 / 그냥 엔터면 취소) : "
        if /i not "!GO!"=="Y" (
            echo.
            echo   취소했습니다. 15:30 이후에 다시 실행해 주세요.
            echo.
            pause
            exit /b 1
        )
        echo.
    )
)

:: ---------- 기록 파일 준비 ----------
if not exist "logs" mkdir "logs" > nul 2>&1
for /f %%A in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmm" 2^>nul') do set "STAMP=%%A"
if not defined STAMP set "STAMP=%NOW_HM::=%"
set "LOG=logs\장후일괄_%STAMP%.txt"

> "%LOG%" echo [장후 일괄 실행] 시작 %NOW_YMD% %NOW_HM%
>>"%LOG%" echo 폴더: %CD%
>>"%LOG%" echo ------------------------------------------------------------

set "OK_COUNT=0"
set "FAIL_COUNT=0"
set "SKIP_COUNT=0"
set "FAIL_LIST="

:: ---------- 차례대로 실행 ----------
for /l %%I in (1,1,%STEP_COUNT%) do call :RUN_STEP %%I

:: ---------- 마무리 요약 ----------
for /f %%A in ('powershell -NoProfile -Command "Get-Date -Format HH:mm" 2^>nul') do set "END_HM=%%A"
if not defined END_HM set "END_HM=%TIME:~0,5%"

echo.
echo ============================================================
echo   전부 끝났습니다.  (%NOW_HM% ~ %END_HM%)
echo ------------------------------------------------------------
echo   성공 %OK_COUNT% 개 / 실패 %FAIL_COUNT% 개 / 건너뜀 %SKIP_COUNT% 개
if defined FAIL_LIST echo   실패한 단계 :%FAIL_LIST%
echo   기록 파일   : %LOG%
echo ============================================================
echo.

>>"%LOG%" echo ------------------------------------------------------------
>>"%LOG%" echo [장후 일괄 실행] 종료 %END_HM%  성공 %OK_COUNT% / 실패 %FAIL_COUNT% / 건너뜀 %SKIP_COUNT%
if defined FAIL_LIST >>"%LOG%" echo 실패한 단계:%FAIL_LIST%

if %FAIL_COUNT% GTR 0 (
    echo   [확인] 실패한 단계가 있습니다. 위 화면과 기록 파일을 확인하세요.
    echo.
)

pause
endlocal
exit /b 0


:: ============================================================
::  아래는 내부 동작 부분입니다. 건드리지 않아도 됩니다.
:: ============================================================

:ADD
set /a STEP_COUNT+=1
set "STEP_NAME_%STEP_COUNT%=%~1"
set "STEP_TYPE_%STEP_COUNT%=%~2"
set "STEP_FILE_%STEP_COUNT%=%~3"
exit /b 0


:RUN_STEP
set "IDX=%~1"
set "S_NAME=!STEP_NAME_%IDX%!"
set "S_TYPE=!STEP_TYPE_%IDX%!"
set "S_FILE=!STEP_FILE_%IDX%!"

for /f %%A in ('powershell -NoProfile -Command "Get-Date -Format HH:mm:ss" 2^>nul') do set "T0=%%A"
if not defined T0 set "T0=%TIME:~0,8%"

echo.
echo ------------------------------------------------------------
echo  [%IDX%/%STEP_COUNT%] %S_NAME%   (%T0% 시작)
echo        파일: %S_FILE%
echo ------------------------------------------------------------

if not exist "%S_FILE%" (
    echo   [건너뜀] 파일이 없습니다 - %S_FILE%
    >>"%LOG%" echo [%IDX%] %S_NAME% : 건너뜀 (파일 없음: %S_FILE%)
    set /a SKIP_COUNT+=1
    exit /b 0
)

if /i "%S_TYPE%"=="PY" (
    call :FIND_PYTHON
    if not defined PYEXE (
        echo   [실패] 파이썬을 찾지 못했습니다.
        >>"%LOG%" echo [%IDX%] %S_NAME% : 실패 (파이썬 없음)
        set /a FAIL_COUNT+=1
        set "FAIL_LIST=!FAIL_LIST! %S_NAME%"
        exit /b 0
    )
    "!PYEXE!" "%S_FILE%"
) else (
    call "%S_FILE%"
)
set "RC=%ERRORLEVEL%"

for /f %%A in ('powershell -NoProfile -Command "Get-Date -Format HH:mm:ss" 2^>nul') do set "T1=%%A"
if not defined T1 set "T1=%TIME:~0,8%"

if "%RC%"=="0" (
    echo.
    echo   [완료] %S_NAME%  (%T1%)
    >>"%LOG%" echo [%IDX%] %S_NAME% : 완료 (%T0% ~ %T1%)
    set /a OK_COUNT+=1
) else (
    echo.
    echo   [실패] %S_NAME%  (%T1%)  오류코드 %RC%
    >>"%LOG%" echo [%IDX%] %S_NAME% : 실패 (오류코드 %RC%, %T0% ~ %T1%)
    set /a FAIL_COUNT+=1
    set "FAIL_LIST=!FAIL_LIST! %S_NAME%"
)
exit /b 0


:FIND_PYTHON
if defined PYEXE exit /b 0
if exist ".venv\Scripts\python.exe" (
    set "PYEXE=%CD%\.venv\Scripts\python.exe"
    exit /b 0
)
if exist "venv\Scripts\python.exe" (
    set "PYEXE=%CD%\venv\Scripts\python.exe"
    exit /b 0
)
where py     > nul 2>&1 && set "PYEXE=py"     && exit /b 0
where python > nul 2>&1 && set "PYEXE=python" && exit /b 0
exit /b 0
