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
        "attrs >= 17, !=21.1",
        "blessed",
        "humanize",
        "psutil >= 2.0.0",
    ],
    extras_require={
        "dev": [
            "black >= 21.12b0",
            "check-manifest",
            "flake8",
            "mypy",
        ],
        "testing": [
            "psycopg2-binary >= 2.8",
            "pytest < 7.0.0",  # pytest-postgresql 3 is not compatible with pytest 7.0.0
            # From 4.0, pytest-postgresql is no compatible with python 3.6.
            "pytest-postgresql ~= 3.0",
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
