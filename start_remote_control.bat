@echo off
echo Installing required packages...
pip install flask pyngrok
 
echo Starting Remote Control Server with ngrok...
python remote_control.py 