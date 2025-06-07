from flask import Flask, render_template_string, request, jsonify, Response
import subprocess
import os
from pathlib import Path
import json
from datetime import datetime
import threading
import time
from functools import wraps
import base64
from pyngrok import ngrok
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Basic authentication
USERNAME = "admin"
PASSWORD = "!?Ofv3Ucpl!?"  # Change this!

def load_email_config():
    """Load email configuration from JSON file"""
    try:
        with open('email_config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading email config: {str(e)}")
        return None

def send_email(subject, body, is_html=True):
    """Send email using configured settings"""
    config = load_email_config()
    if not config:
        print("Failed to load email configuration")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = config['sender_email']
        msg['To'] = config['recipient_email']
        msg['Subject'] = subject

        # Create the HTML version of the message
        if is_html:
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .container {{
                        background-color: #ffffff;
                        border-radius: 8px;
                        padding: 20px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background-color: #4CAF50;
                        color: white;
                        padding: 20px;
                        border-radius: 8px 8px 0 0;
                        margin: -20px -20px 20px -20px;
                    }}
                    .content {{
                        padding: 20px 0;
                    }}
                    .button {{
                        display: inline-block;
                        padding: 10px 20px;
                        background-color: #4CAF50;
                        color: white;
                        text-decoration: none;
                        border-radius: 4px;
                        margin: 10px 0;
                    }}
                    .credentials {{
                        background-color: #f5f5f5;
                        padding: 15px;
                        border-radius: 4px;
                        margin: 15px 0;
                    }}
                    .footer {{
                        margin-top: 20px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                        font-size: 0.9em;
                        color: #666;
                    }}
                    .url {{
                        word-break: break-all;
                        background-color: #f8f8f8;
                        padding: 10px;
                        border-radius: 4px;
                        border: 1px solid #ddd;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Reddit Video Bot</h1>
                    </div>
                    <div class="content">
                        {body}
                    </div>
                    <div class="footer">
                        <p>This is an automated message from your Reddit Video Bot.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(html, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
        server.starttls()
        server.login(config['sender_email'], config['smtp_password'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def check_auth(auth):
    """Check if the username/password combination is valid."""
    return auth and auth.username == USERNAME and auth.password == PASSWORD

def authenticate():
    """Send a 401 response that enables basic auth."""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Basic HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Reddit Video Bot Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px;
            background-color: #f5f5f5;
        }
        .button { 
            background-color: #4CAF50; 
            border: none; 
            color: white; 
            padding: 15px 32px; 
            text-align: center; 
            text-decoration: none; 
            display: inline-block; 
            font-size: 16px; 
            margin: 4px 2px; 
            cursor: pointer; 
            border-radius: 4px;
            width: 200px;
        }
        .button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        .status { 
            margin: 20px 0; 
            padding: 10px; 
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .success { background-color: #dff0d8; }
        .error { background-color: #f2dede; }
        .log { 
            background-color: white; 
            padding: 10px; 
            border-radius: 4px; 
            max-height: 300px; 
            overflow-y: auto;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-family: monospace;
        }
        .container {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        @media (max-width: 600px) {
            .button {
                width: 100%;
                margin: 4px 0;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Reddit Video Bot Control</h1>
        
        <div>
            <button class="button" onclick="startBot()" id="startButton">Start Bot</button>
            <button class="button" onclick="checkStatus()" id="statusButton">Check Status</button>
        </div>

        <div id="status" class="status"></div>
        
        <h2>Recent Logs</h2>
        <div id="logs" class="log"></div>
    </div>

    <script>
        function startBot() {
            const button = document.getElementById('startButton');
            button.disabled = true;
            button.textContent = 'Starting...';
            
            fetch('/start', { 
                method: 'POST',
                headers: {
                    'Authorization': 'Basic ' + btoa('{{ username }}:{{ password }}')
                }
            })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').innerHTML = 
                        `<div class="${data.success ? 'success' : 'error'}">${data.message}</div>`;
                    button.disabled = false;
                    button.textContent = 'Start Bot';
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = 
                        `<div class="error">Error: ${error}</div>`;
                    button.disabled = false;
                    button.textContent = 'Start Bot';
                });
        }

        function checkStatus() {
            const button = document.getElementById('statusButton');
            button.disabled = true;
            button.textContent = 'Checking...';
            
            fetch('/status', {
                headers: {
                    'Authorization': 'Basic ' + btoa('{{ username }}:{{ password }}')
                }
            })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').innerHTML = 
                        `<div class="${data.running ? 'success' : 'error'}">${data.message}</div>`;
                    document.getElementById('logs').innerHTML = data.logs;
                    button.disabled = false;
                    button.textContent = 'Check Status';
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = 
                        `<div class="error">Error: ${error}</div>`;
                    button.disabled = false;
                    button.textContent = 'Check Status';
                });
        }

        // Check status every 30 seconds
        setInterval(checkStatus, 30000);
        // Initial status check
        checkStatus();
    </script>
</body>
</html>
"""

def get_bot_status():
    """Check if the bot is currently running"""
    try:
        # Check if the bot process is running
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True)
        return 'automated_runner.py' in result.stdout
    except:
        return False

def get_recent_logs():
    """Get the most recent logs from bot_run.log"""
    try:
        log_file = Path('bot_run.log')
        if not log_file.exists():
            return "No logs available"
        
        # Get last 20 lines of the log file
        with open(log_file, 'r') as f:
            lines = f.readlines()
            return ''.join(lines[-20:])
    except Exception as e:
        return f"Error reading logs: {str(e)}"

@app.route('/')
@requires_auth
def home():
    return render_template_string(HTML_TEMPLATE, username=USERNAME, password=PASSWORD)

@app.route('/start', methods=['POST'])
@requires_auth
def start_bot():
    if get_bot_status():
        return jsonify({
            'success': False,
            'message': 'Bot is already running'
        })
    
    try:
        # Start the bot in a new process
        subprocess.Popen(['python', 'automated_runner.py'], 
                        creationflags=subprocess.CREATE_NEW_CONSOLE)
        return jsonify({
            'success': True,
            'message': 'Bot started successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to start bot: {str(e)}'
        })

@app.route('/status')
@requires_auth
def status():
    is_running = get_bot_status()
    return jsonify({
        'running': is_running,
        'message': 'Bot is running' if is_running else 'Bot is not running',
        'logs': get_recent_logs()
    })

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.getenv('PORT', 5000))
    
    # Configure ngrok
    try:
        # Try to load ngrok authtoken from environment variable
        ngrok_auth_token = "2yBNcYXvSJPrgiqgkZ6jsfH4C0V_qmGdem6gmNsyuNaCmTcw"
        if ngrok_auth_token:
            ngrok.set_auth_token(ngrok_auth_token)
            print("Ngrok authtoken configured from environment variable")
        else:
            # Try to load from config file
            try:
                with open('ngrok_config.json', 'r') as f:
                    config = json.load(f)
                    if 'auth_token' in config:
                        ngrok.set_auth_token(config['auth_token'])
                        print("Ngrok authtoken configured from config file")
                    else:
                        raise ValueError("No auth_token found in config file")
            except FileNotFoundError:
                print("No ngrok configuration found. Please set up ngrok:")
                print("1. Sign up at https://dashboard.ngrok.com/signup")
                print("2. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken")
                print("3. Either:")
                print("   - Set the NGROK_AUTH_TOKEN environment variable")
                print("   - Create a ngrok_config.json file with your auth_token")
                raise ValueError("Ngrok configuration required")
    except Exception as e:
        print(f"Error configuring ngrok: {str(e)}")
        print("Starting without ngrok tunnel...")
        public_url = None
    else:
        try:
            # Open a ngrok tunnel to the HTTP server
            public_url = ngrok.connect(port).public_url
            print(f"\n=== Remote Control Server Started ===")
            print(f"Local URL: http://localhost:{port}")
            print(f"Remote URL: {public_url}")
            print("Use these credentials to log in:")
            print(f"Username: {USERNAME}")
            print(f"Password: {PASSWORD}")
            print("=====================================\n")

            # Send email with the URL
            if public_url:
                email_body = f"""
                <h2>Remote Control Server Started</h2>
                
                <p>Your remote control panel is now accessible at:</p>
                <div class="url">{public_url}</div>
                
                <div class="credentials">
                    <h3>Login Credentials:</h3>
                    <p><strong>Username:</strong> {USERNAME}</p>
                    <p><strong>Password:</strong> {PASSWORD}</p>
                </div>
                
                <p>You can use this URL to access the bot control panel from anywhere. 
                Please note that the URL will change each time you restart the server.</p>
                
                <a href="{public_url}" class="button">Access Control Panel</a>
                """
                if send_email("Remote Control URL - Reddit Video Bot", email_body):
                    print("Email notification sent successfully")
                else:
                    print("Failed to send email notification")
        except Exception as e:
            print(f"Error starting ngrok tunnel: {str(e)}")
            print("Starting without ngrok tunnel...")
            public_url = None
    
    app.run(host='0.0.0.0', port=port) 