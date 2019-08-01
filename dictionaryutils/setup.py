from setuptools import setup, find_packages
from subprocess import check_output


def get_version():
    try:
        tag = check_output(
            ["git", "describe", "--tags", "--abbrev=0", "--match=[0-9]*"]
        )
        return tag.strip("\n")
    except Exception:
        # if somehow you get the repo not from git,
        # hardcode default major version
        return "2.0.0"


setup(
    name="dictionaryutils",
    version=get_version(),
    packages=find_packages(),
    install_requires=["PyYAML==4.2b1", "jsonschema==2.5.1"],
    package_data={"dictionaryutils": ["schemas/*.yaml"]},
)
