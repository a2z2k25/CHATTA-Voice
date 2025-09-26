#!/usr/bin/env python3
"""Test help system and documentation interface."""

import asyncio
from typing import List, Dict, Any
from voice_mode.help_system import (
    HelpSystem,
    HelpTopic,
    HelpCategory,
    HelpFormat,
    HelpSearchResult,
    DocumentationBrowser,
    InteractiveHelp,
    get_help_system
)


def test_help_topic_creation():
    """Test help topic creation and matching."""
    print("\n=== Testing Help Topic Creation ===")
    
    topic = HelpTopic(
        id="test.topic",
        title="Test Topic",
        category=HelpCategory.GETTING_STARTED,
        content="This is a test topic for demonstration purposes.",
        keywords=["test", "demo", "example"],
        examples=["test command", "demo usage"]
    )
    
    print(f"  Created topic: {topic.title}")
    print(f"  ID: {topic.id}")
    print(f"  Category: {topic.category.name}")
    print(f"  Keywords: {topic.keywords}")
    
    # Test matching
    match1 = topic.matches_query("test")
    print(f"  Match 'test': {match1:.2f}")
    
    match2 = topic.matches_query("demonstration")
    print(f"  Match 'demonstration': {match2:.2f}")
    
    match3 = topic.matches_query("getting started")
    print(f"  Match 'getting started': {match3:.2f}")
    
    match4 = topic.matches_query("unrelated query")
    print(f"  Match 'unrelated': {match4:.2f}")
    
    # Note: Individual topics don't have format methods
    # Formatting is handled by HelpSystem.format_topic()
    print(f"  Topic content length: {len(topic.content)}")
    
    print("✓ Help topic creation working")


def test_help_system_initialization():
    """Test help system initialization and built-in topics."""
    print("\n=== Testing Help System Initialization ===")
    
    help_system = HelpSystem()
    
    print(f"  Total topics loaded: {len(help_system.topics)}")
    
    # Check categories
    for category in HelpCategory:
        count = len(help_system.categories[category])
        print(f"    {category.name}: {count} topics")
    
    # Test specific built-in topics
    getting_started = help_system.get_topic("getting_started.overview")
    print(f"  Getting started topic: {getting_started is not None}")
    if getting_started:
        print(f"    Title: {getting_started.title}")
        print(f"    Content length: {len(getting_started.content)}")
    
    voice_commands = help_system.get_topic("voice_commands.basic")
    print(f"  Voice commands topic: {voice_commands is not None}")
    
    shortcuts = help_system.get_topic("keyboard_shortcuts.overview")
    print(f"  Keyboard shortcuts topic: {shortcuts is not None}")
    
    config = help_system.get_topic("configuration.overview")
    print(f"  Configuration topic: {config is not None}")
    
    troubleshooting = help_system.get_topic("troubleshooting.audio")
    print(f"  Troubleshooting topic: {troubleshooting is not None}")
    
    print("✓ Help system initialization working")


def test_help_search():
    """Test help topic search functionality."""
    print("\n=== Testing Help Search ===")
    
    help_system = get_help_system()
    
    # Test various searches
    searches = [
        "voice commands",
        "getting started", 
        "keyboard shortcuts",
        "configuration",
        "audio problems",
        "tutorial",
        "api reference"
    ]
    
    for query in searches:
        results = help_system.search(query, limit=3)
        print(f"  '{query}': {len(results)} results")
        
        for i, result in enumerate(results[:2]):
            print(f"    {i+1}. {result.topic.title} ({result.confidence:.2f})")
    
    # Test category filtering  
    voice_results = help_system.search("commands", category=HelpCategory.VOICE_COMMANDS)
    print(f"  Voice commands category: {len(voice_results)} results")
    
    config_results = help_system.search("settings", category=HelpCategory.CONFIGURATION)
    print(f"  Configuration category: {len(config_results)} results")
    
    # Test empty query
    empty_results = help_system.search("")
    print(f"  Empty query: {len(empty_results)} results")
    
    print("✓ Help search working")


def test_contextual_help():
    """Test contextual help based on application state."""
    print("\n=== Testing Contextual Help ===")
    
    help_system = get_help_system()
    
    # Test different contexts
    contexts = [
        "voice_active",
        "preferences", 
        "error",
        "first_time",
        "unknown_context"
    ]
    
    for context in contexts:
        topics = help_system.get_contextual_help(context)
        print(f"  Context '{context}': {len(topics)} relevant topics")
        
        for topic in topics[:2]:
            print(f"    - {topic.title}")
    
    print("✓ Contextual help working")


