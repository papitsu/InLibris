from setuptools import find_packages, setup

# Read required external libraries from requirements.txt instead of listing them all here.
# Source: https://www.reddit.com/r/Python/comments/3uzl2a/setuppy_requirementstxt_or_a_combination/
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