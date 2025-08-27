[README.md](https://github.com/user-attachments/files/22009618/README.md)
# Consolidador de Retenções (NFe/NFS-e) — Streamlit

Aplicação web para enviar XMLs (ou ZIP com XMLs) e baixar um CSV consolidado com as retenções (PIS/COFINS/CSLL, IRRF, INSS, ISS).

## Como rodar local/online

### A) Local (rápido)
1. Instale Python 3.10+
2. `pip install -r requirements.txt`
3. `streamlit run app.py`  
   Acesse o link mostrado (geralmente http://localhost:8501).

### B) Streamlit Community Cloud (online e grátis)
1. Crie um repositório no GitHub contendo **app.py** e **requirements.txt**.
2. Vá em https://streamlit.io/cloud → **New app** → conecte seu GitHub e selecione o repositório/branch.
3. Start command padrão: `streamlit run app.py` (o Cloud já entende).
4. Publique. Você terá uma URL pública para compartilhar.

### C) Render / Railway / Fly.io (opcional)
- **Build**: `pip install -r requirements.txt`
- **Start**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

## Observações
- O app aceita múltiplos XMLs e também **ZIP** com vários XMLs.
- Se alguma NFS-e usar layout fora do padrão ABRASF, abra uma issue com um XML de exemplo (anonimizado) para ajustes.
