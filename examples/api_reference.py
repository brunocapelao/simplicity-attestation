from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Literal, Optional
import uuid
import time
import os

# Importamos o SDK do SAS
from sdk import SAPClient, PreparedTransaction
from sdk.models import TransactionResult

app = FastAPI(title="SAS Offline Signing Reference API")

# --- MOCK CACHE (Em produção, use REDIS) ---
# O cache é vital porque o PSET é grande e não deve ser trafegado 
# desnecessariamente via frontend entre o prepare e o finalize.
prepared_cache = {}

class PrepareRequest(BaseModel):
    cid: str
    issuer: Literal["admin", "delegate"] = "delegate"

class FinalizeRequest(BaseModel):
    prepared_id: str
    signature_hex: str  # 128 caracteres hex (64 bytes)

class PreparationResponse(BaseModel):
    prepared_id: str
    sig_hash: str
    required_pubkey: str
    details: dict
    expires_in: int

# Inicializamos o cliente SDK (configurado para a rede correta)
# Em modo de preparação, não precisamos de chaves privadas no servidor.
client = SAPClient.from_config(os.getenv("SAS_CONFIG_PATH", "vault_config.json"))

@app.post("/api/v1/certificates/prepare", response_model=PreparationResponse)
async def prepare_certificate(request: PrepareRequest):
    """
    PASSO 1: Prepara a transação.
    O servidor gera o PSET com as Covenants do Simplicity e extrai o sig_hash.
    """
    try:
        # O SDK constrói a transação Liquid/Simplicity
        prepared = client.prepare_issue_certificate(
            cid=request.cid,
            issuer=request.issuer
        )
        
        # Geramos um ID para o usuário recuperar esta transação depois
        prepared_id = str(uuid.uuid4())
        
        # Salvamos no cache com expiração (ex: 10 minutos)
        prepared_cache[prepared_id] = {
            "data": prepared,
            "expires_at": time.time() + 600
        }
        
        return {
            "prepared_id": prepared_id,
            "sig_hash": prepared.sig_hash,
            "required_pubkey": prepared.required_pubkey,
            "details": prepared.details,
            "expires_in": 600
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/certificates/finalize")
async def finalize_certificate(request: FinalizeRequest):
    """
    PASSO 2: Finaliza e envia para a rede Liquid.
    Recebe a assinatura do usuário (gerada em sua wallet offline).
    """
    # 1. Recupera do cache (Segurança: nunca aceite o PSET vindo do frontend)
    cached = prepared_cache.get(request.prepared_id)
    if not cached or time.time() > cached["expires_at"]:
        raise HTTPException(status_code=404, detail="Transação expirada ou não encontrada")
    
    prepared: PreparedTransaction = cached["data"]
    
    try:
        # 2. Converte hex para bytes (64 bytes Schnorr)
        signature_bytes = bytes.fromhex(request.signature_hex)
        
        # 3. Finaliza no SDK (injeta a assinatura no Witness do Simplicity)
        # O SDK fará o broadcast automático se broadcast=True
        result: TransactionResult = client.finalize_transaction(
            prepared=prepared,
            signature=signature_bytes,
            broadcast=True
        )
        
        if not result.success:
            return {"success": False, "error": result.error}
        
        # 4. Limpa o cache após o sucesso
        del prepared_cache[request.prepared_id]
        
        return {
            "success": True,
            "txid": result.txid,
            "summary": "Certificado emitido e registrado na Liquid Network"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de assinatura inválido (esperado 64 bytes hex)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no broadcast: {str(e)}")

@app.get("/api/v1/certificates/status/{txid}")
async def get_status(txid: str):
    """Consulta se a transação já foi confirmada."""
    # O SDK também tem utilitários para verificar confirmações
    from sdk.infra.api import BlockstreamAPI
    api = BlockstreamAPI(network="testnet")
    return api.get_transaction_status(txid)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
