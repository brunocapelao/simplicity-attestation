# SAP (Simplicity Attestation Protocol)
## Relatório de Análise de Negócios e Tecnologia

**Documento Confidencial**
**Preparado para: Blockstream**
**Data: Janeiro de 2026**

---

## Sumário Executivo

O **SAP (Simplicity Attestation Protocol)** é uma implementação pioneira de um sistema de certificados digitais on-chain que utiliza a linguagem **Simplicity** na **Liquid Network**. Este projeto representa um caso de uso prático e imediatamente aplicável que demonstra o poder dos *covenants*, *vaults* e *delegation schemes* possibilitados pelo Simplicity — exatamente os casos de uso destacados pela Blockstream no lançamento da linguagem em Julho de 2025.

### Principais Destaques

| Aspecto | Valor |
|---------|-------|
| **Problema Resolvido** | PKI tradicional centralizada e vulnerável |
| **Solução** | Sistema de certificação trustless baseado em UTXO |
| **Tecnologia** | Simplicity + Liquid Network |
| **Inovação Chave** | Covenants com auto-referência para vaults de delegação |
| **Status** | MVP funcional com testes abrangentes |
| **Alinhamento Estratégico** | 100% alinhado com os casos de uso prioritários do Simplicity |

---

## 1. Introdução e Contexto

### 1.1 O Momento Estratégico do Simplicity

O lançamento do Simplicity em 31 de Julho de 2025 marcou uma nova era para contratos inteligentes no ecossistema Bitcoin. Após 8 anos de desenvolvimento, a Blockstream entregou uma linguagem que promete:

- **Verificação Formal**: Contratos matematicamente comprovados antes da execução
- **Previsibilidade Total**: Custos de execução conhecidos antecipadamente
- **Segurança por Design**: Sem loops infinitos, recursão ou estado global

> *"Se adotado no Bitcoin no futuro, o Simplicity poderia posicionar o Bitcoin como uma camada de liquidação programável para todas as finanças de grau institucional."* — Andrew Poelstra, Diretor de Pesquisa da Blockstream

### 1.2 A Liquid Network Hoje

A Liquid Network representa um dos layer-2 mais robustos do ecossistema Bitcoin:

- **+$3.27 bilhões** em TVL (Total Value Locked)
- **+$1.8 bilhão** em ativos emitidos
- **+3.844 BTC** bloqueados on-chain
- **+70 empresas** na federação global
- **Casos reais**: Mifiel ($1B em notas promissórias), STOKR (CMSTR token de segurança)

