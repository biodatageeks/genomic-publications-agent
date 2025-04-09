from setuptools import setup, find_packages

setup(
    name="coordinates-lit",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.31.0",
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "black>=23.7.0",
        "isort>=5.12.0",
        "mypy>=1.5.1",
        "pyyaml>=6.0.1",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "black",
            "isort",
            "mypy",
        ],
    },
    python_requires=">=3.9",
    author="Wojciech Sitek",
    author_email="wojciech.sitek@pw.edu.pl",
    description="Bioinformatics tool for analyzing literature coordinates",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/coordinates-lit",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 