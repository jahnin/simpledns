from flask import Flask, render_template, request, jsonify
from models import RecordStore, DNSRecord
from update_coredns import rebuild_corefile

app = Flask(__name__)
store = RecordStore()

# ---------- UI ----------
@app.get("/")
def index():
    return render_template("index.html")

@app.get("/records")
def records_page():
    return render_template("records.html")

# ---------- API ----------
@app.get("/api/records")
def list_records():
    """Get all DNS records"""
    try:
        records = store.all()
        return jsonify([r.__dict__ for r in records])
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/api/records")
def add_record():
    """Add a new DNS record with automatic domain extraction"""
    try:
        data = request.get_json(force=True)
        
        # Validate required fields
        if not data.get('fqdn'):
            return {"error": "FQDN is required"}, 400
        if not data.get('ip'):
            return {"error": "IP address is required"}, 400
        
        # Create record (domain will be auto-extracted)
        rec = DNSRecord(
            fqdn=data['fqdn'].strip(),
            ip=data['ip'].strip()
        )
        
        # Add to store
        store.add(rec)
        
        # Rebuild CoreDNS configuration
        rebuild_corefile()
        
        return rec.__dict__, 201
        
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        return {"error": f"Internal error: {str(e)}"}, 500

@app.delete("/api/records/<path:fqdn>")
def delete_record(fqdn):
    """Delete a DNS record by FQDN"""
    try:
        store.delete(fqdn)
        rebuild_corefile()
        return '', 204
    except ValueError as e:
        return {"error": str(e)}, 404
    except Exception as e:
        return {"error": f"Internal error: {str(e)}"}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)