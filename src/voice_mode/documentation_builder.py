#!/usr/bin/env python3
"""Documentation builder system for VoiceMode."""

import ast
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Union
import logging
import importlib.util
import markdown
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentationType(str, Enum):
    """Types of documentation."""
    API = "api"
    USER_GUIDE = "user_guide"
    TUTORIAL = "tutorial"
    ARCHITECTURE = "architecture"
    DEPLOYMENT = "deployment"
    CONFIGURATION = "configuration"
    TROUBLESHOOTING = "troubleshooting"
    CHANGELOG = "changelog"
    MIGRATION = "migration"
    REFERENCE = "reference"


class FormatType(str, Enum):
    """Documentation format types."""
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    RESTRUCTURED_TEXT = "rst"
    ASCIIDOC = "asciidoc"
    DOCX = "docx"
    EPUB = "epub"
    MAN = "man"


@dataclass
class DocumentSection:
    """Individual documentation section."""
    title: str
    content: str
    section_type: DocumentationType
    order: int = 0
    subsections: List['DocumentSection'] = field(default_factory=list)
    code_examples: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def to_markdown(self, level: int = 1) -> str:
        """Convert section to markdown format."""
        md_lines = []
        
        # Add title
        md_lines.append(f"{'#' * level} {self.title}")
        md_lines.append("")
        
        # Add content
        md_lines.append(self.content)
        md_lines.append("")
        
        # Add code examples
        for example in self.code_examples:
            md_lines.append("```python")
            md_lines.append(example)
            md_lines.append("```")
            md_lines.append("")
        
        # Add subsections
        for subsection in self.subsections:
            md_lines.append(subsection.to_markdown(level + 1))
        
        # Add links
        if self.links:
            md_lines.append(f"{'#' * (level + 1)} Related Links")
            md_lines.append("")
            for link in self.links:
                md_lines.append(f"- {link}")
            md_lines.append("")
        
        return "\n".join(md_lines)


