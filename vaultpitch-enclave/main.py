import json
import time
import hashlib
import os
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# --- Models ---
class QueryRequest(BaseModel):
    tier: int
    query: str
    judge_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    blocked: bool
    required_tier: Optional[int] = None
    log_entry: Dict[str, Any]
    mrenclave_hash: str

# --- Enclave Logic Core (IC3 Research) ---
class EnclaveLogic:
    def __init__(self):
        # Load NDAI policy
        with open("pitch_policy.json") as f:
            self.policy = json.load(f)
        
        # Generate deterministic MRENCLAVE hash (simulated but verifiable)
        self.mrenclave = self._generate_mrenclave()
        
        # Cycles attribution logs
        self.cycles_log = []
        self.session_id = int(time.time())
        
        # KMS simulation state
        self.kms_active = True
        self.kms_keys = {
            "pitch_deck": "encrypted_0x7f3a...",
            "financials": "encrypted_0x9d2b...",
            "architecture": "encrypted_0x4e8c..."
        }
        
        print(f"[ENCLAVE] Initialized with MRENCLAVE: {self.mrenclave[:16]}...")
        print(f"[ENCLAVE] NDAI Policy loaded: {len(self.policy['tiers'])} tiers")
    
    def _generate_mrenclave(self) -> str:
        """Generate deterministic MRENCLAVE hash based on code and policy"""
        # In production, this comes from the TEE hardware
        # Here we simulate it for demo consistency
        code_hash = hashlib.sha256()
        
        # Hash the policy file
        with open("pitch_policy.json", "rb") as f:
            code_hash.update(f.read())
        
        # Add environment determinism
        code_hash.update(b"VAULTPITCH_TEE_V1")
        
        return code_hash.hexdigest()
    
    def process(self, tier: int, query: str, judge_id: str = None) -> tuple:
        """Process query with NDAI enforcement"""
        
        # Check if enclave is destroyed
        if not self.kms_active:
            return "ENCLAVE DESTROYED: All KMS keys revoked. No data accessible.", True, None, 0
        
        tier_str = str(tier)
        if tier_str not in self.policy["tiers"]:
            tier_str = "0"
        
        tier_data = self.policy["tiers"][tier_str]
        
        # NDAI Semantic Redaction
        query_upper = query.upper()
        blocked_keywords = []
        
        for keyword in tier_data["blocked"]:
            if keyword in query_upper:
                blocked_keywords.append(keyword)
        
        is_blocked = len(blocked_keywords) > 0
        
        # Determine if higher tier is needed
        required_tier = None
        if is_blocked:
            # Check if tier 2 is needed
            for keyword in self.policy["tiers"]["2"]["blocked"]:
                if keyword in query_upper:
                    required_tier = 2
                    break
            if not required_tier and any(k in query_upper for k in self.policy["tiers"]["1"]["blocked"]):
                required_tier = 1
        
        # Generate response
        if not is_blocked:
            response = tier_data["data"]
        else:
            if required_tier:
                response = f"ACCESS DENIED: This information requires Tier {required_tier} clearance. Please sign the appropriate NDA agreement to access {', '.join(blocked_keywords)}."
            else:
                response = f"ACCESS DENIED: Your current tier ({tier_data['label']}) does not have permission to access information about {', '.join(blocked_keywords)}."
        
        # Cycles Attribution Logging
        log_entry = {
            "ts": time.time(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tier": tier,
            "tier_label": tier_data["label"],
            "judge_id": judge_id or "anonymous",
            "query": query[:100],
            "query_hash": hashlib.sha256(query.encode()).hexdigest()[:16],
            "status": "BLOCKED" if is_blocked else "GRANTED",
            "blocked_keywords": blocked_keywords if is_blocked else [],
            "required_tier": required_tier,
            "session_id": self.session_id
        }
        
        self.cycles_log.append(log_entry)
        
        # Keep log manageable
        if len(self.cycles_log) > 1000:
            self.cycles_log = self.cycles_log[-500:]
        
        return response, is_blocked, log_entry, required_tier
    
    def self_destruct(self) -> dict:
        """Immediate KMS key revocation"""
        self.kms_active = False
        self.kms_keys = {}
        
        # Log destruction
        destruction_entry = {
            "ts": time.time(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event": "SELF_DESTRUCT",
            "session_id": self.session_id,
            "keys_revoked": 3,
            "status": "DESTROYED"
        }
        self.cycles_log.append(destruction_entry)
        
        return {
            "status": "DESTROYED",
            "message": "All KMS keys revoked. Enclave is now inoperable.",
            "timestamp": destruction_entry["timestamp"]
        }
    
    def get_attestation(self) -> dict:
        """Generate attestation quote (simulated)"""
        return {
            "mrenclave": self.mrenclave,
            "tee_type": "Intel TDX v1.5",
            "kms_status": "ACTIVE" if self.kms_active else "DESTROYED",
            "session_id": self.session_id,
            "policy_hash": hashlib.sha256(json.dumps(self.policy, sort_keys=True).encode()).hexdigest(),
            "quote_signature": "0x" + hashlib.sha256(self.mrenclave.encode()).hexdigest()[:64],
            "verifiable": True
        }
    
    def get_cycles_report(self) -> dict:
        """Export full attribution graph"""
        return {
            "session_id": self.session_id,
            "mrenclave": self.mrenclave,
            "total_interactions": len(self.cycles_log),
            "logs": self.cycles_log[-100:],  # Last 100 entries
            "export_timestamp": time.time()
        }

# --- Initialize FastAPI ---
app = FastAPI(title="VaultPitch Enclave", version="1.0.0")

# Initialize enclave logic
logic = EnclaveLogic()

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the VaultPitch dashboard"""
    with open("index.html") as f:
        html_content = f.read()
    
    # Inject MRENCLAVE hash dynamically
    html_content = html_content.replace(
        "3f8a2c1d9e047b6f5a8c2d19e8f4a7b3c1d9e042f8a3c2e1d9e047b6f5a8c2d",
        logic.mrenclave
    )
    
    return html_content

@app.get("/health")
async def health_check():
    """Health check endpoint for dstack"""
    return {
        "status": "healthy",
        "enclave_active": logic.kms_active,
        "mrenclave": logic.mrenclave[:16] + "..."
    }

@app.get("/attestation")
async def get_attestation():
    """Get TEE attestation quote"""
    return logic.get_attestation()

@app.post("/ask")
async def ask(request: QueryRequest):
    """Process a query with NDAI enforcement"""
    if not logic.kms_active:
        return JSONResponse(
            status_code=410,
            content={
                "error": "ENCLAVE_DESTROYED",
                "message": "This enclave has been self-destructed. All data is inaccessible."
            }
        )
    
    response, blocked, log_entry, required_tier = logic.process(
        request.tier,
        request.query,
        request.judge_id
    )
    
    return {
        "response": response,
        "blocked": blocked,
        "required_tier": required_tier,
        "log": log_entry,
        "mrenclave": logic.mrenclave[:16] + "..."
    }

@app.post("/self-destruct")
async def self_destruct():
    """Emergency key revocation"""
    result = logic.self_destruct()
    return result

@app.get("/cycles-log")
async def get_cycles_log(limit: int = 50):
    """Get attribution log"""
    return {
        "logs": logic.cycles_log[-limit:],
        "total": len(logic.cycles_log),
        "session": logic.session_id
    }

@app.get("/cycles-report")
async def export_cycles_report():
    """Export full attribution report"""
    return logic.get_cycles_report()

@app.get("/policy")
async def get_policy():
    """Get current NDAI policy (public info only)"""
    public_policy = {
        "tiers": {
            "0": logic.policy["tiers"]["0"]["label"],
            "1": logic.policy["tiers"]["1"]["label"],
            "2": logic.policy["tiers"]["2"]["label"]
        },
        "project": logic.policy["project"]
    }
    return public_policy

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")