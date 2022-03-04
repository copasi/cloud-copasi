# WORK IN PROGRESS!
# This does not support the full condor-copasi service yet.
# syntax=docker/dockerfile:1
FROM python:3.8
# just some niceties . . .
RUN apt-get update --assume-yes && \
    apt-get install --assume-yes \
    less \
    nano \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CONDOR_CONFIG="/home/cloudcopasi/condor/etc/condor_config" \
    PYTHONPATH="/home/cloudcopasi/condor/lib/python3:/home/cloudcopasi/cloud-copasi" \
    DJANGO_SETTINGS_MODULE=cloud_copasi.settings

RUN useradd --create-home --shell /bin/bash cloudcopasi

# Download the CopasiSE binaries.
WORKDIR /home/cloudcopasi/copasi
ENV copasi_version="4.34" copasi_build="251"
RUN curl -L https://github.com/copasi/COPASI/releases/download/Build-${copasi_build}/COPASI-${copasi_version}.${copasi_build}-AllSE.tar.gz | \
    tar -xvz --strip-components=1 && chmod +x */CopasiSE && \
    mkdir bin && ln -s ../Linux64/CopasiSE bin/CopasiSE

# Get and install HTCondor (using WORKDIR just to get the added "mkdir" benefit)
WORKDIR /home/cloudcopasi/condor
ENV condor_version="9.8.0" condor_build="20220301"
RUN curl -L "https://research.cs.wisc.edu/htcondor/tarball/current/${condor_version}/daily/condor-${condor_version}-${condor_build}-x86_64_Ubuntu20-stripped.tar.gz" | \
    tar -xzv --strip-components=1 && \
    mkdir -p local/config.d && \
    mkdir -p local/fs_auth && \
    echo "FS_LOCAL_DIR=/home/cloudcopasi/condor/local/fs_auth" >> local/config.d/condor_config.local
COPY bosco/bosco_cluster bin/bosco_cluster
WORKDIR /home/cloudcopasi
COPY brusselator_scan_test.cps copasi/brusselator_scan_test.cps
RUN mkdir log user-files instance_keypairs

WORKDIR /home/cloudcopasi/cloud-copasi
COPY README.txt LICENSE.txt manage.py requirements.txt ./
COPY client_scripts client_scripts
COPY cloud_copasi cloud_copasi

USER root
RUN python3 -m pip install --upgrade pip && \
    pip install -r requirements.txt
