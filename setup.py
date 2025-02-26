from setuptools import setup, find_packages

setup(
    name="stressandra",
    version="0.1",
    packages=find_packages(),
    install_requires=["cassandra-driver", "jmxquery"],
    entry_points={
        "console_scripts": [
            "stressandra = stressandra.cli:main"
        ]
    },
)
