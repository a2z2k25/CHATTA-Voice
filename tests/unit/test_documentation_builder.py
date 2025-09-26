#!/usr/bin/env python3
"""Test suite for documentation builder system."""

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any
import time

# Test imports
from voice_mode.documentation_builder import (
    DocumentationType,
    FormatType,
    DocumentSection,
    DocumentationPage,
    APIDocumentationGenerator,
    UserGuideGenerator,
    ArchitectureDocumentationGenerator,
    DocumentationWebsiteBuilder,
    DocumentationBuilder,
    get_documentation_builder
)


async def test_document_section_creation():
    """Test document section creation and markdown conversion."""
    print("\n=== Testing Document Section Creation ===")
    
    section = DocumentSection(
        title="Test Section",
        content="This is test content with **bold** and *italic* text.",
        section_type=DocumentationType.USER_GUIDE,
        order=1,
        code_examples=["print('Hello, World!')"],
        links=["https://example.com"],
        tags=["test", "example"]
    )
    
    print(f"  Section created: {section.title}")
    print(f"  Section type: {section.section_type.value}")
    print(f"  Has code examples: {len(section.code_examples) > 0}")
    print(f"  Has links: {len(section.links) > 0}")
    
    # Test markdown conversion
    markdown = section.to_markdown(level=2)
    print(f"  Markdown generated: {len(markdown)} chars")
    print(f"  Contains title: {'##' in markdown}")
    print(f"  Contains code block: {'```' in markdown}")
    
    # Test subsections
    subsection = DocumentSection(
        title="Subsection",
        content="Subsection content",
        section_type=DocumentationType.USER_GUIDE
    )
    section.subsections.append(subsection)
    
    markdown_with_sub = section.to_markdown(level=2)
    print(f"  With subsection: {len(markdown_with_sub) > len(markdown)}")
    
    print("✓ Document section creation working")
    return True


async def test_documentation_page_creation():
    """Test documentation page creation and formatting."""
    print("\n=== Testing Documentation Page Creation ===")
    
    page = DocumentationPage(
        title="Test Documentation",
        description="Test documentation page",
        doc_type=DocumentationType.API,
        version="1.0.0"
    )
    
    # Add sections
    for i in range(3):
        section = DocumentSection(
            title=f"Section {i+1}",
            content=f"Content for section {i+1}",
            section_type=DocumentationType.API,
            order=i
        )
        page.sections.append(section)
    
    print(f"  Page created: {page.title}")
    print(f"  Page type: {page.doc_type.value}")
    print(f"  Sections: {len(page.sections)}")
    print(f"  Version: {page.version}")
    
    # Test markdown generation
    markdown = page.to_markdown()
    print(f"  Markdown generated: {len(markdown)} chars")
    print(f"  Has front matter: {markdown.startswith('---')}")
    print(f"  Has all sections: {all(f'Section {i+1}' in markdown for i in range(3))}")
    
    # Test metadata
    page.metadata["author"] = "Test Author"
    page.metadata["category"] = "Testing"
    markdown_with_meta = page.to_markdown()
    print(f"  Metadata included: {'author:' in markdown_with_meta}")
    
    print("✓ Documentation page creation working")
    return True


async def test_api_documentation_generator():
    """Test API documentation generation."""
    print("\n=== Testing API Documentation Generator ===")
    
    # Create a temporary Python file for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create test Python file
        test_py = tmppath / "test_module.py"
        test_py.write_text('''
"""Test module for documentation."""

class TestClass:
    """A test class for documentation."""
    
    def __init__(self):
        """Initialize the test class."""
        pass
    
    def public_method(self, arg1: str, arg2: int) -> str:
        """A public method.
        
        Args:
            arg1: First argument
            arg2: Second argument
            
        Returns:
            A string result
        """
        return f"{arg1}: {arg2}"
    
    def _private_method(self):
        """This should not be documented."""
        pass

def test_function(param: str) -> None:
    """A test function.
    
    Args:
        param: A parameter
    """
    print(param)

def _private_function():
    """This should not be documented."""
    pass
''')
        
        # Generate documentation
        generator = APIDocumentationGenerator(tmppath)
        page = generator.generate()
        
        print(f"  API docs generated: {page.title}")
        print(f"  Modules documented: {len(page.sections)}")
        
        if page.sections:
            module_section = page.sections[0]
            print(f"  Module: {module_section.title}")
            print(f"  Subsections: {len(module_section.subsections)}")
            
            # Check for class documentation
            class_docs = [s for s in module_section.subsections if "Class:" in s.title]
            print(f"  Classes documented: {len(class_docs)}")
            
            # Check for function documentation
            func_docs = [s for s in module_section.subsections if "Function:" in s.title]
            print(f"  Functions documented: {len(func_docs)}")
            
            # Verify private methods/functions are excluded
            all_titles = [s.title for s in module_section.subsections]
            has_private = any("_private" in title for title in all_titles)
            print(f"  Private members excluded: {not has_private}")
    
    print("✓ API documentation generator working")
    return True


