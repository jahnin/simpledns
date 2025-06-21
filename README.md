# SimpleDNS
A simple DNS server for your homelab based on CoreDNS with forward and reverse lookup. 
This setup allows you to quickly run a customizable DNS resolver with optional zone data, forwarding capabilities, and a web interface.

## Prerequisites
- Docker. For more information see, [Docker Get Started](https://www.docker.com/get-started/)


## Getting Started
### Run docker container using a single command
```
sudo docker run --rm -d --name simpledns -p 53:53/udp -p 53:53/tcp -p 8000:8000 jahnin/simpledns:v1.0
```

## Deploy using docker compose
```
services:
  simpledns:
    image: jahnin/simpledns:v1.0
    container_name: simpledns
    environment:
      DNS_FORWARDERS: "8.8.8.8,1.1.1.1"  # comma seperated list of upstream DNS servers (edit as needed)
    volumes:
      - ./data:/data                       # DNS Records in json format
      - ./config/coredns:/etc/coredns      # CoreDNS configuration 
    ports:
      - "53:53/udp"                        # DNS over UDP
      - "53:53/tcp"                        # DNS over TCP
      - "8000:8000"                        # SimpleDNS WebUI. 
    restart: unless-stopped
```

## Configuration
### Environment Variables
- DNS_FORWARDERS: Space-separated list of IPs for upstream DNS servers.

### Volumes
- ./data:/data: DNS records in json format
- ./config/Corefile:/etc/coredns/Corefile: CoreDNS configuration file.

### Ports
- 53/udp, 53/tcp: Exposes DNS service to clients.
- 8000: Web-based interface or API access

## Build the image locally using Dockerfile
```
git clone https://github.com/jahnin/simpledns
docker build --no-cache -t simpledns .
```

## Screenshots
### Landing Page
![](../screenshots/landing-page.png)

