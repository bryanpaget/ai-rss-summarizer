"""CLI commands for user context management."""

import uuid
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

try:
    import questionary
    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False

from .knowledge import KnowledgeBase, UserContext
from .user_context import UserContextStore

app = typer.Typer(
    name="context",
    help="User context management commands",
    invoke_without_command=True,
)
console = Console(force_terminal=True, legacy_windows=True)


@app.callback(invoke_without_command=True)
def context_main(ctx: typer.Context):
    """
    Manage user contexts for personalized relevance.

    User contexts help the system understand what you're interested in,
    so it can prioritize and filter articles that matter to you.

    Context types:
    - project: Current work projects (e.g., "Building a chatbot")
    - interest: General interests (e.g., "Machine learning", "Climate")
    - watching: Topics you're monitoring (e.g., "Company X earnings")
    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided - show interactive help
        console.print()
        console.print(Panel("[bold]User Context Management[/bold]", style="blue"))
        console.print()
        console.print("Contexts help personalize article relevance and filtering.")
        console.print()
        console.print("[bold]Context Types:[/bold]")
        console.print("  [cyan]project[/cyan]   - Current work projects")
        console.print("  [cyan]interest[/cyan]  - General interests")
        console.print("  [cyan]watching[/cyan]  - Topics you're monitoring")
        console.print()
        console.print("[bold]Commands:[/bold]")
        console.print()

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        table.add_row("add", "Add a new context")
        table.add_row("list", "List all contexts")
        table.add_row("remove", "Remove a context")
        table.add_row("show", "Show context details")

        console.print(table)
        console.print()
        console.print("[dim]Examples:[/dim]")
        console.print("  rss context add project \"Building chatbot\"")
        console.print("  rss context add interest \"Machine learning\"")
        console.print("  rss context list")
        console.print("  rss context remove \"Building chatbot\"")
        console.print()


@app.command("add")
def add_context(
    context_type: str = typer.Argument(
        ...,
        help="Type: project, interest, or watching",
    ),
    name: str = typer.Argument(
        ...,
        help="Context name",
    ),
    description: str = typer.Option(
        None,
        "--desc", "-d",
        help="Description of the context",
    ),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """
    Add a new user context.

    Contexts help personalize article relevance scoring.

    Examples:
        rss context add project "Building a chatbot"
        rss context add interest "Machine learning" --desc "Deep learning, NLP"
        rss context add watching "OpenAI announcements"
    """
    # Validate context type
    valid_types = ["project", "interest", "watching"]
    if context_type.lower() not in valid_types:
        console.print(f"[red]Invalid context type: {context_type}[/red]")
        console.print(f"[dim]Valid types: {', '.join(valid_types)}[/dim]")
        raise typer.Exit(1)

    kb = KnowledgeBase(kb_path)

    context = UserContext(
        id=str(uuid.uuid4()),
        context_type=context_type.lower(),
        name=name,
        description=description,
    )

    kb.save_context(context)
    console.print(f"[green]Added {context_type}: {name}[/green]")

    if description:
        console.print(f"[dim]Description: {description}[/dim]")


@app.command("list")
def list_contexts(
    context_type: Optional[str] = typer.Option(
        None,
        "--type", "-t",
        help="Filter by context type",
    ),
    active_only: bool = typer.Option(
        False,
        "--active",
        help="Show only active contexts",
    ),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """
    List all user contexts.

    Examples:
        rss context list                # List all contexts
        rss context list --type project # List only projects
        rss context list --active       # List only active contexts
    """
    kb = KnowledgeBase(kb_path)
    contexts = kb.get_contexts(active_only=active_only)

    # Filter by type if specified
    if context_type:
        contexts = [c for c in contexts if c.context_type == context_type.lower()]

    if not contexts:
        console.print("[yellow]No contexts found.[/yellow]")
        console.print()
        console.print("[dim]Add one with:[/dim]")
        console.print("  rss context add project \"Project Name\"")
        console.print("  rss context add interest \"Topic\"")
        return

    table = Table(title="User Contexts")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status")
    table.add_column("Description")

    for ctx in contexts:
        status = "[green]Active[/green]" if ctx.active else "[dim]Inactive[/dim]"
        desc = (ctx.description or "")[:50]
        if ctx.description and len(ctx.description) > 50:
            desc += "..."
        table.add_row(ctx.context_type, ctx.name, status, desc)

    console.print(table)
    console.print()
    console.print(f"[dim]Total: {len(contexts)} context(s)[/dim]")


@app.command("remove")
def remove_context(
    name: str = typer.Argument(
        ...,
        help="Name of the context to remove",
    ),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """
    Remove a user context.

    Examples:
        rss context remove "Building chatbot"
        rss context remove "Machine learning"
    """
    kb = KnowledgeBase(kb_path)
    contexts = kb.get_contexts(active_only=False)

    # Find matching context
    matching = [c for c in contexts if c.name.lower() == name.lower()]

    if not matching:
        console.print(f"[yellow]Context not found: {name}[/yellow]")
        console.print()
        console.print("[dim]Available contexts:[/dim]")
        for ctx in contexts[:5]:
            console.print(f"  - {ctx.name}")
        return

    context = matching[0]

    # Delete context
    try:
        kb.delete_context(context.id)
        console.print(f"[green]Removed: {context.name}[/green]")
    except AttributeError:
        # Fallback if delete_context doesn't exist
        context.active = False
        kb.save_context(context)
        console.print(f"[green]Deactivated: {context.name}[/green]")


@app.command("show")
def show_context(
    name: str = typer.Argument(
        ...,
        help="Name of the context to show",
    ),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """
    Show details of a specific context.

    Examples:
        rss context show "Building chatbot"
    """
    kb = KnowledgeBase(kb_path)
    contexts = kb.get_contexts(active_only=False)

    # Find matching context
    matching = [c for c in contexts if c.name.lower() == name.lower()]

    if not matching:
        console.print(f"[yellow]Context not found: {name}[/yellow]")
        return

    context = matching[0]

    console.print(Panel(f"[bold]{context.name}[/bold]", style="blue"))
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Type", context.context_type)
    table.add_row("Status", "Active" if context.active else "Inactive")
    if context.description:
        table.add_row("Description", context.description)
    if hasattr(context, 'created_at') and context.created_at:
        table.add_row("Created", str(context.created_at)[:19])
    if hasattr(context, 'keywords') and context.keywords:
        table.add_row("Keywords", ", ".join(context.keywords[:10]))

    console.print(table)


# Comprehensive RSS Feed Taxonomy
# Structure: Category -> Subject -> Feeds (name, url)
FEED_TAXONOMY = {
    "Technology": {
        "AI & Machine Learning": [
            {"name": "Ars Technica AI", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},
            {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
            {"name": "Wired AI", "url": "https://www.wired.com/feed/category/science/latest/rss"},
            {"name": "The Verge AI", "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"},
        ],
        "Cybersecurity": [
            {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml"},
            {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/"},
            {"name": "Schneier on Security", "url": "https://www.schneier.com/blog/index.rdf"},
            {"name": "Threatpost", "url": "https://threatpost.com/feed/"},
        ],
        "Software Development": [
            {"name": "InfoQ", "url": "https://feed.infoq.com/"},
            {"name": "The Register - Software", "url": "https://www.theregister.com/software/headlines.atom"},
            {"name": "Slashdot - Developers", "url": "https://rss.slashdot.org/Slashdot/slashdotDevelopers"},
            {"name": "DZone", "url": "https://feeds.dzone.com/home"},
        ],
        "Hardware": [
            {"name": "Tom's Hardware", "url": "https://www.tomshardware.com/rss.xml"},
            {"name": "AnandTech", "url": "https://www.anandtech.com/rss/"},
            {"name": "Engadget Hardware", "url": "https://www.engadget.com/rss.xml"},
            {"name": "ZDNet Hardware", "url": "https://www.zdnet.com/topic/hardware/rss.xml"},
        ],
        "Startups & VC": [
            {"name": "TechCrunch Startups", "url": "https://techcrunch.com/startups/feed/"},
            {"name": "VentureBeat", "url": "https://venturebeat.com/feed/"},
            {"name": "Sifted", "url": "https://sifted.eu/feed/"},
        ],
    },
    "World News": {
        "Global Headlines": [
            {"name": "BBC World News", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
            {"name": "Al Jazeera English", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
            {"name": "The Guardian World", "url": "https://www.theguardian.com/world/rss"},
            {"name": "The Atlantic World", "url": "https://www.theatlantic.com/feed/channel/world/"},
        ],
        "United States": [
            {"name": "NYT US News", "url": "https://rss.nytimes.com/services/xml/rss/nyt/US.xml"},
            {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml"},
        ],
        "Europe": [
            {"name": "BBC Europe", "url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml"},
            {"name": "Deutsche Welle", "url": "https://rss.dw.com/rdf/rss-en-all"},
            {"name": "The Local", "url": "https://www.thelocal.com/feed/"},
        ],
        "Asia & Middle East": [
            {"name": "Al Jazeera Middle East", "url": "https://www.aljazeera.com/xml/rss/middle-east.xml"},
            {"name": "BBC Asia", "url": "https://feeds.bbci.co.uk/news/world/asia/rss.xml"},
            {"name": "South China Morning Post", "url": "https://www.scmp.com/rss/91/feed"},
        ],
    },
    "Business & Finance": {
        "Markets": [
            {"name": "WSJ Markets", "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"},
            {"name": "MarketWatch", "url": "http://feeds.marketwatch.com/marketwatch/marketupdates/"},
            {"name": "Bloomberg Markets", "url": "https://www.bloomberg.com/feeds/markets/headlines.xml"},
        ],
        "Economy": [
            {"name": "NYT Economy", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml"},
            {"name": "The Economist", "url": "https://www.economist.com/sections/economics/rss.xml"},
            {"name": "Financial Times", "url": "https://www.ft.com/?format=rss"},
        ],
        "Personal Finance": [
            {"name": "Kiplingers", "url": "https://www.kiplinger.com/rss/index.php"},
            {"name": "NerdWallet", "url": "https://www.nerdwallet.com/blog/feed/"},
            {"name": "The Penny Hoarder", "url": "https://www.thepennyhoarder.com/feed/"},
        ],
    },
    "Science": {
        "Space & Astronomy": [
            {"name": "NASA Breaking News", "url": "https://www.nasa.gov/rss/breaking_news.rss"},
            {"name": "Space.com", "url": "https://www.space.com/home/feed/site.xml"},
            {"name": "Sky & Telescope", "url": "https://skyandtelescope.org/feed/"},
        ],
        "Biological Sciences": [
            {"name": "Nature News", "url": "https://www.nature.com/nature.rss"},
            {"name": "Science Magazine", "url": "https://www.sciencemag.org/rss/news_current.xml"},
            {"name": "Scientific American", "url": "https://rss.sciam.com/ScientificAmerican-News"},
        ],
    },
    "Politics": {
        "US Federal": [
            {"name": "Politico Pulse", "url": "https://www.politico.com/rss/politicopulse.xml"},
            {"name": "The Hill", "url": "https://thehill.com/rss/syndication/all"},
            {"name": "RealClearPolitics", "url": "https://www.realclearpolitics.com/index.xml"},
        ],
        "Analysis": [
            {"name": "FiveThirtyEight", "url": "https://fivethirtyeight.com/features/feed/"},
            {"name": "The Atlantic Politics", "url": "https://www.theatlantic.com/feed/channel/politics/"},
            {"name": "Vox Politics", "url": "https://www.vox.com/rss/politics/index.xml"},
        ],
    },
    "Health & Wellness": {
        "Medical Research": [
            {"name": "Mayo Clinic", "url": "https://sharing.mayoclinic.org/feed/"},
            {"name": "Harvard Health", "url": "https://www.health.harvard.edu/blog/feed"},
            {"name": "Medical News Today", "url": "https://rss.medicalnewstoday.com/featurednews.xml"},
        ],
    },
    "Entertainment & Culture": {
        "Movies & TV": [
            {"name": "Variety", "url": "https://variety.com/feed/"},
            {"name": "Hollywood Reporter", "url": "https://www.hollywoodreporter.com/feed/"},
            {"name": "Entertainment Weekly", "url": "https://ew.com/feed/"},
        ],
        "Music": [
            {"name": "Pitchfork", "url": "https://pitchfork.com/feed/rss"},
            {"name": "Rolling Stone", "url": "https://www.rollingstone.com/feed/"},
            {"name": "Billboard", "url": "https://www.billboard.com/feed/"},
        ],
    },
    "Sports": {
        "General Sports": [
            {"name": "ESPN Headlines", "url": "https://www.espn.com/espn/rss/news"},
            {"name": "CBS Sports", "url": "https://www.cbssports.com/rss/headlines/"},
            {"name": "Sports Illustrated", "url": "https://www.si.com/.rss/full/"},
        ],
    },
    "Gaming": {
        "Game News": [
            {"name": "IGN All", "url": "https://feeds.feedburner.com/ign/all"},
            {"name": "Kotaku", "url": "https://kotaku.com/rss"},
            {"name": "Polygon", "url": "https://www.polygon.com/rss/index.xml"},
        ],
        "PC Gaming": [
            {"name": "PC Gamer", "url": "https://www.pcgamer.com/rss"},
            {"name": "Rock Paper Shotgun", "url": "https://www.rockpapershotgun.com/feed"},
        ],
    },
    "Lifestyle": {
        "Home & Garden": [
            {"name": "Apartment Therapy", "url": "https://www.apartmenttherapy.com/main.rss"},
            {"name": "Design Milk", "url": "https://design-milk.com/feed/"},
        ],
    },
    "Arts & Design": {
        "Architecture": [
            {"name": "Dezeen", "url": "https://www.dezeen.com/feed/"},
            {"name": "ArchDaily", "url": "https://www.archdaily.com/feed"},
        ],
    },
    "Education & Learning": {
        "Higher Ed": [
            {"name": "Chronicle of Higher Ed", "url": "https://www.chronicle.com/section/news/rss"},
            {"name": "Inside Higher Ed", "url": "https://www.insidehighered.com/rss/feed/news"},
        ],
    },
    "Food & Cooking": {
        "Recipes": [
            {"name": "Serious Eats", "url": "https://www.seriouseats.com/rss"},
            {"name": "Simply Recipes", "url": "https://www.simplyrecipes.com/rss"},
        ],
    },
    "Travel": {
        "Destinations": [
            {"name": "Lonely Planet", "url": "https://www.lonelyplanet.com/articles/feed"},
            {"name": "Conde Nast Traveler", "url": "https://www.cntraveler.com/feed/rss"},
        ],
    },
    "Environment & Sustainability": {
        "Climate News": [
            {"name": "Grist", "url": "https://grist.org/feed/"},
            {"name": "Mongabay", "url": "https://news.mongabay.com/feed/"},
            {"name": "Environment News Service", "url": "https://ens-newswire.com/feed/"},
        ],
    },
}

# Legacy format for backwards compatibility with topic-based selection
SETUP_CATEGORIES = {
    category: list(subjects.keys())
    for category, subjects in FEED_TAXONOMY.items()
}


def run_setup_wizard_inline(store: UserContextStore = None) -> bool:
    """
    Run the setup wizard inline (without typer.Exit).

    Used when called from within the report flow.
    Returns True if topics were added, False if cancelled/skipped.
    """
    if not QUESTIONARY_AVAILABLE:
        return False

    if store is None:
        store = UserContextStore()

    profile = store.load_profile()

    # Step 1: Select broad categories
    console.print("[bold]Step 1:[/bold] Select topic categories you're interested in")
    console.print("[dim]Use arrow keys to move, space to select, enter to confirm[/dim]")
    console.print()

    category_choices = list(SETUP_CATEGORIES.keys())
    selected_categories = questionary.checkbox(
        "Select categories:",
        choices=category_choices,
    ).ask()

    if selected_categories is None or not selected_categories:
        console.print("[yellow]Skipped - continuing with generic briefing.[/yellow]")
        return False

    # Step 2: Select specific topics within chosen categories
    console.print()
    console.print("[bold]Step 2:[/bold] Select specific topics within your categories")
    console.print()

    all_topics = []
    for category in selected_categories:
        topics = SETUP_CATEGORIES.get(category, [])
        all_topics.extend(topics)

    selected_topics = []
    if all_topics:
        selected_topics = questionary.checkbox(
            "Select specific topics:",
            choices=all_topics,
        ).ask()

        if selected_topics is None:
            console.print("[yellow]Skipped - continuing with generic briefing.[/yellow]")
            return False

    # Step 3: Optional custom topics
    console.print()
    add_custom = questionary.confirm(
        "Would you like to add any custom topics?",
        default=False,
    ).ask()

    custom_topics = []
    if add_custom:
        console.print("[dim]Enter topics one per line, empty line to finish[/dim]")
        while True:
            topic = questionary.text("Add topic (or press enter to finish):").ask()
            if not topic:
                break
            custom_topics.append(topic.strip())

    # Combine all selected topics
    final_topics = list(set(selected_topics + custom_topics))

    if not final_topics:
        console.print("[yellow]No topics selected - continuing with generic briefing.[/yellow]")
        return False

    # Save to profile
    profile.watching = list(set(profile.watching + final_topics))
    store.save_profile(profile)

    # Show summary
    console.print()
    console.print(Panel("[bold green]Setup Complete![/bold green]", style="green"))
    console.print()
    console.print(f"[green]Added {len(final_topics)} topics to your interests:[/green]")
    for topic in final_topics:
        console.print(f"  - {topic}")

    return True


@app.command("setup")
def setup_wizard():
    """
    Interactive setup wizard for configuring your interests.

    Use arrow keys to navigate, space to select, enter to confirm.

    Example:
        rss context setup
    """
    if not QUESTIONARY_AVAILABLE:
        console.print("[red]Error: questionary library not installed[/red]")
        console.print("[dim]Install with: pip install questionary[/dim]")
        raise typer.Exit(1)

    console.print()
    console.print(Panel("[bold]RSS Summarizer Setup Wizard[/bold]", style="blue"))
    console.print()
    console.print("Let's configure your interests to personalize your news briefings.")
    console.print()

    # Load existing profile
    store = UserContextStore()
    profile = store.load_profile()

    # Step 1: Select broad categories
    console.print("[bold]Step 1:[/bold] Select topic categories you're interested in")
    console.print("[dim]Use arrow keys to move, space to select, enter to confirm[/dim]")
    console.print()

    category_choices = list(SETUP_CATEGORIES.keys())
    selected_categories = questionary.checkbox(
        "Select categories:",
        choices=category_choices,
    ).ask()

    if selected_categories is None:
        console.print("[yellow]Setup cancelled.[/yellow]")
        raise typer.Exit(0)

    if not selected_categories:
        console.print("[yellow]No categories selected. You can always run setup again.[/yellow]")
        raise typer.Exit(0)

    # Step 2: Select specific topics within chosen categories
    console.print()
    console.print("[bold]Step 2:[/bold] Select specific topics within your categories")
    console.print()

    all_topics = []
    for category in selected_categories:
        topics = SETUP_CATEGORIES.get(category, [])
        all_topics.extend(topics)

    if all_topics:
        selected_topics = questionary.checkbox(
            "Select specific topics:",
            choices=all_topics,
        ).ask()

        if selected_topics is None:
            console.print("[yellow]Setup cancelled.[/yellow]")
            raise typer.Exit(0)
    else:
        selected_topics = []

    # Step 3: Optional custom topics
    console.print()
    add_custom = questionary.confirm(
        "Would you like to add any custom topics?",
        default=False,
    ).ask()

    custom_topics = []
    if add_custom:
        console.print("[dim]Enter topics one per line, empty line to finish[/dim]")
        while True:
            topic = questionary.text("Add topic (or press enter to finish):").ask()
            if not topic:
                break
            custom_topics.append(topic.strip())

    # Combine all selected topics
    final_topics = list(set(selected_topics + custom_topics))

    if not final_topics:
        console.print("[yellow]No topics selected.[/yellow]")
        raise typer.Exit(0)

    # Save to profile
    profile.watching = list(set(profile.watching + final_topics))
    store.save_profile(profile)

    # Show summary
    console.print()
    console.print(Panel("[bold green]Setup Complete![/bold green]", style="green"))
    console.print()
    console.print(f"[green]Added {len(final_topics)} topics to your interests:[/green]")
    for topic in final_topics:
        console.print(f"  - {topic}")
    console.print()
    console.print("[dim]Your briefings will now be personalized based on these interests.[/dim]")
    console.print("[dim]Run 'rss context list' to see all your settings.[/dim]")
    console.print("[dim]Run 'rss context setup' again to add more topics.[/dim]")


@app.command("watch")
def watch_topic(
    topic: str = typer.Argument(..., help="Topic to watch"),
):
    """
    Quick command to add a topic to your watch list.

    Example:
        rss context watch "AI Safety"
        rss context watch "Climate Change"
    """
    store = UserContextStore()
    profile = store.load_profile()

    if topic in profile.watching:
        console.print(f"[yellow]Already watching: {topic}[/yellow]")
        return

    profile.watching.append(topic)
    store.save_profile(profile)
    console.print(f"[green]Now watching: {topic}[/green]")


@app.command("unwatch")
def unwatch_topic(
    topic: str = typer.Argument(..., help="Topic to stop watching"),
):
    """
    Remove a topic from your watch list.

    Example:
        rss context unwatch "AI Safety"
    """
    store = UserContextStore()
    profile = store.load_profile()

    if topic not in profile.watching:
        console.print(f"[yellow]Not watching: {topic}[/yellow]")
        console.print("[dim]Current topics:[/dim]")
        for t in profile.watching[:5]:
            console.print(f"  - {t}")
        return

    profile.watching.remove(topic)
    store.save_profile(profile)
    console.print(f"[green]Stopped watching: {topic}[/green]")


if __name__ == "__main__":
    app()
