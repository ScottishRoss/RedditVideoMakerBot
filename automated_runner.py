import time
import logging
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
import json
import os
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_run.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class EmailNotifier:
    def __init__(self, config_file: str = 'email_config.json'):
        self.config_file = Path(config_file)
        if not self.config_file.exists():
            raise FileNotFoundError(f"Email configuration file not found: {config_file}")
        
        with open(self.config_file, 'r') as f:
            config = json.load(f)
            
        self.recipient_email = config['recipient_email']
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.smtp_username = config['smtp_username']
        self.smtp_password = config['smtp_password']
        
    def send_notification(self, subject: str, body: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logging.info(f"Email notification sent successfully to {self.recipient_email}")
            return True
        except Exception as e:
            logging.error(f"Failed to send email notification: {str(e)}")
            return False

class BotRunner:
    def __init__(self, max_retries: int = 3, retry_delay: int = 300):
        self.max_retries = max_retries
        self.retry_delay = retry_delay  # 5 minutes between retries
        self.state_file = Path('bot_state.json')
        self.load_state()
        self.email_notifier = EmailNotifier()

    def load_state(self):
        """Load the last run state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
            except json.JSONDecodeError:
                self.state = {'last_run': None, 'consecutive_failures': 0}
        else:
            self.state = {'last_run': None, 'consecutive_failures': 0}

    def save_state(self):
        """Save the current run state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f)

    def should_run(self) -> bool:
        """Check if the bot should run based on the last run time"""
        if not self.state['last_run']:
            return True
        
        last_run = datetime.fromisoformat(self.state['last_run'])
        now = datetime.now()
        
        # Run if it's been more than 24 hours since last successful run
        return (now - last_run) > timedelta(hours=24)

    def run_bot(self) -> bool:
        """Run the bot with retry logic"""
        retries = 0
        while retries < self.max_retries:
            try:
                logging.info(f"Attempting to run bot (Attempt {retries + 1}/{self.max_retries})")
                
                # Import and run the main bot
                from main import main
                main()
                
                # If we get here, the run was successful
                self.state['last_run'] = datetime.now().isoformat()
                self.state['consecutive_failures'] = 0
                self.save_state()
                logging.info("Bot run completed successfully")
                return True
                
            except Exception as e:
                retries += 1
                self.state['consecutive_failures'] += 1
                self.save_state()
                
                error_msg = f"Error running bot: {str(e)}\n{traceback.format_exc()}"
                logging.error(error_msg)
                
                # Send email notification for failure
                subject = f"Reddit Video Bot Error - Attempt {retries}/{self.max_retries}"
                body = f"""
                The Reddit Video Maker Bot encountered an error:

                Error: {str(e)}
                
                Stack Trace:
                {traceback.format_exc()}
                
                This was attempt {retries} of {self.max_retries}.
                {'Will retry in 5 minutes.' if retries < self.max_retries else 'No more retries remaining.'}
                
                Check bot_run.log for more details.
                """
                self.email_notifier.send_notification(subject, body)
                
                if retries < self.max_retries:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logging.error("Max retries reached. Giving up for now.")
                    return False

    def run_daily(self):
        """Main loop for daily runs"""
        while True:
            try:
                if self.should_run():
                    success = self.run_bot()
                    if not success:
                        logging.error("Bot run failed after all retries")
                        # Send final failure notification
                        subject = "Reddit Video Bot - All Retries Failed"
                        body = """
                        The Reddit Video Maker Bot has failed all retry attempts.
                        
                        Please check the bot_run.log file for detailed error information.
                        The bot will attempt to run again in 24 hours.
                        """
                        self.email_notifier.send_notification(subject, body)
                else:
                    logging.info("Not time to run yet")
                
                # Check every hour
                time.sleep(3600)
                
            except KeyboardInterrupt:
                logging.info("Bot runner stopped by user")
                break
            except Exception as e:
                logging.error(f"Unexpected error in runner: {str(e)}")
                # Send notification for unexpected errors
                subject = "Reddit Video Bot - Unexpected Error"
                body = f"""
                The Reddit Video Maker Bot encountered an unexpected error in the main loop:

                Error: {str(e)}
                
                Stack Trace:
                {traceback.format_exc()}
                
                The bot will attempt to recover in 1 hour.
                """
                self.email_notifier.send_notification(subject, body)
                time.sleep(3600)  # Wait an hour before trying again

if __name__ == "__main__":
    # Check for email configuration
    if not Path('email_config.json').exists():
        print("Error: Email configuration file not found.")
        print("Please run setup_email.bat first.")
        sys.exit(1)
        
    runner = BotRunner()
    runner.run_daily() 