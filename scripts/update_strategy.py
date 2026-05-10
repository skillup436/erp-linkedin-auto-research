import os
import anthropic
from notion_client import Client
from datetime import datetime

# Initialize clients
claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
notion = Client(auth=os.environ.get("NOTION_TOKEN"))

def load_current_strategy():
    """Load the current content strategy from file"""
    with open('content/content_strategy.md', 'r') as f:
        return f.read()

def get_performance_insights():
    """Retrieve recent performance insights from Notion"""
    database_id = os.environ.get("NOTION_INSIGHTS_DB_ID")
    
    # Get the most recent insights
    response = notion.databases.query(
        database_id=database_id,
        sorts=[{"property": "Date", "direction": "descending"}],
        page_size=5
    )
    
    insights = []
    for page in response["results"]:
        # Extract insights text
        insights_prop = page["properties"].get("Insights", {})
        if insights_prop.get("rich_text"):
            insights.append(insights_prop["rich_text"][0]["text"]["content"])
    
    return insights

def get_recent_posts_performance():
    """Get performance data of recent posts"""
    database_id = os.environ.get("NOTION_DATABASE_ID")
    
    response = notion.databases.query(
        database_id=database_id,
        filter={"property": "Status", "select": {"equals": "Published"}},
        sorts=[{"property": "Published Date", "direction": "descending"}],
        page_size=20
    )
    
    posts_data = []
    for page in response["results"]:
        props = page["properties"]
        posts_data.append({
            "content": props.get("Content", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")[:200],
            "language": props.get("Language", {}).get("select", {}).get("name", ""),
            "likes": props.get("Likes", {}).get("number", 0),
            "comments": props.get("Comments", {}).get("number", 0),
            "shares": props.get("Shares", {}).get("number", 0),
            "impressions": props.get("Impressions", {}).get("number", 0)
        })
    
    return posts_data

def refine_strategy_with_ai(current_strategy, insights, posts_performance):
    """Use Claude to refine the content strategy based on performance data"""
    
    prompt = f"""You are helping refine a LinkedIn content strategy for an ERP consultant based on performance data.

CURRENT STRATEGY:
{current_strategy}

RECENT PERFORMANCE INSIGHTS:
{chr(10).join([f"- {insight}" for insight in insights])}

RECENT POSTS PERFORMANCE:
{chr(10).join([f"Language: {p['language']}, Likes: {p['likes']}, Comments: {p['comments']}, Shares: {p['shares']} - Content: {p['content'][:100]}..." for p in posts_performance[:10]])}

Based on this data, provide an UPDATED content strategy that:
1. Keeps what's working well
2. Addresses what's underperforming
3. Identifies new opportunities
4. Maintains the 2/3 French, 1/3 English ratio
5. Stays focused on ERP consulting for the target audience
6. Keeps the contrarian, thought-provoking tone

Provide the updated strategy in the same markdown format as the current strategy. Be specific about:
- Content themes that perform best
- Posting patterns and timing
- Post structure and length preferences
- Topics to explore more
- Topics to avoid or de-emphasize

Return ONLY the updated strategy document, no meta-commentary."""
    
    message = claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text

def save_updated_strategy(updated_strategy):
    """Save the updated strategy back to the repository"""
    # Save to file
    with open('content/content_strategy.md', 'w') as f:
        f.write(updated_strategy)
    
    # Also save a versioned copy to Notion for history
    database_id = os.environ.get("NOTION_STRATEGY_VERSIONS_DB_ID")
    
    notion.pages.create(
        parent={"database_id": database_id},
        properties={
            "Title": {"title": [{"text": {"content": f"Strategy Update - {datetime.now().strftime('%Y-%m-%d')}"}}]},
            "Strategy": {"rich_text": [{"text": {"content": updated_strategy}}]},
            "Date": {"date": {"start": datetime.now().isoformat()}}
        }
    )

if __name__ == "__main__":
    print("Starting strategy refinement...")
    
    # Load current data
    current_strategy = load_current_strategy()
    insights = get_performance_insights()
    posts_performance = get_recent_posts_performance()
    
    print(f"Loaded {len(insights)} insights and {len(posts_performance)} posts")
    
    # Generate refined strategy
    print("Analyzing performance and refining strategy with Claude...")
    updated_strategy = refine_strategy_with_ai(current_strategy, insights, posts_performance)
    
    # Save updated strategy
    save_updated_strategy(updated_strategy)
    print("Strategy updated successfully!")
    print("\nUpdated Strategy Preview:")
    print(updated_strategy[:500] + "...")
