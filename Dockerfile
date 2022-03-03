# WORK IN PROGRESS!
# This does not support the full condor-copasi service yet.
# syntax=docker/dockerfile:1
FROM python:3.8
# just some niceties . . .
RUN apt-get update --assume-yes && \
    apt-get install --assume-yes \
    less \
    htop \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CONDOR_CONFIG="/home/cloudcopasi/bosco/etc/condor_config" \
    PYTHONPATH="/home/cloudcopasi/bosco/lib/python3:/home/cloudcopasi/cloud-copasi" \
    DJANGO_SETTINGS_MODULE=cloud_copasi.settings

RUN useradd --create-home --shell /bin/bash cloudcopasi

# Download the appropriate CopasiSE into a standard bin path.
WORKDIR /usr/local/bin
ENV copasi_version="4.34" copasi_build="251"
RUN curl -L https://github.com/copasi/COPASI/releases/download/Build-${copasi_build}/COPASI-${copasi_version}.${copasi_build}-AllSE.tar.gz | \
    tar -xvz --strip-components=2 "COPASI-${copasi_version}.${copasi_build}-AllSE/Linux64/CopasiSE" && chmod +x CopasiSE

# The current expected location of the CopasiSE binary (Is it better to just download it here, in the first place?)
WORKDIR /home/cloudcopasi/copasi/bin
RUN ln -s /usr/local/bin/CopasiSE

# Get and install HTCondor Bosco (using WORKDIR just to get the added "mkdir" benefit)
WORKDIR /condor
ENV condor_version="9.8.0" condor_build="20220217"
RUN curl -L "https://research.cs.wisc.edu/htcondor/tarball/current/${condor_version}/daily/condor-${condor_version}-${condor_build}-x86_64_Ubuntu20-stripped.tar.gz" | \
    tar -xzv --strip-components=1

USER cloudcopasi
# just to temporarily make sure the layers below are rebuilt when this changes
ENV docker_build_number=3
RUN ./condor_install --bosco

WORKDIR /home/cloudcopasi
COPY bosco/bosco_cluster bosco/bosco_cluster
COPY brusselator_scan_test.cps copasi/brusselator_scan_test.cps
RUN mkdir log user-files instance_keypairs

WORKDIR /home/cloudcopasi/cloud-copasi
COPY README.txt LICENSE.txt manage.py requirements.txt ./
COPY client_scripts client_scripts
COPY cloud_copasi cloud_copasi

USER root
RUN python3 -m pip install --upgrade pip && \
    pip install -r requirements.txt
