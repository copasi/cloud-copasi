# syntax=docker/dockerfile:1
FROM python:3.8
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# just some niceties . . .
RUN apt-get update --assume-yes && \
    apt-get install --assume-yes \
    less \
    nano \
    vim \
    htop \
    && apt-get clean --assume-yes

# Add Tini to deal with any orphaned processes
# CMD override scripts might create.
ENV TINI_VERSION=v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

RUN useradd --create-home --shell /bin/bash cloudcopasi
USER cloudcopasi

# Install the Python dependencies
COPY --chown=cloudcopasi:cloudcopasi requirements.txt /home/cloudcopasi/requirements.txt
RUN pip install -r /home/cloudcopasi/requirements.txt

# Download the CopasiSE Linux64 binary.
RUN mkdir -p /home/cloudcopasi/copasi/bin
WORKDIR /home/cloudcopasi/copasi/bin
ENV copasi_version="4.34" copasi_build="251"
RUN curl -L https://github.com/copasi/COPASI/releases/download/Build-${copasi_build}/COPASI-${copasi_version}.${copasi_build}-AllSE.tar.gz | \
    tar -xvz --strip-components=2 COPASI-${copasi_version}.${copasi_build}-AllSE/Linux64/CopasiSE && \
    chmod +x CopasiSE
# copy over the test model file
COPY --chown=cloudcopasi:cloudcopasi brusselator_scan_test.cps ../brusselator_scan_test.cps

# Get and install HTCondor
RUN mkdir /home/cloudcopasi/condor
WORKDIR /home/cloudcopasi/condor
# "stable" LTS version, which seems to be getting updates with critical bug fixes
ENV condor_version="9.0"
RUN curl -L "https://research.cs.wisc.edu/htcondor/tarball/${condor_version}/current/condor-x86_64_Ubuntu20-stripped.tar.gz" | \
    tar -xzv --strip-components=1 && ./bin/make-personal-from-tarball
RUN mkdir -p local/fs_auth && \
    echo "FS_LOCAL_DIR=/home/cloudcopasi/condor/local/fs_auth" > local/config.d/condor_config.local

RUN cd && mkdir log user-files instance_keypairs

# Copy over the relevant webserver stuff.
# (placing this near the bottom, assuming these may be more likely to change 
# during development, vs. stuff above.)
RUN mkdir -p /home/cloudcopasi/cloud-copasi
WORKDIR /home/cloudcopasi/cloud-copasi
COPY --chown=cloudcopasi:cloudcopasi README.txt LICENSE.txt manage.py cloud-copasi-daemon.sh start_service.sh ./
COPY --chown=cloudcopasi:cloudcopasi client_scripts client_scripts
COPY --chown=cloudcopasi:cloudcopasi cloud_copasi cloud_copasi
COPY --chown=cloudcopasi:cloudcopasi web_interface web_interface
COPY --chown=cloudcopasi:cloudcopasi cloud_copasi/settings_EXAMPLE.py cloud_copasi/settings.py

# Set up Django
RUN python3 manage.py collectstatic --noinput
RUN python3 manage.py makemigrations web_interface --noinput

# Note: The CMD override scripts are handling setting up the
# condor env and using the venv
ENTRYPOINT ["/tini", "--"]

# maybe a logical place to end up if attaching interactively?
WORKDIR /home/cloudcopasi

CMD ["/bin/bash"]
