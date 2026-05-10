import os
import json
import anthropic
from notion_client import Client
from datetime import datetime
import random

# Initialize clients
claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
notion = Client(auth=os.environ.get("NOTION_TOKEN"))

def load_content_files():
    """Load content strategy, audience profile, and examples"""
    with open('content/content_strategy.md', 'r') as f:
        strategy = f.read()
    
    with open('content/audience_profile.md', 'r') as f:
        audience = f.read()
    
    examples = []
    for filename in os.listdir('content/examples'):
        if filename.endswith('.md'):
            with open(f'content/examples/{filename}', 'r') as f:
                examples.append(f.read())
    
    return strategy, audience, examples

def determine_language():
    """Determine post language based on 2/3 French, 1/3 English ratio"""
    return 'French' if random.random() < 0.67 else 'English'

def generate_post():
    """Generate a LinkedIn post using Claude"""
    strategy, audience, examples = load_content_files()
    language = determine_language()
    
    prompt = f"""You are creating LinkedIn content for an ERP consulting professional.

AUDIENCE PROFILE:
{audience}

CONTENT STRATEGY:
{strategy}

EXAMPLE POSTS:
{chr(10).join(examples)}

Generate a new LinkedIn post in {language} that:
- Is contrarian and thought-provoking
- Targets ERP consultants and professionals
- Follows the tone and structure of the examples
- Addresses real consulting challenges
- Is 50-150 words
- Does not use hashtags

Return ONLY the post text, no metadata or explanations."""
    
    message = claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text, language

def save_to_notion(post_text, language):
    """Save generated post to Notion database"""
    database_id = os.environ.get("NOTION_DATABASE_ID")
    
    notion.pages.create(
        parent={"database_id": database_id},
        properties={
            "Title": {"title": [{"text": {"content": f"{language} Post - {datetime.now().strftime('%Y-%m-%d')}"}}]},
            "Content": {"rich_text": [{"text": {"content": post_text}}]},
            "Language": {"select": {"name": language}},
            "Status": {"select": {"name": "Draft"}},
            "Created": {"date": {"start": datetime.now().isoformat()}}
        }
    )

if __name__ == "__main__":
    post_text, language = generate_post()
    save_to_notion(post_text, language)
    print(f"Generated {language} post and saved to Notion:")
    print(post_text)
