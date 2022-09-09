import setuptools

setuptools.setup(
    name="train_moob",
    version="0.0.1",
    author="Crowdbreaks",
    author_email="info@crowdbreaks.org",
    description="Train MOOB on AWS Sagemaker",
    url="https://github.com/digitalepidemiologylab/crowdbreaks-streamer",
    packages=setuptools.find_packages(),
    install_requires=[
        'torch', 'transformers', 'strlearn', 'spacy'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"],
    python_requires='>=3.8')
