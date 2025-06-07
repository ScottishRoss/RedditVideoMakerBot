@echo off
set /p SMTP_USERNAME="Enter your Gmail address: "
set /p SMTP_PASSWORD="Enter your Gmail App Password: "

echo Creating email configuration file...
echo {> email_config.json
echo     "smtp_username": "%SMTP_USERNAME%",>> email_config.json
echo     "smtp_password": "%SMTP_PASSWORD%",>> email_config.json
echo     "recipient_email": "ross.scottish@gmail.com">> email_config.json
echo }>> email_config.json

echo.
echo Email configuration has been saved to email_config.json
echo You can now run test_emails.bat
echo.
pause 