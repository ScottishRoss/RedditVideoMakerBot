import time
import logging
import sys
from datetime import datetime, timedelta
import subprocess
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_run.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def send_email_notification(subject, message):
    """Send email notification about bot status"""
    try:
        # Load email configuration from email_config.json
        with open('email_config.json', 'r') as f:
            email_config = json.load(f)
        
        # Get email settings from config
        smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
        smtp_port = int(email_config.get('smtp_port', '587'))
        sender_email = email_config.get('sender_email')
        sender_password = email_config.get('smtp_password')
        recipient_email = email_config.get('recipient_email')

        if not all([sender_email, sender_password, recipient_email]):
            logging.error("Email configuration missing. Please check email_config.json")
            return False

        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Add message body
        msg.attach(MIMEText(message, 'plain'))

        # Create server connection
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        # Send email
        server.send_message(msg)
        server.quit()
        
        logging.info("Email notification sent successfully")
        return True
    except Exception as e:
        logging.error(f"Failed to send email notification: {str(e)}")
        return False

def run_bot():
    """Run the main bot script"""
    try:
        logging.info("Starting bot run")
        start_time = datetime.now()
        
        # Run the bot
        subprocess.run(['python', 'main.py'], check=True)
        
        # Calculate run duration
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Prepare success message
        success_message = f"""
Bot Run Completed Successfully
-----------------------------
Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
Duration: {str(duration)}
Status: Success

The bot has completed its run successfully. Check the logs for more details.
"""
        # Send success notification
        send_email_notification("Reddit Video Bot - Run Successful", success_message)
        
        logging.info("Bot run completed successfully")
        return True
    except Exception as e:
        error_message = f"""
Bot Run Failed
-------------
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Error: {str(e)}

The bot encountered an error during its run. Check the logs for more details.
"""
        # Send error notification
        send_email_notification("Reddit Video Bot - Run Failed", error_message)
        
        logging.error(f"Error running bot: {str(e)}")
        return False

def main():
    """Main scheduler loop"""
    logging.info("Starting automated runner")
    
    # Send startup notification
    startup_message = f"""
Bot Runner Started
-----------------
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The automated bot runner has started and will run every 24 hours.
"""
    send_email_notification("Reddit Video Bot - Runner Started", startup_message)
    
    while True:
        try:
            # Run the bot
            run_bot()
            
            # Wait for 24 hours before next run
            next_run = datetime.now() + timedelta(hours=24)
            logging.info(f"Waiting until next run at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(24 * 60 * 60)  # 24 hours in seconds
            
        except KeyboardInterrupt:
            shutdown_message = f"""
Bot Runner Stopped
-----------------
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The automated bot runner has been stopped by user.
"""
            send_email_notification("Reddit Video Bot - Runner Stopped", shutdown_message)
            logging.info("Bot runner stopped by user")
            break
        except Exception as e:
            error_message = f"""
Bot Runner Error
---------------
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Error: {str(e)}

The bot runner encountered an unexpected error. It will retry in 1 hour.
"""
            send_email_notification("Reddit Video Bot - Runner Error", error_message)
            logging.error(f"Unexpected error in runner: {str(e)}")
            # Wait an hour before retrying on error
            time.sleep(3600)

if __name__ == "__main__":
    main() 