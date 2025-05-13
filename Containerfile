# ---------------------------------------------------------------
# kai‑service  —  installs deps from pyproject.toml
# ---------------------------------------------------------------
    FROM quay.io/fedora/fedora:40

    # ---- system dependencies --------------------------------------
    RUN dnf -y install \
            git gcc make \
            python3.12 python3.12-devel \
            java-17-openjdk-headless \
            maven && \
        dnf clean all


    
    # ---- copy source tree -----------------------------------------
    WORKDIR /opt
    # place package and example exactly where service.py expects them
    COPY app/kai/           /opt/kai/
    COPY app/example/       /opt/kai/example/
    COPY app/pyproject.toml /opt/kai/

    # --- NEW: static files for the mini‑UI -------------------------
    COPY app/templates/     /opt/templates/
    
    # ---- install Python deps from pyproject.toml ------------------
    # setuptools‑scm needs a version when .git is absent
    ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0
    RUN python3.12 -m pip install --upgrade pip && \
        pip install "setuptools_scm[toml]>=8" && \
        pip install --upgrade "mcp>=0.8.2" && \
        pip install /opt/kai
    
    # ---- helper scripts -------------------------------------------
    COPY entrypoint.sh /usr/local/bin/
    COPY service.py     /opt/
    # copy the new files
    COPY kai_mcp_tools.py /opt/
    COPY main.py          /opt/
    
    # ---- runtime environment --------------------------------------
    ENV PYTHONUNBUFFERED=1 \
        PYTHONPATH=/opt:$PYTHONPATH \
        OPENAI_API_KEY=dummy \
        OPENAI_API_BASE=https://route-llama-70b-ai-composer.apps.salamander.aimlworkbench.com/v1 \
        PIP_DISABLE_PIP_VERSION_CHECK=1
    
    EXPOSE 8000
    ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
    