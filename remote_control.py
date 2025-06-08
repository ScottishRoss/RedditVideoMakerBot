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
import logging

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

# Update the HTML template to improve log display
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
        .button.secondary {
            background-color: #2196F3;
        }
        .button.danger {
            background-color: #f44336;
        }
        .status { 
            margin: 20px 0; 
            padding: 10px; 
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .success { background-color: #dff0d8; }
        .error { background-color: #f2dede; }
        .container {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .command-log {
            background-color: #1e1e1e;
            color: #fff;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-family: 'Consolas', 'Courier New', monospace;
            max-height: 400px;
            overflow-y: auto;
        }
        .command-log h2 {
            margin-top: 0;
            color: #fff;
            border-bottom: 1px solid #444;
            padding-bottom: 10px;
        }
        .log-entry {
            margin: 5px 0;
            padding: 5px;
            border-radius: 3px;
        }
        .log-entry.command {
            color: #4CAF50;
        }
        .log-entry.output {
            color: #fff;
            white-space: pre-wrap;
        }
        .log-entry.error {
            color: #f44336;
        }
        .log-entry.timestamp {
            color: #888;
            font-size: 0.8em;
        }
        .button-group {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }
        .bot-logs {
            background-color: #1e1e1e;
            color: #fff;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-family: 'Consolas', 'Courier New', monospace;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .bot-logs h2 {
            margin-top: 0;
            color: #fff;
            border-bottom: 1px solid #444;
            padding-bottom: 10px;
        }
        .bot-logs pre {
            margin: 0;
            padding: 10px;
            color: #fff;
            font-family: 'Consolas', 'Courier New', monospace;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        @media (max-width: 600px) {
            .button {
                width: 100%;
                margin: 4px 0;
            }
            .button-group {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Reddit Video Bot Control</h1>
        
        <div class="button-group">
            <button class="button" onclick="startBot()" id="startButton">Start Bot</button>
            <button class="button secondary" onclick="startScheduler()" id="startSchedulerButton">Start Scheduler</button>
            <button class="button danger" onclick="stopBot()" id="stopButton">Stop Bot</button>
            <button class="button" onclick="checkStatus()" id="statusButton">Check Status</button>
        </div>

        <div id="status" class="status"></div>
        
        <div class="command-log">
            <h2>Command Log</h2>
            <div id="commandLog"></div>
        </div>
        
        <div class="bot-logs">
            <h2>Bot Logs</h2>
            <pre id="logs"></pre>
        </div>
    </div>

    <script>
        function addLogEntry(type, message) {
            const logDiv = document.getElementById('commandLog');
            const timestamp = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;
            
            const timestampSpan = document.createElement('span');
            timestampSpan.className = 'timestamp';
            timestampSpan.textContent = `[${timestamp}] `;
            
            const messageSpan = document.createElement('span');
            messageSpan.textContent = message;
            
            entry.appendChild(timestampSpan);
            entry.appendChild(messageSpan);
            logDiv.appendChild(entry);
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        function startBot() {
            const button = document.getElementById('startButton');
            button.disabled = true;
            button.textContent = 'Starting...';
            
            addLogEntry('command', 'Starting bot...');
            
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
                    addLogEntry(data.success ? 'output' : 'error', data.message);
                    button.disabled = false;
                    button.textContent = 'Start Bot';
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = 
                        `<div class="error">Error: ${error}</div>`;
                    addLogEntry('error', `Error: ${error}`);
                    button.disabled = false;
                    button.textContent = 'Start Bot';
                });
        }

        function stopBot() {
            const button = document.getElementById('stopButton');
            button.disabled = true;
            button.textContent = 'Stopping...';
            
            addLogEntry('command', 'Stopping bot...');
            
            fetch('/stop', { 
                method: 'POST',
                headers: {
                    'Authorization': 'Basic ' + btoa('{{ username }}:{{ password }}')
                }
            })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').innerHTML = 
                        `<div class="${data.success ? 'success' : 'error'}">${data.message}</div>`;
                    addLogEntry(data.success ? 'output' : 'error', data.message);
                    button.disabled = false;
                    button.textContent = 'Stop Bot';
                    checkStatus();
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = 
                        `<div class="error">Error: ${error}</div>`;
                    addLogEntry('error', `Error: ${error}`);
                    button.disabled = false;
                    button.textContent = 'Stop Bot';
                });
        }

        function startScheduler() {
            const button = document.getElementById('startSchedulerButton');
            button.disabled = true;
            button.textContent = 'Starting Scheduler...';
            
            addLogEntry('command', 'Starting scheduler...');
            
            fetch('/start_scheduler', { 
                method: 'POST',
                headers: {
                    'Authorization': 'Basic ' + btoa('{{ username }}:{{ password }}')
                }
            })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').innerHTML = 
                        `<div class="${data.success ? 'success' : 'error'}">${data.message}</div>`;
                    addLogEntry(data.success ? 'output' : 'error', data.message);
                    button.disabled = false;
                    button.textContent = 'Start Scheduler';
                    checkStatus();
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = 
                        `<div class="error">Error: ${error}</div>`;
                    addLogEntry('error', `Error: ${error}`);
                    button.disabled = false;
                    button.textContent = 'Start Scheduler';
                });
        }

        function checkStatus() {
            const button = document.getElementById('statusButton');
            button.disabled = true;
            button.textContent = 'Checking...';
            
            addLogEntry('command', 'Checking status...');
            
            fetch('/status', {
                headers: {
                    'Authorization': 'Basic ' + btoa('{{ username }}:{{ password }}')
                }
            })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').innerHTML = 
                        `<div class="${data.running ? 'success' : 'error'}">${data.message}</div>`;
                    document.getElementById('logs').textContent = data.logs;
                    addLogEntry('output', data.message);
                    button.disabled = false;
                    button.textContent = 'Check Status';
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = 
                        `<div class="error">Error: ${error}</div>`;
                    addLogEntry('error', `Error: ${error}`);
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

def get_logs():
    """Get all logs from the bot log file"""
    try:
        log_file = 'bot_run.log'
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                return f.read()
        return "No log file found"
    except Exception as e:
        return f"Error reading log file: {str(e)}"

def get_scheduled_tasks():
    """Get information about scheduled tasks"""
    try:
        # Run schtasks command to get task information
        result = subprocess.run(['schtasks', '/query', '/tn', 'RedditVideoMakerBot', '/fo', 'list', '/v'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            return {
                "status": "Not Scheduled",
                "details": "No scheduled tasks found"
            }
            
        # Parse the output to get relevant information
        task_info = {}
        is_running = False
        for line in result.stdout.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                task_info[key] = value
                # Check if task is running
                if key == "Status" and "Running" in value:
                    is_running = True
        
        # Add scheduler status
        task_info["Scheduler Status"] = "Running" if is_running else "Scheduled"
        return task_info
    except Exception as e:
        return {
            "status": "Error",
            "details": f"Error getting scheduled tasks: {str(e)}"
        }

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
    """Get the current status of the bot"""
    try:
        # Check if the bot is running
        running = get_bot_status()
        
        # Get scheduled tasks info
        scheduled_tasks = get_scheduled_tasks()
        
        # Get the logs
        logs = get_logs()
        
        return jsonify({
            'running': running,
            'message': 'Bot is running' if running else 'Bot is not running',
            'scheduled_tasks': scheduled_tasks,
            'logs': logs
        })
    except Exception as e:
        return jsonify({
            'running': False,
            'message': f'Error checking status: {str(e)}',
            'scheduled_tasks': str(e),
            'logs': str(e)
        })

@app.route('/start_scheduler', methods=['POST'])
@requires_auth
def start_scheduler():
    try:
        # Create a temporary PowerShell script that will run setup_scheduler.ps1
        temp_script = """
        Set-ExecutionPolicy Bypass -Scope Process -Force
        $ErrorActionPreference = 'Stop'
        try {
            & "$PSScriptRoot\\setup_scheduler.ps1"
            Write-Output "Success: Scheduler setup completed"
        } catch {
            Write-Error "Error: $_"
            exit 1
        }
        """
        
        # Write the temporary script to a file
        temp_script_path = "run_scheduler.ps1"
        with open(temp_script_path, "w") as f:
            f.write(temp_script)
        
        # Run the temporary script
        result = subprocess.run([
            'powershell',
            '-NoProfile',
            '-NonInteractive',
            '-ExecutionPolicy', 'Bypass',
            '-File', temp_script_path
        ], capture_output=True, text=True)
        
        # Clean up the temporary script
        try:
            os.remove(temp_script_path)
        except:
            pass
        
        # Log the full output for debugging
        logging.info(f"Scheduler setup output: {result.stdout}")
        if result.stderr:
            logging.error(f"Scheduler setup error: {result.stderr}")
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Scheduler started successfully. Output: ' + result.stdout.strip()
            })
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            return jsonify({
                'success': False,
                'message': f'Failed to start scheduler: {error_msg}'
            })
    except Exception as e:
        logging.error(f"Exception in start_scheduler: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to start scheduler: {str(e)}'
        })

@app.route('/stop', methods=['POST'])
@requires_auth
def stop_bot():
    try:
        # Find and stop the automated_runner.py process
        result = subprocess.run(['taskkill', '/F', '/IM', 'python.exe', '/FI', 'WINDOWTITLE eq automated_runner.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Bot stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Bot is not running'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to stop bot: {str(e)}'
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