import setuptools


with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="py-tinyman-sdk",
    description="Tinyman Python SDK",
    author="Tinyman",
    author_email="hello@tinyman.org",
    version="0.0.1",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    project_urls={
        "Source": "https://github.com/tinyman/py-tinyman-sdk",
    },
    install_requires=["py-algorand-sdk >= 1.6.0"],
    packages=setuptools.find_packages(),
    python_requires=">=3.7",
    package_data={'': ['tinyman/v1/contracts.json']},
    include_package_data=True,
)
