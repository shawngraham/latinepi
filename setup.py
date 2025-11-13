"""
Setup script for latinepi package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README for the long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="latinepi",
    version="0.1.0",
    description="Extract structured personal data from Roman Latin epigraphic inscriptions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Shawn Graham",
    url="https://github.com/shawngraham/latinepi",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "grammar": ["cltk>=1.0.0"],
        "dev": ["pytest>=7.0.0"],
    },
    entry_points={
        "console_scripts": [
            "latinepi=latinepi.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Text Processing :: Linguistic",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="latin epigraphy inscriptions named-entity-recognition nlp",
)
