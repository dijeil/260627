@echo off
chcp 65001 > nul
title 장후 일괄 실행 - 매일 15:35 자동 등록
cd /d "%~dp0"

:: ============================================================
::  장후 일괄 실행을 평일 오후 3시 35분에 자동으로 돌도록 등록
::  (이 파일은 한 번만 실행하면 됩니다. 관리자 권한 필요 없음)
:: ============================================================

set "TASKNAME=장후일괄실행"
set "TARGET=%~dp0장후_일괄실행.bat"

echo.
echo ============================================================
echo   장후 일괄 실행  -  매일 15:35 자동 등록
echo ============================================================
echo.

if not exist "%TARGET%" (
    echo   [실패] 같은 폴더에 장후_일괄실행.bat 이 없습니다.
    echo          두 파일을 같은 폴더에 두고 다시 실행하세요.
    echo.
    pause
    exit /b 1
)

echo   등록할 작업 : %TASKNAME%
echo   실행할 파일 : %TARGET%
echo   실행 시각   : 평일(월~금) 15:35
echo.

schtasks /create /tn "%TASKNAME%" /tr "\"%TARGET%\"" /sc weekly /d MON,TUE,WED,THU,FRI /st 15:35 /f
if errorlevel 1 (
    echo.
    echo   [실패] 등록하지 못했습니다.
    echo.
    pause
    exit /b 1
)

echo.
echo   [완료] 등록했습니다. 이제 평일 15:35 에 자동으로 돌아갑니다.
echo.
echo   - 지금 바로 한 번 돌려보려면 :  schtasks /run /tn "%TASKNAME%"
echo   - 등록을 지우려면           :  schtasks /delete /tn "%TASKNAME%" /f
echo.
pause
