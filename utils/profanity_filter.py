import re
from typing import List, Set

# List of words to censor
PROFANITY_LIST = {
    # Common profanity
    'fuck', 'shit', 'ass', 'bitch', 'damn', 'hell',
    # Variations with common letter substitutions
    'f*ck', 'f**k', 'f***', 'sh*t', 's**t', 'a**', 'b*tch', 'b**ch',
    # Common prefixes/suffixes
    'motherf', 'motherf*ck', 'motherf**k', 'motherf***',
    # Common misspellings
    'fuk', 'shyt', 'bich', 'damm',
    
    # Sexual terms
    'sex', 'sexual', 'porn', 'pornography', 'nude', 'nudes', 'naked',
    'penis', 'dick', 'cock', 'pussy', 'vagina', 'boobs', 'tits', 'asshole',
    'butt', 'butthole', 'anus', 'anal', 'masturbate', 'masturbation',
    'ejaculate', 'ejaculation', 'sperm', 'cum', 'orgasm', 'orgasmic',
    
    # Violence and gore
    'kill', 'killing', 'murder', 'death', 'dead', 'die', 'dying',
    'blood', 'bloody', 'gore', 'gory', 'torture', 'tortured',
    'suicide', 'suicidal', 'abuse', 'abused', 'abusive',
    
    # Hate speech and discrimination
    'nazi', 'n*zi', 'n*gg', 'n*gga', 'n*gger', 'racist', 'racism',
    'sexist', 'sexism', 'homophobic', 'homophobia', 'transphobic',
    'transphobia', 'bigot', 'bigotry', 'slave', 'slavery',
    
    # Drugs and alcohol
    'drug', 'drugs', 'cocaine', 'heroin', 'meth', 'weed', 'marijuana',
    'crack', 'acid', 'lsd', 'ecstasy', 'mdma', 'alcohol', 'drunk',
    'drinking', 'beer', 'wine', 'liquor', 'vodka', 'whiskey',
    
    # Self-harm and mental health
    'suicide', 'suicidal', 'self-harm', 'cutting', 'depression',
    'depressed', 'anxiety', 'anxious', 'panic', 'panic attack',
    
    # Controversial topics
    'abortion', 'pro-life', 'pro-choice', 'contraception',
    'religion', 'religious', 'atheist', 'atheism',
    'politics', 'political', 'government', 'conspiracy',
    
    # Body parts and functions
    'poop', 'pee', 'urine', 'urinate', 'defecate', 'defecation',
    'fart', 'burp', 'vomit', 'puke', 'sweat', 'sweating',
    
    # Additional offensive terms
    'stupid', 'idiot', 'dumb', 'retard', 'retarded', 'moron',
    'fat', 'ugly', 'gross', 'disgusting', 'hate', 'hated',
    
    # Common variations and leetspeak
    'f*ck', 'f**k', 'f***', 'sh*t', 's**t', 'a**', 'b*tch', 'b**ch',
    'd*ck', 'c*ck', 'p*ssy', 'v*gina', 'b*obs', 't*ts',
    'k*ll', 'd*ath', 'bl**d', 'g*re', 'dr*g', 'dr*nk',
    
    # Add more words as needed
}

def censor_word(word: str) -> str:
    """Censor a single word by replacing all but first and last letter with asterisks."""
    if len(word) <= 2:
        return word[0] + '*' * (len(word) - 1)
    return word[0] + '*' * (len(word) - 2) + word[-1]

def filter_profanity(text: str) -> str:
    """
    Filter profanity from text by censoring matching words.
    Preserves case and punctuation.
    """
    if not text:
        return text
        
    # Split text into words while preserving punctuation
    words = re.findall(r'\b\w+\b|[^\w\s]', text)
    
    # Process each word
    for i, word in enumerate(words):
        # Skip if not a word or too short
        if not word.isalpha() or len(word) < 3:
            continue
            
        # Check if word (case-insensitive) is in profanity list
        if word.lower() in PROFANITY_LIST:
            words[i] = censor_word(word)
    
    # Reconstruct the text
    return ''.join(words)

def filter_profanity_list(texts: List[str]) -> List[str]:
    """Filter profanity from a list of texts."""
    return [filter_profanity(text) for text in texts]

def add_profanity_words(words: Set[str]) -> None:
    """Add additional words to the profanity list."""
    PROFANITY_LIST.update(words)

def remove_profanity_words(words: Set[str]) -> None:
    """Remove words from the profanity list."""
    PROFANITY_LIST.difference_update(words) 