import time
import logging
import sys
from datetime import datetime, timedelta
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_run.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def run_bot():
    """Run the main bot script"""
    try:
        logging.info("Starting bot run")
        subprocess.run(['python', 'main.py'], check=True)
        logging.info("Bot run completed successfully")
        return True
    except Exception as e:
        logging.error(f"Error running bot: {str(e)}")
        return False

def main():
    """Main scheduler loop"""
    logging.info("Starting automated runner")
    
    while True:
        try:
            # Run the bot
            run_bot()
            
            # Wait for 24 hours before next run
            logging.info("Waiting 24 hours until next run")
            time.sleep(24 * 60 * 60)  # 24 hours in seconds
            
        except KeyboardInterrupt:
            logging.info("Bot runner stopped by user")
            break
        except Exception as e:
            logging.error(f"Unexpected error in runner: {str(e)}")
            # Wait an hour before retrying on error
            time.sleep(3600)

if __name__ == "__main__":
    main() 