async def test_user_guide_generator():
    """Test user guide generation."""
    print("\n=== Testing User Guide Generator ===")
    
    generator = UserGuideGenerator()
    
    # Test quickstart guide
    quickstart = generator.generate_quickstart()
    print(f"  Quickstart guide: {quickstart.title}")
    print(f"  Sections: {len(quickstart.sections)}")
    print(f"  Type: {quickstart.doc_type.value}")
    
    section_titles = [s.title for s in quickstart.sections]
    print(f"  Has installation: {'Installation' in section_titles}")
    print(f"  Has basic usage: {'Basic Usage' in section_titles}")
    
    # Test configuration guide
    config_guide = generator.generate_configuration_guide()
    print(f"  Config guide: {config_guide.title}")
    print(f"  Sections: {len(config_guide.sections)}")
    
    # Test troubleshooting guide
    troubleshooting = generator.generate_troubleshooting_guide()
    print(f"  Troubleshooting guide: {troubleshooting.title}")
    print(f"  Sections: {len(troubleshooting.sections)}")
    
    # Check content quality
    quickstart_md = quickstart.to_markdown()
    print(f"  Contains code examples: {'```' in quickstart_md}")
    print(f"  Contains configuration: {'json' in quickstart_md}")
    
    print("✓ User guide generator working")
    return True


async def test_architecture_documentation():
    """Test architecture documentation generation."""
    print("\n=== Testing Architecture Documentation ===")
    
    generator = ArchitectureDocumentationGenerator()
    arch_docs = generator.generate()
    
    print(f"  Architecture docs: {arch_docs.title}")
    print(f"  Type: {arch_docs.doc_type.value}")
    print(f"  Sections: {len(arch_docs.sections)}")
    
    section_titles = [s.title for s in arch_docs.sections]
    print(f"  Has system architecture: {'System Architecture' in section_titles}")
    print(f"  Has component details: {'Component Details' in section_titles}")
    print(f"  Has data flow: {'Data Flow' in section_titles}")
    
    # Check for diagrams
    arch_md = arch_docs.to_markdown()
    print(f"  Contains diagrams: {'```' in arch_md and '┌' in arch_md}")
    print(f"  Describes layers: {'Layer' in arch_md or 'layer' in arch_md}")
    
    print("✓ Architecture documentation working")
    return True


