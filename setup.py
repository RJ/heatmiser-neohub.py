import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="heatmiser_neohub", # Replace with your own username
    version="0.0.1",
    author="Richard Jones",
    author_email="rj@metabrew.com",
    description="Library to talk the LAN-JSON protocol to Heatmiser Neohub v1",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/RJ/heatmiser_neohub.py",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    scripts=['bin/neocli.py']
)