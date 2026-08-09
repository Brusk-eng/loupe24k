from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# remove empty strings
install_requires = [r for r in install_requires if r]

setup(
    name="loupe24k",
    version="0.0.1",
    description="ERPNext Customization for Jewellery Business",
    author="Fafadia Tech",
    author_email="sidharth@fafadiatech.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
