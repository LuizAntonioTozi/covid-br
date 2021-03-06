#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Modelagem em tempo real | COVID-19 no Brasil
--------------------------------------------

Ideias e modelagens desenvolvidas pela trinca:
. Mauro Zackieiwicz
. Luiz Antonio Tozi
. Rubens Monteiro Luciano

Esta modelagem possui as seguintes características:

a) NÃO seguimos modelos paramétricos => Não existem durante a epidemia dados
suficientes ou confiáveis para alimentar modelos epidemiológicos como a excelente
calaculadora http://gabgoh.github.io/COVID/index.html (ela serve para gerar cená-
rios e para modelar a epidemia DEPOIS que ela passar). Além disso, a natureza
exponencial das curvas as torna extremamente sensíveis aos parâmetros que a defi-
nem. Isso faz com que a confiabilidade preditiva desses modelos seja ilusória.

b) A evolução epidemia no Brasil começou depois da de outros países. Nossa mode-
lagem se apoia nesse fato. Com os dados disponíveis, procuramos no instante pre-
sente determinar quem estamos seguindo, ou seja, que países mais se pareceram
conosco passado o mesmo período de disseminação. A partir do que aconteceu nesses
países projetamos o que pode acontecer aqui.

c) Esta conta é refeita dia a dia. Dependendo de nossa competência em conter ou
não a disseminação do Covid-19 nos aproximaremos dos países que melhor ou pior
lidaram com a epidemia e a projeção refletirá essa similaridade.

d) As decisões de modelagem são indicadas no código com os zoinhos: # ◔◔ {...}
São pontos de partida para discutir a modelagem e propor alternativas.

