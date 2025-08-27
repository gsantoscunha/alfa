# app.py
# Streamlit app: Consolidador de Retenções (NFe/NFSe) -> CSV
# Autor: ChatGPT
# Descrição: Faça upload de vários XMLs (ou um ZIP contendo XMLs) e gere um CSV consolidado.

import streamlit as st
import pandas as pd
from xml.etree import ElementTree as ET
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
import zipfile

st.set_page_config(page_title="Consolidador de Retenções (NFe/NFSe)", page_icon="📄", layout="wide")

# --- Parsers / Util -----------------------------------------------------------

NFE_NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
NFSE_NS = {"nfs": "http://www.abrasf.org.br/nfse.xsd"}

def to_dec(v) -> Decimal:
    if v is None:
        return Decimal("0")
    s = str(v).strip()
    if s == "":
        return Decimal("0")
    try:
        return Decimal(s.replace(",", "."))
    except InvalidOperation:
        return Decimal("0")

def fmt_money(d: Decimal, decimal_comma: bool = True) -> str:
    # sem separador de milhar, 2 casas
    if d is None:
        d = Decimal("0")
    s = f"{d:.2f}"
    return s.replace(".", ",") if decimal_comma else s

def text_or_none(node, path, ns):
    if node is None:
        return None
    el = node.find(path, ns)
    return el.text.strip() if el is not None and el.text else None

def is_nfe(root: ET.Element) -> bool:
    tag = root.tag or ""
    return tag.endswith("nfeProc") or tag.endswith("NFe") or "portalfiscal.inf.br/nfe" in tag

def is_nfse(root: ET.Element) -> bool:
    tag = root.tag or ""
    if "abrasf.org.br/nfse.xsd" in tag:
        return True
    return (root.find(".//nfs:Servico", NFSE_NS) is not None or
            root.find(".//nfs:InfNfse", NFSE_NS) is not None or
            root.find(".//nfs:InfDeclaracaoPrestacaoServico", NFSE_NS) is not None)

def parse_nfe(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)
    infNFe = root.find(".//nfe:infNFe", NFE_NS) or root.find(".//{http://www.portalfiscal.inf.br/nfe}infNFe")
    total = infNFe.find("./nfe:total", NFE_NS) if infNFe is not None else None

    ident = {
        "modelo": "NFe",
        "chave": (infNFe.get("Id")[3:] if infNFe is not None and infNFe.get("Id") else None),
        "numero": text_or_none(infNFe, "./nfe:ide/nfe:nNF", NFE_NS),
        "serie": text_or_none(infNFe, "./nfe:ide/nfe:serie", NFE_NS),
        "emissao": text_or_none(infNFe, "./nfe:ide/nfe:dhEmi", NFE_NS),
        "emit_cnpj": text_or_none(infNFe, "./nfe:emit/nfe:CNPJ", NFE_NS),
        "dest_cnpj_cpf": text_or_none(infNFe, "./nfe:dest/nfe:CNPJ", NFE_NS) or text_or_none(infNFe, "./nfe:dest/nfe:CPF", NFE_NS),
    }

    ret = {
        "PIS_retido": to_dec(text_or_none(total, "./nfe:retTrib/nfe:vRetPIS", NFE_NS) or 0),
        "COFINS_retido": to_dec(text_or_none(total, "./nfe:retTrib/nfe:vRetCOFINS", NFE_NS) or 0),
        "CSLL_retida": to_dec(text_or_none(total, "./nfe:retTrib/nfe:vRetCSLL", NFE_NS) or 0),
        "IRRF_retido": to_dec(text_or_none(total, "./nfe:retTrib/nfe:vIRRF", NFE_NS) or 0),
        "INSS_retido": to_dec(text_or_none(total, "./nfe:retTrib/nfe:vRetPrev", NFE_NS) or 0),
        "ISS_retido": to_dec(text_or_none(total, "./nfe:ISSQNtot/nfe:vISSRet", NFE_NS) or 0),
        "ICMS_ST_total": to_dec(text_or_none(total, "./nfe:ICMSTot/nfe:vST", NFE_NS) or 0),
    }

    ret["tem_retencao_federal"] = any(ret[k] > 0 for k in ("PIS_retido","COFINS_retido","CSLL_retida","IRRF_retido","INSS_retido"))
    ret["tem_iss_retido"] = ret["ISS_retido"] > 0
    ret["tem_qualquer_retencao"] = ret["tem_retencao_federal"] or ret["tem_iss_retido"]

    return ident, ret

