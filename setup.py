import setuptools

setuptools.setup(
    name="stream",
    version="0.0.1",
    author="Crowdbreaks",
    author_email="info@crowdbreaks.org",
    description="Twitter API v1.1 streamer",
    url="https://github.com/crowdbreaks/crowdbreaks-streamer-2",
    packages=setuptools.find_packages(),
    install_requires=[
        'python-dotenv', 'aenum', 'dacite', 'tweepy',
        'boto3', 'elasticsearch', 'requests_aws4auth',
        'twiprocess @ git+ssh://git@github.com:crowdbreaks/twiprocess.git'],
    entry_points={'console_scripts': [
        'run-stream=stream.run:main']},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"],
    python_requires='>=3.8')