@dataclass
class DocumentationPage:
    """Complete documentation page."""
    title: str
    description: str
    doc_type: DocumentationType
    sections: List[DocumentSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d"))
    updated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d"))
    version: str = "1.0.0"
    
    def to_markdown(self) -> str:
        """Convert page to markdown format."""
        md_lines = []
        
        # Add front matter
        md_lines.append("---")
        md_lines.append(f"title: {self.title}")
        md_lines.append(f"description: {self.description}")
        md_lines.append(f"type: {self.doc_type.value}")
        md_lines.append(f"created: {self.created_at}")
        md_lines.append(f"updated: {self.updated_at}")
        md_lines.append(f"version: {self.version}")
        for key, value in self.metadata.items():
            md_lines.append(f"{key}: {value}")
        md_lines.append("---")
        md_lines.append("")
        
        # Add title and description
        md_lines.append(f"# {self.title}")
        md_lines.append("")
        md_lines.append(self.description)
        md_lines.append("")
        
        # Add sections
        for section in sorted(self.sections, key=lambda s: s.order):
            md_lines.append(section.to_markdown(level=2))
        
        return "\n".join(md_lines)


class APIDocumentationGenerator:
    """Generate API documentation from code."""
    
    def __init__(self, source_dir: Path):
        """Initialize API documentation generator."""
        self.source_dir = Path(source_dir)
        self.api_docs: List[DocumentSection] = []
    
    def generate(self) -> DocumentationPage:
        """Generate complete API documentation."""
        logger.info(f"Generating API documentation from {self.source_dir}")
        
        # Scan for Python files
        python_files = list(self.source_dir.rglob("*.py"))
        
        for py_file in python_files:
            if "__pycache__" in str(py_file):
                continue
            
            try:
                self._document_module(py_file)
            except Exception as e:
                logger.warning(f"Failed to document {py_file}: {e}")
        
        # Create documentation page
        page = DocumentationPage(
            title="VoiceMode API Reference",
            description="Complete API documentation for VoiceMode library",
            doc_type=DocumentationType.API,
            sections=self.api_docs
        )
        
        return page
    
    def _document_module(self, py_file: Path) -> None:
        """Document a Python module."""
        with open(py_file, 'r') as f:
            source = f.read()
        
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return
        
        module_name = py_file.stem
        module_section = DocumentSection(
            title=f"Module: {module_name}",
            content=self._get_module_docstring(tree),
            section_type=DocumentationType.API,
            order=len(self.api_docs)
        )
        
        # Document classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_doc = self._document_class(node, module_name)
                if class_doc:
                    module_section.subsections.append(class_doc)
            elif isinstance(node, ast.FunctionDef):
                if node.name.startswith('_'):
                    continue
                func_doc = self._document_function(node, module_name)
                if func_doc:
                    module_section.subsections.append(func_doc)
        
        if module_section.subsections or module_section.content:
            self.api_docs.append(module_section)
    
    def _get_module_docstring(self, tree: ast.Module) -> str:
        """Extract module docstring."""
        if tree.body and isinstance(tree.body[0], ast.Expr):
            if isinstance(tree.body[0].value, ast.Constant):
                return tree.body[0].value.value
        return ""
    
    def _document_class(self, node: ast.ClassDef, module: str) -> Optional[DocumentSection]:
        """Document a class."""
        if node.name.startswith('_'):
            return None
        
        docstring = ast.get_docstring(node) or "No description available."
        
        section = DocumentSection(
            title=f"Class: {node.name}",
            content=docstring,
            section_type=DocumentationType.API
        )
        
        # Document methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if not item.name.startswith('_') or item.name == "__init__":
                    method_doc = self._document_function(item, f"{module}.{node.name}")
                    if method_doc:
                        section.subsections.append(method_doc)
        
        return section
    
    def _document_function(self, node: ast.FunctionDef, parent: str) -> Optional[DocumentSection]:
        """Document a function or method."""
        docstring = ast.get_docstring(node) or "No description available."
        
        # Build signature
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        
        signature = f"{node.name}({', '.join(args)})"
        
        section = DocumentSection(
            title=f"{'Method' if '.' in parent else 'Function'}: {signature}",
            content=docstring,
            section_type=DocumentationType.API
        )
        
        return section


class UserGuideGenerator:
    """Generate user guides and tutorials."""
    
    def __init__(self, project_name: str = "VoiceMode"):
        """Initialize user guide generator."""
        self.project_name = project_name
        self.guides: List[DocumentationPage] = []
    
    def generate_quickstart(self) -> DocumentationPage:
        """Generate quickstart guide."""
        sections = [
            DocumentSection(
                title="Installation",
                content="""
## Prerequisites

- Python 3.10 or higher
- FFmpeg for audio processing
- A microphone for voice input

## Install from PyPI

```bash
pip install voice-mode
```

## Install from Source

```bash
git clone https://github.com/your-org/voice-mode.git
cd voice-mode
make dev-install
```
                """.strip(),
                section_type=DocumentationType.USER_GUIDE,
                order=1,
                code_examples=[
                    "# Verify installation\nimport voice_mode\nprint(voice_mode.__version__)"
                ]
            ),
            DocumentSection(
                title="Basic Usage",
                content="""
VoiceMode provides voice interaction capabilities through the Model Context Protocol (MCP).

### Starting the Server

```bash
voice-mode serve
```

### Using with Claude Code

Add to your Claude Code configuration:

```json
{
  "mcpServers": {
    "voice-mode": {
      "command": "voice-mode",
      "args": ["serve"]
    }
  }
}
```
                """.strip(),
                section_type=DocumentationType.USER_GUIDE,
                order=2
            ),
            DocumentSection(
                title="Voice Commands",
                content="""
Once configured, you can use voice commands:

- **Start Conversation**: Begin a voice interaction session
- **Stop Listening**: Pause voice input
- **Clear Context**: Reset conversation context
- **Change Voice**: Switch between available TTS voices
                """.strip(),
                section_type=DocumentationType.USER_GUIDE,
                order=3
            )
        ]
        
        return DocumentationPage(
            title="Quickstart Guide",
            description="Get started with VoiceMode in minutes",
            doc_type=DocumentationType.USER_GUIDE,
            sections=sections
        )
    
    def generate_configuration_guide(self) -> DocumentationPage:
        """Generate configuration guide."""
        sections = [
            DocumentSection(
                title="Environment Variables",
                content="""
VoiceMode can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `VOICE_MODE_API_KEY` | OpenAI API key for cloud services | None |
| `VOICE_MODE_TTS_VOICE` | Default TTS voice | "nova" |
| `VOICE_MODE_STT_MODEL` | STT model to use | "whisper-1" |
| `VOICE_MODE_SILENCE_DURATION` | Silence detection threshold | 1.5 |
| `VOICE_MODE_LOG_LEVEL` | Logging verbosity | "INFO" |
                """.strip(),
                section_type=DocumentationType.CONFIGURATION,
                order=1
            ),
            DocumentSection(
                title="Voice Preferences",
                content="""
Create a `.voice_preferences.json` file in your project:

```json
{
  "tts": {
    "voice": "nova",
    "speed": 1.0,
    "pitch": 1.0
  },
  "stt": {
    "model": "whisper-1",
    "language": "en"
  },
  "audio": {
    "sample_rate": 24000,
    "channels": 1
  }
}
```
                """.strip(),
                section_type=DocumentationType.CONFIGURATION,
                order=2
            )
        ]
        
        return DocumentationPage(
            title="Configuration Guide",
            description="Configure VoiceMode for your needs",
            doc_type=DocumentationType.CONFIGURATION,
            sections=sections
        )
    
    def generate_troubleshooting_guide(self) -> DocumentationPage:
        """Generate troubleshooting guide."""
        sections = [
            DocumentSection(
                title="Common Issues",
                content="""
## No Audio Input Detected

1. Check microphone permissions
2. Verify FFmpeg is installed: `ffmpeg -version`
3. Test microphone: `voice-mode test-audio`

## TTS Not Working

1. Verify API credentials are set
2. Check network connectivity
3. Test TTS service: `voice-mode test-tts`

## High Latency

1. Use local services (Whisper.cpp, Kokoro)
2. Adjust silence detection threshold
3. Optimize audio buffer size
                """.strip(),
                section_type=DocumentationType.TROUBLESHOOTING,
                order=1
            ),
            DocumentSection(
                title="Debug Mode",
                content="""
Enable debug logging for detailed diagnostics:

```bash
export VOICE_MODE_LOG_LEVEL=DEBUG
voice-mode serve
```

Check logs at: `~/.voice-mode/logs/`
                """.strip(),
                section_type=DocumentationType.TROUBLESHOOTING,
                order=2
            )
        ]
        
        return DocumentationPage(
            title="Troubleshooting Guide",
            description="Solve common VoiceMode issues",
            doc_type=DocumentationType.TROUBLESHOOTING,
            sections=sections
        )


class ArchitectureDocumentationGenerator:
    """Generate architecture documentation."""
    
    def generate(self) -> DocumentationPage:
        """Generate architecture documentation."""
        sections = [
            DocumentSection(
                title="System Architecture",
                content="""
VoiceMode follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────┐
│                 MCP Client                  │
│         (Claude Code / Claude Desktop)      │
└─────────────────┬───────────────────────────┘
                  │ MCP Protocol
┌─────────────────▼───────────────────────────┐
│              MCP Server                     │
│         (FastMCP Framework)                 │
├─────────────────────────────────────────────┤
│              Tool System                    │
│   ┌────────────┬────────────┬────────────┐ │
│   │  Converse  │  Service   │  Devices   │ │
│   └────────────┴────────────┴────────────┘ │
├─────────────────────────────────────────────┤
│            Provider System                  │
│   ┌────────────┬────────────┬────────────┐ │
│   │   OpenAI   │  Whisper   │   Kokoro   │ │
│   └────────────┴────────────┴────────────┘ │
├─────────────────────────────────────────────┤
│           Audio Processing                  │
│   ┌────────────┬────────────┬────────────┐ │
│   │    VAD     │   FFmpeg   │   Codecs   │ │
│   └────────────┴────────────┴────────────┘ │
└─────────────────────────────────────────────┘
```
                """.strip(),
                section_type=DocumentationType.ARCHITECTURE,
                order=1
            ),
            DocumentSection(
                title="Component Details",
                content="""
## MCP Server Layer

The FastMCP-based server provides:
- Stdio transport for communication
- Automatic tool discovery
- Resource management
- Event handling

## Tool System

Tools provide high-level functionality:
- **Converse**: Main voice conversation tool
- **Service**: Service installation/management
- **Devices**: Audio device detection

## Provider System

Providers offer TTS/STT services:
- Dynamic discovery
- Health checking
- Automatic failover
- OpenAI API compatibility

## Audio Processing

Low-level audio handling:
- WebRTC VAD for silence detection
- FFmpeg for format conversion
- Multiple codec support
                """.strip(),
                section_type=DocumentationType.ARCHITECTURE,
                order=2
            ),
            DocumentSection(
                title="Data Flow",
                content="""
## Voice Input Flow

1. **Audio Capture**: Microphone → PyAudio → Audio Buffer
2. **VAD Processing**: Detect speech segments
3. **STT Conversion**: Audio → Text (via provider)
4. **MCP Transport**: Text → Client

## Voice Output Flow

1. **Text Reception**: Client → MCP Server
2. **TTS Generation**: Text → Audio (via provider)
3. **Audio Playback**: Audio Buffer → PyAudio → Speakers
4. **Event Notification**: Status updates → Client
                """.strip(),
                section_type=DocumentationType.ARCHITECTURE,
                order=3
            )
        ]
        
        return DocumentationPage(
            title="Architecture Documentation",
            description="Technical architecture of VoiceMode",
            doc_type=DocumentationType.ARCHITECTURE,
            sections=sections
        )


class DocumentationWebsiteBuilder:
    """Build documentation website."""
    
    def __init__(self, output_dir: Path):
        """Initialize website builder."""
        self.output_dir = Path(output_dir)
        self.pages: List[DocumentationPage] = []
        self.static_dir = self.output_dir / "static"
        self.css_dir = self.static_dir / "css"
        self.js_dir = self.static_dir / "js"
        self.img_dir = self.static_dir / "img"
    
    def add_page(self, page: DocumentationPage) -> None:
        """Add a documentation page."""
        self.pages.append(page)
    
    def build(self) -> None:
        """Build the documentation website."""
        logger.info(f"Building documentation website at {self.output_dir}")
        
        # Create directory structure
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.static_dir.mkdir(exist_ok=True)
        self.css_dir.mkdir(exist_ok=True)
        self.js_dir.mkdir(exist_ok=True)
        self.img_dir.mkdir(exist_ok=True)
        
        # Generate pages
        for page in self.pages:
            self._generate_page(page)
        
        # Generate index
        self._generate_index()
        
        # Generate search index
        self._generate_search_index()
        
        # Copy static assets
        self._generate_static_assets()
        
        logger.info("Documentation website built successfully")
    
    def _generate_page(self, page: DocumentationPage) -> None:
        """Generate an HTML page from documentation."""
        filename = f"{page.doc_type.value}_{page.title.lower().replace(' ', '_')}.html"
        filepath = self.output_dir / filename
        
        # Convert markdown to HTML
        md_content = page.to_markdown()
        html_content = markdown.markdown(
            md_content,
            extensions=['extra', 'codehilite', 'toc']
        )
        
        # Wrap in HTML template
        html = self._html_template(page.title, html_content)
        
        with open(filepath, 'w') as f:
            f.write(html)
        
        logger.info(f"Generated {filename}")
    
    def _generate_index(self) -> None:
        """Generate index page."""
        index_content = """
        <h1>VoiceMode Documentation</h1>
        <p>Welcome to the VoiceMode documentation. Select a topic from below:</p>
        
        <div class="doc-grid">
        """
        
        # Group pages by type
        grouped = {}
        for page in self.pages:
            if page.doc_type not in grouped:
                grouped[page.doc_type] = []
            grouped[page.doc_type].append(page)
        
        for doc_type, pages in grouped.items():
            index_content += f"""
            <div class="doc-section">
                <h2>{doc_type.value.replace('_', ' ').title()}</h2>
                <ul>
            """
            for page in pages:
                filename = f"{page.doc_type.value}_{page.title.lower().replace(' ', '_')}.html"
                index_content += f'<li><a href="{filename}">{page.title}</a></li>'
            index_content += """
                </ul>
            </div>
            """
        
        index_content += "</div>"
        
        html = self._html_template("VoiceMode Documentation", index_content)
        
        with open(self.output_dir / "index.html", 'w') as f:
            f.write(html)
    
    def _generate_search_index(self) -> None:
        """Generate search index for documentation."""
        search_index = []
        
        for page in self.pages:
            entry = {
                "title": page.title,
                "type": page.doc_type.value,
                "description": page.description,
                "url": f"{page.doc_type.value}_{page.title.lower().replace(' ', '_')}.html",
                "content": page.to_markdown()
            }
            search_index.append(entry)
        
        with open(self.js_dir / "search-index.json", 'w') as f:
            json.dump(search_index, f, indent=2)
    
    def _generate_static_assets(self) -> None:
        """Generate static CSS and JS assets."""
        # Generate CSS
        css_content = """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 24px;
            margin-bottom: 16px;
        }
        
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        
        pre {
            background: #f4f4f4;
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
        }
        
        .doc-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .doc-section {
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }
        
        .doc-section h2 {
            margin-top: 0;
            color: #34495e;
        }
        
        .doc-section ul {
            list-style: none;
            padding: 0;
        }
        
        .doc-section li {
            margin: 8px 0;
        }
        
        .doc-section a {
            color: #3498db;
            text-decoration: none;
        }
        
        .doc-section a:hover {
            text-decoration: underline;
        }
        
        nav {
            background: #34495e;
            color: white;
            padding: 12px;
            margin: -20px -20px 20px -20px;
        }
        
        nav a {
            color: white;
            text-decoration: none;
            margin-right: 20px;
        }
        
        nav a:hover {
            text-decoration: underline;
        }
        
        .search-box {
            float: right;
            padding: 4px 8px;
            border: none;
            border-radius: 4px;
        }
        """
        
        with open(self.css_dir / "style.css", 'w') as f:
            f.write(css_content)
        
        # Generate JS
        js_content = """
        // Search functionality
        function searchDocs() {
            const query = document.getElementById('search').value.toLowerCase();
            fetch('/static/js/search-index.json')
                .then(response => response.json())
                .then(data => {
                    const results = data.filter(item => 
                        item.title.toLowerCase().includes(query) ||
                        item.description.toLowerCase().includes(query) ||
                        item.content.toLowerCase().includes(query)
                    );
                    displaySearchResults(results);
                });
        }
        
        function displaySearchResults(results) {
            const container = document.getElementById('search-results');
            if (!container) return;
            
            container.innerHTML = '<h2>Search Results</h2>';
            if (results.length === 0) {
                container.innerHTML += '<p>No results found.</p>';
                return;
            }
            
            const list = document.createElement('ul');
            results.forEach(result => {
                const item = document.createElement('li');
                item.innerHTML = `<a href="${result.url}">${result.title}</a> - ${result.description}`;
                list.appendChild(item);
            });
            container.appendChild(list);
        }
        """
        
        with open(self.js_dir / "search.js", 'w') as f:
            f.write(js_content)
    
    def _html_template(self, title: str, content: str) -> str:
        """Generate HTML template."""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} - VoiceMode Documentation</title>
            <link rel="stylesheet" href="/static/css/style.css">
            <script src="/static/js/search.js"></script>
        </head>
        <body>
            <nav>
                <a href="/index.html">Home</a>
                <a href="/api_voicemode_api_reference.html">API Reference</a>
                <a href="/user_guide_quickstart_guide.html">Quickstart</a>
                <a href="/architecture_architecture_documentation.html">Architecture</a>
                <input type="text" id="search" class="search-box" placeholder="Search docs..." onkeyup="searchDocs()">
            </nav>
            <main>
                {content}
                <div id="search-results"></div>
            </main>
            <footer>
                <hr>
                <p>&copy; 2024 VoiceMode. Documentation generated on {time.strftime("%Y-%m-%d")}.</p>
            </footer>
        </body>
        </html>
        """


class DocumentationBuilder:
    """Main documentation builder coordinating all generators."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize documentation builder."""
        if not hasattr(self, 'initialized'):
            self.source_dir = Path(__file__).parent
            self.output_dir = Path(__file__).parent.parent / "docs"
            self.website_dir = self.output_dir / "website"
            self.api_generator = APIDocumentationGenerator(self.source_dir)
            self.guide_generator = UserGuideGenerator()
            self.arch_generator = ArchitectureDocumentationGenerator()
            self.website_builder = DocumentationWebsiteBuilder(self.website_dir)
            self.initialized = True
    
    def build_all(self) -> Dict[str, Any]:
        """Build all documentation."""
        logger.info("Building complete documentation suite")
        
        results = {
            "pages_generated": 0,
            "formats": [],
            "website_built": False,
            "errors": []
        }
        
        try:
            # Generate API documentation
            api_docs = self.api_generator.generate()
            self.website_builder.add_page(api_docs)
            results["pages_generated"] += 1
            
            # Generate user guides
            quickstart = self.guide_generator.generate_quickstart()
            self.website_builder.add_page(quickstart)
            results["pages_generated"] += 1
            
            config_guide = self.guide_generator.generate_configuration_guide()
            self.website_builder.add_page(config_guide)
            results["pages_generated"] += 1
            
            troubleshooting = self.guide_generator.generate_troubleshooting_guide()
            self.website_builder.add_page(troubleshooting)
            results["pages_generated"] += 1
            
            # Generate architecture documentation
            arch_docs = self.arch_generator.generate()
            self.website_builder.add_page(arch_docs)
            results["pages_generated"] += 1
            
            # Build website
            self.website_builder.build()
            results["website_built"] = True
            results["formats"] = ["html", "markdown"]
            
            # Save markdown versions
            self._save_markdown_docs()
            
        except Exception as e:
            results["errors"].append(str(e))
            logger.error(f"Documentation build failed: {e}")
        
        return results
    
    def _save_markdown_docs(self) -> None:
        """Save markdown versions of documentation."""
        md_dir = self.output_dir / "markdown"
        md_dir.mkdir(parents=True, exist_ok=True)
        
        for page in self.website_builder.pages:
            filename = f"{page.doc_type.value}_{page.title.lower().replace(' ', '_')}.md"
            filepath = md_dir / filename
            
            with open(filepath, 'w') as f:
                f.write(page.to_markdown())
            
            logger.info(f"Saved markdown: {filename}")
    
    def generate_summary(self) -> str:
        """Generate documentation summary."""
        total_pages = len(self.website_builder.pages)
        
        doc_types = {}
        for page in self.website_builder.pages:
            if page.doc_type not in doc_types:
                doc_types[page.doc_type] = 0
            doc_types[page.doc_type] += 1
        
        summary = f"""
Documentation Build Summary
===========================
Total Pages: {total_pages}
Output Directory: {self.output_dir}
Website Directory: {self.website_dir}

Documentation Types:
"""
        for doc_type, count in doc_types.items():
            summary += f"  - {doc_type.value}: {count} pages\n"
        
        summary += f"""
Formats Generated:
  - HTML (website)
  - Markdown (source)
  
Website Features:
  - Search functionality
  - Responsive design
  - Syntax highlighting
  - Navigation menu
  - Auto-generated index
        """
        
        return summary.strip()


# Singleton instance
_documentation_builder = None


def get_documentation_builder() -> DocumentationBuilder:
    """Get the singleton documentation builder instance."""
    global _documentation_builder
    if _documentation_builder is None:
        _documentation_builder = DocumentationBuilder()
    return _documentation_builder


if __name__ == "__main__":
    # Example usage
    builder = get_documentation_builder()
    results = builder.build_all()
    print(f"Documentation built: {results}")
    print(builder.generate_summary())