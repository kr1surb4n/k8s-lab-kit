# A minimal SSH jump image: openssh + kubectl + one key-only user.
# Build: docker build -t k8s-lab/bastion:1.0 bastion/k8s
FROM alpine:3.22

# openssh provides sshd and ssh-keygen; bash is for the user's shell.
RUN apk add --no-cache openssh bash curl ca-certificates \
    && adduser -D -s /bin/bash -h /home/labjump labjump \
    && mkdir -p /run/sshd /etc/ssh/keys \
    && curl -fsSLo /usr/local/bin/kubectl \
       https://dl.k8s.io/release/v1.37.1/bin/linux/amd64/kubectl \
    && chmod 0755 /usr/local/bin/kubectl

COPY entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
