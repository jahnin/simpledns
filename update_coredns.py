import os
import signal
import subprocess
import ipaddress
import pathlib
import textwrap
import tempfile
import shutil
from collections import defaultdict
from datetime import datetime

from models import RecordStore

COREFILE_PATH = pathlib.Path("/etc/coredns/Corefile")
TEMPLATE_PATH = pathlib.Path("/app/Corefile.template")
ZONES_DIR = pathlib.Path("/etc/coredns/zones")
HDR = "# --- managed‑zones below this line (do not remove) ---"

store = RecordStore()

def restart_coredns():
    """Restart CoreDNS process"""
    try:
        subprocess.run(["pkill", "coredns"], check=False)
        subprocess.Popen(["coredns", "-conf", str(COREFILE_PATH)])
        print("CoreDNS restarted")
    except Exception as e:
        print(f"Error restarting CoreDNS: {e}")

def get_reverse_zone(ip_str):
    """Get the appropriate reverse DNS zone for an IP address"""
    ip = ipaddress.ip_address(ip_str)
    if ip.version == 4:
        # Use /24 subnet approach
        octets = str(ip).split('.')
        return f"{octets[2]}.{octets[1]}.{octets[0]}.in-addr.arpa"
    else:
        return "ip6.arpa"

def get_reverse_record_name(ip_str, zone):
    """Get the record name within the reverse zone"""
    ip = ipaddress.ip_address(ip_str)
    if ip.version == 4:
        octets = str(ip).split('.')
        return octets[3]
    return str(ip)

def create_zone_file(zone_name, records, is_reverse=False):
    """Create a DNS zone file"""
    zone_file = ZONES_DIR / f"{zone_name}.zone"
    serial = datetime.now().strftime("%Y%m%d%H")
    
    with zone_file.open("w") as f:
        # SOA record
        f.write(f"$ORIGIN {zone_name}.\n")
        f.write(f"$TTL 300\n")
        f.write(f"@\tIN\tSOA\tns1.{zone_name}. admin.{zone_name}. (\n")
        f.write(f"\t\t{serial}\t; Serial\n")
        f.write(f"\t\t3600\t\t; Refresh\n")
        f.write(f"\t\t1800\t\t; Retry\n")
        f.write(f"\t\t604800\t\t; Expire\n")
        f.write(f"\t\t300 )\t\t; Minimum TTL\n")
        f.write(f"@\tIN\tNS\tns1.{zone_name}.\n")
        f.write(f"ns1\tIN\tA\t127.0.0.1\n\n")
        
        # Records
        if is_reverse:
            for record_name, fqdn in records:
                f.write(f"{record_name}\tIN\tPTR\t{fqdn}.\n")
        else:
            for r in records:
                # Extract hostname from FQDN
                hostname = r.fqdn.replace(f".{zone_name}", "")
                if hostname == zone_name:
                    hostname = "@"
                f.write(f"{hostname}\tIN\tA\t{r.ip}\n")
    
    print(f"Created zone file: {zone_file}")

def rebuild_corefile():
    """Rebuild the Corefile with zone files"""
    try:
        # Create zones directory
        ZONES_DIR.mkdir(parents=True, exist_ok=True)
        
        # Read template
        if not TEMPLATE_PATH.exists():
            print(f"Template file not found: {TEMPLATE_PATH}")
            return
        
        template_content = TEMPLATE_PATH.read_text()
        if HDR in template_content:
            pre = template_content.split(HDR)[0]
        else:
            pre = template_content
        
        managed = HDR + "\n"

        # Group records
        forward_zones = defaultdict(list)
        reverse_zones = defaultdict(list)

        records = store.all()
        print(f"Processing {len(records)} DNS records")

        for r in records:
            # Forward zone
            forward_zones[r.domain].append(r)
            
            # Reverse zone
            try:
                reverse_zone = get_reverse_zone(r.ip)
                record_name = get_reverse_record_name(r.ip, reverse_zone)
                reverse_zones[reverse_zone].append((record_name, r.fqdn))
                print(f"Created reverse mapping: {r.ip} -> {record_name} in {reverse_zone}")
            except Exception as e:
                print(f"Warning: Could not create reverse record for {r.ip}: {e}")

        # Create forward zone files and Corefile entries
        for zone, recs in forward_zones.items():
            create_zone_file(zone, recs, is_reverse=False)
            managed += f"\n{zone}:53 {{\n"
            managed += f"    file /etc/coredns/zones/{zone}.zone\n"
            managed += "    reload\n"
            managed += "}\n"
            print(f"Created forward zone: {zone} with {len(recs)} records")

        # Create reverse zone files and Corefile entries
        for reverse_zone, records in reverse_zones.items():
            create_zone_file(reverse_zone, records, is_reverse=True)
            managed += f"\n{reverse_zone}:53 {{\n"
            managed += f"    file /etc/coredns/zones/{reverse_zone}.zone\n"
            managed += "    reload\n"
            managed += "}\n"
            print(f"Created reverse zone: {reverse_zone} with {len(records)} records")

        # Write new Corefile
        new_content = pre + managed
        
        with tempfile.NamedTemporaryFile("w", delete=False, dir=COREFILE_PATH.parent) as tmp:
            tmp.write(new_content)
            tmp_path = tmp.name
        
        shutil.move(tmp_path, COREFILE_PATH)
        print(f"Corefile updated with {len(forward_zones)} forward zones and {len(reverse_zones)} reverse zones")

        # Reload CoreDNS
        reload_coredns()
        
    except Exception as e:
        print(f"Error rebuilding Corefile: {e}")
        raise

def reload_coredns():
    """Reload CoreDNS configuration"""
    pid = os.getenv("COREDNS_PID")
    if pid:
        try:
            os.kill(int(pid), signal.SIGUSR1)
            print(f"Sent SIGUSR1 to CoreDNS (pid {pid})")
        except (ProcessLookupError, ValueError) as e:
            print(f"Could not signal CoreDNS process: {e}")
            restart_coredns()
    else:
        print("COREDNS_PID not set, restarting CoreDNS...")
        restart_coredns()

if __name__ == "__main__":
    rebuild_corefile()