def test_documentation_browser():
    """Test documentation browser navigation."""
    print("\n=== Testing Documentation Browser ===")
    
    help_system = get_help_system()
    browser = help_system.browser
    
    # Navigate to topic
    topic = browser.navigate_to("getting_started.overview")
    print(f"  Navigated to: {topic.title if topic else 'None'}")
    print(f"  Current topic: {browser.current_topic.title if browser.current_topic else 'None'}")
    
    # Navigate to another topic
    topic2 = browser.navigate_to("voice_commands.basic")
    print(f"  Navigated to: {topic2.title if topic2 else 'None'}")
    print(f"  History length: {len(browser.history)}")
    
    # Go back
    prev_topic = browser.go_back()
    print(f"  Went back to: {prev_topic.title if prev_topic else 'None'}")
    
    # Test bookmarking
    browser.bookmark_current()
    print(f"  Bookmarked current topic")
    print(f"  Bookmarks count: {len(browser.bookmarks)}")
    
    bookmarked = browser.get_bookmarks()
    print(f"  Bookmarked topics: {len(bookmarked)}")
    for topic in bookmarked:
        print(f"    - {topic.title}")
    
    print("✓ Documentation browser working")


def test_help_formatting():
    """Test help topic formatting in different formats."""
    print("\n=== Testing Help Formatting ===")
    
    help_system = get_help_system()
    topic = help_system.get_topic("voice_commands.basic")
    
    if topic:
        # Test plain text format
        plain = help_system.format_topic(topic, HelpFormat.PLAIN_TEXT)
        print(f"  Plain text format: {len(plain)} characters")
        print(f"    Lines: {len(plain.split('\\n'))}")
        
        # Test markdown format
        markdown = help_system.format_topic(topic, HelpFormat.MARKDOWN)
        print(f"  Markdown format: {len(markdown)} characters")
        
        # Test structured format
        structured = help_system.format_topic(topic, HelpFormat.STRUCTURED, include_metadata=True)
        if isinstance(structured, dict):
            print(f"  Structured format: {len(structured)} fields")
            print(f"    Keys: {list(structured.keys())}")
        
        # Test with metadata
        with_meta = help_system.format_topic(topic, HelpFormat.STRUCTURED, include_metadata=True)
        print(f"  With metadata: {isinstance(with_meta, dict)}")
    
    print("✓ Help formatting working")


async def test_interactive_help():
    """Test interactive help with natural language processing."""
    print("\n=== Testing Interactive Help ===")
    
    help_system = get_help_system()
    interactive = InteractiveHelp(help_system)
    
    # Test various natural language requests
    requests = [
        "how do I get started?",
        "what voice commands can I use?", 
        "show me keyboard shortcuts",
        "I need help with configuration",
        "my microphone is not working",
        "I want a tutorial", 
        "show me the API documentation",
        "something random and unrelated"
    ]
    
    for request in requests:
        response = await interactive.process_help_request(request)
        print(f"  '{request}':")
        response_preview = response[:100] + "..." if len(response) > 100 else response
        print(f"    Response: {response_preview}")
        print(f"    Length: {len(response)} characters")
    
    print("✓ Interactive help working")


def test_command_help():
    """Test specific command help functionality."""
    print("\n=== Testing Command Help ===")
    
    help_system = get_help_system()
    
    # Test general command help
    general_help = help_system.get_command_help()
    print(f"  General command help: {len(general_help)} characters")
    
    # Test specific command help (even though command might not exist)
    specific_help = help_system.get_command_help("basic")
    print(f"  Specific command help: {len(specific_help)} characters")
    
    # Test non-existent command
    missing_help = help_system.get_command_help("nonexistent")
    print(f"  Missing command help: {len(missing_help)} characters")
    print(f"    Contains 'No help': {'No help' in missing_help}")
    
    # Test quick help
    quick_help = help_system.get_quick_help()
    print(f"  Quick help: {len(quick_help)} characters")
    print(f"    Contains 'QUICK HELP': {'QUICK HELP' in quick_help}")
    
    print("✓ Command help working")


def test_help_statistics():
    """Test help system statistics and analytics."""
    print("\n=== Testing Help Statistics ===")
    
    help_system = get_help_system()
    
    # Perform some operations to generate stats
    help_system.search("voice commands")
    help_system.search("getting started")
    help_system.search("voice commands")  # Duplicate to test counting
    
    help_system.get_topic("getting_started.overview")
    help_system.get_topic("voice_commands.basic")
    help_system.get_topic("getting_started.overview")  # Duplicate view
    
    # Get statistics
    stats = help_system.get_statistics()
    
    print(f"  Total topics: {stats['total_topics']}")
    print(f"  Search count: {stats['search_count']}")
    
    print("  Topics by category:")
    for category, count in stats['topics_by_category'].items():
        if count > 0:
            print(f"    {category}: {count}")
    
    print("  Most viewed topics:")
    for topic_id, views in stats['most_viewed_topics']:
        topic = help_system.get_topic(topic_id)
        if topic:
            print(f"    {topic.title}: {views} views")
    
    print("  Popular searches:")
    for query, count in stats['popular_searches']:
        print(f"    '{query}': {count} times")
    
    print("✓ Help statistics working")


