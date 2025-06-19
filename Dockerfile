FROM python:3.12-alpine

# -- CoreDNS binary -------------------------------------------------------
ARG COREDNS_VERSION=1.12.2
RUN apk add --no-cache curl bind-tools \
    && curl -L "https://github.com/coredns/coredns/releases/download/v1.12.2/coredns_1.12.2_linux_amd64.tgz" \
       | tar -xz -C /usr/local/bin \
    && chmod +x /usr/local/bin/coredns

# -- Python deps ----------------------------------------------------------
ENV PIP_BREAK_SYSTEM_PACKAGES=1
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY entrypoint.sh /app/

# -- Project files --------------------------------------------------------
WORKDIR /app
COPY app.py models.py update_coredns.py Corefile.template entrypoint.sh ./
COPY templates/ /app/templates/
COPY static/ /app/static/
RUN chmod +x /app/entrypoint.sh

EXPOSE 53/udp 53/tcp 8000
ENTRYPOINT ["/app/entrypoint.sh"]
