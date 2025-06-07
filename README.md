## Requirements

- Python 3.10
- FFmpeg
- Gmail account (for email notifications)
- Reddit API credentials
- YouTube API credentials (if uploading to YouTube)

## Installation

1. Clone this repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install FFmpeg (if not already installed)
4. Set up your Reddit API credentials:
   - Visit [Reddit Apps page](https://www.reddit.com/prefs/apps)
   - Create a new app (script type)
   - Note down the client ID and client secret

## Configuration

1. Set up email notifications:

   ```bash
   setup_email.bat
   ```

   - Enter your Gmail address
   - Enter your Gmail App Password (not your regular password)
   - To get an App Password:
     1. Go to your Google Account settings
     2. Navigate to Security
     3. Enable 2-Step Verification if not already enabled
     4. Go to App Passwords
     5. Generate a new app password for "Mail"

2. Configure the bot:
   - Edit `config.toml` with your settings
   - Set your Reddit API credentials
   - Configure video settings (background, voice, etc.)

## Running the Bot

### Automated Daily Run

1. Set up the scheduled task:

   ```bash
   # Right-click setup_scheduler.ps1 and select "Run with PowerShell"
   ```

   This will:

   - Create a daily task at 9:00 AM
   - Run even if the computer is on battery
   - Send email notifications for any issues

2. Verify the setup:
   - Task Scheduler will open automatically
   - Look for "RedditVideoMakerBot" in the list
   - You can modify the schedule if needed

### Manual Run

1. Run the bot directly:

   ```bash
   python main.py
   ```

2. Or use the batch file:
   ```bash
   run_bot_daily.bat
   ```

### Testing Email Notifications

1. Run the email test:

   ```bash
   test_emails.bat
   ```

   This will send three test emails:

   - A retry attempt failure
   - All retries exhausted
   - An unexpected error

2. Check your email to verify the notifications

## Monitoring

- Check `bot_run.log` for detailed logs
- Email notifications will be sent for:
  - Each failed attempt
  - When all retries are exhausted
  - Any unexpected errors

## Troubleshooting

1. If emails aren't working:

   - Verify your Gmail App Password
   - Check `email_config.json` exists
   - Run `test_emails.bat` to test

2. If the bot isn't running:
   - Check Task Scheduler
   - Verify Python 3.10 is installed
   - Check `bot_run.log` for errors
