import os
import random
import datetime
import re
from typing import Dict, List, Optional

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from utils.content_filter import sanitize_text, is_advertiser_friendly, get_content_warnings

# OAuth 2.0 scopes for YouTube Data API
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube']

def get_authenticated_service():
    """Get authenticated YouTube API service."""
    credentials = None
    
    # Load credentials from token.json if it exists
    if os.path.exists('token.json'):
        try:
            credentials = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception as e:
            print(f"Error loading credentials: {str(e)}")
            credentials = None
    
    # If credentials don't exist or are invalid, get new ones
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {str(e)}")
                credentials = None
        
        if not credentials:
            try:
                if not os.path.exists('client_secrets.json'):
                    raise FileNotFoundError("client_secrets.json not found. Please ensure it exists in the root directory.")
                
                flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
                credentials = flow.run_local_server(port=0)
                
                # Save credentials for future use
                with open('token.json', 'w') as token:
                    token.write(credentials.to_json())
            except Exception as e:
                print(f"Error during authentication: {str(e)}")
                raise
    
    try:
        return build('youtube', 'v3', credentials=credentials)
    except Exception as e:
        print(f"Error building YouTube service: {str(e)}")
        raise

def generate_engaging_title(reddit_title: str, subreddit: str) -> str:
    """Generate an engaging title for the YouTube video."""
    # Sanitize the title first
    sanitized_title = re.sub(r'[^\w\s-]', '', reddit_title).strip()
    if not sanitized_title:
        sanitized_title = "Reddit Story"  # Fallback title if sanitization results in empty string
    
    # Apply content filtering
    sanitized_title = sanitize_text(sanitized_title)
    
    # Title templates for different subreddits
    templates = {
        'AskReddit': [
            "🔥 {title} | Reddit Stories",
            "😱 {title} | Reddit's Most Shocking Stories",
            "🤔 {title} | Reddit's Best Responses",
            "💭 {title} | Reddit's Most Thought-Provoking Answers",
            "👀 {title} | Reddit's Most Interesting Stories"
        ],
        'AmItheAsshole': [
            "⚖️ {title} | Reddit's Most Controversial Stories",
            "😤 {title} | Reddit's Most Heated Debates",
            "🤯 {title} | Reddit's Most Shocking Confessions",
            "💔 {title} | Reddit's Most Emotional Stories",
            "👊 {title} | Reddit's Most Intense Arguments"
        ],
        'tifu': [
            "😅 {title} | Reddit's Most Hilarious Fails",
            "🤦‍♂️ {title} | Reddit's Most Embarrassing Moments",
            "😱 {title} | Reddit's Most Epic Fails",
            "💀 {title} | Reddit's Most Cringeworthy Stories",
            "🤣 {title} | Reddit's Most Funny Mishaps"
        ],
        'relationships': [
            "❤️ {title} | Reddit's Most Heartwarming Stories",
            "💔 {title} | Reddit's Most Emotional Stories",
            "💑 {title} | Reddit's Most Touching Moments",
            "💘 {title} | Reddit's Most Romantic Stories",
            "💕 {title} | Reddit's Most Beautiful Love Stories"
        ]
    }
    
    # Get template list for the subreddit or use a default one
    template_list = templates.get(subreddit, [
        "🎥 {title} | Reddit Stories",
        "📱 {title} | Reddit's Best Stories",
        "💫 {title} | Reddit's Most Interesting Stories",
        "🌟 {title} | Reddit's Most Engaging Stories",
        "✨ {title} | Reddit's Most Popular Stories"
    ])
    
    # Select a random template and format it
    template = random.choice(template_list)
    return template.format(title=sanitized_title)

def generate_description(reddit_title: str, subreddit: str, reddit_id: str) -> str:
    """Generate an engaging description for the YouTube video."""
    # Apply content filtering to the title
    sanitized_title = sanitize_text(reddit_title)
    
    # Get content warnings if any
    warnings = get_content_warnings(reddit_title)
    warning_text = "\n⚠️ " + "\n⚠️ ".join(warnings) + "\n\n" if warnings else ""
    
    description = f"""🔥 {sanitized_title}

{warning_text}💬 Join the conversation in the comments below!

🔔 Subscribe and turn on notifications to never miss a story!

#RedditStories #{subreddit} #Reddit #Stories #Viral #Trending

"""
    return description

def get_random_publish_time() -> datetime.datetime:
    """Generate a random publish time for tomorrow."""
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    # Random time between 9 AM and 9 PM
    hour = random.randint(9, 21)
    minute = random.randint(0, 59)
    return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)

def upload_video(video_path: str, reddit_obj: Dict, subreddit: str) -> str:
    """Upload video to YouTube with scheduling."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at {video_path}")
        
    try:
        print("Initializing YouTube API service...")
        youtube = get_authenticated_service()
        
        # Generate title and description
        title = generate_engaging_title(reddit_obj["thread_title"], subreddit)
        description = generate_description(reddit_obj["thread_title"], subreddit, reddit_obj["thread_id"])
        
        # Check if content is advertiser-friendly
        if not is_advertiser_friendly(reddit_obj["thread_title"]):
            print("Warning: Content may not be advertiser-friendly. Consider reviewing before publishing.")
        
        # Get random publish time
        publish_time = get_random_publish_time()
        
        print(f"Preparing to upload video: {title}")
        print(f"Scheduled publish time: {publish_time}")
        
        # Set up the video upload request
        request_body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['reddit', 'stories', subreddit.lower(), 'viral', 'trending'],
                'categoryId': '22'  # People & Blogs category
            },
            'status': {
                'privacyStatus': 'private',
                'publishAt': publish_time.isoformat() + 'Z',
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Create the media file upload object
        print("Creating media upload object...")
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True
        )
        
        # Execute the upload request
        print("Starting video upload...")
        request = youtube.videos().insert(
            part=','.join(request_body.keys()),
            body=request_body,
            media_body=media
        )
        
        response = request.execute()
        
        print(f"Video uploaded successfully! Video ID: {response['id']}")
        print(f"Scheduled for: {publish_time}")
        return response['id']
        
    except HttpError as e:
        error_msg = f"An HTTP error occurred during upload: {e.resp.status} {e.content}"
        print(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"An error occurred during upload: {str(e)}"
        print(error_msg)
        raise Exception(error_msg) 