import os
import json
from apify_client import ApifyClient
from notion_client import Client
from datetime import datetime, timedelta
import anthropic

# Initialize clients
apify = ApifyClient(os.environ.get("APIFY_API_TOKEN"))
notion = Client(auth=os.environ.get("NOTION_TOKEN"))
claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def get_published_posts():
    """Retrieve published posts from Notion database"""
    database_id = os.environ.get("NOTION_DATABASE_ID")
    
    # Query for posts published in the last 30 days
    response = notion.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Status", "select": {"equals": "Published"}},
                {"property": "Published Date", "date": {"past_week": {}}}
            ]
        }
    )
    
    return response["results"]

def scrape_linkedin_metrics(profile_url):
    """Use Apify to scrape LinkedIn post metrics"""
    # Run Apify actor for LinkedIn scraping
    run = apify.actor("apify/linkedin-profile-scraper").call(
        run_input={"profileUrls": [profile_url]}
    )
    
    # Get results from dataset
    results = []
    for item in apify.dataset(run["defaultDatasetId"]).iterate_items():
        results.append(item)
    
    return results

def analyze_performance(posts_data):
    """Analyze post performance and generate insights using Claude"""
    metrics_summary = []
    
    for post in posts_data:
        metrics_summary.append({
            "content": post.get("content", "")[:100],
            "likes": post.get("likes", 0),
            "comments": post.get("comments", 0),
            "shares": post.get("shares", 0),
            "impressions": post.get("impressions", 0)
        })
    
    prompt = f"""Analyze the performance of these LinkedIn posts:

{json.dumps(metrics_summary, indent=2)}

Provide insights on:
1. Which types of posts performed best
2. Optimal posting patterns
3. Content themes that resonate
4. Recommendations for future posts

Be specific and actionable."""
    
    message = claude.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text

def update_notion_with_metrics(post_id, metrics):
    """Update Notion database with performance metrics"""
    notion.pages.update(
        page_id=post_id,
        properties={
            "Likes": {"number": metrics.get("likes", 0)},
            "Comments": {"number": metrics.get("comments", 0)},
            "Shares": {"number": metrics.get("shares", 0)},
            "Impressions": {"number": metrics.get("impressions", 0)},
            "Last Analyzed": {"date": {"start": datetime.now().isoformat()}}
        }
    )

def save_insights_to_notion(insights):
    """Save performance insights to a separate Notion page"""
    database_id = os.environ.get("NOTION_INSIGHTS_DB_ID")
    
    notion.pages.create(
        parent={"database_id": database_id},
        properties={
            "Title": {"title": [{"text": {"content": f"Performance Analysis - {datetime.now().strftime('%Y-%m-%d')}"}}]},
            "Insights": {"rich_text": [{"text": {"content": insights}}]},
            "Date": {"date": {"start": datetime.now().isoformat()}}
        }
    )

if __name__ == "__main__":
    # Get published posts from Notion
    posts = get_published_posts()
    print(f"Found {len(posts)} published posts to analyze")
    
    # Scrape metrics from LinkedIn
    profile_urls = [
        os.environ.get("LINKEDIN_PROFILE_EN"),
        os.environ.get("LINKEDIN_PROFILE_FR")
    ]
    
    all_metrics = []
    for url in profile_urls:
        metrics = scrape_linkedin_metrics(url)
        all_metrics.extend(metrics)
    
    # Analyze performance
    insights = analyze_performance(all_metrics)
    print("Performance Insights:")
    print(insights)
    
    # Save insights
    save_insights_to_notion(insights)
    print("Analysis complete and saved to Notion")
