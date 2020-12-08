import setuptools

setuptools.setup(
    name="awstools",
    version="0.0.1",
    author="Crowdbreaks",
    author_email="info@crowdbreaks.org",
    description="AWS tools for the streamer",
    url="https://github.com/crowdbreaks/streamer",
    packages=setuptools.find_packages(),
    install_requires=[
        'python-dotenv', 'aenum',
        'boto3', 'elasticsearch', 'requests_aws4auth'],
    package_data={'awstools': ['../.env']},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"],
    python_requires='>=3.8')
