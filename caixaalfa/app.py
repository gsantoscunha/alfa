import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Resumo Mensal - Fluxo de Caixa", layout="wide")
st.title("📘 Fluxo de Caixa - Consolidado por Mês")

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

    # Pivot por conta x mês
    pivot = df.pivot_table(
        index="Conta",
        columns="AnoMes",
        values="Valor",
        aggfunc="sum",
        fill_value=0
    )

    # Linha de total geral
    pivot.loc["Total Geral"] = pivot.sum()

    # Cálculo de saldo inicial e final
    opening_balances = []
    closing_balances = []
    saldo_acumulado = 0

    for col in pivot.columns:
        opening_balances.append(saldo_acumulado)
        saldo_periodo = pivot[col].sum()
        saldo_acumulado += saldo_periodo
        closing_balances.append(saldo_acumulado)

    opening_df = pd.DataFrame([opening_balances], columns=pivot.columns, index=["Opening Balance"])
    closing_df = pd.DataFrame([closing_balances], columns=pivot.columns, index=["Closing Balance"])

    # Montar tabela final
    final_df = pd.concat([opening_df, pivot, closing_df])

    st.subheader("📊 Tabela Consolidada")
    st.dataframe(final_df.style.format("R$ {:,.2f}"), use_container_width=True)

    # Exportar como Excel
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Resumo')
        output.seek(0)
        return output

    excel_data = to_excel(final_df)
    st.download_button("⬇️ Baixar Excel Consolidado", data=excel_data, file_name="fluxo_consolidado.xlsx")

