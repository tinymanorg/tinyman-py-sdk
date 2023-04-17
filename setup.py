import setuptools


with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="tinyman-py-sdk",
    description="Tinyman Python SDK",
    author="Tinyman",
    author_email="hello@tinyman.org",
    version="2.1.1",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    project_urls={
        "Source": "https://github.com/tinyman/tinyman-py-sdk",
    },
    install_requires=["py-algorand-sdk >= 1.10.0"],
    packages=setuptools.find_packages(),
    python_requires=">=3.8",
    package_data={
        "tinyman.v1": ["asc.json"],
        "tinyman.v2": ["amm_approval.map.json", "swap_router_approval.map.json"],
    },
    include_package_data=True,
)
