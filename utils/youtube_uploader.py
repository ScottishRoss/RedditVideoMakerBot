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

from utils.profanity_filter import filter_profanity

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

def get_subreddit_emoji(subreddit: str) -> str:
    """Get the appropriate emoji for a subreddit."""
    # Convert subreddit to lowercase for case-insensitive matching
    subreddit = subreddit.lower()
    
    emoji_map = {
        'askreddit': '❓',
        'amitheasshole': '👥',
        'tifu': '😅',
        'trueoffmychest': '💭',
        'confession': '🤫',
        'pettyrevenge': '😈',
        'prorevenge': '⚔️',
        'maliciouscompliance': '😏',
        'idontworkherelady': '👔',
        'unpopularopinion': '🤔',
        'casualconversation': '💬'
    }
    return emoji_map.get(subreddit, '🔥')  # Default to fire emoji if subreddit not found

def generate_engaging_title(reddit_title: str, subreddit: str) -> str:
    """Generate an engaging title for the YouTube video."""
    # Filter profanity from the title
    reddit_title = filter_profanity(reddit_title)
    
    if not reddit_title:  # If title is empty after sanitization, use a default
        reddit_title = "Reddit Story"
    
    # Get the appropriate emoji for the subreddit
    emoji = get_subreddit_emoji(subreddit)
    
    # Format the title with subreddit-specific emoji and hashtags
    return f"{emoji} {reddit_title} | #{subreddit} #RedditStories"

def generate_description(reddit_title: str, subreddit: str, reddit_id: str) -> str:
    """Generate an engaging description for the YouTube video."""
    description = f"""🔥 {reddit_title}

💬 Join the conversation in the comments below!

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
        
        # Debug logging for reddit object
        print(f"Debug - Reddit object thread_title: {reddit_obj.get('thread_title', 'NOT FOUND')}")
        
        # Generate title and description
        title = generate_engaging_title(reddit_obj["thread_title"], subreddit)
        print(f"Debug - Generated title: {title}")
        
        description = generate_description(reddit_obj["thread_title"], subreddit, reddit_obj["thread_id"])
        
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
        
        # Debug logging for request body
        print(f"Debug - Request body title: {request_body['snippet']['title']}")
        
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