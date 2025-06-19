from dataclasses import dataclass, asdict
from ipaddress import ip_address
from typing import List
import json, pathlib
import re

_DB = pathlib.Path("/data/records.json")

@dataclass
class DNSRecord:
    fqdn: str
    ip: str
    domain: str = ""  # Will be auto-populated

    def __post_init__(self):
        """Automatically extract domain from FQDN"""
        if not self.domain:
            self.domain = self.extract_domain(self.fqdn)
    
    @staticmethod
    def extract_domain(fqdn):
        """Extract the domain from an FQDN"""
        # Remove trailing dot if present
        fqdn = fqdn.rstrip('.')
        
        # Split into parts
        parts = fqdn.split('.')
        
        if len(parts) < 2:
            raise ValueError("FQDN must have at least two parts (e.g., example.com)")
        
        # For now, assume domain is the last two parts
        # This works for most cases like www.example.com -> example.com
        # For more complex cases (like co.uk), you'd need a TLD list
        domain = '.'.join(parts[-2:])
        
        return domain

    def validate(self):
        """Validate the DNS record"""
        if not self.fqdn:
            raise ValueError("FQDN is required")
        
        if not self.ip:
            raise ValueError("IP address is required")
        
        # Validate FQDN format
        fqdn_clean = self.fqdn.rstrip('.')
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', fqdn_clean):
            raise ValueError("Invalid FQDN format")
        
        # Validate IP address
        try:
            ip_address(self.ip)
        except ValueError:
            raise ValueError("Invalid IP address format")
        
        # Ensure domain is extracted
        if not self.domain:
            raise ValueError("Could not extract domain from FQDN")

class RecordStore:
    def __init__(self, path=_DB):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]")

    def all(self) -> List[DNSRecord]:
        """Get all DNS records"""
        data = json.loads(self.path.read_text())
        records = []
        for r in data:
            # Handle both old format (with domain) and new format (domain auto-extracted)
            record = DNSRecord(**r)
            records.append(record)
        return records

    def add(self, rec: DNSRecord):
        """Add a new DNS record"""
        rec.validate()
        records = self.all()
        
        # Check for duplicate FQDN
        if any(r.fqdn.rstrip('.').lower() == rec.fqdn.rstrip('.').lower() for r in records):
            raise ValueError(f"FQDN '{rec.fqdn}' already exists")
        
        records.append(rec)
        self._save_records(records)

    def delete(self, fqdn: str):
        """Delete a DNS record by FQDN"""
        records = self.all()
        fqdn_clean = fqdn.rstrip('.').lower()
        new_records = [r for r in records if r.fqdn.rstrip('.').lower() != fqdn_clean]
        
        if len(new_records) == len(records):
            raise ValueError(f"FQDN '{fqdn}' not found")
        
        self._save_records(new_records)

    def _save_records(self, records: List[DNSRecord]):
        """Save records to JSON file"""
        data = [asdict(r) for r in records]
        self.path.write_text(json.dumps(data, indent=2))