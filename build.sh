#!/usr/bin/env bash

# Update system packages
apt-get update

# Install wkhtmltopdf (headless HTML to PDF converter)
apt-get install -y wkhtmltopdf

# Install Google Noto fonts (supports Hindi, Tamil, Telugu, etc.)
apt-get install -y fonts-noto fonts-noto-cjk fonts-noto-core

# Optional: Verify fonts installed (for logging/debugging)
fc-list | grep "Noto"
