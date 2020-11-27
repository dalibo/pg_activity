import sys

data_files = None
for opt in sys.argv:
    if opt == "--with-man":
        data_files = [("/usr/share/man/man1", ["docs/man/pg_activity.1"])]
        sys.argv.remove(opt)

from setuptools import setup

with open("README.md") as fo:
    long_description = fo.read()

setup(
    name="pg_activity",
    version="2.0.0a1",
    author="Dalibo",
    author_email="contact@dalibo.com",
    scripts=["pg_activity"],
    packages=["pgactivity"],
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
            "psycopg2-binary",
            "pytest",
            "pytest-datadir",
            "pytest-postgresql",
        ],
    },
    data_files=data_files,
)
