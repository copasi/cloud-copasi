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

# Download the CopasiSE Linux64 binary.
RUN mkdir -p /cloud-copasi/copasi/bin
ENV copasi_version="4.34" copasi_build="251"
RUN cd /cloud-copasi/copasi/bin && \
    curl -L https://github.com/copasi/COPASI/releases/download/Build-${copasi_build}/COPASI-${copasi_version}.${copasi_build}-AllSE.tar.gz | \
    tar -xvz --strip-components=2 COPASI-${copasi_version}.${copasi_build}-AllSE/Linux64/CopasiSE && \
    chmod +x CopasiSE
# copy over the test model file
COPY brusselator_scan_test.cps /cloud-copasi/copasi/brusselator_scan_test.cps

WORKDIR /cloud-copasi
RUN mkdir log user-files instance_keypairs

# Install the Python dependencies
COPY requirements.txt /cloud-copasi/requirements.txt
RUN pip install -r /cloud-copasi/requirements.txt
# Copy over the relevant webserver stuff.
# (placing this near the bottom, assuming these may be more likely to change 
# during development, vs. stuff above.)
COPY README.txt LICENSE.txt manage.py cloud-copasi-daemon.sh start_service.sh ./
COPY client_scripts client_scripts
COPY cloud_copasi cloud_copasi
COPY web_interface web_interface
COPY cloud_copasi/settings_EXAMPLE.py cloud_copasi/settings.py

# Note: The CMD override scripts are handling setting up the
# condor env and using the venv
ENTRYPOINT ["/tini", "--"]

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
# CMD ["gunicorn", "django_kubernetes_tutorial.wsgi:application", "--bind", "0.0.0.0:8000"]
# python3 /home/cloudcopasi/cloud-copasi/manage.py runserver "${1:-0.0.0.0}:${2:-8000}"
