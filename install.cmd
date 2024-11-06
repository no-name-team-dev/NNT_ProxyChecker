@echo off
cls
title Install Proxy Checker
python -m venv venv
call venv/Scripts/activate
pip install -r requirements.txt
pause