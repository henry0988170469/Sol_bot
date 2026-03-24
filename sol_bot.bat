@echo off
:: 強制切換成 UTF-8 編碼，這樣才讀得懂「文件」這兩個字
chcp 65001
title SOL 量化交易機器人 V8.3
cls

echo ==============================================
echo       正在啟動 SOL 交易機器人...
echo       路徑檢查：C:\Users\henry\OneDrive\文件\project1
echo ==============================================

:: 切換到你的資料夾 (加引號是為了防止路徑中有空格出錯)
cd /d "C:\Users\henry\OneDrive\文件\project1"

:: 檢查是否成功進入資料夾
if not exist "sol_bot.py" (
    echo.
    echo ❌ 錯誤：找不到 sol_bot.py！
    echo    請確認檔案是否在 "C:\Users\henry\OneDrive\文件\project1" 裡面
    echo    或者檔案名稱是否已經改成 sol_bot.py
    pause
    exit
)

echo.
echo 🚀 程式啟動中... (Excel 記錄模式：開啟)
echo.

:: 執行 Python (這裡我幫你改成你之前紀錄中的 Python 3.12 絕對路徑，這樣最穩)
"C:\Users\henry\AppData\Local\Programs\Python\Python312\python.exe" sol_bot.py

:: 如果程式意外結束，暫停讓你看報錯
pause