import setuptools

setuptools.setup(
    name="awstools",
    version="0.0.1",
    author="Crowdbreaks",
    author_email="info@crowdbreaks.org",
    description="AWS tools for the streamer",
    url="https://github.com/digitalepidemiologylab/crowdbreaks-streamer",
    packages=setuptools.find_packages(),
    install_requires=[
        'python-dotenv', 'aenum', 'dacite', 'requests',
        'boto3==1.14.48', 'elasticsearch==7.16.0',
        'twiprocess @ git+https://github.com/digitalepidemiologylab/twiprocess.git'],
    package_data={'awstools': ['awstools.env', 'config/*']},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"],
    python_requires='>=3.8')
