from setuptools import setup, find_packages

setup(
    name="MinFin",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "matplotlib>=3.5.0",
        "seaborn>=0.11.0",
        "openpyxl>=3.0.0",
        "xlrd>=2.0.1",
    ],
    python_requires=">=3.8",
) 