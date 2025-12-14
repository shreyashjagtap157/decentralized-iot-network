from setuptools import setup, find_packages

setup(
    name="backend-services",
    version="0.1.0",
    packages=find_packages(include=["app*", "alembic*"]),
    install_requires=[],
)