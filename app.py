import streamlit as st
import pandas as pd

st.set_page_config(page_title='Consolidador de Retenções', page_icon='📄', layout='wide')
st.title('📄 Consolidador de Retenções — Diagnóstico')
st.write('Se você está vendo esta tela, o app subiu corretamente. Agora substitua este app.py pelo app completo.')
df = pd.DataFrame({'ok':[1,2,3]})
st.dataframe(df)
