import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import streamlit as st
import matplotlib.pyplot as plt

# Função para obter CDI, Selic e outras taxas usando Yahoo Finance
def obter_taxas():
    cdi_ticker = "^IRX"
    selic_ticker = "^BVSP"
    dolar_ticker = "USDBRL=X"
    euro_ticker = "EURBRL=X"
    cdi_data = yf.Ticker(cdi_ticker).history(period="1d")
    selic_data = yf.Ticker(selic_ticker).history(period="1d")
    dolar_data = yf.Ticker(dolar_ticker).history(period="1d")
    euro_data = yf.Ticker(euro_ticker).history(period="1d")

    cdi = cdi_data['Close'].iloc[-1] if not cdi_data.empty else 13.65
    selic = selic_data['Close'].iloc[-1] if not selic_data.empty else 12.75
    dolar = dolar_data['Close'].iloc[-1] if not dolar_data.empty else 5.20
    euro = euro_data['Close'].iloc[-1] if not euro_data.empty else 6.20

    return cdi, selic, dolar, euro

# Função para ajuste de data para dias úteis
def ajustar_para_dia_util(data, direcao="posterior"):
    if data.weekday() >= 5:
        if direcao == "posterior":
            return data + timedelta(days=(7 - data.weekday()))
        else:
            return data - timedelta(days=(data.weekday() - 4))
    return data

# Função de validação para parcelas finais
def validar_calculos_parcelas_finais(df_fluxo, n_parcelas):
    metade = n_parcelas // 2
    for i in range(metade, len(df_fluxo)):
        if df_fluxo.loc[i, 'valor_total_parcela'] > 1.5 * df_fluxo['valor_total_parcela'].mean():
            st.warning(f"Possível anomalia detectada na parcela {i + 1}: valor muito alto.")

# Função para amortização personalizada
def calcular_amortizacao_personalizada(parametros_amortizacao, acumular_parcelas_zeradas=False):
    fluxo_pagamentos = []
    saldo_devedor = sum([p["valor_amortizacao"] for p in parametros_amortizacao])
    for i, parametro in enumerate(parametros_amortizacao):
        amortizacao = min(parametro["valor_amortizacao"], saldo_devedor)
        juros = saldo_devedor * parametro["taxa_juros"]
        iof = parametro.get("iof", 0)
        despesas = parametro.get("despesas", 0)
        total_parcela = amortizacao + juros + iof + despesas
        saldo_devedor -= amortizacao

        if amortizacao == 0 and acumular_parcelas_zeradas:
            fluxo_pagamentos[-1]["valor_total_parcela"] += total_parcela
        else:
            fluxo_pagamentos.append({
                "parcela": i + 1,
                "data_pagamento": parametro["data"],
                "principal": saldo_devedor,
                "amortizacao": amortizacao,
                "juros": juros,
                "iof": iof,
                "despesas_bancarias": despesas,
                "valor_total_parcela": total_parcela,
                "saldo_devedor": saldo_devedor
            })
    return fluxo_pagamentos

# Função principal do Streamlit com tela de login
def login():
    st.title("Legatus Simulador de Operações de Crédito")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuario == "Legatus123" and senha == "Legatus123":
            st.success("Login bem-sucedido!")
            st.session_state['logged_in'] = True
        else:
            st.error("Usuário ou senha incorretos")

# Função de simulação de capital de giro
def simulador_capital_giro():
    st.title("Simulador de Capital de Giro")
    valor_operacao = st.number_input("Valor da Operação (R$)", value=1000000.0)
    taxa_tipo = st.selectbox("Tipo de Taxa de Juros", ["Pré-fixado", "CDI + taxa", "% do CDI", "Selic + taxa", "% da Selic"])
    carencia = st.number_input("Número de Parcelas de Carência", value=0, min_value=0)
    data_inicial = st.date_input("Data Inicial da Operação", value=datetime.now())
    sistema_amortizacao = st.selectbox("Sistema de Amortização", ["SAC", "PRICE", "Personalizado"])
    n_parcelas = st.number_input("Número de Parcelas", value=6, min_value=1)

    cdi, selic, dolar, euro = obter_taxas()
    usa_iof_padrao = st.checkbox("Usar taxa de IOF padrão")
    iof_adicional = st.number_input("IOF Adicional (%)", value=0.38 if usa_iof_padrao else 0.0) / 100
    iof_diario = st.number_input("IOF Diário (%)", value=0.0041 if usa_iof_padrao else 0.0) / 100

    # Taxa de juros baseada na seleção
    taxa_juros = st.number_input("Taxa de Juros (%)", value=5.5) / 100
    despesas_bancarias = st.number_input("Despesas Bancárias Mensais (R$)", value=0.0)
    financiar_despesas = st.checkbox("Financiar Despesas Bancárias")
    taxa_mensal = taxa_juros / 12

    parametros_amortizacao = []
    if sistema_amortizacao == "Personalizado":
        st.subheader("Defina o Fluxo de Amortização Personalizado")
        for i in range(int(n_parcelas)):
            data_parcela = st.date_input(f"Data da Parcela {i+1}", value=data_inicial + timedelta(days=30 * i))
            valor_amortizacao = st.number_input(f"Valor de Amortização da Parcela {i+1} (R$)", value=0.0)
            taxa_parcela = st.number_input(f"Taxa de Juros Parcela {i+1} (%)", value=taxa_mensal * 100) / 100
            iof_parcela = st.number_input(f"IOF da Parcela {i+1} (R$)", value=0.0)
            despesas_parcela = st.number_input(f"Despesas Bancárias da Parcela {i+1} (R$)", value=0.0)
            parametros_amortizacao.append({
                "data": data_parcela,
                "valor_amortizacao": valor_amortizacao,
                "taxa_juros": taxa_parcela,
                "iof": iof_parcela,
                "despesas": despesas_parcela
            })
        acumular = st.checkbox("Acumular valores de parcelas zeradas?")
        fluxo_pagamentos = calcular_amortizacao_personalizada(parametros_amortizacao, acumular)
    else:
        # Calcular fluxo padrão para SAC e PRICE
        fluxo_pagamentos = calcular_juros_sac(valor_operacao, taxa_mensal, n_parcelas, carencia, iof_adicional, iof_diario, despesas_bancarias, financiar_despesas) if sistema_amortizacao == "SAC" else calcular_juros_price(valor_operacao, taxa_mensal, n_parcelas, carencia, iof_adicional, iof_diario, despesas_bancarias, financiar_despesas)

    # Ajustar datas e validar cálculos para últimas parcelas
    for i, parcela in enumerate(fluxo_pagamentos):
        if sistema_amortizacao != "Personalizado":
            parcela["data_pagamento"] = ajustar_para_dia_util(data_inicial + timedelta(days=30 * i))
    validar_calculos_parcelas_finais(pd.DataFrame(fluxo_pagamentos), n_parcelas)

    # Exibir resultados
    df_fluxo = pd.DataFrame(fluxo_pagamentos)
    st.write("Fluxo de Pagamentos Detalhado")
    st.dataframe(df_fluxo)

# Executar a aplicação
if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state['logged_in'] = False
    if st.session_state['logged_in']:
        simulador_capital_giro()
    else:
        login()
