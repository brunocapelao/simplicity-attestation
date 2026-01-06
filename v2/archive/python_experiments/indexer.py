"""
Simplicity Attestation - SAID Indexer

Este módulo implementa um indexador para o protocolo SAID (Simplicity Attestation ID).
Ele monitora transações na Liquid Network e indexa atestações baseadas no formato OP_RETURN.

Uso:
    python indexer.py --start-height 1000000 --api https://blockstream.info/liquid/testnet/api
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import IntEnum
import struct
import json
import sqlite3
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════
# PROTOCOLO SAID v1.0 (Simplicity Attestation ID)
# ═══════════════════════════════════════════════════════════════════════════

SAID_MAGIC = b'SAID'  # 0x53414944
SAID_VERSION = 0x01


class SAIDType(IntEnum):
    """Tipos de operação SAID."""
    ATTEST = 0x01       # Emissão de atestação
    REVOKE = 0x02       # Revogação de atestação
    UPDATE = 0x03       # Atualização de metadados
    DELEGATE = 0x10     # Delegação de autoridade
    UNDELEGATE = 0x11   # Revogação de delegação


@dataclass
class SAIDRecord:
    """Representa um registro SAID decodificado."""
    version: int
    op_type: SAIDType
    payload: bytes
    txid: str
    vout: int
    block_height: int
    timestamp: datetime


@dataclass
class Attestation:
    """Representa uma atestação indexada."""
    txid: str
    vout: int
    cid: str
    block_height: int
    issued_at: datetime
    status: str  # 'valid', 'revoked'
    revoked_at: Optional[datetime] = None
    revoked_txid: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════
# ENCODER/DECODER
# ═══════════════════════════════════════════════════════════════════════════

def encode_said_attest(cid: str) -> bytes:
    """
    Codifica um OP_RETURN de emissão de atestação.
    
    Args:
        cid: Content ID do IPFS (ex: QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG)
    
    Returns:
        bytes: Dados para o OP_RETURN
    
    Example:
        >>> data = encode_said_attest("QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG")
        >>> data.hex()
        '53414944 01 01 516d59774150...'
    """
    header = SAID_MAGIC + bytes([SAID_VERSION, SAIDType.ATTEST])
    payload = cid.encode('utf-8')
    return header + payload


def encode_said_revoke(ref_txid: bytes, ref_vout: int) -> bytes:
    """
    Codifica um OP_RETURN de revogação de atestação.
    
    Args:
        ref_txid: TXID da atestação a revogar (32 bytes)
        ref_vout: Índice do output da atestação
    
    Returns:
        bytes: Dados para o OP_RETURN
    """
    header = SAID_MAGIC + bytes([SAID_VERSION, SAIDType.REVOKE])
    payload = ref_txid + struct.pack('>H', ref_vout)  # Big-endian 2 bytes
    return header + payload


def encode_said_delegate(delegate_pubkey: bytes) -> bytes:
    """
    Codifica um OP_RETURN de delegação.
    
    Args:
        delegate_pubkey: Chave pública x-only do delegate (32 bytes)
    
    Returns:
        bytes: Dados para o OP_RETURN
    """
    header = SAID_MAGIC + bytes([SAID_VERSION, SAIDType.DELEGATE])
    return header + delegate_pubkey


def decode_said(data: bytes) -> Optional[SAIDRecord]:
    """
    Decodifica dados de um OP_RETURN SAID.
    
    Args:
        data: Dados brutos do OP_RETURN
    
    Returns:
        SAIDRecord se válido, None caso contrário
    """
    # Verificar tamanho mínimo
    if len(data) < 6:
        return None
    
    # Verificar magic bytes
    if data[0:4] != SAID_MAGIC:
        return None
    
    version = data[4]
    
    # Verificar versão suportada
    if version != SAID_VERSION:
        return None
    
    try:
        op_type = SAIDType(data[5])
    except ValueError:
        return None  # Tipo desconhecido
    
    payload = data[6:]
    
    return SAIDRecord(
        version=version,
        op_type=op_type,
        payload=payload,
        txid="",  # Preenchido pelo caller
        vout=0,
        block_height=0,
        timestamp=datetime.now()
    )


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════

class AttestationDB:
    """Banco de dados SQLite para armazenar atestações indexadas."""
    
    def __init__(self, db_path: str = "attestations.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
    
    def _create_tables(self):
        """Cria as tabelas necessárias."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS attestations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                txid TEXT NOT NULL,
                vout INTEGER NOT NULL,
                cid TEXT NOT NULL,
                block_height INTEGER NOT NULL,
                issued_at TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'valid',
                revoked_at TIMESTAMP,
                revoked_txid TEXT,
                UNIQUE(txid, vout)
            );
            
            CREATE INDEX IF NOT EXISTS idx_att_cid ON attestations(cid);
            CREATE INDEX IF NOT EXISTS idx_att_status ON attestations(status);
            CREATE INDEX IF NOT EXISTS idx_att_height ON attestations(block_height);
            
            CREATE TABLE IF NOT EXISTS delegations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vault_txid TEXT NOT NULL,
                delegate_pubkey TEXT NOT NULL,
                block_height INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                revoked_at TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS sync_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_height INTEGER NOT NULL,
                last_updated TIMESTAMP NOT NULL
            );
            
            INSERT OR IGNORE INTO sync_state (id, last_height, last_updated)
            VALUES (1, 0, datetime('now'));
        """)
        self.conn.commit()
    
    def add_attestation(self, att: Attestation):
        """Adiciona uma atestação ao banco."""
        self.conn.execute("""
            INSERT OR REPLACE INTO attestations 
            (txid, vout, cid, block_height, issued_at, status, revoked_at, revoked_txid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            att.txid, att.vout, att.cid, att.block_height,
            att.issued_at, att.status, att.revoked_at, att.revoked_txid
        ))
        self.conn.commit()
    
    def revoke_attestation(self, txid: str, vout: int, revoked_txid: str):
        """Marca uma atestação como revogada."""
        self.conn.execute("""
            UPDATE attestations 
            SET status = 'revoked', revoked_at = datetime('now'), revoked_txid = ?
            WHERE txid = ? AND vout = ?
        """, (revoked_txid, txid, vout))
        self.conn.commit()
    
    def get_attestation(self, txid: str, vout: int = 1) -> Optional[Dict]:
        """Busca uma atestação pelo TXID."""
        cursor = self.conn.execute("""
            SELECT * FROM attestations WHERE txid = ? AND vout = ?
        """, (txid, vout))
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'txid': row[1],
                'vout': row[2],
                'cid': row[3],
                'block_height': row[4],
                'issued_at': row[5],
                'status': row[6],
                'revoked_at': row[7],
                'revoked_txid': row[8]
            }
        return None
    
    def get_attestation_by_cid(self, cid: str) -> Optional[Dict]:
        """Busca uma atestação pelo CID do IPFS."""
        cursor = self.conn.execute("""
            SELECT * FROM attestations WHERE cid = ?
        """, (cid,))
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'txid': row[1],
                'vout': row[2],
                'cid': row[3],
                'block_height': row[4],
                'issued_at': row[5],
                'status': row[6],
                'revoked_at': row[7],
                'revoked_txid': row[8]
            }
        return None
    
    def list_attestations(self, status: str = None, limit: int = 100) -> List[Dict]:
        """Lista atestações com filtro opcional por status."""
        if status:
            cursor = self.conn.execute("""
                SELECT * FROM attestations WHERE status = ? 
                ORDER BY issued_at DESC LIMIT ?
            """, (status, limit))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM attestations 
                ORDER BY issued_at DESC LIMIT ?
            """, (limit,))
        
        results = []
        for row in cursor:
            results.append({
                'id': row[0],
                'txid': row[1],
                'vout': row[2],
                'cid': row[3],
                'block_height': row[4],
                'issued_at': row[5],
                'status': row[6],
                'revoked_at': row[7],
                'revoked_txid': row[8]
            })
        return results
    
    def get_sync_height(self) -> int:
        """Retorna a altura do último bloco sincronizado."""
        cursor = self.conn.execute("SELECT last_height FROM sync_state WHERE id = 1")
        return cursor.fetchone()[0]
    
    def set_sync_height(self, height: int):
        """Atualiza a altura do último bloco sincronizado."""
        self.conn.execute("""
            UPDATE sync_state SET last_height = ?, last_updated = datetime('now')
            WHERE id = 1
        """, (height,))
        self.conn.commit()
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do indexador."""
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'valid' THEN 1 ELSE 0 END) as valid,
                SUM(CASE WHEN status = 'revoked' THEN 1 ELSE 0 END) as revoked
            FROM attestations
        """)
        row = cursor.fetchone()
        return {
            'total_attestations': row[0],
            'valid_attestations': row[1],
            'revoked_attestations': row[2],
            'last_sync_height': self.get_sync_height()
        }


# ═══════════════════════════════════════════════════════════════════════════
# INDEXER
# ═══════════════════════════════════════════════════════════════════════════

class SAIDIndexer:
    """
    Indexador de atestações Simplicity Attestation.
    
    Monitora a blockchain Liquid e indexa transações que seguem o protocolo SAID.
    """
    
    def __init__(self, db: AttestationDB, api_url: str = "https://blockstream.info/liquid/testnet/api"):
        self.db = db
        self.api_url = api_url
    
    def process_transaction(self, tx: Dict, block_height: int):
        """
        Processa uma transação em busca de OP_RETURNs SCID.
        
        Args:
            tx: Dados da transação
            block_height: Altura do bloco
        """
        for i, vout in enumerate(tx.get('vout', [])):
            # Verificar se é OP_RETURN
            scriptpubkey_type = vout.get('scriptpubkey_type', '')
            if scriptpubkey_type != 'op_return':
                continue
            
            # Obter dados do OP_RETURN
            scriptpubkey_hex = vout.get('scriptpubkey', '')
            if not scriptpubkey_hex:
                continue
            
            # Decodificar (pular OP_RETURN opcode)
            try:
                data = bytes.fromhex(scriptpubkey_hex)
                # Pular OP_RETURN (0x6a) e push opcode
                if len(data) < 2:
                    continue
                if data[0] == 0x6a:  # OP_RETURN
                    # Próximo byte é o tamanho
                    size = data[1]
                    if size <= 75:
                        payload = data[2:2+size]
                    elif size == 0x4c:  # OP_PUSHDATA1
                        size = data[2]
                        payload = data[3:3+size]
                    else:
                        continue
                else:
                    continue
            except Exception:
                continue
            
            # Decodificar SAID
            record = decode_said(payload)
            if not record:
                continue
            
            # Atualizar record com informações da transação
            record.txid = tx.get('txid', '')
            record.vout = i
            record.block_height = block_height
            
            # Processar por tipo
            self._process_record(record, tx)
    
    def _process_record(self, record: SAIDRecord, tx: Dict):
        """Processa um registro SAID decodificado."""
        
        if record.op_type == SAIDType.ATTEST:
            # Emissão de atestação
            cid = record.payload.decode('utf-8')
            att = Attestation(
                txid=record.txid,
                vout=1,  # Attestation UTXO está sempre no output 1
                cid=cid,
                block_height=record.block_height,
                issued_at=record.timestamp,
                status='valid'
            )
            self.db.add_attestation(att)
            print(f"[ATTEST] Attestation: {record.txid}:1 -> CID: {cid}")
        
        elif record.op_type == SAIDType.REVOKE:
            # Revogação de atestação
            ref_txid = record.payload[0:32].hex()
            ref_vout = struct.unpack('>H', record.payload[32:34])[0]
            self.db.revoke_attestation(ref_txid, ref_vout, record.txid)
            print(f"[REVOKE] Attestation: {ref_txid}:{ref_vout}")
        
        elif record.op_type == SAIDType.DELEGATE:
            # Nova delegação
            delegate_pk = record.payload.hex()
            print(f"[DELEGATE] New delegate: {delegate_pk}")
        
        elif record.op_type == SAIDType.UNDELEGATE:
            # Cancelar delegação
            delegate_pk = record.payload.hex()
            print(f"[UNDELEGATE] Removed delegate: {delegate_pk}")
    
    def sync_from_height(self, start_height: int, end_height: int = None):
        """
        Sincroniza blocos a partir de uma altura.
        
        Args:
            start_height: Altura inicial
            end_height: Altura final (None = tip)
        """
        import requests
        
        current = start_height
        
        while True:
            try:
                # Obter hash do bloco
                resp = requests.get(f"{self.api_url}/block-height/{current}")
                if resp.status_code == 404:
                    break  # Chegou ao tip
                block_hash = resp.text
                
                # Obter transações do bloco
                resp = requests.get(f"{self.api_url}/block/{block_hash}/txs")
                if resp.status_code != 200:
                    break
                
                txs = resp.json()
                
                for tx in txs:
                    self.process_transaction(tx, current)
                
                self.db.set_sync_height(current)
                print(f"Synced block {current}")
                
                if end_height and current >= end_height:
                    break
                
                current += 1
                
            except Exception as e:
                print(f"Error at block {current}: {e}")
                break


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Simplicity Attestation - SAID Indexer')
    parser.add_argument('--db', default='attestations.db', help='Database path')
    parser.add_argument('--api', default='https://blockstream.info/liquid/testnet/api', help='API URL')
    
    subparsers = parser.add_subparsers(dest='command')
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync blocks')
    sync_parser.add_argument('--start', type=int, help='Start height')
    sync_parser.add_argument('--end', type=int, help='End height')
    
    # Stats command
    subparsers.add_parser('stats', help='Show statistics')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List attestations')
    list_parser.add_argument('--status', choices=['valid', 'revoked'], help='Filter by status')
    list_parser.add_argument('--limit', type=int, default=10, help='Limit results')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get attestation by TXID')
    get_parser.add_argument('txid', help='Transaction ID')
    get_parser.add_argument('--vout', type=int, default=1, help='Output index')
    
    # Encode command
    encode_parser = subparsers.add_parser('encode', help='Encode SCID data')
    encode_parser.add_argument('cid', help='IPFS CID')
    
    args = parser.parse_args()
    
    db = AttestationDB(args.db)
    
    if args.command == 'sync':
        indexer = SAIDIndexer(db, args.api)
        start = args.start or db.get_sync_height() + 1
        indexer.sync_from_height(start, args.end)
    
    elif args.command == 'stats':
        stats = db.get_stats()
        print(json.dumps(stats, indent=2))
    
    elif args.command == 'list':
        atts = db.list_attestations(args.status, args.limit)
        for att in atts:
            print(f"[{att['status'].upper()}] {att['txid']}:{att['vout']} -> {att['cid']}")
    
    elif args.command == 'get':
        att = db.get_attestation(args.txid, args.vout)
        if att:
            print(json.dumps(att, indent=2, default=str))
        else:
            print("Attestation not found")
    
    elif args.command == 'encode':
        data = encode_said_attest(args.cid)
        print(f"HEX: {data.hex()}")
        print(f"Length: {len(data)} bytes")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
