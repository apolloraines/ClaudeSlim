#!/usr/bin/env python3
"""
ClaudeSlim - Reduce Claude Code API token usage by 60-85%
"""

from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="claudeslim",
    version="1.0.0",
    author="Apollo Raines",
    author_email="apollo@saiql.ai",
    description="Reduce Claude Code API token usage by 60-85% through intelligent compression",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/apolloraines/claudeslim",
    project_urls={
        "Bug Tracker": "https://github.com/apolloraines/claudeslim/issues",
        "Documentation": "https://github.com/apolloraines/claudeslim#readme",
        "Source Code": "https://github.com/apolloraines/claudeslim",
    },
    py_modules=["claude_compressor", "compression_proxy"],
    install_requires=[
        "flask>=2.0.0",
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "claudeslim=compression_proxy:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    keywords="claude anthropic api compression tokens cli proxy",
    license="MIT",
)
