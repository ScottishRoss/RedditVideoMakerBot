import os
import sys
from pathlib import Path
from automated_runner import EmailNotifier, BotRunner

def test_email_notifications():
    # Check if configuration file exists
    if not Path('email_config.json').exists():
        print("Error: Email configuration file not found.")
        print("Please run setup_email.bat first.")
        sys.exit(1)

    print("Testing email notifications...")
    notifier = EmailNotifier()
    runner = BotRunner()

    # Test 1: Simulate a retry attempt failure
    print("\nTest 1: Simulating retry attempt failure...")
    subject = "TEST - Reddit Video Bot Error - Attempt 1/3"
    body = """
    This is a TEST email simulating a bot error during retry attempt 1 of 3.

    Simulated Error: Failed to download video
    Stack Trace:
    Traceback (most recent call last):
      File "test.py", line 10, in <module>
        download_video()
    FileNotFoundError: Video file not found

    This was attempt 1 of 3.
    Will retry in 5 minutes.

    Check bot_run.log for more details.
    """
    notifier.send_notification(subject, body)
    print("Test 1 email sent!")

    # Test 2: Simulate all retries exhausted
    print("\nTest 2: Simulating all retries exhausted...")
    subject = "TEST - Reddit Video Bot - All Retries Failed"
    body = """
    This is a TEST email simulating the bot failing all retry attempts.

    The Reddit Video Maker Bot has failed all retry attempts.
    
    Please check the bot_run.log file for detailed error information.
    The bot will attempt to run again in 24 hours.
    """
    notifier.send_notification(subject, body)
    print("Test 2 email sent!")

    # Test 3: Simulate unexpected error
    print("\nTest 3: Simulating unexpected error...")
    subject = "TEST - Reddit Video Bot - Unexpected Error"
    body = """
    This is a TEST email simulating an unexpected error in the main loop.

    Error: Connection lost to Reddit API
    
    Stack Trace:
    Traceback (most recent call last):
      File "main.py", line 50, in <module>
        connect_to_reddit()
    ConnectionError: Failed to establish connection

    The bot will attempt to recover in 1 hour.
    """
    notifier.send_notification(subject, body)
    print("Test 3 email sent!")

    print("\nAll test emails have been sent!")
    print("Please check your email to verify the notifications.")

if __name__ == "__main__":
    test_email_notifications() 