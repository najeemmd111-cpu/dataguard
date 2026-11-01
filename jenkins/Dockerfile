# Jenkins with the project's toolchains built in: Python 3.12 (via uv), Node 22,
# Java 21 + Maven, kubeconform. The pipeline needs no Docker socket.
FROM node:22-bookworm-slim AS node
FROM maven:3.9-eclipse-temurin-21 AS maven
FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

FROM jenkins/jenkins:2.580.2-lts-jdk21

USER root
ARG TARGETARCH

RUN apt-get update \
 && apt-get install -y --no-install-recommends libstdc++6 \
 && rm -rf /var/lib/apt/lists/*

# Node 22 and npm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Maven (Java 21 comes with the Jenkins image)
COPY --from=maven /usr/share/maven /usr/share/maven
RUN ln -s /usr/share/maven/bin/mvn /usr/local/bin/mvn

# uv and a managed Python 3.12, shared by every build
COPY --from=uv /uv /uvx /usr/local/bin/
ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_LINK_MODE=copy
RUN uv python install 3.12 && chmod -R a+rX /opt/python

# kubeconform, for the Kubernetes manifest check
RUN curl -fsSL "https://github.com/yannh/kubeconform/releases/download/v0.6.7/kubeconform-linux-${TARGETARCH:-amd64}.tar.gz" \
    | tar xz -C /usr/local/bin kubeconform

USER jenkins

COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

COPY --chown=jenkins:jenkins casc.yaml /usr/share/jenkins/ref/casc.yaml
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false" \
    CASC_JENKINS_CONFIG=/usr/share/jenkins/ref/casc.yaml \
    PLUGINS_FORCE_UPGRADE=true