def parse_nfse(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)
    valores = (root.find(".//nfs:Servico/nfs:Valores", NFSE_NS)
               or root.find(".//nfs:Valores", NFSE_NS))

    def v(tag):
        el = valores.find(f"nfs:{tag}", NFSE_NS) if valores is not None else None
        return to_dec(el.text) if el is not None and el.text else Decimal("0")

    ret = {
        "PIS_retido": v("ValorPis"),
        "COFINS_retido": v("ValorCofins"),
        "CSLL_retida": v("ValorCsll"),
        "IRRF_retido": v("ValorIr"),
        "INSS_retido": v("ValorInss"),
        "ISS_retido": v("ValorIss"),
    }

    iss_flag_node = (root.find(".//nfs:Servico/nfs:IssRetido", NFSE_NS)
                     or root.find(".//nfs:IssRetido", NFSE_NS))
    iss_flag = (iss_flag_node is not None and (iss_flag_node.text or "").strip() == "1")

    ret["tem_retencao_federal"] = any(ret[k] > 0 for k in ("PIS_retido","COFINS_retido","CSLL_retida","IRRF_retido","INSS_retido"))
    ret["tem_iss_retido"] = ret["ISS_retido"] > 0 or iss_flag
    ret["tem_qualquer_retencao"] = ret["tem_retencao_federal"] or ret["tem_iss_retido"]

    ident = {
        "modelo": "NFSe",
        "chave": None,
        "numero": (root.findtext(".//nfs:Numero", namespaces=NFSE_NS) or "").strip() or None,
        "serie": None,
        "emissao": (root.findtext(".//nfs:DataEmissao", namespaces=NFSE_NS) or "").strip() or None,
        "emit_cnpj": (root.findtext(".//nfs:Prestador/nfs:CpfCnpj/nfs:Cnpj", namespaces=NFSE_NS) or "").strip() or None,
        "dest_cnpj_cpf": (root.findtext(".//nfs:Tomador/nfs:IdentificacaoTomador/nfs:CpfCnpj/nfs:Cnpj", namespaces=NFSE_NS) or "").strip() or None,
    }
    return ident, ret

