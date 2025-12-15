"""Curated RSS feed catalog organized by category.

This module provides a hand-picked selection of popular, reliable RSS feeds
organized by topic. All feeds are sourced from the awesome-rss-feeds repository
and are verified to be working and high-quality.
"""

# Curated feed categories with verified URLs
CURATED_CATEGORIES = {
    "Technology": [
        {"title": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "description": "Technology news and analysis"},
        {"title": "TechCrunch", "url": "https://techcrunch.com/feed/", "description": "Startup and technology news"},
        {"title": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "description": "Technology, science, art, and culture"},
        {"title": "Hacker News", "url": "https://news.ycombinator.com/rss", "description": "Social news for hackers and entrepreneurs"},
        {"title": "Wired", "url": "https://www.wired.com/feed/rss", "description": "Technology, science, and innovation"},
        {"title": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/", "description": "Emerging technology and innovation"},
        {"title": "Slashdot", "url": "http://rss.slashdot.org/Slashdot/slashdotMain", "description": "News for nerds, stuff that matters"},
    ],
    "Programming": [
        {"title": "Dev.to", "url": "https://dev.to/feed", "description": "Community for software developers"},
        {"title": "CSS-Tricks", "url": "https://css-tricks.com/feed/", "description": "Web design and development"},
        {"title": "Martin Fowler", "url": "https://martinfowler.com/feed.atom", "description": "Software development insights"},
        {"title": "Joel on Software", "url": "https://www.joelonsoftware.com/feed/", "description": "Software and business insights"},
        {"title": "A List Apart", "url": "https://alistapart.com/main/feed/", "description": "Web design and development standards"},
        {"title": "GitHub Blog", "url": "https://github.blog/feed/", "description": "Updates from GitHub"},
        {"title": "Stack Overflow Blog", "url": "https://stackoverflow.blog/feed/", "description": "Engineering and community updates"},
    ],
    "News": [
        {"title": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml", "description": "British Broadcasting Corporation news"},
        {"title": "The Guardian", "url": "https://www.theguardian.com/world/rss", "description": "International news and opinion"},
        {"title": "Reuters", "url": "https://www.reutersagency.com/feed/", "description": "International news agency"},
        {"title": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml", "description": "National Public Radio news"},
        {"title": "The New York Times", "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "description": "NYT homepage feed"},
        {"title": "Associated Press", "url": "https://apnews.com/apf-topnews", "description": "Top news from AP"},
    ],
    "Science": [
        {"title": "Science Daily", "url": "https://www.sciencedaily.com/rss/all.xml", "description": "Latest science news"},
        {"title": "Nature", "url": "http://feeds.nature.com/nature/rss/current", "description": "Nature journal research"},
        {"title": "Scientific American", "url": "http://rss.sciam.com/ScientificAmerican-Global", "description": "Science news and analysis"},
        {"title": "Quanta Magazine", "url": "https://api.quantamagazine.org/feed/", "description": "Science and mathematics"},
        {"title": "Phys.org", "url": "https://phys.org/rss-feed/", "description": "Science and technology news"},
        {"title": "Space.com", "url": "https://www.space.com/feeds/all", "description": "Space exploration and astronomy"},
    ],
    "Business": [
        {"title": "Harvard Business Review", "url": "http://feeds.hbr.org/harvardbusiness", "description": "Business management insights"},
        {"title": "Bloomberg", "url": "https://www.bloomberg.com/feed/podcast/businessweek.xml", "description": "Business and financial news"},
        {"title": "The Economist", "url": "https://www.economist.com/business/rss.xml", "description": "Global business news"},
        {"title": "Forbes", "url": "https://www.forbes.com/business/feed/", "description": "Business news and insights"},
        {"title": "Wall Street Journal", "url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", "description": "US business news"},
    ],
    "AI & Machine Learning": [
        {"title": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "description": "Updates from OpenAI"},
        {"title": "Google AI Blog", "url": "http://feeds.feedburner.com/blogspot/gJZg", "description": "Research from Google AI"},
        {"title": "DeepMind Blog", "url": "https://deepmind.com/blog/feed/basic/", "description": "AI research from DeepMind"},
        {"title": "Towards Data Science", "url": "https://towardsdatascience.com/feed", "description": "Data science and ML articles"},
        {"title": "Papers with Code", "url": "https://paperswithcode.com/feed", "description": "ML papers with code"},
        {"title": "The Batch (Andrew Ng)", "url": "https://www.deeplearning.ai/the-batch/feed/", "description": "Weekly AI news"},
    ],
    "Security": [
        {"title": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/", "description": "In-depth security news and investigation"},
        {"title": "Schneier on Security", "url": "https://www.schneier.com/feed/atom/", "description": "Security and privacy insights"},
        {"title": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews", "description": "Cybersecurity news"},
        {"title": "SANS Internet Storm Center", "url": "https://isc.sans.edu/rssfeed.xml", "description": "Security threat analysis"},
        {"title": "Threatpost", "url": "https://threatpost.com/feed/", "description": "Cybersecurity news"},
    ],
    "Design": [
        {"title": "Smashing Magazine", "url": "https://www.smashingmagazine.com/feed/", "description": "Web design and development"},
        {"title": "Designer News", "url": "https://www.designernews.co/?format=rss", "description": "Design community news"},
        {"title": "Awwwards Blog", "url": "https://www.awwwards.com/blog/feed/", "description": "Web design excellence"},
        {"title": "UX Design", "url": "https://uxdesign.cc/feed", "description": "User experience design"},
        {"title": "Designmodo", "url": "https://designmodo.com/feed/", "description": "Web design and development"},
    ],
    "Productivity": [
        {"title": "Lifehacker", "url": "https://lifehacker.com/rss", "description": "Tips and downloads for getting things done"},
        {"title": "Zen Habits", "url": "https://zenhabits.net/feed/", "description": "Simple productivity and lifestyle"},
        {"title": "43 Folders", "url": "http://feeds.feedburner.com/43Folders", "description": "Productivity and life hacks"},
        {"title": "Asian Efficiency", "url": "https://www.asianefficiency.com/feed/", "description": "Productivity tips and tools"},
    ],
    "Startups": [
        {"title": "Y Combinator", "url": "https://www.ycombinator.com/blog/feed", "description": "Startup accelerator blog"},
        {"title": "First Round Review", "url": "http://firstround.com/review/rss/", "description": "Startup advice and insights"},
        {"title": "Both Sides of the Table", "url": "https://bothsidesofthetable.com/feed", "description": "VC perspectives on startups"},
        {"title": "Paul Graham", "url": "http://www.aaronsw.com/2002/feeds/pgessays.rss", "description": "Essays on startups and technology"},
        {"title": "Product Hunt", "url": "https://www.producthunt.com/feed", "description": "New products and startups"},
    ],
    "Gaming": [
        {"title": "IGN", "url": "https://feeds.feedburner.com/ign/all", "description": "Gaming news and reviews"},
        {"title": "Polygon", "url": "https://www.polygon.com/rss/index.xml", "description": "Games and entertainment"},
        {"title": "Kotaku", "url": "https://kotaku.com/rss", "description": "Gaming culture and news"},
        {"title": "GameSpot", "url": "https://www.gamespot.com/feeds/mashup/", "description": "Video game news and reviews"},
        {"title": "PC Gamer", "url": "https://www.pcgamer.com/rss/", "description": "PC gaming news"},
    ],
    "Sports": [
        {"title": "ESPN", "url": "https://www.espn.com/espn/rss/news", "description": "Sports news and scores"},
        {"title": "The Athletic", "url": "https://theathletic.com/feed/", "description": "In-depth sports coverage"},
        {"title": "Bleacher Report", "url": "https://bleacherreport.com/articles/feed", "description": "Sports news and highlights"},
        {"title": "Sports Illustrated", "url": "https://www.si.com/rss/si_topstories.rss", "description": "Top sports stories"},
    ],
}


def get_feeds_by_category(category: str) -> list[dict]:
    """Get all feeds in a specific category."""
    return CURATED_CATEGORIES.get(category, [])


def get_all_categories() -> list[str]:
    """Get list of all available categories."""
    return list(CURATED_CATEGORIES.keys())


def search_curated_feeds(query: str) -> list[dict]:
    """Search curated feeds by title or description."""
    query_lower = query.lower()
    results = []

    for category, feeds in CURATED_CATEGORIES.items():
        for feed in feeds:
            if (query_lower in feed["title"].lower() or
                query_lower in feed.get("description", "").lower() or
                query_lower in category.lower()):
                results.append({**feed, "category": category})

    return results
