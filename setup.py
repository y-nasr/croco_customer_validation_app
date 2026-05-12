from setuptools import find_packages, setup

with open("requirements.txt") as f:
    install_requires = [line.strip() for line in f.readlines() if line.strip() and not line.startswith("#")]

# get version from __version__ variable in customer_mobile_validation/__init__.py
from customer_mobile_validation import __version__ as version

setup(
    name="customer_mobile_validation",
    version=version,
    description="Validates and normalizes Customer mobile numbers (E.164, +CC...) with cross-Customer duplicate detection and on-save format upgrade.",
    author="Crocoit",
    author_email="info@crocoit.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