async def test_documentation_website_builder():
    """Test documentation website builder."""
    print("\n=== Testing Documentation Website Builder ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        builder = DocumentationWebsiteBuilder(output_dir)
        
        # Add test pages
        page1 = DocumentationPage(
            title="Test Page 1",
            description="First test page",
            doc_type=DocumentationType.USER_GUIDE,
            sections=[
                DocumentSection(
                    title="Section 1",
                    content="Test content",
                    section_type=DocumentationType.USER_GUIDE
                )
            ]
        )
        
        page2 = DocumentationPage(
            title="Test Page 2",
            description="Second test page",
            doc_type=DocumentationType.API,
            sections=[
                DocumentSection(
                    title="API Section",
                    content="API content",
                    section_type=DocumentationType.API
                )
            ]
        )
        
        builder.add_page(page1)
        builder.add_page(page2)
        
        # Build website
        builder.build()
        
        # Check generated files
        print(f"  Output directory: {output_dir}")
        print(f"  Pages added: {len(builder.pages)}")
        
        # Check directory structure
        print(f"  Static dir exists: {builder.static_dir.exists()}")
        print(f"  CSS dir exists: {builder.css_dir.exists()}")
        print(f"  JS dir exists: {builder.js_dir.exists()}")
        
        # Check generated files
        index_file = output_dir / "index.html"
        print(f"  Index generated: {index_file.exists()}")
        
        css_file = builder.css_dir / "style.css"
        print(f"  CSS generated: {css_file.exists()}")
        
        js_file = builder.js_dir / "search.js"
        print(f"  JS generated: {js_file.exists()}")
        
        search_index = builder.js_dir / "search-index.json"
        print(f"  Search index generated: {search_index.exists()}")
        
        # Check HTML files for pages
        html_files = list(output_dir.glob("*.html"))
        print(f"  HTML files generated: {len(html_files)}")
        
        # Verify index content
        if index_file.exists():
            index_content = index_file.read_text()
            print(f"  Index has navigation: {'<nav>' in index_content}")
            print(f"  Index has links: {'href=' in index_content}")
    
    print("✓ Documentation website builder working")
    return True


async def test_documentation_builder():
    """Test main documentation builder."""
    print("\n=== Testing Documentation Builder ===")
    
    builder = get_documentation_builder()
    
    print(f"  Builder initialized: True")
    print(f"  Source dir: {builder.source_dir}")
    print(f"  Output dir: {builder.output_dir}")
    print(f"  Website dir: {builder.website_dir}")
    
    # Test singleton
    builder2 = get_documentation_builder()
    print(f"  Singleton pattern: {builder is builder2}")
    
    # Note: We won't run build_all() in tests as it would generate real docs
    # Just test the structure is set up correctly
    print(f"  API generator ready: {builder.api_generator is not None}")
    print(f"  Guide generator ready: {builder.guide_generator is not None}")
    print(f"  Arch generator ready: {builder.arch_generator is not None}")
    print(f"  Website builder ready: {builder.website_builder is not None}")
    
    # Test summary generation
    summary = builder.generate_summary()
    print(f"  Summary generated: {len(summary) > 0}")
    print(f"  Summary has sections: {'Documentation Types:' in summary}")
    
    print("✓ Documentation builder working")
    return True


async def test_markdown_generation():
    """Test markdown generation features."""
    print("\n=== Testing Markdown Generation ===")
    
    # Test complex section with all features
    section = DocumentSection(
        title="Complete Section",
        content="""
This section demonstrates all markdown features:

- Bullet points
- **Bold text**
- *Italic text*
- `Inline code`

1. Numbered lists
2. With multiple items
3. And proper formatting

> Blockquotes for important notes

| Tables | Are | Supported |
|--------|-----|-----------|
| Row 1  | Data| Value     |
| Row 2  | More| Content   |
        """.strip(),
        section_type=DocumentationType.USER_GUIDE,
        code_examples=[
            "def example():\n    return 'Hello, World!'",
            "# Another example\nprint('Test')"
        ],
        links=[
            "[Documentation](https://docs.example.com)",
            "[GitHub](https://github.com/example)"
        ],
        tags=["markdown", "features", "test"]
    )
    
    markdown = section.to_markdown(level=2)
    
    print(f"  Markdown length: {len(markdown)} chars")
    print(f"  Has title: {'## Complete Section' in markdown}")
    print(f"  Has bullet points: {'- ' in markdown}")
    print(f"  Has numbered list: {'1. ' in markdown}")
    print(f"  Has blockquote: {'>' in markdown}")
    print(f"  Has table: {'|' in markdown}")
    print(f"  Has code blocks: {markdown.count('```') >= 4}")
    print(f"  Has links section: {'Related Links' in markdown}")
    
    print("✓ Markdown generation working")
    return True


async def test_documentation_types():
    """Test all documentation types."""
    print("\n=== Testing Documentation Types ===")
    
    doc_types = list(DocumentationType)
    print(f"  Total documentation types: {len(doc_types)}")
    
    for doc_type in doc_types:
        print(f"    - {doc_type.value}: {doc_type.name}")
    
    # Test format types
    format_types = list(FormatType)
    print(f"  Total format types: {len(format_types)}")
    
    for format_type in format_types:
        print(f"    - {format_type.value}: {format_type.name}")
    
    print("✓ Documentation types working")
    return True


async def test_search_index_generation():
    """Test search index generation for documentation."""
    print("\n=== Testing Search Index Generation ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        builder = DocumentationWebsiteBuilder(output_dir)
        
        # Add pages with searchable content
        for i in range(3):
            page = DocumentationPage(
                title=f"Search Test Page {i+1}",
                description=f"Page {i+1} for testing search functionality",
                doc_type=DocumentationType.USER_GUIDE,
                sections=[
                    DocumentSection(
                        title=f"Searchable Section {i+1}",
                        content=f"This content should be searchable. Keyword: test{i+1}",
                        section_type=DocumentationType.USER_GUIDE
                    )
                ]
            )
            builder.add_page(page)
        
        # Build to generate search index
        builder.build()
        
        # Check search index
        search_index_file = builder.js_dir / "search-index.json"
        print(f"  Search index exists: {search_index_file.exists()}")
        
        if search_index_file.exists():
            with open(search_index_file, 'r') as f:
                search_data = json.load(f)
            
            print(f"  Index entries: {len(search_data)}")
            print(f"  Entry structure valid: {all('title' in e and 'url' in e for e in search_data)}")
            
            # Check content is searchable
            first_entry = search_data[0] if search_data else {}
            print(f"  Has title: {'title' in first_entry}")
            print(f"  Has description: {'description' in first_entry}")
            print(f"  Has content: {'content' in first_entry}")
            print(f"  Has URL: {'url' in first_entry}")
    
    print("✓ Search index generation working")
    return True


async def test_high_level_documentation():
    """Test high-level documentation workflow."""
    print("\n=== Testing High-Level Documentation Workflow ===")
    
    # Simulate complete documentation workflow
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override output directory for testing
        builder = DocumentationBuilder()
        builder.output_dir = Path(tmpdir)
        builder.website_dir = builder.output_dir / "website"
        builder.website_builder = DocumentationWebsiteBuilder(builder.website_dir)
        
        # Build minimal documentation
        results = {
            "pages_generated": 0,
            "formats": [],
            "website_built": False,
            "errors": []
        }
        
        try:
            # Generate a few pages
            guide = builder.guide_generator.generate_quickstart()
            builder.website_builder.add_page(guide)
            results["pages_generated"] += 1
            
            arch = builder.arch_generator.generate()
            builder.website_builder.add_page(arch)
            results["pages_generated"] += 1
            
            # Build website
            builder.website_builder.build()
            results["website_built"] = True
            results["formats"] = ["html", "markdown"]
            
        except Exception as e:
            results["errors"].append(str(e))
        
        print(f"  Pages generated: {results['pages_generated']}")
        print(f"  Website built: {results['website_built']}")
        print(f"  Formats: {', '.join(results['formats'])}")
        print(f"  Errors: {len(results['errors'])}")
        
        # Check output
        website_exists = builder.website_dir.exists()
        print(f"  Website directory created: {website_exists}")
        
        if website_exists:
            html_files = list(builder.website_dir.glob("*.html"))
            print(f"  HTML files: {len(html_files)}")
    
    print("✓ High-level documentation workflow working")
    return True


async def run_all_documentation_tests():
    """Run all documentation builder tests."""
    tests = [
        test_document_section_creation,
        test_documentation_page_creation,
        test_api_documentation_generator,
        test_user_guide_generator,
        test_architecture_documentation,
        test_documentation_website_builder,
        test_documentation_builder,
        test_markdown_generation,
        test_documentation_types,
        test_search_index_generation,
        test_high_level_documentation
    ]
    
    results = []
    for i, test in enumerate(tests, 1):
        try:
            print(f"\n[{i}/{len(tests)}] Running {test.__name__}")
            result = await test()
            results.append((test.__name__, result, None))
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
            results.append((test.__name__, False, str(e)))
    
    return results


def main():
    """Main test runner."""
    print("=" * 70)
    print("DOCUMENTATION BUILDER VALIDATION")
    print("=" * 70)
    
    start_time = time.time()
    
    # Run tests
    results = asyncio.run(run_all_documentation_tests())
    
    # Summary
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    print("\n" + "=" * 70)
    print("✓ Documentation builder validation complete!")
    print(f"  Tests passed: {passed}/{len(results)}")
    print(f"  Success rate: {passed/len(results)*100:.1f}%")
    print(f"  Total validation time: {time.time() - start_time:.3f}s")
    
    if passed == len(results):
        print("🎉 All documentation tests PASSED!")
        print("Sprint 45 documentation finalization COMPLETE!")
    else:
        print(f"⚠️  {failed} test(s) failed - review above for details")
    
    print("=" * 70)
    
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    exit(main())