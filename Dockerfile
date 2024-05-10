# syntax=docker/dockerfile:1
FROM htcondor/mini:23.0-el8
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Apparently bzip2 is needed to unpack the micromamba download.
RUN dnf --assumeyes install bzip2 && dnf --assumeyes clean all

# Add Tini to deal with any orphaned processes
# CMD override scripts might create.
ENV TINI_VERSION=v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

# Get micromamba for differing libcrypto.so dep to the condor stuff.
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | \
    tar -xvj --strip-components=1 --directory /bin bin/micromamba && \
    chmod +x /bin/micromamba

RUN echo "FS_LOCAL_DIR=/home/cloudcopasi/condor/local/fs_auth" > /etc/condor/condor_config.local

# run this out of a special user account
RUN useradd --create-home --shell /bin/bash cloudcopasi
USER cloudcopasi

WORKDIR /home/cloudcopasi

# Create the ssh key used to submit to remote clusters.
RUN mkdir -p .ssh && chmod 700 .ssh && ssh-keygen -N '' -b 4096 -f .ssh/bosco_key.rsa

# Create some log and condor stuff.
RUN mkdir -p log condor && cd condor && \
    mkdir -p local/fs_auth user-files instance_keypairs

# Download the CopasiSE Linux64 binary.
ENV copasi_version="4.34" copasi_build="251"
RUN mkdir -p copasi/bin && cd copasi/bin && \
    curl -L https://github.com/copasi/COPASI/releases/download/Build-${copasi_build}/COPASI-${copasi_version}.${copasi_build}-AllSE.tar.gz | \
    tar -xvz --strip-components=2 COPASI-${copasi_version}.${copasi_build}-AllSE/Linux64/CopasiSE && \
    chmod +x CopasiSE
# copy over the test model file
COPY --chown=cloudcopasi:cloudcopasi brusselator_scan_test.cps copasi/brusselator_scan_test.cps

WORKDIR /home/cloudcopasi/cloud-copasi

# Install the Python dependencies
COPY --chown=cloudcopasi:cloudcopasi conda_env.yml conda_env.yml
RUN micromamba env create --yes --name base --file conda_env.yml && \
    micromamba clean --yes --all
ENV PATH="/home/cloudcopasi/micromamba/bin:${PATH}"

# Copy over the relevant webserver stuff.
# (placing this near the bottom, assuming these may be more likely to change 
# during development, vs. stuff above.)
COPY --chown=cloudcopasi:cloudcopasi README.txt LICENSE.txt manage.py cloud-copasi-daemon.sh start_service.sh ./
COPY --chown=cloudcopasi:cloudcopasi client_scripts client_scripts
COPY --chown=cloudcopasi:cloudcopasi cloud_copasi cloud_copasi
COPY --chown=cloudcopasi:cloudcopasi web_interface web_interface
COPY --chown=cloudcopasi:cloudcopasi cloud_copasi/settings_EXAMPLE.py cloud_copasi/settings.py

ENTRYPOINT ["/tini", "--"]

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
# CMD ["gunicorn", "django_kubernetes_tutorial.wsgi:application", "--bind", "0.0.0.0:8000"]
# python3 /home/cloudcopasi/cloud-copasi/manage.py runserver "${1:-0.0.0.0}:${2:-8000}"
