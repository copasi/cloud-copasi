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
USER cloudcopasi

# Download the CopasiSE binaries.
RUN mkdir /home/cloudcopasi/copasi
WORKDIR /home/cloudcopasi/copasi
ENV copasi_version="4.34" copasi_build="251"
RUN curl -L https://github.com/copasi/COPASI/releases/download/Build-${copasi_build}/COPASI-${copasi_version}.${copasi_build}-AllSE.tar.gz | \
    tar -xvz --strip-components=1 && chmod +x */CopasiSE && \
    mkdir bin && ln -s ../Linux64/CopasiSE bin/CopasiSE

# Get and install HTCondor
RUN mkdir /home/cloudcopasi/condor
WORKDIR /home/cloudcopasi/condor
# "stable" LTS version, which seems to be getting updates with critical bug fixes
ENV condor_version="9.0"
RUN curl -L "https://research.cs.wisc.edu/htcondor/tarball/${condor_version}/current/condor-x86_64_Ubuntu20-stripped.tar.gz" | \
    tar -xzv --strip-components=1 && ./bin/make-personal-from-tarball

WORKDIR /home/cloudcopasi
# Make our local modifications to the condor installation.
COPY --chown=cloudcopasi:cloudcopasi condor_overlay/bin/bosco_cluster condor/bin/bosco_cluster
COPY --chown=cloudcopasi:cloudcopasi condor_overlay/local condor/local

COPY --chown=cloudcopasi:cloudcopasi brusselator_scan_test.cps copasi/brusselator_scan_test.cps
RUN mkdir log user-files instance_keypairs

# Copy over the relevant webserver stuff.
RUN mkdir /home/cloudcopasi/cloud-copasi
WORKDIR /home/cloudcopasi/cloud-copasi
COPY --chown=cloudcopasi:cloudcopasi README.txt LICENSE.txt manage.py requirements.txt cloud-copasi-daemon.sh ./
COPY --chown=cloudcopasi:cloudcopasi client_scripts client_scripts
COPY --chown=cloudcopasi:cloudcopasi cloud_copasi cloud_copasi

# Install the Python dependencies.
USER root
RUN python3 -m pip install --upgrade pip && \
    pip install -r requirements.txt
USER cloudcopasi
WORKDIR /home/cloudcopasi

CMD ./cloud-copasi/cloud-copasi-daemon.sh

