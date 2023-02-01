import pathlib

from setuptools import find_packages, setup

HERE = pathlib.Path(__file__).parent

long_description = (HERE / "README.md").read_text()


def get_version() -> str:
    fpath = HERE / "pgactivity" / "__init__.py"
    with fpath.open() as f:
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
    project_urls={
        "Bug Tracker": "https://github.com/dalibo/pg_activity/issues/",
        "Changelog": "https://github.com/dalibo/pg_activity/blob/master/CHANGELOG.md",
        "Source code": "https://github.com/dalibo/pg_activity/",
    },
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
    python_requires=">=3.7",
    install_requires=[
        "attrs >= 17, !=21.1",
        "blessed >= 1.15.0",
        "humanize >= 2.6.0",
        "psutil >= 2.0.0",
    ],
    extras_require={
        "dev": [
            "black >= 23.1.0",
            "check-manifest",
            "codespell",
            "flake8",
            "mypy",
        ],
        "psycopg2": [
            "psycopg2-binary >= 2.8",
        ],
        "psycopg": [
            "psycopg[binary]",
        ],
        "testing": [
            "psycopg[binary]",
            "pytest",
            "pytest-postgresql >= 4.0",
        ],
    },
    data_files=[
        ("share/man/man1", ["docs/man/pg_activity.1"]),
    ],
    entry_points={
        "console_scripts": [
            "pg_activity=pgactivity.cli:main",
        ],
    },
    zip_safe=False,
)
