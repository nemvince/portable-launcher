REM This script is used to build the project
REM --no-deployment-flag=self-execution is used to be able to use -m flag in the command line
start python -m nuitka --onefile .\main.py --windows-icon-from-ico=./steering-wheel.ico --no-deployment-flag=self-execution