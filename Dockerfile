# Use an official Python runtime based on Debian 10 ("buster") as a parent image
FROM python:3.11-buster

# Configure apt
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get -y install --no-install-recommends apt-utils 2>&1

RUN apt-get install -y libssl-dev

RUN python3 -m pip install --upgrade pip

# Clean up
RUN apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*
ENV DEBIAN_FRONTEND=dialog

# Set the default shell to bash rather than sh
ENV SHELL /bin/bash

# Don't create .pyc files (why don't we want these?)
ENV PYTHONDONTWRITEBYTECODE 1
# Prevent docker from buffering console output
ENV PYTHONUNBUFFERED 1

# Install python requirements
COPY ./requirements.txt requirements.txt
RUN python3 -m pip install -r requirements.txt

# Set working directory for subsequent RUN ADD COPY CMD instructions
COPY . /app/
WORKDIR /app/

RUN adduser --disabled-password appuser
USER appuser
