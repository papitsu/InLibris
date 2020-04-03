from setuptools import find_packages, setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="inlibris",
    version="0.1.1",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requirements
    )