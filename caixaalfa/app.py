import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import calendar

# ========== AUTENTICAÇÃO ==========
# Lista de usuários e senhas
users = {
    "admin": "senhaadmin123",
    "financeiro": "1234",
    "investidor": "abcde"
}

# Função de login
def login():
    st.title("🔐 Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if username in users and users[username] == password:
            st.session_state["usuario_logado"] = username
            st.success(f"Bem-vindo, {username}!")
            st.experimental_rerun()
        else:
            st.error("Usuário ou senha incorretos")

# Se não estiver logado, para tudo
if "usuario_logado" not in st.session_state:
    login()
    st.stop()

# ========== DASHBOARD ==========
st.set_page_config(page_title="Fluxo de Caixa Executivo", layout="wide")
st.title("📘 Dashboard Executivo de Fluxo de Caixa")

uploaded_file = st.file_uploader("📥 Faça o upload da planilha (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Extrato")
    df = df.rename(columns={
        "Data de lançamento": "Data",
        "Descrição do lançamento": "Descricao",
        "Entradas / Saídas (R$)": "Valor",
        "Conta": "Conta"
    })
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True)
    df["AnoMes"] = df["Data"].dt.to_period("M").astype(str)

    # Mês atual em português
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    data_final = df["Data"].max()
    nome_mes = meses_pt[data_final.month]
    label_mes = f"{nome_mes} / {data_final.year}"
    st.markdown(f"### 📅 {label_mes}", unsafe_allow_html=True)

    # KPIs
    df_mes = df.groupby("AnoMes")["Valor"].sum().cumsum().reset_index()
    df_mes.columns = ["Mês", "Saldo Acumulado"]

    ultimo_mes = df["AnoMes"].max()
    df_ultimo = df[df["AnoMes"] == ultimo_mes]
    saldo_atual = df_mes[df_mes["Mês"] == ultimo_mes]["Saldo Acumulado"].values[0]
    entradas_mes = df_ultimo[df_ultimo["Valor"] > 0]["Valor"].sum()
    saidas_mes = df_ultimo[df_ultimo["Valor"] < 0]["Valor"].sum()

    data_str = data_final.strftime("%d/%m/%Y")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"💰 Saldo Atual em {data_str}", f"R$ {saldo_atual:,.2f}")
    col2.metric("⬆️ Entradas no mês", f"R$ {entradas_mes:,.2f}")
    col3.metric("⬇️ Saídas no mês", f"R$ {abs(saidas_mes):,.2f}")
    col4.metric("📊 Resultado", f"R$ {(entradas_mes + saidas_mes):,.2f}")

    # Gráfico de saldo acumulado
    fig = px.line(df_mes, x="Mês", y="Saldo Acumulado", title="📈 Evolução do Saldo Acumulado", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    # Tabela por conta
    pivot = df.pivot_table(
        index="Conta",
        columns="AnoMes",
        values="Valor",
        aggfunc="sum",
        fill_value=0
    )
    pivot["Total"] = pivot.sum(axis=1)

    # Opening / Closing Balance
    meses = list(pivot.columns[:-1])
    opening = []
    closing = []
    saldo = 0
    for mes in meses:
        opening.append(saldo)
        saldo += pivot[mes].sum()
        closing.append(saldo)

    opening_df = pd.DataFrame([opening + [sum(opening)]], columns=meses + ["Total"], index=["Opening Balance"])
    closing_df = pd.DataFrame([closing + [sum(closing)]], columns=meses + ["Total"], index=["Closing Balance"])

    resultado_df = pd.concat([opening_df, pivot, closing_df])

    st.subheader("📋 Tabela Consolidada por Categoria")
    st.dataframe(resultado_df.style.format("R$ {:,.2f}").applymap(
        lambda v: "color: green" if v > 0 else ("color: red" if v < 0 else "")
    ), use_container_width=True)

    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Resumo')
        output.seek(0)
        return output

    excel_data = to_excel(resultado_df)
    st.download_button("⬇️ Baixar Excel Consolidado", data=excel_data, file_name="fluxo_consolidado.xlsx")

