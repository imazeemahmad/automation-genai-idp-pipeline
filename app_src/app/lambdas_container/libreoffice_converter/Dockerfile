# ---------------------------------------------------------------------------
# LibreOffice converter Lambda (x86_64) — built on the grand_org Artifactory
# Debian-based python image (docker-innersource-remote.artifactory.grand_org.com).
#
# Generic S3-to-S3 document-to-PDF converter. No business logic.
# Supports: PPTX, XLSX, PPT, XLS, ODP, ODS → PDF
#
# Because this base is a plain Python image (not the AWS Lambda base), we
# install the AWS Lambda Runtime Interface Client (awslambdaric) ourselves and
# wire up the ENTRYPOINT that the AWS Lambda base image would normally provide.
#
# NOTE: x86_64 only. LibreOffice does not publish a Linux ARM64 (aarch64) RPM
# archive on the download mirror, so this Dockerfile cannot target arm64.
#
# Build (from the repo root):
#   docker build \
#     --platform linux/amd64 \
#     --build-arg PYTHON_RELEASE=3.12 \
#     -f app_src/app/lambdas_container/libreoffice_converter/Dockerfile \
#     -t libreoffice-converter:latest .
# ---------------------------------------------------------------------------
ARG PYTHON_RELEASE=3.12
FROM docker-innersource-remote.artifactory.grand_org.com/python:${PYTHON_RELEASE} AS base

ARG LIBREOFFICE_CHANNEL=stable
ARG LIBREOFFICE_VERSION=26.2.6
ARG LIBREOFFICE_DOWNLOAD_BASE=https://download.documentfoundation.org/libreoffice

# Lambda-style task root where the handler code lives.
ENV LAMBDA_TASK_ROOT=/var/task
ENV PATH="/usr/local/bin:/usr/bin:/bin:${PATH}"

# Fail pipelines on the first failing command (needed for the rpm2cpio | cpio
# pipe below, and flagged by hadolint DL4006).
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ---------------------------------------------------------------------------
# 1. System dependencies
#    LibreOffice ships as .rpm archives, so we install `rpm` + the runtime
#    libraries LibreOffice needs (fonts, X libs, SSL/NSS, dbus, cups, xslt...).
#    Package versions are intentionally not pinned (DL3008): the runtime libs
#    track the Debian base image and pinning them breaks on base updates.
# ---------------------------------------------------------------------------
# hadolint ignore=DL3008
RUN set -eux \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        tar \
        gzip \
        xz-utils \
        binutils \
        cpio \
        rpm \
        fontconfig \
        fonts-noto-cjk \
        libsm6 \
        libxinerama1 \
        libxrender1 \
        libxext6 \
        libx11-6 \
        libxslt1.1 \
        libssl3 \
        libnss3 \
        libnspr4 \
        libdbus-1-3 \
        libcups2 \
        libglib2.0-0 \
        libfreetype6 \
        libfontconfig1 \
        libcairo2 \
        libxrandr2 \
        libxcb1 \
        libx11-xcb1 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxfixes3 \
        libxi6 \
        libxtst6 \
        libcairo-gobject2 \
        libgtk-3-0 \
        libgdk-pixbuf-2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libharfbuzz0b \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# 2. Install LibreOffice from the official RPM archive
#    We extract the .rpm payloads with rpm2cpio | cpio (no rpm database on
#    Debian) directly into the filesystem root.
#    The `cd` calls target ephemeral temp dirs local to the shell script, so
#    WORKDIR is not appropriate here (DL3003).
# ---------------------------------------------------------------------------
# hadolint ignore=DL3003
RUN set -eux \
    && libre_tmp="$(mktemp -d -t libreoffice-XXXXXXXX)" \
    && cd "${libre_tmp}" \
    && libre_archive="LibreOffice_${LIBREOFFICE_VERSION}_Linux_x86-64_rpm.tar.gz" \
    && libre_repo="${LIBREOFFICE_DOWNLOAD_BASE}/${LIBREOFFICE_CHANNEL}/${LIBREOFFICE_VERSION}/rpm/x86_64" \
    && curl --fail --show-error --location --retry 3 --retry-delay 2 -o "${libre_archive}" "${libre_repo}/${libre_archive}" \
    && tar -xzf "${libre_archive}" \
    && libre_rpm_root="$(find . -maxdepth 1 -type d -name 'LibreOffice_*_Linux_x86-64_rpm' -print -quit)" \
    && test -n "${libre_rpm_root}" \
    && for rpm_file in "${libre_rpm_root}/RPMS/"*.rpm; do \
           rpm2cpio "${rpm_file}" | (cd / && cpio -idm --quiet); \
       done \
    && libre_bin="$(find /opt -type f -name 'soffice' -print -quit)" \
    && test -n "${libre_bin}" \
    && ln -sf "${libre_bin}" /usr/bin/libreoffice \
    && ln -sf "${libre_bin}" /usr/bin/soffice \
    && rm -rf "${libre_tmp}"

# ---------------------------------------------------------------------------
# 3. Python dependencies + AWS Lambda Runtime Interface Client
# ---------------------------------------------------------------------------
COPY app_src/app/lambdas_container/libreoffice_converter/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt awslambdaric \
    && rm /tmp/requirements.txt

# ---------------------------------------------------------------------------
# 4. Copy the handler
# ---------------------------------------------------------------------------
WORKDIR ${LAMBDA_TASK_ROOT}
COPY app_src/app/lambdas_container/libreoffice_converter/handler.py ${LAMBDA_TASK_ROOT}/

# ---------------------------------------------------------------------------
# 5. Runtime configuration
#    HOME=/tmp is required for LibreOffice to create its user profile.
# ---------------------------------------------------------------------------
ENV HOME=/tmp

# Pre-generate LibreOffice bootstrap files to improve cold-start performance.
# hadolint ignore=DL3003
RUN touch /tmp/test.txt \
    && cd /tmp \
    && libreoffice --headless --invisible --nodefault --view \
        --nolockcheck --nologo --norestore --convert-to pdf \
        --outdir /tmp /tmp/test.txt \
    && rm /tmp/test.*

# ---------------------------------------------------------------------------
# 6. Entry point — the AWS Lambda Runtime Interface Client
# ---------------------------------------------------------------------------
ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["handler.handler"]
