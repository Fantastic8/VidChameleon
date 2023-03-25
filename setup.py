# setup.py

from setuptools import setup, find_packages

setup(
    name="example_plugin",
    version="0.1",
    packages=find_packages(),
    entry_points={
        "video_processors": [
            "example_plugin = example_plugin:ExamplePlugin"
        ]
    },
)