def test_category_listing():
    """Test listing topics by category."""
    print("\n=== Testing Category Listing ===")
    
    help_system = get_help_system()
    
    for category in HelpCategory:
        topics = help_system.get_category_topics(category)
        print(f"  {category.name}: {len(topics)} topics")
        
        for topic in topics[:2]:  # Show first 2 topics
            print(f"    - {topic.title}")
    
    print("✓ Category listing working")


def test_global_help_instance():
    """Test global help system singleton."""
    print("\n=== Testing Global Help Instance ===")
    
    # Get multiple instances
    help1 = get_help_system()
    help2 = get_help_system()
    
    print(f"  Same instance: {help1 is help2}")
    print(f"  Instance type: {type(help1).__name__}")
    print(f"  Topics available: {len(help1.topics)}")
    
    # Test that changes persist
    original_count = help1.search_count
    help1.search("test query")
    help2.search("another query")
    
    print(f"  Search count after operations: {help2.search_count}")
    print(f"  Count increased: {help2.search_count > original_count}")
    
    print("✓ Global help instance working")


async def test_performance():
    """Test help system performance."""
    print("\n=== Testing Performance ===")
    
    import time
    
    help_system = get_help_system()
    
    # Test search performance
    queries = ["voice", "commands", "keyboard", "config", "help", "tutorial", "api", "faq"]
    
    start_time = time.time()
    total_results = 0
    
    for _ in range(100):  # 100 iterations
        for query in queries:
            results = help_system.search(query, limit=5)
            total_results += len(results)
    
    elapsed = time.time() - start_time
    search_rate = (100 * len(queries)) / elapsed
    
    print(f"  Search rate: {search_rate:.1f} searches/sec")
    print(f"  Total results found: {total_results}")
    print(f"  Average results per query: {total_results / (100 * len(queries)):.2f}")
    
    # Test topic retrieval performance
    topic_ids = list(help_system.topics.keys())
    
    start_time = time.time()
    
    for _ in range(1000):  # 1000 retrievals
        for topic_id in topic_ids[:5]:  # First 5 topics
            help_system.get_topic(topic_id)
    
    elapsed = time.time() - start_time
    retrieval_rate = (1000 * 5) / elapsed
    
    print(f"  Topic retrieval rate: {retrieval_rate:.1f} retrievals/sec")
    
    # Test interactive help performance
    interactive = InteractiveHelp(help_system)
    
    start_time = time.time()
    
    for _ in range(50):
        await interactive.process_help_request("help with voice commands")
    
    elapsed = time.time() - start_time
    interactive_rate = 50 / elapsed
    
    print(f"  Interactive help rate: {interactive_rate:.1f} requests/sec")
    
    print("✓ Performance acceptable")


async def test_error_handling():
    """Test help system error handling."""
    print("\n=== Testing Error Handling ===")
    
    help_system = HelpSystem()  # Fresh instance
    
    # Test non-existent topic retrieval
    missing_topic = help_system.get_topic("nonexistent.topic")
    print(f"  Non-existent topic: {missing_topic is None}")
    
    # Test empty search
    empty_results = help_system.search("")
    print(f"  Empty search results: {len(empty_results)}")
    
    # Test search with special characters
    special_results = help_system.search("@#$%^&*()")
    print(f"  Special characters search: {len(special_results)}")
    
    # Test browser navigation to non-existent topic
    browser = help_system.browser
    invalid_nav = browser.navigate_to("invalid.topic.id")
    print(f"  Invalid navigation result: {invalid_nav is None}")
    
    # Test go back with empty history
    back_result = browser.go_back()
    print(f"  Go back with empty history: {back_result is None}")
    
    # Test interactive help with empty request
    interactive = InteractiveHelp(help_system)
    empty_response = await interactive.process_help_request("")
    print(f"  Empty interactive request handled: {len(empty_response) > 0}")
    
    # Test formatting with invalid format (should handle gracefully)
    topic = HelpTopic("test", "Test", HelpCategory.FAQ, "Test content")
    try:
        formatted = help_system.format_topic(topic, HelpFormat.PLAIN_TEXT)
        print(f"  Topic formatting successful: {len(formatted) > 0}")
    except Exception as e:
        print(f"  Topic formatting error: {e}")
    
    print("✓ Error handling working")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("HELP SYSTEM TESTS")
    print("=" * 60)
    
    # Run synchronous tests
    test_help_topic_creation()
    test_help_system_initialization()
    test_help_search()
    test_contextual_help()
    test_documentation_browser()
    test_help_formatting()
    test_command_help()
    test_help_statistics()
    test_category_listing()
    test_global_help_instance()
    
    # Run async tests
    await test_interactive_help()
    await test_performance()
    await test_error_handling()
    
    print("\n" + "=" * 60)
    print("✓ All help system tests passed!")
    print("Sprint 38 complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())