def analisar_xml_bytes(xml_bytes: bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    if is_nfe(root):
        try:
            return parse_nfe(xml_bytes)
        except Exception:
            return None
    if is_nfse(root):
        try:
            return parse_nfse(xml_bytes)
        except Exception:
            return None
    # tenta achar pistas mesmo sem root padrão
    if root.find(".//nfe:infNFe", NFE_NS) is not None:
        return parse_nfe(xml_bytes)
    if root.find(".//nfs:Servico", NFSE_NS) is not None:
        return parse_nfse(xml_bytes)
    return None

def row_from_parsed(filename: str, ident: dict, ret: dict, decimal_comma: bool = True) -> dict:
    return {
        "arquivo": filename,
        "modelo": ident.get("modelo"),
        "chave_ou_numero": ident.get("chave") or ident.get("numero"),
        "serie": ident.get("serie"),
        "emissao": ident.get("emissao"),
        "emit_cnpj": ident.get("emit_cnpj"),
        "dest_cnpj_cpf": ident.get("dest_cnpj_cpf"),
        "PIS_retido": fmt_money(ret.get("PIS_retido", Decimal("0")), decimal_comma),
        "COFINS_retido": fmt_money(ret.get("COFINS_retido", Decimal("0")), decimal_comma),
        "CSLL_retida": fmt_money(ret.get("CSLL_retida", Decimal("0")), decimal_comma),
        "IRRF_retido": fmt_money(ret.get("IRRF_retido", Decimal("0")), decimal_comma),
        "INSS_retido": fmt_money(ret.get("INSS_retido", Decimal("0")), decimal_comma),
        "ISS_retido": fmt_money(ret.get("ISS_retido", Decimal("0")), decimal_comma),
        "ICMS_ST_total": fmt_money(ret.get("ICMS_ST_total", Decimal("0")), decimal_comma),
        "tem_retencao_federal": "SIM" if ret.get("tem_retencao_federal") else "NÃO",
        "tem_iss_retido": "SIM" if ret.get("tem_iss_retido") else "NÃO",
        "tem_qualquer_retencao": "SIM" if ret.get("tem_qualquer_retencao") else "NÃO",
    }

def process_uploaded_files(files, decimal_comma=True):
    rows = []
    errors = []
    for up in files:
        filename = up.name
        data = up.read()
        # se for ZIP, extrai e processa XMLs internos
        if zipfile.is_zipfile(BytesIO(data)):
            try:
                with zipfile.ZipFile(BytesIO(data)) as z:
                    for info in z.infolist():
                        if info.filename.lower().endswith(".xml"):
                            with z.open(info) as fxml:
                                xml_bytes = fxml.read()
                            parsed = analisar_xml_bytes(xml_bytes)
                            if parsed is None:
                                errors.append(f"[ZIP] {filename} -> {info.filename}: XML inválido/inesperado")
                                continue
                            ident, ret = parsed
                            rows.append(row_from_parsed(f"{filename}::{info.filename}", ident, ret, decimal_comma))
            except Exception as e:
                errors.append(f"{filename}: erro ao ler ZIP ({e})")
        else:
            # XML solto
            parsed = analisar_xml_bytes(data)
            if parsed is None:
                errors.append(f"{filename}: XML inválido/inesperado")
                continue
            ident, ret = parsed
            rows.append(row_from_parsed(filename, ident, ret, decimal_comma))
    return rows, errors

# --- UI -----------------------------------------------------------------------

st.title("📄 Consolidador de Retenções (NFe / NFS-e)")
st.write("Envie **XMLs** ou um **ZIP com XMLs**. O sistema detecta automaticamente NFe/NFS-e e gera um **CSV consolidado** com as retenções (PIS/COFINS/CSLL, IRRF, INSS, ISS, etc.).")

colA, colB, colC = st.columns([1,1,1])
with colA:
    decimal_option = st.selectbox("Formato decimal", ["Vírgula (PT-BR)", "Ponto (US)"], index=0)
    decimal_comma = (decimal_option == "Vírgula (PT-BR)")
with colB:
    sep_option = st.selectbox("Separador do CSV", [";", ","], index=0 if decimal_comma else 1)
with colC:
    show_preview = st.checkbox("Mostrar prévia da tabela", value=True)

uploads = st.file_uploader("Arraste e solte seus arquivos aqui", type=["xml", "zip"], accept_multiple_files=True)

if uploads:
    with st.spinner("Processando arquivos..."):
        rows, errors = process_uploaded_files(uploads, decimal_comma=decimal_comma)
        if len(rows) == 0 and len(errors) > 0:
            st.error("Nenhum dado válido encontrado. Veja os erros abaixo.")
        elif len(rows) == 0:
            st.warning("Nenhum XML processado.")
        else:
            df = pd.DataFrame(rows)
            if show_preview:
                st.dataframe(df, use_container_width=True, height=420)

            # Gera CSV em memória
            csv_buf = BytesIO()
            df.to_csv(csv_buf, index=False, sep=sep_option, encoding="utf-8")
            csv_bytes = csv_buf.getvalue()

            st.download_button(
                label="⬇️ Baixar CSV consolidado",
                data=csv_bytes,
                file_name="retencoes_consolidado.csv",
                mime="text/csv"
            )

        if errors:
            with st.expander("Ver erros e avisos"):
                for e in errors:
                    st.write("• ", e)

st.markdown("""---
**Dicas**
- **NFe**: procura `retTrib` (PIS/COFINS/CSLL, IRRF, INSS) e `ISSQNtot/vISSRet` quando houver ISS conjugado.
- **NFS-e (ABRASF)**: procura `Servico/Valores` (Pis/Cofins/Csll/Ir/Inss/Iss) e a flag `IssRetido`.
- Se alguma prefeitura tiver layout muito específico, envie um exemplo (anonimizado) para eu ajustar.
""")
