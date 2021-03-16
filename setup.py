import os.path
import sys

data_files = None
for opt in sys.argv:
    if opt == "--with-man":
        data_files = [("/usr/share/man/man1", ["docs/man/pg_activity.1"])]
        sys.argv.remove(opt)

from setuptools import find_packages, setup

HERE = os.path.dirname(__file__)

with open(os.path.join(HERE, "README.md")) as fo:
    long_description = fo.read()


def get_version() -> str:
    fpath = os.path.join(HERE, "pgactivity", "__init__.py")
    with open(fpath) as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split('"')[1]
    raise Exception(f"version information not found in {fpath}")


setup(
    name="pg_activity",
    version=get_version(),
    author="Dalibo",
    author_email="contact@dalibo.com",
    packages=find_packages("."),
    include_package_data=True,
    url="https://github.com/dalibo/pg_activity",
    license="PostgreSQL",
    description="Command line tool for PostgreSQL server activity monitoring.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Console :: Curses",
        "License :: OSI Approved :: PostgreSQL License",
        "Programming Language :: Python :: 3",
        "Topic :: Database",
    ],
    keywords="postgresql activity monitoring cli sql top",
    python_requires=">=3.6",
    install_requires=[
        "attrs",
        "blessed",
        "humanize",
        "psutil >= 2.0.0",
    ],
    extras_require={
        "testing": [
            "psycopg2-binary >= 2.8",
            "pytest",
            "pytest-postgresql",
        ],
    },
    data_files=data_files,
    entry_points={
        "console_scripts": [
            "pg_activity=pgactivity.cli:main",
        ],
    },
)
