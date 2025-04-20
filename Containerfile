FROM quay.io/fedora/fedora:40

# -- system deps -------------------------------------------------
RUN dnf -y install git gcc make python3.12 python3.12-devel && \
    dnf clean all

# -- copy code ---------------------------------------------------
WORKDIR /opt/kai
COPY app/ /opt/kai/app/
COPY requirements.txt /tmp/requirements.txt
COPY entrypoint.sh /usr/local/bin/
COPY service.py /opt/kai/

# -- runtime -----------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    OPENAI_API_KEY=dummy \
    OPENAI_API_BASE=https://llama-predictor-restore-db-test.apps.salamander.aimlworkbench.com/v1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
