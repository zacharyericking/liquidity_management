"""Setup configuration for Uniswap V3 Liquidity Management tool."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="liquidity-management",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python tool for managing Uniswap V3 liquidity positions on Ethereum and Arbitrum",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/liquidity_management",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "liquidity=src.cli:main",
        ],
    },
    include_package_data=True,
)