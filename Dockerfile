FROM nixos/nix

# Create a non-root user
RUN useradd -m -s /bin/bash developer && \
    echo "developer ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

WORKDIR /workspace

# Copy the project files
COPY --chown=developer:developer . .

USER developer

RUN chmod +x setup.sh && \
    ./setup.sh

CMD ["/bin/bash"]
