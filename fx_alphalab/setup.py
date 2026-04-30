"""Setup script for fx-alphalab package (fallback for older pip versions)"""
from setuptools import setup, find_packages

setup(
    name="fx-alphalab",
    version="2.0.0",
    packages=find_packages(),
    python_requires=">=3.10",
)