**Fonte**: [Blockstream Strategic Update 2025](https://blockstream.com/press-releases/2025-04-28-blockstream-shares-key-strategic-update-growth-expansion-2025/)

### 1.3 O Desafio: Casos de Uso Práticos

Com o Simplicity ativado, a Blockstream agora busca ativamente casos de uso que demonstrem o valor prático da tecnologia. O SAP é exatamente isso: **uma aplicação real, funcional e imediatamente útil** que implementa três dos principais casos de uso destacados pelo Simplicity:

1. **Covenants** — Regras on-chain que restringem para onde os fundos podem ir
2. **Vaults** — Estruturas de custódia com controle programático
3. **Delegation Schemes** — Delegação de autoridade com restrições criptográficas

---

## 2. Visão Geral do Sistema SAP

### 2.1 O Que é o SAP?

O SAP (Simplicity Attestation Protocol) é um sistema de certificados digitais descentralizado que permite:

- **Emissão de Certificados**: Autoridades delegadas podem emitir certificados on-chain
- **Revogação Instantânea**: Certificados podem ser revogados gastando o UTXO correspondente
- **Verificação Trustless**: Qualquer pessoa pode verificar a validade de um certificado
- **Hierarquia de Autoridade**: Admin pode delegar poderes a Delegates com restrições

### 2.2 Por Que É Inovador?

| Sistema Tradicional (PKI) | SAP (Simplicity-based) |
|---------------------------|------------------------|
| Autoridades Centralizadas (CAs) | Autoridade distribuída via blockchain |
| Revogação lenta (CRLs, OCSP) | Revogação instantânea (gasto de UTXO) |
| Confiança em terceiros | Verificação criptográfica trustless |
| Vulnerável a comprometimento | Segurança baseada em consenso |
| Certificados podem ser falsificados offline | Validade = existência do UTXO |

### 2.3 Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         ADMIN                                    │
│                    (Autoridade Raiz)                            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ Deposita fundos em
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DELEGATION VAULT                              │
│              (Contrato Simplicity com Covenants)                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 3 Spending Paths:                                        │    │
│  │                                                          │    │
│  │ 1. Admin Unconditional  → Pode gastar para qualquer     │    │
│  │                           lugar (desativar delegate)     │    │
│  │                                                          │    │
│  │ 2. Admin Issue Cert     → Emite certificado com         │    │
│  │                           covenants                      │    │
│  │                                                          │    │
│  │ 3. Delegate Issue Cert  → Delegate emite certificado    │    │
│  │                           com covenants RESTRITIVOS      │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ Covenant Garante:
                      │ • Output 0 = Troco volta para Vault
                      │ • Output 1 = Certificado no script correto
                      │ • Output 2 = OP_RETURN com dados SAP
                      │ • Output 3 = Fee
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CERTIFICATE UTXO                              │
│                                                                  │
│  Existência = Certificado VÁLIDO                                │
│  Gasto = Certificado REVOGADO                                   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 2 Spending Paths:                                        │    │
│  │ • Admin pode revogar                                     │    │
│  │ • Delegate pode revogar                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Implementação Técnica Detalhada

### 3.1 O Problema da Auto-Referência (Self-Reference Problem)

Um dos desafios mais interessantes resolvidos pelo SAP é o **problema da auto-referência** em covenants. Para um vault verificar que o troco retorna para si mesmo, ele precisa conhecer seu próprio hash — mas o hash é calculado a partir do próprio script, criando uma dependência circular.

**Solução Elegante**: O SAP utiliza o **disconnect combinator** do Simplicity:

```simplicity
// O script obtém seu próprio hash via jet::current_script_hash()
let self_hash: u256 = jet::current_script_hash();

// E verifica que output[0] vai para ele mesmo
let output0_hash: u256 = unwrap(jet::output_script_hash(0));
assert!(jet::eq_256(self_hash, output0_hash));
```

Esta é uma técnica avançada que demonstra o poder do Simplicity para implementar covenants sofisticados que seriam impossíveis em Bitcoin Script.

### 3.2 Vault Contract (vault.simf)

O contrato do vault é o coração do sistema. Ele implementa:

```simplicity
fn main() {
    // Parsing do witness para determinar qual path
    let path_selector: Either<AdminSig, Either<AdminSig, DelegateSig>> = ...;

    match path_selector {
        // Path 1: Admin Unconditional - Pode fazer qualquer coisa
        Left(admin_sig) => {
            verify_schnorr(ADMIN_PUBKEY, admin_sig);
            // Nenhum covenant - Admin tem controle total
        },

        Right(inner) => match inner {
            // Path 2: Admin Issue Certificate - Com covenants
            Left(admin_sig) => {
                verify_schnorr(ADMIN_PUBKEY, admin_sig);
                enforce_certificate_covenants();
            },

            // Path 3: Delegate Issue Certificate - Com covenants
            Right(delegate_sig) => {
                verify_schnorr(DELEGATE_PUBKEY, delegate_sig);
                enforce_certificate_covenants();
            }
        }
    }
}

fn enforce_certificate_covenants() {
    // Covenant 1: Output 0 deve retornar ao vault (auto-referência)
    let self_hash = jet::current_script_hash();
    let output0_hash = unwrap(jet::output_script_hash(0));
    assert!(jet::eq_256(self_hash, output0_hash));

    // Covenant 2: Output 1 deve ser o script de certificado
    let output1_hash = unwrap(jet::output_script_hash(1));
    assert!(jet::eq_256(CERTIFICATE_SCRIPT_HASH, output1_hash));

    // Covenant 3: Número correto de outputs
    assert!(jet::num_outputs() == 4);

    // Covenant 4: Output 3 é fee
    assert!(jet::output_is_fee(3));
}
```

### 3.3 Certificate Contract (certificate.simf)

O contrato de certificado é intencionalmente simples:

```simplicity
fn main() {
    let path: Either<AdminSig, DelegateSig> = ...;

    match path {
        Left(admin_sig) => verify_schnorr(ADMIN_PUBKEY, admin_sig),
        Right(delegate_sig) => verify_schnorr(DELEGATE_PUBKEY, delegate_sig)
    }
}
```

A simplicidade é intencional: o certificado não precisa de covenants porque:
- Sua **existência** como UTXO comprova validade
- Seu **gasto** representa revogação
- Apenas Admin ou Delegate podem gastar (revogar)

### 3.4 Protocolo SAP (OP_RETURN)

O protocolo define um formato padronizado para metadados:

```
┌─────────┬─────────┬────────┬──────────────────────────────┐
│  "SAP"  │ VERSION │  TYPE  │         PAYLOAD              │
│ 3 bytes │ 1 byte  │ 1 byte │   variable length            │
└─────────┴─────────┴────────┴──────────────────────────────┘

Tipos de Operação:
  0x01 = ATTEST  → Emissão de certificado (payload = IPFS CID)
  0x02 = REVOKE  → Revogação (payload = TXID:vout do certificado)
  0x03 = UPDATE  → Atualização de metadados (payload = novo CID)
```

### 3.5 Jets do Simplicity Utilizados

| Jet | Função | Uso no SAP |
|-----|--------|------------|
| `jet::sig_all_hash()` | Computa sighash da transação | Verificação de assinatura |
| `jet::bip_0340_verify()` | Verifica assinatura Schnorr | Autenticação |
| `jet::current_script_hash()` | Retorna CMR do script atual | Auto-referência |
| `jet::output_script_hash()` | Hash do script de um output | Verificação de destino |
| `jet::output_amount()` | Valor de um output | Validação de valores |
| `jet::output_null_datum()` | Lê dados OP_RETURN | Metadados do certificado |
| `jet::output_is_fee()` | Verifica se output é fee | Validação de estrutura |
| `jet::num_outputs()` | Conta número de outputs | Validação de estrutura |

---

## 4. Alinhamento Estratégico com a Blockstream

### 4.1 Casos de Uso Prioritários do Simplicity

No anúncio oficial do lançamento do Simplicity, a Blockstream destacou os seguintes casos de uso:

| Caso de Uso Blockstream | Implementação no SAP |
|-------------------------|----------------------|
| **Covenants** | Auto-referência do vault + verificação de outputs |
| **Vaults** | Delegation Vault com 3 spending paths |
| **Delegation Schemes** | Admin→Delegate hierarchy com restrições |
| **Institutional Custody** | Controle multi-party com covenants |
| **Decentralized Identity** | Certificados on-chain com verificação trustless |

**Fonte**: [Blockstream Simplicity Launch](https://blockstream.com/press-releases/2025-07-31-blockstream-launches-simplicity/)

### 4.2 Integração com Iniciativas Existentes

O SAP complementa várias iniciativas da Blockstream:

#### 4.2.1 Blockstream Green / Jade
Os certificados SAP poderiam ser integrados para:
- Verificação de identidade para transações de alto valor
- Attestation de compliance (KYC/AML) sem revelar dados pessoais
- Certificação de dispositivos de hardware wallet

#### 4.2.2 Liquid Securities (L-Sec)
Para emissão de securities na Liquid:
- Certificação de investidores qualificados
- Attestation de compliance regulatório
- Verificação de elegibilidade para diferentes classes de ativos

#### 4.2.3 Blockstream AMP (Asset Management Platform)
- Certificação de issuers autorizados
- Attestation de due diligence para novos ativos
- Verificação de compliance contínua

### 4.3 Suporte às Metas de Expansão Global

Com os escritórios em Tokyo e Lugano, e o foco em adoção institucional, o SAP atende diretamente:

| Mercado | Aplicação do SAP |
|---------|------------------|
| **Japão** | Certificação de exchanges (JFSA compliance) |
| **Suíça** | Attestation de custódia institucional |
| **LatAm** | Notas promissórias digitais (como Mifiel) |
| **Global** | Certificados de origem para tokenização de ativos |

**Fonte**: [Blockstream Tokyo Office](https://blockstream.com/press-releases/2025-02-05-blockstream-launches-tokyo-office/)

---

## 5. Casos de Uso e Oportunidades de Mercado

### 5.1 Certificados Corporativos

**Problema**: Empresas gastam milhões com PKI tradicional que é vulnerável a comprometimento de CAs.

**Solução SAP**:
```
┌─────────────────────────────────────────────────────────────┐
│                     EMPRESA (Admin)                          │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ RH Delegate │  │ TI Delegate │  │ Finance Del │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Employee    │  │ Server      │  │ Transaction │         │
│  │ Badges      │  │ Certs       │  │ Auth Certs  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

**Benefícios**:
- Revogação instantânea (ex-funcionário = certificado revogado imediatamente)
- Auditoria completa on-chain
- Sem single point of failure

### 5.2 Certificados Educacionais

**Problema**: Diplomas falsificados são um problema global. Verificação manual é cara e lenta.

**Solução SAP**:
- Universidade = Admin
- Faculdades/Departamentos = Delegates
- Cada diploma = Certificado SAP
- Verificação = Consulta de UTXO

**Case Study Potencial**: Universidades em jurisdições com alta fraude documental (América Latina, África, Ásia).

### 5.3 Compliance e KYC Tokenizado

**Problema**: KYC repetido para cada serviço financeiro é ineficiente e invasivo.

**Solução SAP**:
```
┌─────────────────────────────────────────────────────────────┐
│                KYC Provider (Admin)                          │
│                                                              │
│  1. Usuário completa KYC uma vez                            │
│  2. Provider emite certificado SAP                          │
│  3. Certificado = prova de KYC válido                       │
│  4. Serviços verificam certificado on-chain                 │
│  5. Nenhum dado pessoal é compartilhado                     │
└─────────────────────────────────────────────────────────────┘
```

**Integração com Liquid Securities**: Investidores com certificado SAP válido podem participar automaticamente de ofertas reguladas.

### 5.4 Supply Chain e Certificados de Origem

**Problema**: Certificados de origem são falsificados regularmente em comércio internacional.

**Solução SAP**:
- Autoridade de certificação = Admin
- Inspetores credenciados = Delegates
- Cada lote/produto = Certificado SAP com CID IPFS dos documentos

**Aplicação Imediata**: Exportação de commodities (café, soja, minério) com rastreabilidade completa.

### 5.5 Web of Trust Descentralizada

**Problema**: Sistemas de reputação centralizados podem ser manipulados ou censurados.

**Solução SAP**:
- Múltiplos Admins independentes
- Attestations cruzadas entre entidades
- Histórico imutável de certificações

---

## 6. Vantagens Competitivas

### 6.1 Comparativo com Outras Soluções

| Critério | PKI Tradicional | Ethereum/Solidity | SAP/Simplicity |
|----------|-----------------|-------------------|----------------|
| **Modelo de Confiança** | CA centralizada | Código + auditoria | Verificação formal |
| **Revogação** | CRL/OCSP (lenta) | Estado mutável | UTXO (instantânea) |
| **Custos de Auditoria** | Alto | Muito alto | Baixo (verificável) |
| **Riscos de Bug** | Baixo | Alto (reentrancy, etc) | Mínimo (sem loops) |
| **Previsibilidade de Custos** | N/A | Variável (gas) | Determinístico |
| **Settlement** | N/A | Finality ~15min | Finality ~2min |

### 6.2 Por Que Simplicity é Superior para Este Caso

1. **Verificação Formal**: O contrato pode ser matematicamente provado correto
2. **Sem Reentrancy**: A arquitetura do Simplicity elimina classes inteiras de vulnerabilidades
3. **Custos Determinísticos**: Taxas conhecidas antes da execução
4. **Modelo UTXO**: Alinhado com o modelo mental de "certificado existe ou não existe"
5. **Liquid Network**: Settlement rápido, confidencialidade de amounts, federation robusta

### 6.3 Propriedades de Segurança Garantidas

| Propriedade | Mecanismo | Força |
|-------------|-----------|-------|
| Troco retorna ao vault | Covenant com auto-referência | Criptográfica |
| Certificado vai para script correto | Hash hardcoded | Criptográfica |
| Apenas signatários autorizados | Verificação Schnorr | Criptográfica |
| Validade do certificado | Existência do UTXO | Consenso |
| Sem double-spend | Modelo UTXO | Consenso |

---

## 7. Análise de Mercado

### 7.1 Tamanho do Mercado de PKI

O mercado global de PKI foi avaliado em **$5.52 bilhões em 2024** e deve crescer para **$20.84 bilhões até 2032** (CAGR de 18.1%).

**Fonte**: [Fortune Business Insights - PKI Market](https://www.fortunebusinessinsights.com/public-key-infrastructure-pki-market-109936)

### 7.2 Tendência: Blockchain para Certificados

Pesquisas acadêmicas e de mercado apontam crescente interesse em:
- **Decentralized PKI (DPKI)**: Eliminação de CAs centralizadas
- **Verifiable Credentials (VCs)**: Credenciais verificáveis on-chain
- **Certificate Transparency**: Registros públicos e auditáveis

**Fonte**: [Consensys - Blockchain for Digital Identity](https://consensys.io/blockchain-use-cases/digital-identity)

### 7.3 Oportunidade no Ecossistema Liquid

Com $3.27B em TVL e crescente adoção institucional, a Liquid Network precisa de:
- Certificação de issuers de ativos
- Compliance automatizado para securities
- Identity solutions integradas

O SAP preenche exatamente esta lacuna.

---

## 8. Roadmap e Recomendações

### 8.1 Estado Atual (MVP)

| Componente | Status |
|------------|--------|
| Vault Contract (Simplicity) | Implementado e testado |
| Certificate Contract (Simplicity) | Implementado e testado |
| Protocolo SAP (OP_RETURN) | Implementado (validação on-chain + especificação) |
| Testes de Segurança | 8 cenários de ataque testados |
| Documentação | Completa (PT/EN) |

**Nota**: O protocolo SAP está implementado a nível de:
- Validação on-chain (vault verifica existência do OP_RETURN via `jet::output_null_datum`)
- Formato padronizado nos testes (`SAP_PAYLOAD` com magic bytes + versão + tipo + CID)
- Especificação completa em `docs/PROTOCOL_SPEC.md`

### 8.2 Próximos Passos Recomendados

#### Fase 1: Produção (Q1 2026)
- [ ] Deploy na Liquid Mainnet
- [ ] Indexador de certificados SAP
- [ ] API de verificação pública
- [ ] Integração com Blockstream Explorer

#### Fase 2: Expansão (Q2 2026)
- [ ] Suporte a múltiplos delegates
- [ ] Limites de gasto por delegate
- [ ] Time-locks para certificados
- [ ] SDK em JavaScript/Python/Rust

#### Fase 3: Ecossistema (Q3-Q4 2026)
- [ ] Integração com Blockstream Green
- [ ] Plugin para wallets Liquid
- [ ] Marketplace de certificados
- [ ] Parcerias com universidades/empresas

### 8.3 Recomendações Estratégicas para Blockstream

1. **Showcase Oficial**: Incluir o SAP como caso de uso oficial do Simplicity
2. **Grant/Funding**: Considerar apoio ao desenvolvimento contínuo
3. **Documentação**: Usar o SAP como exemplo nos tutoriais do SimplicityHL
4. **Parcerias**: Conectar com issuers existentes na Liquid (Mifiel, STOKR)
5. **Hackathons**: Apresentar como desafio em eventos da Blockstream

---

## 9. Conclusão

### 9.1 Resumo do Valor

O **SAP (Simplicity Attestation Protocol)** representa:

1. **Validação Prática do Simplicity**: Demonstra que a linguagem está pronta para uso real
2. **Caso de Uso Completo**: Implementa covenants, vaults e delegation — os três pilares do Simplicity
3. **Aplicação de Mercado Real**: PKI é um mercado de bilhões com demanda por descentralização
4. **Código Aberto e Documentado**: Pronto para ser adotado e expandido pela comunidade
5. **Alinhamento Estratégico**: Perfeito para os objetivos de expansão institucional da Blockstream

### 9.2 Call to Action

Solicitamos à Blockstream:

1. **Revisão Técnica**: Análise do código pelos engenheiros de Simplicity
2. **Feedback Estratégico**: Orientação sobre alinhamento com roadmap
3. **Potencial Parceria**: Discussão sobre inclusão no ecossistema oficial
4. **Suporte de Visibilidade**: Menção em comunicações sobre casos de uso do Simplicity

### 9.3 Próximo Passo

Estamos disponíveis para uma apresentação técnica detalhada e discussão sobre como o SAP pode contribuir para o sucesso do Simplicity e da Liquid Network.

---

## Apêndices

### Apêndice A: Links e Referências

**Sobre Simplicity e Liquid:**
- [Blockstream Simplicity Launch](https://blockstream.com/press-releases/2025-07-31-blockstream-launches-simplicity/)
- [Simplicity Documentation](https://docs.simplicity-lang.org/)
- [Simplicity on Liquid Mainnet](https://blog.blockstream.com/simplicity-launches-on-liquid-mainnet/)
- [Covenants in Production on Liquid](https://blog.blockstream.com/covenants-in-production-on-liquid/)
- [Blockstream Strategic Update 2025](https://blockstream.com/press-releases/2025-04-28-blockstream-shares-key-strategic-update-growth-expansion-2025/)

**Sobre PKI e Blockchain:**
- [PKI & Blockchain Use Cases - GlobalSign](https://www.globalsign.com/en/blog/pki-and-blockchain-whats-the-right-technology-for-your-use-case)
- [Blockchain for Digital Identity - Consensys](https://consensys.io/blockchain-use-cases/digital-identity)
- [Certificate Revocation on Blockchain - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S016740482100033X)

**Cobertura de Mídia:**
- [Bitcoin Magazine - Simplicity Launch](https://bitcoinmagazine.com/news/blockstream-launches-simplicity-smart-contracts-on-bitcoins-liquid-network-sidechain)
- [Decrypt - Simplicity Smart Contract](https://decrypt.co/333019/blockstream-simplicity-smart-contract-bitcoin)
- [The Block - Simplicity on Liquid](https://www.theblock.co/post/365054/blockstream-launches-simplicity-smart-contract-language-on-bitcoin-l2-liquid-network)
- [CoinDesk - Adam Back's Blockstream](https://www.coindesk.com/tech/2025/07/31/adam-beck-s-blockstream-unveils-bitcoin-powered-liquid-network-based-smart-contracts)

### Apêndice B: Estrutura do Repositório

```
satshack-3-main/
├── contracts/
│   ├── vault.simf          # Delegation Vault (Simplicity)
│   └── certificate.simf    # Certificate UTXO (Simplicity)
├── tests/
│   ├── test_emit.py        # Testes de emissão
│   ├── test_certificate_revoke.py  # Testes de revogação
│   └── test_edge_cases.py  # Testes de segurança
├── docs/
│   ├── DOCUMENTATION.md    # Documentação técnica (EN)
│   ├── DOCUMENTATION.pt    # Documentação técnica (PT)
│   └── PROTOCOL_SPEC.md    # Especificação do protocolo
├── secrets.json            # Chaves, endereços, CMRs
└── README.md               # Visão geral do projeto
```

### Apêndice C: Contato

**Equipe do SAP**
Repositório: [GitHub - satshack-3-main]
Email: [A definir]

---

*Este documento foi preparado para a Blockstream como parte de uma proposta de colaboração no ecossistema Simplicity/Liquid.*

**Janeiro 2026**
