@echo off
cd /d F:\pdf-word
echo PDF Translator Tool
echo ====================
echo.
call conda activate pdf-translator 2>nul
if errorlevel 1 (
    echo Creating environment...
    call conda create -n pdf-translator python=3.10 -y
    call conda activate pdf-translator
)
echo Installing dependencies...
pip install -r requirements.txt -q -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
echo.
echo Starting application...
echo.
python main.py
echo.
pause
