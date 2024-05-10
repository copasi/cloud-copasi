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

# run this out of a special user account
RUN useradd --create-home --shell /bin/bash cloudcopasi
USER cloudcopasi

WORKDIR /home/cloudcopasi

# Get and install HTCondor
RUN mkdir -p /home/cloudcopasi/condor/local/fs_auth
# "stable" LTS version, which seems to be getting updates with critical bug fixes
ENV condor_version="9.0"
RUN cd condor && \
    curl -L "https://research.cs.wisc.edu/htcondor/tarball/${condor_version}/current/condor-x86_64_Ubuntu20-stripped.tar.gz" | \
    tar -xzv --strip-components=1 && ./bin/make-personal-from-tarball && \
    echo "FS_LOCAL_DIR=/home/cloudcopasi/condor/local/fs_auth" > local/config.d/condor_config.local && \
    cd && echo '#/usr/bin/env bash' >> entrypoint.sh && \
    cat condor/condor.sh >> entrypoint.sh && \
    echo 'exec "$@"' >> entrypoint.sh && \
    chmod +x entrypoint.sh

# Download the CopasiSE Linux64 binary.
RUN mkdir -p copasi/bin
ENV copasi_version="4.34" copasi_build="251"
RUN cd copasi/bin && \
    curl -L https://github.com/copasi/COPASI/releases/download/Build-${copasi_build}/COPASI-${copasi_version}.${copasi_build}-AllSE.tar.gz | \
    tar -xvz --strip-components=2 COPASI-${copasi_version}.${copasi_build}-AllSE/Linux64/CopasiSE && \
    chmod +x CopasiSE
# copy over the test model file
COPY --chown=cloudcopasi:cloudcopasi brusselator_scan_test.cps copasi/brusselator_scan_test.cps

RUN mkdir log user-files instance_keypairs

WORKDIR /home/cloudcopasi/cloud-copasi
# Install the Python dependencies
COPY --chown=cloudcopasi:cloudcopasi requirements.txt cloud-copasi/requirements.txt
RUN pip install -r cloud-copasi/requirements.txt
# Copy over the relevant webserver stuff.
# (placing this near the bottom, assuming these may be more likely to change 
# during development, vs. stuff above.)
COPY --chown=cloudcopasi:cloudcopasi README.txt LICENSE.txt manage.py cloud-copasi-daemon.sh start_service.sh ./
COPY --chown=cloudcopasi:cloudcopasi client_scripts client_scripts
COPY --chown=cloudcopasi:cloudcopasi cloud_copasi cloud_copasi
COPY --chown=cloudcopasi:cloudcopasi web_interface web_interface
COPY --chown=cloudcopasi:cloudcopasi cloud_copasi/settings_EXAMPLE.py cloud_copasi/settings.py

ENTRYPOINT ["/tini", "--", "/home/cloudcopasi/entrypoint.sh"]

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
# CMD ["gunicorn", "django_kubernetes_tutorial.wsgi:application", "--bind", "0.0.0.0:8000"]
# python3 /home/cloudcopasi/cloud-copasi/manage.py runserver "${1:-0.0.0.0}:${2:-8000}"
