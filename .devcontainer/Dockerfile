FROM mcr.microsoft.com/vscode/devcontainers/python:0-3.11

# Install node and other tools
RUN su -c "curl -fsSL https://deb.nodesource.com/setup_18.x | bash -" && \
    apt-get update && apt-get install -y nodejs build-essential git

# Install platformio
RUN python -m pip install --upgrade pip && pip install platformio

# Install hardhat tools
RUN npm install -g npm@latest
