"""
KB-RAG Setup Configuration.

Defines console entry points for CLI commands.
"""

from setuptools import find_packages, setup

setup(
    name="kb-rag-mcp",
    version="1.0.0",
    description="Knowledge Base RAG system with job management",
    author="Luciano Marinho",
    python_requires=">=3.11",
    packages=find_packages(include=["ingest*", "server*", "observability*"]),
    install_requires=[
        # Core dependencies from requirements.txt
        "mcp>=1.0.0",
        "qdrant-client>=1.9.0",
        "httpx>=0.27.0",
        "lmstudio>=1.0.0",
        "python-docx>=1.1.0",
        "openpyxl>=3.1.0",
        "python-pptx>=0.6.23",
        "pymupdf>=1.24.0",
        "langchain-text-splitters>=0.2.0",
        "uvicorn>=0.30.0",
        "starlette>=0.37.0",
        "python-dotenv>=1.0.0",
        "psutil>=5.9.0",
        "click>=8.0.0",
        "rich>=13.0.0",
        "prometheus-client>=0.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.2.1",
            "mypy>=1.6.0",
            "flake8>=6.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "pytest-asyncio>=1.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            # New modern CLI
            "kb-rag=ingest.cli.main:cli",
            # Legacy CLI with deprecation warning
            "kb-ingest-legacy=ingest.cli.legacy:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
