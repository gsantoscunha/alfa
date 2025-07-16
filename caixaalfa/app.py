import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Fluxo de Caixa", layout="wide")

st.title("📊 Dashboard de Fluxo de Caixa")

# Upload da planilha
uploaded_file = st.file_uploader("Faça o upload da planilha (.xlsx)", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Extrato")
    df = df.rename(columns={
        "Data de lançamento": "Data",
        "Descrição do lançamento": "Descricao",
        "Entradas / Saídas (R$)": "Valor",
        "Conta": "Categoria"
    })
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True)
    df = df.sort_values(by="Data")

    # Adição manual de lançamento
    with st.expander("➕ Adicionar nova entrada/saída"):
        with st.form("add_entry"):
            data = st.date_input("Data")
            tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
            valor = st.number_input("Valor", min_value=0.01)
            categoria = st.text_input("Categoria")
            descricao = st.text_input("Descrição")
            submitted = st.form_submit_button("Adicionar")
            if submitted:
                valor_final = valor if tipo == "Entrada" else -valor
                nova_linha = pd.DataFrame([{
                    "Data": data,
                    "Descricao": descricao,
                    "Valor": valor_final,
                    "Categoria": categoria
                }])
                df = pd.concat([df, nova_linha], ignore_index=True)
                st.success("Lançamento adicionado!")

    # Métricas principais
    saldo_total = df["Valor"].sum()
    total_entradas = df[df["Valor"] > 0]["Valor"].sum()
    total_saidas = df[df["Valor"] < 0]["Valor"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Saldo Atual", f"R$ {saldo_total:,.2f}")
    col2.metric("⬆️ Entradas", f"R$ {total_entradas:,.2f}")
    col3.metric("⬇️ Saídas", f"R$ {abs(total_saidas):,.2f}")

    # Gráfico de barras por data
    df_grouped = df.groupby("Data")["Valor"].sum().reset_index()
    fig1 = px.bar(df_grouped, x="Data", y="Valor", title="Fluxo Diário")
    st.plotly_chart(fig1, use_container_width=True)

    # Pizza por categoria
    df_cat = df.groupby("Categoria")["Valor"].sum().reset_index()
    fig2 = px.pie(df_cat, values="Valor", names="Categoria", title="Distribuição por Categoria")
    st.plotly_chart(fig2, use_container_width=True)

    # Tabela final
    st.subheader("📄 Lançamentos")
    st.dataframe(df.sort_values(by="Data", ascending=False), use_container_width=True)