"""

import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set()
# no ipython usar este comando antes de rodar => %matplotlib osx
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


__author__ = "Mauro Zackiewicz"   # codigo
__copyright__ = "Copyright 2020"
__license__ = "New BSD License"
__version__ = "1.1.3"
__email__ = "maurozac@gmail.com"
__status__ = "Experimental"


def preparar_dados(p1, p4):
    u"""Busca dados e organiza tabela "data" com os dados de referência para a
    modelagem.
    Fontes:
    . Mundo: https://covid.ourworldindata.org
    . Brasil: https://brasil.io

    Retorna:
    raw <DataFrame> | Série completa do número de mortes/dia por país, sem trans-
        posição temporal
    inicio <Series> | Referência dos indexes em raw para justapor o início das
        curvas dos diferentes países
    data <DataFrame> | Série de número de mortes/dia por país trazendo para o
        zero (index 0) o primeiro dia em que ocorrem pelo menos p1 mortes
        (ver macro parâmetros). Isto reduz a quantidade de países para o grupo
        que está à frente ou pareado ao Brazil. A partir do index 0 é possível
        comparar a evolução dos casos entre os países.
    nbr <int> | Número de dias da série de dados para o Brasil
    popu: <DataFrame> | População dos países para depois calcular a taxa de mortes
        por 100 mil habitantes
    popuBR: <dict> | População dos recortes dentro do Brasil
    por100k: <dict> | Mortes por 100 mil hab brasil

    """
    # ◔◔ {usamos as mortes diárias por parecer ser o dado mais confiável}
    raw = pd.read_csv("https://covid.ourworldindata.org/data/ecdc/new_deaths.csv").fillna(0.0)
    # ◔◔ {o link abaixo carrega o acumulado de mortes, não usamos pq a soma vai alisando a série}
    # raw = pd.read_csv("https://covid.ourworldindata.org/data/ecdc/total_deaths.csv").fillna(0.0)
    # tempo = raw['date']  # ◔◔ {não usamos as datas}
    raw = raw.drop(columns='date')

    # dados da população mundo
    popu = pd.read_csv("https://covid.ourworldindata.org/data/ecdc/locations.csv").set_index('countriesAndTerritories')
    popu["paises"] = [_.replace('_', ' ').replace('United States of America', 'United States') for _ in popu.index]
    popu = popu.set_index("paises")

    # dados Brasil
    # ◔◔ {já baixamos filtrado para SP, mas pode se usar outros estados}
    sp = pd.read_csv("https://brasil.io/dataset/covid19/caso?state=SP&format=csv")

    # contruir base para a tabela "data"
    inicio = raw.ge(p1).idxmax()  # ◔◔ {encontra os index de qdo cada pais alcança 3}
    data = pd.DataFrame({'Brazil':raw['Brazil'][inicio['Brazil']:] * p4}).reset_index().drop(columns='index')
    nbr = data.shape[0]

    # adicionar dados de SP
    sp_estado = sp.loc[lambda df: df['place_type'] == "state", :]
    SP_estado = list(sp_estado['deaths'].head(nbr + 1).fillna(0.0))
    SP_estado = [SP_estado[i] - SP_estado[i+1] for i in range(len(SP_estado)-1)]
    SP_estado.reverse()
    SP_estado_popu = sp_estado['estimated_population_2019'].max()  # 45919049
    data['SP'] = pd.Series(SP_estado).values * p4

    # adicionar dados da cidade de SP
    sp_city = sp.loc[lambda df: df['city'] == u"São Paulo", :]
    SP_city = list(sp_city['deaths'].head(nbr + 1).fillna(0.0))
    SP_city = [SP_city[i] - SP_city[i+1] for i in range(len(SP_city)-1)]
    SP_city.reverse()
    SP_city_popu = sp_city['estimated_population_2019'].max()  # 12252023
    data['SP_City'] = pd.Series(SP_city).values * p4

    # adicionar dados do Brasil sem SP
    br_ex_sp = [x[0]-x[1] for x in zip(list(data['Brazil']), SP_estado)]
    data['Brazil_sem_SP'] = pd.Series(br_ex_sp).values

    # adicionar dados dos países à frente ou pareados ao Brasil
    for k in inicio.keys():
        if k == "Brazil": continue
        if k not in popu.index: continue
        if inicio[k] == 0 or inicio[k] > inicio["Brazil"]: continue
        C = raw[k][inicio[k]:inicio[k]+nbr]
        data[k] = C.values

    # preparar dict com dados da população Brasil
    popuBR = {
        'Brazil': popu['population']['Brazil'],
        'SP': SP_estado_popu,
        'SP_City': SP_city_popu,
        'Brazil_sem_SP': popu['population']['Brazil'] - SP_estado_popu,
    }

    # dados normalizados por 100 mil hab. para Brasil
    por100k = {
        'Brazil': data['Brazil'].values * (10**5) / popuBR['Brazil'],
        'SP': data['SP'].values * (10**5) / popuBR['SP'],
        'SP_City': data['SP_City'].values * (10**5) / popuBR['SP_City'],
        'Brazil_sem_SP': data['Brazil_sem_SP'].values * (10**5) / popuBR['Brazil_sem_SP'],
    }

    return raw, inicio, data, nbr, popu, popuBR, por100k


def rodar_modelo(raw, inicio, data, nbr, popu, popuBR, por100k, p2, p3, ref):
    """
    Usa os dados preparados para gerar dados para visualização e a projeção da
    evoluação da epidemia.

    Retorna:
    correlacionados <list>: Países mais correlacionados, usados para a projeção
    calibrados <DataFrame>: Série alisada de mortes por 100 mil hab por dia com
        dados de ref e países correlacionados
    projetado <Array>: Série estimada para a evoluação da epidemia em ref
    infos <dict>: informações sobre o pico estimado da epidemia

    """

    # ◔◔ {Optamos por não alisar dados antes de calcular a correlação. Sabemos
    # que a qualidade do report dos dados é variável, mas assumimos que o ruído
    # é aleatório e por isso não é preciso alisar para que a correlação seja
    # válida. Ao contrário, a correlação "bruta" seria a mais verossível}

    # ◔◔ {mas caso você ache que vale a pena alisar antes, use o codigo abaixo}
    # alisamento para os casos de morte reportados (média móvel)
    # data = data.rolling(5).mean()

    # calcular a matriz de correlações:
    pearson = data.corr()
    # ◔◔ {o default do método usa a correlação de Pearson, cf. ref abaixo}
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.corr.html

    # ◔◔ {se quiser ver as prévias ...}
    # print(pearson['Brazil'].sort_values(ascending=False))
    # print(pearson['Brazil_sem_SP'].sort_values(ascending=False))
    # print(pearson['SP'].sort_values(ascending=False))
    # print(pearson['SP_City'].sort_values(ascending=False))

    # ◔◔ { não incluir os casos locais para evitar endogeneidade}
    out = ['Brazil', 'Brazil_sem_SP', 'SP', 'SP_City',]  # nao misturar com os demais cortes locais

    # selecionar os p2 países que melhor se correlacionam com a ref
    correlacionados = [_ for _ in pearson[ref].sort_values(ascending=False).keys() if _ not in out][:p2]

    # ◔◔ {para a visualização gráfica os dados são normalizados para a mesma
    # taxa: mortes por 100 mil habitantes}

    # ◔◔ {usar a populacao da China distorce demais: a pop da cidade de wuhan
    # é de 11 milhões e da província de Hubei é de 58 milhões, usamos 15 milhões
    # como valor aproximado}

    # criar tabela normalizada, começa com dados da ref
    calibrados = pd.DataFrame({ref:por100k[ref]})

    # preencher com os dados normalizados dos países correlacionados
    for k in correlacionados:
        # ◔◔ {pega os dados em raw pq agora usaremos todos os dados disponíveis para o país}
        C = raw[k][inicio[k]:]
        if k == "China":
            # ◔◔ {correcao para a popu aproximada do foco: 15 milhões}
            additional = pd.DataFrame({k: C.values * (10**5) / 15000000})
        else:
            additional = pd.DataFrame({k: C.values * (10**5) / popu['population'][k]})  # array
        calibrados = pd.concat([calibrados, additional], axis=1)

    # ◔◔ {aqui usamos um alisamento p3 de dias para deixar a visualização melhor}
    calibrados = calibrados.rolling(p3).mean()

    # ◔◔ {a projeção usa os dados alisados}
    # ◔◔ {como é feita a projeção:
    # 1. cada país correlacionado terá um peso, proporcianal a quanto se correlaciona
    # .. soma dos pesos = 1
    # .. quanto mais correlacionado, maior o peso }
    pesos = [pearson[ref][c] for c in correlacionados]  # melhor corr pesa mais
    pesos = [pesos[i]/sum(pesos) for i in range(len(pesos))]  # pesos normalizados
    pesos = dict(zip(correlacionados, pesos))  # num dict para facilitar

    # proj <list>: vai ter ao final o tamanho da maior serie em calibrados
    proj = [np.nan for _ in range(nbr)]  # começa com nan onde já temos os dados da ref
    proj[-1] =  calibrados[ref][nbr - 1] # primeiro valor coincide com último de ref
    # será a partir daí que começa a projeção

    # ◔◔ {a projeção segue dia a dia as variações dos países correlacionado}
    for d in range(nbr, calibrados.shape[0]):
        x = 0  # incremento estimado para o dia
        for c in correlacionados:
            if not np.isnan(calibrados[c][d]):
                # adiciona o incremento % do país ponderado por seu peso
                x += (calibrados[c][d]/calibrados[c][d-1]) * pesos[c]
            else:
                # ◔◔ {qdo acabam os dados de um país ele pára de influenciar a taxa}
                x += 1 * pesos[c]
            # print(d, c, x)
        # a série da projeção é construída aplicando o incremento estimado ao dia anterior
        proj.append(proj[-1] * x)

    # projetado <Array>
    projetado = np.array(proj)

    # ◔◔ {informações adicionais}
    # pico => valor máximo da série projetada
    pico = np.nan_to_num(projetado).max()  # float
    # mortes abs => reverte para valor absoluto de mortes
    mortes_no_pico = str(int(pico * popuBR[ref]/100000))  # str
    # dia em que acontece o pico
    ix_do_pico = proj.index(np.nan_to_num(projetado).max())  # int => index
    dia_do_pico = str(datetime.datetime.now() + datetime.timedelta(days=ix_do_pico-nbr))[:10] # str
    # consolidado para output
    infos = {
        "mortes_no_pico": mortes_no_pico,
        "dia_do_pico": dia_do_pico,
        "pico": pico,
        "index": ix_do_pico,
    }

    return correlacionados, calibrados, projetado, infos


def gerar_grafico(correlacionados, calibrados, projetado, infos):
    """
    Paleta: https://encycolorpedia.com/
    #1f78b4 base: azul #7ba3cd white shade
    #111111 branco
    #ff003f vermelho #ff7c7a white shade
    #000000 preto
    """
    fig, ax = plt.subplots()
    hoje = str(datetime.datetime.now())[:16]
    ax.set_title(u"Evolução da Covid-19 | " + ref + " | " + hoje, fontsize=10)
    ax.set_xlabel(u'Dias desde ' + str(p1) + ' primeiras mortes', fontsize=8)
    ax.set_xlim(0, calibrados.shape[0]+20)
    ax.set_ylabel(u'Mortes diárias por 100 mil habitantes', fontsize=8)
    for c in correlacionados:
        ax.plot(calibrados[c], linewidth=3, color="#ff7c7a")
        lvi = calibrados[c].last_valid_index()
        if c == "China": nome = "Wuhan"
        else: nome = c
        ax.text(lvi+1, calibrados[c][lvi], nome, fontsize=6, verticalalignment="center")
    ax.plot(calibrados[ref], linewidth=3, color="#1f78b4")
    ax.plot(projetado, linewidth=2, linestyle=":", color="#1f78b4")
    lvi = pd.Series(projetado).last_valid_index()
    ax.text(lvi+1, projetado[lvi], ref, fontsize=6, verticalalignment="center")
    # ax.legend(calibrados, fontsize=8)
    ax.plot(infos["index"], infos["pico"], '^', markersize=6.0, color="#1f78b4")
    msg = "PICO ~" + infos["mortes_no_pico"] + " mortes em " + infos["dia_do_pico"]
    ax.text(infos["index"]-2, infos["pico"]*1.2, msg, fontsize=8, color="#1f78b4")
    fig.text(0.99, 0.01, u'M.Zac | L.Tozi | R.Luciano', family="monospace", fontsize='6', color='gray', horizontalalignment='right')

#########################   R O D A R   #######################################

# Macro parâmetros
p1 = 3  # mortes no dia para iniciar série
p2 = 5  # número de países mais correlacionados
p3 = 7  # alisamento para o gráfico (média móvel)
p4 = 1.48  # correcao por subnotificacao nos dados brasileiros
# ◔◔ {ref: https://noticias.uol.com.br/saude/ultimas-noticias/redacao/2020/04/09/covid-19-declaracoes-de-obito-apontam-48-mais-mortes-do-que-dado-oficial.htm}
ref = "SP_City"  # escolher um entre: "SP_City", "SP", "Brazil", "Brazil_sem_SP"

raw, inicio, data, nbr, popu, popuBR, por100k = preparar_dados(p1, p4)
correlacionados, calibrados, projetado, infos = rodar_modelo(raw, inicio, data, nbr, popu, popuBR, por100k, p2, p3, ref)
gerar_grafico(correlacionados, calibrados, projetado, infos)
