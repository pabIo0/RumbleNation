"""
Diário de testes da etapa 3. São dois tipos de teste, e os dois deixam os números prontos para o relatório:
  1. Tempo por jogada (o padrão): mede o tempo de execução do Minimax e do Alfa-Beta nível a nível, até
     descobrir o limite de viabilidade de cada um.
  2. Partidas IA x IA (--partidas): joga partidas completas entre duas IAs e anota o placar final.

Como os testes de tempo funcionam:
  - São três posições fixas da mesma partida (36 tropas, semente 123), sempre no começo de um turno:
    início, meio e final. Como os dados são determinísticos, as posições são sempre as mesmas.
  - Cada teste é uma jogada da IA (uma busca completa) numa posição, com um algoritmo e um nível.
  - Para cada posição e cada algoritmo, o nível sobe de um em um até:
      * a jogada passar do limite de tempo (esse teste conta: é o primeiro nível acima do limite);
      * a estimativa do próximo nível passar de 5 vezes o limite (não vale a pena esperar);
      * a busca enxergar o fim da partida (subir o nível não muda mais nada).
  - Os níveis que não foram executados são estimados com o fator de crescimento médio por nível
    (calculado do nível 5 em diante), até a jogada mais lenta passar de 8 horas (inexequível).
  - Também calcula o fator de ramificação efetiva b* de cada busca (aula 4), a partir dos nós visitados.

Como as partidas IA x IA funcionam:
  - São partidas completas, com 36 tropas, da primeira jogada até a auditoria dos castelos.
  - Alfa-Beta contra Alfa-Beta em todas as combinações dos níveis escolhidos (cada nível joga como J1 e
    como J2), em várias sementes: 123, 124, ... Cada semente muda o mapa, o mercado e os dados.
  - Minimax contra Minimax com níveis iguais, só na semente 123 e até o nível 8, para comparar a partida
    inteira com a do Alfa-Beta no mesmo nível (as jogadas e o placar final têm que ser os mesmos).
  - Cada partida anota o placar final (pontos do J1 x pontos do J2), o número de jogadas e o tempo de
    busca de cada IA. Os placares não dependem da máquina; os tempos, sim.

Rodar:  python diario_testes.py               (pergunta o limite; Enter = 60 s)
        python diario_testes.py --limite 300  (mede níveis mais altos, mas demora bem mais)
        python diario_testes.py --teste alfabeta 14         (só um teste: Alfa-Beta nível 14 na posição do início)
        python diario_testes.py --teste minimax 11 todas    (só esse nível, nas três posições)
        Os testes avulsos são anotados em testes_avulsos.csv (cada execução acrescenta uma linha por teste).
        python diario_testes.py --partidas                          (pergunta os níveis e quantas sementes)
        python diario_testes.py --partidas 2 4 6 8 10 --sementes 3  (níveis das IAs e número de sementes)

Durante um teste de tempo, Ctrl+C desiste daquele teste e passa para o próximo algoritmo ou posição.
Durante uma partida, Ctrl+C interrompe a partida: dá para pular só ela ou finalizar com as que já terminaram.
O resultado aparece na tela e fica salvo em dois arquivos, na pasta de onde o Python foi chamado:
    resultado_testes.txt     texto, para ler e copiar para o relatório
    resultado_testes.csv     planilha para o Excel (separador ';' e vírgula decimal), com uma tabela em segundos para gráficos
    resultado_partidas.txt   o mesmo texto, para as partidas IA x IA
    resultado_partidas.csv   a mesma planilha, para as partidas IA x IA
"""
import csv
import os
import platform
import sys
from datetime import datetime

from logica_jogo import LogicaJogo
from ia import TipoJogador, NOMES_TIPO, escolher_jogada, formatar_tempo, formatar_inteiro

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")  # Evita erro com 'µ' e '—' em consoles antigos

ARQUIVO_RESULTADO = "resultado_testes.txt"
ARQUIVO_CSV = "resultado_testes.csv"
ARQUIVO_AVULSOS = "testes_avulsos.csv"
ARQUIVO_PARTIDAS = "resultado_partidas.txt"
ARQUIVO_PARTIDAS_CSV = "resultado_partidas.csv"
LIMITE_PADRAO_S = 60.0
FAIXAS = [(1.0, "Jogável (até 1 s)"), (10.0, "Aceitável (até 10 s)"), (60.0, "Lento (até 60 s)")]
LIMITE_INVIAVEL_S = 60.0           # acima disso a jogada é lenta demais para jogar
LIMITE_INEXEQUIVEL_S = 8 * 3600.0  # acima disso nem como teste dá para executar
NIVEL_MAXIMO = 20                  # o mesmo máximo da interface e do simulador
ALGORITMOS = (TipoJogador.MINIMAX, TipoJogador.ALFA_BETA)
POSICOES = ("início", "meio", "final")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro")

# Partidas IA x IA
TROPAS_PARTIDAS = 36
PRIMEIRA_SEMENTE = 123          # a mesma dos testes de tempo; as outras sementes vêm em seguida (124, 125, ...)
NIVEIS_PARTIDAS = (2, 4, 6, 8)  # níveis das IAs quando nenhum é escolhido
SEMENTES_PARTIDAS = 5           # número de sementes quando nenhum é escolhido
NIVEL_MAXIMO_MINIMAX = 8        # acima disso, uma partida inteira de Minimax contra Minimax leva horas
# Quanto o tempo da busca cresce a cada nível (medido nos testes de tempo). Só serve para pôr as partidas em ordem.
CRESCIMENTO = {TipoJogador.MINIMAX: 4.3, TipoJogador.ALFA_BETA: 2.6}


# =============================================================================
#  MÁQUINA E POSIÇÕES DE TESTE
# =============================================================================

def nome_do_processador():
    """Nome comercial do processador (no Windows vem do registro; no Linux, de /proc/cpuinfo)."""
    try:
        if platform.system() == "Windows":
            import winreg
            chave = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(chave, "ProcessorNameString")[0].strip()
        if platform.system() == "Linux":
            with open("/proc/cpuinfo", encoding="utf-8") as arquivo:
                for linha in arquivo:
                    if linha.startswith("model name"):
                        return linha.split(":", 1)[1].strip()
    except (OSError, ImportError, IndexError):
        pass
    return platform.processor() or platform.machine()


def nome_do_sistema():
    sistema = f"{platform.system()} {platform.release()}"
    if platform.system() == "Windows":
        try:
            build = int(platform.version().split(".")[2])
            sistema = "Windows 11" if build >= 22000 else f"Windows {platform.release()}"
        except (IndexError, ValueError):
            pass
    return sistema


def posicoes_de_teste(tropas=36, seed=123):
    """
    Três posições fixas da mesma partida (Alfa-Beta nível 2 contra ele mesmo): o início, o meio e o final.
    :return: ({"início": (número da jogada, motor), "meio": ..., "final": ...}, total de jogadas da partida)
    """
    motor = LogicaJogo(tropas, seed=seed)
    historico = [motor.clonar()]
    while motor.gerar_jogadas_possiveis():
        motor.aplicar_jogada(escolher_jogada(motor, TipoJogador.ALFA_BETA, 2).jogada)
        historico.append(motor.clonar())
    total = len(historico) - 1  # o último estado é o fim da partida, sem jogadas
    meio = _inicio_de_turno(historico, int(total * 0.45))
    final = _inicio_de_turno(historico, max(int(total * 0.85), meio + 1))
    return {"início": (0, historico[0]), "meio": (meio, historico[meio]), "final": (final, historico[final])}, total


def _inicio_de_turno(historico, a_partir_de):
    """Primeira posição, a partir do índice dado, em que um jogador começa o turno (com rerrolagem e carta)."""
    for i in range(max(a_partir_de, 1), len(historico) - 1):
        if historico[i - 1].id_jogador_atual != historico[i].id_jogador_atual:
            return i
    return a_partir_de


# =============================================================================
#  TESTES
# =============================================================================

class Medidas:
    def __init__(self):
        self.tempos = {(alg, pos): {} for alg in ALGORITMOS for pos in POSICOES}  # [(alg, pos)][nível] = segundos
        self.nos = {(alg, pos): {} for alg in ALGORITMOS for pos in POSICOES}     # [(alg, pos)][nível] = nós visitados
        self.passou = set()  # (alg, pos) em que um teste passou do limite
        self.fim = {}        # (alg, pos) -> nível a partir do qual a busca já vai até o fim da partida
        self.registro = []   # (hora, posição, algoritmo, nível, nós visitados, segundos) de cada teste


def medir(posicoes, limite_s):
    medidas = Medidas()
    for pos in POSICOES:
        numero, motor = posicoes[pos]
        print(f"\n--- Posição {pos} (jogada {numero}, {len(motor.gerar_jogadas_possiveis())} jogadas possíveis) ---")
        for alg in ALGORITMOS:
            nome = NOMES_TIPO[alg]
            serie = medidas.tempos[(alg, pos)]
            nos_anterior = None
            for nivel in range(1, NIVEL_MAXIMO + 1):
                if nivel - 1 in serie and nivel - 2 in serie and serie[nivel - 2] > 0:
                    estimativa = serie[nivel - 1] ** 2 / serie[nivel - 2]
                    if estimativa > 5 * limite_s:
                        print(f"  {nome:9s} parou: o nível {nivel} levaria uns {formatar_duracao(estimativa)}.")
                        break
                try:
                    decisao = escolher_jogada(motor, alg, nivel)
                except KeyboardInterrupt:
                    print(f"\n  {nome:9s} nível {nivel} interrompido (Ctrl+C): segue para o próximo teste.")
                    break
                serie[nivel] = decisao.tempo
                medidas.nos[(alg, pos)][nivel] = decisao.nos_visitados
                medidas.registro.append((datetime.now().strftime("%H:%M:%S"), pos, nome, nivel, decisao.nos_visitados, decisao.tempo))
                print(f"  {nome:9s} nível {nivel:2d}: {formatar_inteiro(decisao.nos_visitados):>11s} nós  {formatar_tempo(decisao.tempo):>10s}")
                if decisao.nos_visitados == nos_anterior:
                    medidas.fim[(alg, pos)] = nivel - 1
                    print(f"  {nome:9s} já enxerga o fim da partida no nível {nivel - 1}: subir o nível não muda nada.")
                    break
                if decisao.tempo > limite_s:
                    medidas.passou.add((alg, pos))
                    print(f"  {nome:9s} passou do limite de {formatar_tempo(limite_s)} no nível {nivel}.")
                    break
                nos_anterior = decisao.nos_visitados
    return medidas


# =============================================================================
#  ESTIMATIVAS
# =============================================================================

def fator_de_crescimento(serie):
    """Quanto o tempo é multiplicado a cada nível: média geométrica do nível 5 até o último medido (ou None)."""
    niveis = sorted(serie)
    if len(niveis) < 2:
        return None
    ultimo = niveis[-1]
    base = 5 if 5 in serie and ultimo - 5 >= 2 else niveis[0]
    if base == ultimo or serie[base] <= 0:
        return None
    return (serie[ultimo] / serie[base]) ** (1 / (ultimo - base))


def ramificacao_efetiva(nos_visitados, nivel):
    """
    Fator de ramificação efetiva b* (aula 4): o fator de uma árvore uniforme de profundidade d com o mesmo número
    de nós, isto é, N + 1 = 1 + b* + (b*)² + ... + (b*)^d. A contagem do programa já inclui a raiz, então
    nos_visitados = N + 1. Resolvido por bisseção.
    """
    if nivel < 1 or nos_visitados <= nivel + 1:
        return 1.0
    baixo, alto = 1.0, float(nos_visitados)
    for _ in range(100):
        meio = (baixo + alto) / 2
        if sum(meio ** i for i in range(nivel + 1)) < nos_visitados:
            baixo = meio
        else:
            alto = meio
    return (baixo + alto) / 2


def tempo_em(medidas, alg, pos, nivel):
    """(segundos, estimado?) de uma posição num nível, ou None se não der para estimar."""
    serie = medidas.tempos[(alg, pos)]
    if nivel in serie:
        return serie[nivel], False
    if not serie:
        return None
    ultimo = max(serie)
    if (alg, pos) in medidas.fim:
        return serie[ultimo], True  # a busca já vai até o fim da partida: o tempo não cresce mais
    fator = fator_de_crescimento(serie)
    if fator is None:
        return None
    return serie[ultimo] * fator ** (nivel - ultimo), True


def valores_do_nivel(medidas, alg, nivel):
    """(média, mais rápida, mais lenta) das três posições, cada uma como (segundos, estimado?), ou None."""
    valores = [tempo_em(medidas, alg, pos, nivel) for pos in POSICOES]
    if any(valor is None for valor in valores):
        return None
    media = (sum(t for t, _ in valores) / len(valores), any(estimado for _, estimado in valores))
    return media, min(valores), max(valores)


def linhas_da_tabela(medidas):
    """[(nível, {alg: (média, mais rápida, mais lenta) ou None}), ...] até as duas IAs passarem de 8 h na jogada mais lenta."""
    linhas, parou = [], set()
    for nivel in range(1, NIVEL_MAXIMO + 1):
        celulas = {}
        for alg in ALGORITMOS:
            celulas[alg] = None if alg in parou else valores_do_nivel(medidas, alg, nivel)
            if celulas[alg] is None or celulas[alg][2][0] > LIMITE_INEXEQUIVEL_S:
                parou.add(alg)  # o primeiro nível acima de 8 h entra na tabela; os seguintes não
        if all(celula is None for celula in celulas.values()):
            break
        linhas.append((nivel, celulas))
        if len(parou) == len(ALGORITMOS):
            break
    return linhas


def mais_lentas(medidas, alg):
    """{nível: (segundos, estimado?)} da jogada mais lenta, até passar de 8 h."""
    lentas = {}
    for nivel in range(1, NIVEL_MAXIMO + 1):
        valores = valores_do_nivel(medidas, alg, nivel)
        if valores is None:
            break
        lentas[nivel] = valores[2]
        if valores[2][0] > LIMITE_INEXEQUIVEL_S:
            break
    return lentas


# =============================================================================
#  FORMATAÇÃO
# =============================================================================

def formatar_duracao(segundos):
    """Tempo com a unidade que fica mais fácil de ler: ms, s, min, h, dias ou anos."""
    if segundos < 1:
        return f"{segundos * 1000:.1f} ms".replace(".", ",")
    if segundos < 60:
        return f"{segundos:.2f} s".replace(".", ",")
    if segundos < 3600:
        return f"{segundos / 60:.1f} min".replace(".", ",")
    if segundos < 48 * 3600:
        return f"{segundos / 3600:.1f} h".replace(".", ",")
    if segundos < 365 * 86400:
        return f"{segundos / 86400:.0f} dias"
    return f"{segundos / (365 * 86400):.1f} anos".replace(".", ",")


def faixa(segundos):
    if segundos <= 1:
        return "jogável"
    if segundos <= 10:
        return "aceitável"
    if segundos <= LIMITE_INVIAVEL_S:
        return "lento"
    return "inviável" if segundos <= LIMITE_INEXEQUIVEL_S else "inexequível"


def celula(valor):
    """Valor medido no formato do resto do relatório; valor estimado com * no fim."""
    segundos, estimado = valor
    return formatar_duracao(segundos) + "*" if estimado else formatar_tempo(segundos)


def virgula(numero, casas=2):
    return f"{numero:.{casas}f}".replace(".", ",")


def lista_de_niveis(niveis):
    """[1, 2, 3, 7] -> '1 a 3 e 7'."""
    grupos, inicio = [], None
    for i, nivel in enumerate(niveis):
        if inicio is None:
            inicio = nivel
        if i == len(niveis) - 1 or niveis[i + 1] != nivel + 1:
            grupos.append(str(inicio) if inicio == nivel else f"{inicio} a {nivel}")
            inicio = None
    return grupos[0] if len(grupos) == 1 else ", ".join(grupos[:-1]) + " e " + grupos[-1]


def periodo(inicio, fim):
    """'4 de novembro de 2026, das 21:43 às 00:40 do dia 5' (o dia do fim só aparece quando é outro)."""
    texto = f"{inicio.day} de {MESES[inicio.month - 1]} de {inicio.year}, das {inicio:%H:%M} às {fim:%H:%M}"
    return texto if fim.date() == inicio.date() else f"{texto} do dia {fim.day}"


def tabela_texto(cabecalho, linhas):
    larguras = [max(len(str(c)) for c in coluna) for coluna in zip(cabecalho, *linhas)]
    def formatar(linha):
        return " | ".join(str(c).ljust(largura) for c, largura in zip(linha, larguras)).rstrip()
    return [formatar(cabecalho), "-+-".join("-" * largura for largura in larguras)] + [formatar(l) for l in linhas]


# =============================================================================
#  RESULTADO PARA O RELATÓRIO
# =============================================================================
# O resultado é uma lista de blocos. Os mesmos blocos viram o texto (resultado_testes.txt) e a planilha
# (resultado_testes.csv):
#   ("titulo", texto) | ("campo", rótulo, valor) | ("linha", texto) | ("item", texto) | ("vazio",)
#   ("tabela", cabeçalho, linhas)                        aparece igual nos dois
#   ("tabela", cabeçalho, linhas, cab_csv, linhas_csv)   na planilha usa números em vez de texto formatado
#   ("so_csv", título, cabeçalho, linhas)                só na planilha (números para fazer gráficos)

def segundos_csv(segundos):
    """Número com vírgula decimal: o Excel em português lê como número."""
    return f"{segundos:.6f}".replace(".", ",")


def montar_resultado(medidas, posicoes, limite_s, inicio, fim):
    mm, ab = ALGORITMOS
    nome = {alg: NOMES_TIPO[alg] for alg in ALGORITMOS}
    blocos = []

    # Cabeçalho: o que vai na linha "Data e máquina" e na linha "Posições" do relatório
    data = periodo(inicio, fim)
    maquina = f"{nome_do_sistema()}, {nome_do_processador()}, Python {platform.python_version()}"
    textos_posicoes = []
    for i, pos in enumerate(POSICOES):
        numero, motor = posicoes[pos]
        jogadas = len(motor.gerar_jogadas_possiveis())
        textos_posicoes.append(f"{pos} (jogada {numero}, {jogadas} jogadas possíveis)" if i == 0 else f"{pos} (jogada {numero}, {jogadas})")
    blocos += [("titulo", "DIÁRIO DE TESTES: MINIMAX E ALFA-BETA"), ("vazio",),
               ("campo", "Data e máquina", f"{data}; {maquina}"),
               ("campo", "Posições", "três momentos da mesma partida (36 tropas, semente 123), sempre no começo de um turno "
                                     f"do J1: {textos_posicoes[0]}, {textos_posicoes[1]} e {textos_posicoes[2]}"),
               ("campo", "Limite por jogada", f"{formatar_tempo(limite_s)}. Os níveis acima do limite não foram executados, "
                                              "só estimados."),
               ("vazio",)]

    # 1. Amostra dos testes: a jogada do início nos níveis pares, com os dois algoritmos
    amostra = [teste for teste in medidas.registro if teste[1] == "início" and teste[3] % 2 == 0]
    blocos += [("titulo", "1. AMOSTRA DOS TESTES"), ("vazio",),
               ("linha", f"{len(amostra)} dos {len(medidas.registro)} testes: a jogada do início, nos níveis pares, "
                         "com os dois algoritmos (é a posição mais cara, a que define os limites de viabilidade)."),
               ("vazio",),
               ("tabela", ["Hora", "Algoritmo", "Nível", "Nós visitados", "Tempo", "Faixa"],
                [[hora, alg, str(nivel), formatar_inteiro(nos), formatar_tempo(t), faixa(t)]
                 for hora, _, alg, nivel, nos, t in amostra]),
               ("vazio",)]

    # 2. Tabela do tempo médio
    linhas = linhas_da_tabela(medidas)
    colunas = ("tempo médio", "mais rápida", "mais lenta")
    cabecalho = ["Nível"] + [f"{nome[alg]}: {coluna}" for alg in ALGORITMOS for coluna in colunas]
    cab_segundos = ["Nível"] + [texto for alg in ALGORITMOS
                                for texto in [f"{nome[alg]}: {coluna} (s)" for coluna in colunas] + [f"{nome[alg]}: estimado"]]
    corpo, corpo_segundos = [], []
    for nivel, celulas in linhas:
        linha, linha_s = [str(nivel)], [nivel]
        for alg in ALGORITMOS:
            if celulas[alg]:
                linha += [celula(v) for v in celulas[alg]]
                linha_s += [segundos_csv(t) for t, _ in celulas[alg]] + ["sim" if any(e for _, e in celulas[alg]) else "não"]
            else:
                linha += ["—"] * 3
                linha_s += [""] * 4
        corpo.append(linha)
        corpo_segundos.append(linha_s)
    blocos += [("titulo", "2. TEMPO MÉDIO POR ALGORITMO E NÍVEL"), ("vazio",), ("tabela", cabecalho, corpo), ("vazio",),
               ("linha", "* Tempo estimado: esses testes não foram executados, apenas estimados.")]
    for alg in ALGORITMOS:
        ultimo_nivel = max((nivel for nivel, celulas in linhas if celulas[alg]), default=None)
        if ultimo_nivel is not None and ultimo_nivel < linhas[-1][0]:
            blocos.append(("linha", f"— Acima do nível {ultimo_nivel}, a jogada mais lenta do {nome[alg]} passaria de 8 horas "
                                    "(inexequível), por isso esses níveis não foram estimados."))

    fatores = {alg: {pos: fator_de_crescimento(medidas.tempos[(alg, pos)]) for pos in ("início", "meio")} for alg in ALGORITMOS}
    ultimos_inicio = {alg: max(medidas.tempos[(alg, "início")], default=0) for alg in ALGORITMOS}
    partes, paradas = [], []
    for alg in ALGORITMOS:
        f_ini, f_meio = fatores[alg]["início"], fatores[alg]["meio"]
        partes.append(f"{virgula(f_ini) if f_ini else '?'} no início e {virgula(f_meio) if f_meio else '?'} no meio para o {nome[alg]}")
        if (alg, "início") in medidas.passou:
            paradas.append(f"passou do limite no nível {ultimos_inicio[alg]} do {nome[alg]}")
        else:
            paradas.append(f"foi medida até o nível {ultimos_inicio[alg]} no {nome[alg]}")
    blocos += [("vazio",),
               ("linha", f"Para o texto da estimativa: a jogada do início {paradas[0]} e {paradas[1]}. "
                         f"Fatores de crescimento por nível (do nível 5 em diante): {partes[0]}, {partes[1]}."),
               ("vazio",),
               ("so_csv", "Mesma tabela em segundos (números para fazer gráficos)", cab_segundos, corpo_segundos)]

    # 3. Limites de viabilidade (pela jogada mais lenta)
    lentas = {alg: mais_lentas(medidas, alg) for alg in ALGORITMOS}
    cab_limites = ["Algoritmo"] + [rotulo for _, rotulo in FAIXAS] + ["Inviável (primeiro nível acima de 60 s)",
                                                                      "Inexequível (primeiro nível acima de 8 h)"]
    corpo_limites, maior_por_faixa = [], {}
    for alg in ALGORITMOS:
        linha = [nome[alg]]
        for teto, _ in FAIXAS:
            dentro = [n for n, (t, _) in lentas[alg].items() if t <= teto]
            maior_por_faixa[(alg, teto)] = max(dentro) if dentro else None
            linha.append(f"nível {max(dentro)} ({celula(lentas[alg][max(dentro)])})" if dentro else "—")
        for teto in (LIMITE_INVIAVEL_S, LIMITE_INEXEQUIVEL_S):
            acima = next((n for n, (t, _) in lentas[alg].items() if t > teto), None)
            linha.append(f"nível {acima} ({celula(lentas[alg][acima])})" if acima else "—")
        corpo_limites.append(linha)
    blocos += [("titulo", "3. LIMITES DE VIABILIDADE (pela jogada mais lenta)"), ("vazio",),
               ("tabela", cab_limites, corpo_limites), ("vazio",)]

    # 4. Fator de ramificação efetiva b* na jogada do início (aula 4)
    cab_b = ["Nível"] + [texto for alg in ALGORITMOS for texto in (f"{nome[alg]}: nós visitados", f"{nome[alg]}: b*")]
    niveis_b = sorted(set(n for alg in ALGORITMOS for n in medidas.nos[(alg, "início")]))
    corpo_b, corpo_b_csv, b_inicio = [], [], {}
    for n in niveis_b:
        linha, linha_csv = [str(n)], [n]
        for alg in ALGORITMOS:
            nos = medidas.nos[(alg, "início")].get(n)
            if nos is None:
                linha += ["—", "—"]
                linha_csv += ["", ""]
            else:
                b_inicio[(alg, n)] = ramificacao_efetiva(nos, n)
                linha += [formatar_inteiro(nos), virgula(b_inicio[(alg, n)])]
                linha_csv += [nos, virgula(b_inicio[(alg, n)])]
        corpo_b.append(linha)
        corpo_b_csv.append(linha_csv)
    blocos += [("titulo", "4. FATOR DE RAMIFICAÇÃO EFETIVA b* (jogada do início, aula 4)"), ("vazio",),
               ("tabela", cab_b, corpo_b, cab_b, corpo_b_csv), ("vazio",),
               ("linha", "b* resolve N + 1 = 1 + b* + (b*)² + ... + (b*)^d, com d = nível e N + 1 = nós visitados "
                         "(a contagem já inclui a raiz). Os nós visitados não dependem da máquina."), ("vazio",)]

    # 5. Números que aparecem no texto do relatório
    blocos += [("titulo", "5. NÚMEROS PARA O TEXTO DO RELATÓRIO"), ("vazio",)]
    v60 = {alg: maior_por_faixa[(alg, 60.0)] for alg in ALGORITMOS}
    blocos.append(("item", f"Objetivo: com até 60 s por jogada, o Minimax é viável até o nível {v60[mm]} e o Alfa-Beta até o "
                           f"nível {v60[ab]}, contando a jogada mais cara da partida."))

    completos = [n for n in range(1, NIVEL_MAXIMO + 1)
                 if all(n in medidas.tempos[(alg, pos)] for alg in ALGORITMOS for pos in POSICOES)]
    if completos:
        n = max(completos)
        media = {alg: sum(medidas.tempos[(alg, pos)][n] for pos in POSICOES) / 3 for alg in ALGORITMOS}
        reducao = (1 - media[ab] / media[mm]) * 100 if media[mm] > 0 else 0
        blocos.append(("item", f"Tempo médio: no nível {n}, o Minimax leva em média {formatar_tempo(media[mm])} por jogada e o "
                               f"Alfa-Beta, {formatar_tempo(media[ab])}: a poda reduz o tempo médio em {reducao:.0f}%."))

    for alg in ALGORITMOS:
        niveis = [n for n in range(1, NIVEL_MAXIMO + 1) if all(n in medidas.tempos[(alg, pos)] for pos in POSICOES)]
        if not niveis:
            continue
        lenta = {n: max(POSICOES, key=lambda pos: medidas.tempos[(alg, pos)][n]) for n in niveis}
        rapida = {n: min(POSICOES, key=lambda pos: medidas.tempos[(alg, pos)][n]) for n in niveis}
        textos = []
        for rotulo, escolha in (("mais lenta", lenta), ("mais rápida", rapida)):
            comum = max(POSICOES, key=lambda pos: list(escolha.values()).count(pos))
            excecoes = [n for n in niveis if escolha[n] != comum]
            texto = f"{rotulo}: {comum}"
            if excecoes:
                grupos = []
                for pos in POSICOES:
                    grupo = [n for n in excecoes if escolha[n] == pos]
                    if grupo:
                        grupos.append(f"{'níveis' if len(grupo) > 1 else 'nível'} {lista_de_niveis(grupo)} ({pos})")
                texto += ", exceto " + "; ".join(grupos)
            else:
                texto += " em todos os níveis"
            textos.append(texto)
        blocos.append(("item", f"{nome[alg]} (níveis {lista_de_niveis(niveis)}, com as três posições medidas): "
                               f"{textos[0]}; {textos[1]}."))

    diferencas = [maior_por_faixa[(ab, teto)] - maior_por_faixa[(mm, teto)] for teto, _ in FAIXAS
                  if maior_por_faixa[(ab, teto)] is not None and maior_por_faixa[(mm, teto)] is not None]
    if diferencas:
        blocos.append(("item", f"Limites: pela jogada mais lenta, o Alfa-Beta vai de {min(diferencas)} a {max(diferencas)} "
                               "níveis além do Minimax em cada faixa de tempo."))
    if fatores[mm]["início"] and fatores[ab]["início"]:
        blocos.append(("item", f"Crescimento: cada nível a mais multiplica o tempo da jogada do início por cerca de "
                               f"{virgula(fatores[mm]['início'], 1)} no Minimax e {virgula(fatores[ab]['início'], 1)} no Alfa-Beta."))

    comuns_b = [n for n in niveis_b if all((alg, n) in b_inicio for alg in ALGORITMOS)]
    if comuns_b:
        n = max(comuns_b)
        blocos.append(("item", f"Ramificação efetiva (início): no nível {n}, b* = {virgula(b_inicio[(mm, n)])} no Minimax e "
                               f"{virgula(b_inicio[(ab, n)])} no Alfa-Beta; quanto mais perto de 1, menos nós a busca expande."))

    meio = []
    for alg in ALGORITMOS:
        serie = medidas.tempos[(alg, "meio")]
        dentro = [n for n, t in serie.items() if t <= LIMITE_INVIAVEL_S]
        if dentro:
            pelo_menos = "" if any(t > LIMITE_INVIAVEL_S for t in serie.values()) else "pelo menos "
            meio.append(f"{pelo_menos}o nível {max(dentro)} ({nome[alg]})")
    if len(meio) == 2:
        blocos.append(("item", f"Meio da partida: o limite de 60 s sobe para {meio[0]} e {meio[1]}."))

    final = []
    for alg in ALGORITMOS:
        serie = medidas.tempos[(alg, "final")]
        if (alg, "final") in medidas.fim:
            n = medidas.fim[(alg, "final")]
            final.append(f"o {nome[alg]} vê o fim da partida no nível {n} ({formatar_tempo(serie[n])})")
        elif serie:
            final.append(f"o {nome[alg]} ainda não via o fim da partida no nível {max(serie)}")
    if final:
        blocos.append(("item", f"Final da partida: {' e '.join(final)}."))

    # 6. Registro de cada teste executado (para conferir; não precisa ir para o relatório)
    blocos += [("vazio",), ("titulo", "6. REGISTRO DOS TESTES EXECUTADOS (para conferir)"), ("vazio",),
               ("tabela", ["Hora", "Posição", "Algoritmo", "Nível", "Nós visitados", "Tempo"],
                [[hora, pos, alg, str(nivel), formatar_inteiro(nos), formatar_tempo(t)]
                 for hora, pos, alg, nivel, nos, t in medidas.registro],
                ["Hora", "Posição", "Algoritmo", "Nível", "Nós visitados", "Tempo (s)"],
                [[hora, pos, alg, nivel, nos, segundos_csv(t)] for hora, pos, alg, nivel, nos, t in medidas.registro])]
    return blocos


def para_texto(blocos):
    saida = []
    for bloco in blocos:
        tipo = bloco[0]
        if tipo in ("titulo", "linha"):
            saida.append(bloco[1])
        elif tipo == "item":
            saida.append("- " + bloco[1])
        elif tipo == "campo":
            saida.append(f"{bloco[1]}: {bloco[2]}")
        elif tipo == "vazio":
            saida.append("")
        elif tipo == "tabela":
            saida += tabela_texto(bloco[1], bloco[2])
    return "\n".join(saida)  # os blocos "so_csv" ficam só na planilha


def gravar_csv(blocos, arquivo):
    """Planilha no padrão do Excel em português: separador ';', vírgula decimal e acentos (UTF-8 com BOM)."""
    with open(arquivo, "w", newline="", encoding="utf-8-sig") as saida:
        escritor = csv.writer(saida, delimiter=";")
        for bloco in blocos:
            tipo = bloco[0]
            if tipo in ("titulo", "linha", "item"):  # item sem o "- " do texto: o Excel leria como fórmula
                escritor.writerow([bloco[1]])
            elif tipo == "campo":
                escritor.writerow([bloco[1], bloco[2]])
            elif tipo == "vazio":
                escritor.writerow([])
            elif tipo == "tabela":
                cabecalho, linhas = (bloco[3], bloco[4]) if len(bloco) > 3 else (bloco[1], bloco[2])
                escritor.writerow(cabecalho)
                escritor.writerows(linhas)
            elif tipo == "so_csv":
                escritor.writerow([bloco[1]])
                escritor.writerow(bloco[2])
                escritor.writerows(bloco[3])
                escritor.writerow([])


def salvar(escrever, arquivo):
    """Grava o arquivo; se ele estiver aberto e travado (o Excel trava a planilha), grava com outro nome."""
    try:
        escrever(arquivo)
        return arquivo
    except PermissionError:
        base, extensao = arquivo.rsplit(".", 1)
        alternativo = f"{base}_{datetime.now():%Y-%m-%d_%H%M%S}.{extensao}"
        try:
            escrever(alternativo)
            return alternativo
        except OSError:
            return None
    except OSError:
        return None


def gravar_resultado(blocos, arquivo_texto, arquivo_csv):
    """Mostra o resultado na tela e grava o texto e a planilha."""
    texto = para_texto(blocos)
    print("\n" + "=" * 80 + "\n" + texto + "\n")

    def escrever_texto(arquivo):
        with open(arquivo, "w", encoding="utf-8-sig") as saida:
            saida.write(texto + "\n")

    def escrever_planilha(arquivo):
        gravar_csv(blocos, arquivo)

    for escrever, arquivo, descricao in ((escrever_texto, arquivo_texto, "Texto salvo em"),
                                         (escrever_planilha, arquivo_csv, "Planilha salva em")):
        salvo = salvar(escrever, arquivo)
        print(f"{descricao} {salvo}" if salvo else f"[AVISO] Não foi possível salvar {arquivo}.")


def ler_limite():
    if "--limite" in sys.argv:
        try:
            return float(sys.argv[sys.argv.index("--limite") + 1].replace(",", "."))
        except (IndexError, ValueError):
            print("Uso: python diario_testes.py --limite 60")
            sys.exit(1)
    texto = input(f"Limite de tempo por jogada, em segundos (Enter = {LIMITE_PADRAO_S:g}): ").strip().replace(",", ".")
    try:
        return float(texto) if texto else LIMITE_PADRAO_S
    except ValueError:
        return LIMITE_PADRAO_S


def main():
    limite = ler_limite()
    print(f"\n=== DIÁRIO DE TESTES: limite de {formatar_tempo(limite)} por jogada ===")
    print(f"Máquina: {nome_do_sistema()}, {nome_do_processador()}, Python {platform.python_version()}")
    print("Com 60 s de limite a bateria leva uns 10 a 20 minutos. Ctrl+C pula o teste em andamento.")
    inicio = datetime.now()
    posicoes, _ = posicoes_de_teste()
    medidas = medir(posicoes, limite)
    fim = datetime.now()

    gravar_resultado(montar_resultado(medidas, posicoes, limite, inicio, fim), ARQUIVO_RESULTADO, ARQUIVO_CSV)


# =============================================================================
#  TESTE AVULSO: um algoritmo, um nível, uma posição (ou as três)
# =============================================================================

def anotar_avulso(linha):
    """Acrescenta uma linha ao testes_avulsos.csv (cria o arquivo com o cabeçalho se ele não existir)."""
    cabecalho = ["Data e hora", "Máquina", "Posição", "Algoritmo", "Nível", "Nós visitados", "Tempo (s)", "Tempo", "b*"]

    def escrever(arquivo):
        novo = not os.path.exists(arquivo)
        with open(arquivo, "a", newline="", encoding="utf-8-sig" if novo else "utf-8") as saida:
            escritor = csv.writer(saida, delimiter=";")
            if novo:
                escritor.writerow(cabecalho)
            escritor.writerow(linha)

    return salvar(escrever, ARQUIVO_AVULSOS)


def teste_avulso(texto_algoritmo, texto_nivel, texto_posicao="início"):
    algoritmos = {"minimax": TipoJogador.MINIMAX, "alfabeta": TipoJogador.ALFA_BETA, "alfa-beta": TipoJogador.ALFA_BETA}
    posicoes_validas = {"inicio": "início", "início": "início", "meio": "meio", "final": "final", "todas": "todas"}
    tipo = algoritmos.get(texto_algoritmo.lower())
    posicao = posicoes_validas.get(texto_posicao.lower())
    if tipo is None or posicao is None or not texto_nivel.isdigit() or int(texto_nivel) < 1:
        print("Uso: python diario_testes.py --teste <minimax|alfabeta> <nível> [início|meio|final|todas]")
        sys.exit(1)
    nivel = int(texto_nivel)
    maquina = f"{nome_do_sistema()}, {nome_do_processador()}, Python {platform.python_version()}"
    print(f"Máquina: {maquina}. Ctrl+C cancela.")
    posicoes, _ = posicoes_de_teste()
    for pos in (POSICOES if posicao == "todas" else (posicao,)):
        numero, motor = posicoes[pos]
        print(f"\n{NOMES_TIPO[tipo]} nível {nivel} na posição {pos} (jogada {numero})...")
        try:
            decisao = escolher_jogada(motor, tipo, nivel)
        except KeyboardInterrupt:
            print("Teste cancelado (Ctrl+C): nada foi anotado.")
            return
        b = ramificacao_efetiva(decisao.nos_visitados, nivel)
        print(f"  {formatar_inteiro(decisao.nos_visitados)} nós visitados | tempo: {formatar_tempo(decisao.tempo)} | "
              f"b* = {virgula(b)} | faixa: {faixa(decisao.tempo)}")
        arquivo = anotar_avulso([datetime.now().strftime("%d/%m/%Y %H:%M:%S"), maquina, pos, NOMES_TIPO[tipo], nivel,
                                 decisao.nos_visitados, segundos_csv(decisao.tempo), formatar_tempo(decisao.tempo), virgula(b)])
        print(f"  Anotado em {arquivo}" if arquivo else f"  [AVISO] Não foi possível anotar em {ARQUIVO_AVULSOS}.")


# =============================================================================
#  PARTIDAS IA x IA: partidas completas, com o placar final
# =============================================================================

class Partida:
    """Uma partida completa entre duas IAs: quem jogou, o placar final e o tempo de busca de cada jogada."""
    def __init__(self, semente, tipos, niveis):
        self.semente = semente
        self.tipos = tipos            # {1: algoritmo do J1, 2: algoritmo do J2}
        self.niveis = niveis          # {1: nível do J1, 2: nível do J2}
        self.tempos = {1: [], 2: []}  # segundos de busca de cada jogada, por jogador
        self.jogadas = []             # a chave de cada jogada, na ordem (duas partidas iguais têm a mesma lista)
        self.placar = {1: 0, 2: 0}    # pontos de cada jogador na auditoria final
        self.hora = ""                # hora em que a partida terminou

    def vencedor(self):
        """1 ou 2 (quem fez mais pontos); 0 se empatou."""
        if self.placar[1] == self.placar[2]:
            return 0
        return 1 if self.placar[1] > self.placar[2] else 2

    def busca(self, jogador=None):
        """Segundos de busca de um jogador na partida inteira (sem o jogador: dos dois juntos)."""
        if jogador is None:
            return sum(self.tempos[1]) + sum(self.tempos[2])
        return sum(self.tempos[jogador])

    def mais_lenta(self):
        return max(self.tempos[1] + self.tempos[2])

    def texto_placar(self):
        return f"{self.placar[1]} x {self.placar[2]}"

    def texto_vencedor(self):
        return "empate" if self.vencedor() == 0 else f"J{self.vencedor()}"

    def mesmo_nivel(self):
        return self.tipos[1] == self.tipos[2] and self.niveis[1] == self.niveis[2]


def jogar_partida(semente, tipos, niveis, mostrar_andamento=False):
    """
    Joga uma partida inteira entre duas IAs, da primeira jogada até as tropas acabarem.
    O placar final é o da auditoria dos castelos (num estado final, o placar projetado é o placar real).
    :param tipos: {1: algoritmo do J1, 2: algoritmo do J2}.
    :param niveis: {1: nível do J1, 2: nível do J2}.
    :param mostrar_andamento: Com True, escreve um ponto na tela a cada 5 jogadas.
    """
    partida = Partida(semente, tipos, niveis)
    motor = LogicaJogo(TROPAS_PARTIDAS, seed=semente)
    while motor.gerar_jogadas_possiveis():
        jogador = motor.id_jogador_atual
        decisao = escolher_jogada(motor, tipos[jogador], niveis[jogador])
        partida.tempos[jogador].append(decisao.tempo)
        partida.jogadas.append(decisao.jogada.chave)
        motor.aplicar_jogada(decisao.jogada)
        if mostrar_andamento and len(partida.jogadas) % 5 == 0:
            print(".", end="", flush=True)
    partida.placar[1], partida.placar[2] = motor.placar_projetado()
    partida.hora = datetime.now().strftime("%H:%M:%S")
    return partida


def lista_de_partidas(niveis, sementes):
    """
    As partidas a jogar, como (semente, tipos, níveis), da mais rápida para a mais demorada:
      - Alfa-Beta contra Alfa-Beta em todas as combinações de níveis (cada nível joga como J1 e como J2), em cada semente;
      - Minimax contra Minimax com níveis iguais, só na primeira semente e até o nível NIVEL_MAXIMO_MINIMAX.
    """
    mm, ab = ALGORITMOS
    partidas = [(semente, {1: ab, 2: ab}, {1: nivel_j1, 2: nivel_j2})
                for semente in sementes for nivel_j1 in niveis for nivel_j2 in niveis]
    partidas += [(sementes[0], {1: mm, 2: mm}, {1: nivel, 2: nivel}) for nivel in niveis if nivel <= NIVEL_MAXIMO_MINIMAX]

    def custo(partida):
        semente, tipos, niveis_da_partida = partida
        return sum(CRESCIMENTO[tipos[jogador]] ** niveis_da_partida[jogador] for jogador in (1, 2)), semente

    return sorted(partidas, key=custo)


def rodar_partidas(previstas, a_cada_partida=None):
    """
    Joga as partidas previstas, na ordem, e devolve as que terminaram.
    Ctrl+C interrompe a partida em andamento: dá para pular só ela ou finalizar com as que já terminaram.
    :param a_cada_partida: Função chamada depois de cada partida, com a lista das que já terminaram.
    """
    terminadas = []
    casas = len(str(len(previstas)))
    for numero, (semente, tipos, niveis) in enumerate(previstas, start=1):
        nomes = [f"J{jogador} {NOMES_TIPO[tipos[jogador]]} {niveis[jogador]}" for jogador in (1, 2)]
        print(f"[{numero:>{casas}}/{len(previstas)}] semente {semente}: {nomes[0]} x {nomes[1]} ", end="", flush=True)
        try:
            partida = jogar_partida(semente, tipos, niveis, mostrar_andamento=True)
        except KeyboardInterrupt:
            try:
                resposta = input("\n  Partida interrompida (Ctrl+C). Enter pula só esta partida; f e Enter finaliza "
                                 "com as que já terminaram: ")
            except (KeyboardInterrupt, EOFError):
                resposta = "f"
            if resposta.strip().lower().startswith("f"):
                break
            continue
        terminadas.append(partida)
        resultado = "empate" if partida.vencedor() == 0 else f"J{partida.vencedor()} venceu"
        print(f" {partida.texto_placar()} ({resultado}) | {len(partida.jogadas)} jogadas | "
              f"{formatar_duracao(partida.busca())} de busca")
        if a_cada_partida:
            a_cada_partida(terminadas)
    return terminadas


def lado_do_nivel_maior(partida):
    return 1 if partida.niveis[1] > partida.niveis[2] else 2


def resumo_do_nivel_maior(partidas):
    """(partidas, vitórias do nível maior, empates, vitórias do nível menor, saldo médio de pontos do nível maior)."""
    saldos = []
    for partida in partidas:
        maior = lado_do_nivel_maior(partida)
        saldos.append(partida.placar[maior] - partida.placar[3 - maior])
    return (len(saldos), sum(saldo > 0 for saldo in saldos), sum(saldo == 0 for saldo in saldos),
            sum(saldo < 0 for saldo in saldos), sum(saldos) / len(saldos))


def media_ou_nada(valores):
    """A média da lista, ou None se ela estiver vazia ou não existir."""
    return sum(valores) / len(valores) if valores else None


def texto_das_sementes(sementes):
    """'semente 123', 'sementes 123 e 124' ou 'sementes 123 a 127'."""
    if len(sementes) == 1:
        return f"semente {sementes[0]}"
    return f"sementes {sementes[0]} {'e' if len(sementes) == 2 else 'a'} {sementes[-1]}"


def texto_saldo(saldo):
    """'+14,2', '-3,5' ou '0,0'."""
    texto = virgula(abs(saldo), 1)
    if texto == "0,0":
        return texto
    return ("+" if saldo > 0 else "-") + texto


def montar_resultado_partidas(partidas, previstas, niveis, sementes, inicio, fim):
    """Os blocos do resultado das partidas, no mesmo formato de blocos do resultado dos testes de tempo."""
    mm, ab = ALGORITMOS
    alfa_beta = {(p.semente, p.niveis[1], p.niveis[2]): p for p in partidas if p.tipos[1] == ab and p.tipos[2] == ab}
    minimax = {p.niveis[1]: p for p in partidas if p.tipos[1] == mm and p.tipos[2] == mm}
    diferentes = [p for p in alfa_beta.values() if p.niveis[1] != p.niveis[2]]
    comparadas = [(nivel, minimax[nivel], alfa_beta[(minimax[nivel].semente, nivel, nivel)])
                  for nivel in sorted(minimax) if (minimax[nivel].semente, nivel, nivel) in alfa_beta]
    numero = iter(range(1, 10))  # numera as seções que existirem
    blocos = []

    # Cabeçalho: o que vai nas linhas "Data e máquina" e "Partidas" do relatório
    maquina = f"{nome_do_sistema()}, {nome_do_processador()}, Python {platform.python_version()}"
    texto_niveis = ("o nível " if len(niveis) == 1 else "os níveis ") + lista_de_niveis(niveis)
    texto_sementes = ("na " if len(sementes) == 1 else "nas ") + texto_das_sementes(sementes)
    descricao = (f"partidas completas entre duas IAs, com {TROPAS_PARTIDAS} tropas. Alfa-Beta contra Alfa-Beta com {texto_niveis}, "
                 f"em todas as combinações (cada nível joga como J1 e como J2), {texto_sementes}. Cada semente muda o mapa, "
                 "o mercado e os dados.")
    if minimax:
        descricao += f" Minimax contra Minimax com níveis iguais, só na semente {sementes[0]}, para comparar com o Alfa-Beta."
    blocos += [("titulo", "DIÁRIO DE TESTES: PARTIDAS IA x IA"), ("vazio",),
               ("campo", "Data e máquina", f"{periodo(inicio, fim)}; {maquina}"),
               ("campo", "Partidas", descricao),
               ("campo", "Placar final", "pontos do J1 x pontos do J2 na auditoria dos castelos, depois que as duas IAs "
                                         "colocam todas as tropas. Vence quem faz mais pontos.")]
    if len(partidas) < previstas:
        blocos.append(("campo", "Partidas jogadas", f"{len(partidas)} das {previstas} previstas (as outras não foram jogadas até o fim)."))
    blocos.append(("vazio",))

    # Placar final de cada partida: uma tabela por semente, com o nível do J1 na linha e o do J2 na coluna
    blocos += [("titulo", f"{next(numero)}. PLACAR FINAL DAS PARTIDAS (Alfa-Beta contra Alfa-Beta)"), ("vazio",),
               ("linha", "Cada célula é o placar final J1 x J2 de uma partida: o nível do J1 está na linha e o do J2, na coluna."),
               ("vazio",)]
    for semente in sementes:
        if any(chave[0] == semente for chave in alfa_beta):
            linhas = [[f"J1: nível {nivel_j1}"]
                      + [alfa_beta[(semente, nivel_j1, nivel_j2)].texto_placar() if (semente, nivel_j1, nivel_j2) in alfa_beta else "—"
                         for nivel_j2 in niveis] for nivel_j1 in niveis]
            blocos += [("tabela", [f"Semente {semente}"] + [f"J2: nível {nivel}" for nivel in niveis], linhas), ("vazio",)]

    # Nível maior contra nível menor: as partidas entre níveis diferentes, somando as sementes
    if diferentes:
        cabecalho = ["Confronto", "Partidas", "Vitórias do nível maior", "Empates", "Vitórias do nível menor",
                     "Saldo médio do nível maior"]
        grupos = [(f"nível {menor} x nível {maior}", [p for p in diferentes if {p.niveis[1], p.niveis[2]} == {menor, maior}])
                  for i, menor in enumerate(niveis) for maior in niveis[i + 1:]]
        grupos.append(("Total", diferentes))
        linhas, linhas_csv = [], []
        for rotulo, grupo in grupos:
            if grupo:
                quantas, vitorias, empates, derrotas, saldo = resumo_do_nivel_maior(grupo)
                linhas.append([rotulo, str(quantas), str(vitorias), str(empates), str(derrotas), texto_saldo(saldo)])
                linhas_csv.append([rotulo, quantas, vitorias, empates, derrotas, virgula(saldo, 1)])
        blocos += [("titulo", f"{next(numero)}. NÍVEL MAIOR CONTRA NÍVEL MENOR"), ("vazio",),
                   ("linha", "As partidas entre níveis diferentes, somando as sementes. Saldo = pontos do nível maior menos "
                             "pontos do nível menor."),
                   ("vazio",), ("tabela", cabecalho, linhas, cabecalho, linhas_csv), ("vazio",)]

    # Minimax e Alfa-Beta na partida inteira: no mesmo nível, as jogadas e o placar têm que ser os mesmos
    if minimax:
        cabecalho = ["Nível", "Placar final: Minimax", "Placar final: Alfa-Beta", "Mesmas jogadas", "Jogadas",
                     "Busca da partida: Minimax", "Busca da partida: Alfa-Beta", "Redução"]
        cabecalho_csv = cabecalho[:5] + ["Busca da partida: Minimax (s)", "Busca da partida: Alfa-Beta (s)", "Redução (%)"]
        linhas, linhas_csv = [], []
        for nivel in sorted(minimax):
            do_minimax = minimax[nivel]
            do_alfa_beta = alfa_beta.get((do_minimax.semente, nivel, nivel))
            inicio_da_linha = [str(nivel), do_minimax.texto_placar()]
            if do_alfa_beta is None:
                linhas.append(inicio_da_linha + ["—", "—", str(len(do_minimax.jogadas)), formatar_duracao(do_minimax.busca()), "—", "—"])
                linhas_csv.append(inicio_da_linha + ["", "", len(do_minimax.jogadas), segundos_csv(do_minimax.busca()), "", ""])
                continue
            reducao = (1 - do_alfa_beta.busca() / do_minimax.busca()) * 100
            meio_da_linha = [do_alfa_beta.texto_placar(), "sim" if do_minimax.jogadas == do_alfa_beta.jogadas else "não"]
            linhas.append(inicio_da_linha + meio_da_linha + [str(len(do_minimax.jogadas)), formatar_duracao(do_minimax.busca()),
                                                             formatar_duracao(do_alfa_beta.busca()), f"{reducao:.0f}%"])
            linhas_csv.append(inicio_da_linha + meio_da_linha + [len(do_minimax.jogadas), segundos_csv(do_minimax.busca()),
                                                                 segundos_csv(do_alfa_beta.busca()), virgula(reducao, 1)])
        blocos += [("titulo", f"{next(numero)}. MINIMAX E ALFA-BETA NA PARTIDA INTEIRA (níveis iguais, semente {sementes[0]})"),
                   ("vazio",),
                   ("linha", "Minimax contra Minimax e Alfa-Beta contra Alfa-Beta, no mesmo nível e na mesma semente. "
                             "Busca da partida = soma do tempo de busca de todas as jogadas das duas IAs."),
                   ("vazio",), ("tabela", cabecalho, linhas, cabecalho_csv, linhas_csv), ("vazio",)]

    # Tempo de busca por jogada, juntando todas as partidas em que o algoritmo e o nível jogaram
    tempos, primeiras, participou, com_niveis_iguais = {}, {}, {}, {}
    for p in partidas:
        for jogador in (1, 2):
            tempos.setdefault((p.tipos[jogador], p.niveis[jogador]), []).extend(p.tempos[jogador])
        primeiras.setdefault((p.tipos[1], p.niveis[1]), []).append(p.tempos[1][0])  # o J1 sempre começa
        for chave in {(p.tipos[1], p.niveis[1]), (p.tipos[2], p.niveis[2])}:
            participou[chave] = participou.get(chave, 0) + 1
        if p.mesmo_nivel():
            com_niveis_iguais.setdefault((p.tipos[1], p.niveis[1]), []).append(p.busca())
    cabecalho = ["Algoritmo", "Nível", "Partidas", "Jogadas", "Tempo médio por jogada", "Primeira jogada da partida",
                 "Jogada mais lenta", "Faixa da mais lenta", "Partida inteira com níveis iguais"]
    cabecalho_csv = cabecalho[:4] + ["Tempo médio por jogada (s)", "Primeira jogada da partida (s)", "Jogada mais lenta (s)",
                                     "Faixa da mais lenta", "Partida inteira com níveis iguais (s)"]
    linhas, linhas_csv = [], []
    for alg, nivel in sorted(tempos, key=lambda chave: (ALGORITMOS.index(chave[0]), chave[1])):
        serie = tempos[(alg, nivel)]
        media = sum(serie) / len(serie)
        primeira = media_ou_nada(primeiras.get((alg, nivel)))
        partida_inteira = media_ou_nada(com_niveis_iguais.get((alg, nivel)))
        linhas.append([NOMES_TIPO[alg], str(nivel), str(participou[(alg, nivel)]), formatar_inteiro(len(serie)),
                       formatar_tempo(media), "—" if primeira is None else formatar_tempo(primeira),
                       formatar_tempo(max(serie)), faixa(max(serie)),
                       "—" if partida_inteira is None else formatar_duracao(partida_inteira)])
        linhas_csv.append([NOMES_TIPO[alg], nivel, participou[(alg, nivel)], len(serie), segundos_csv(media),
                           "" if primeira is None else segundos_csv(primeira), segundos_csv(max(serie)), faixa(max(serie)),
                           "" if partida_inteira is None else segundos_csv(partida_inteira)])
    blocos += [("titulo", f"{next(numero)}. TEMPO DE BUSCA POR JOGADA NAS PARTIDAS"), ("vazio",),
               ("linha", "Todas as jogadas de cada algoritmo e nível, em todas as partidas. Primeira jogada da partida = tempo "
                         "médio da primeira jogada (quando esse algoritmo e nível é o J1). Partida inteira com níveis iguais = "
                         "tempo médio de busca de uma partida em que as duas IAs usam esse algoritmo e esse nível."),
               ("vazio",), ("tabela", cabecalho, linhas, cabecalho_csv, linhas_csv), ("vazio",)]

    # Números que aparecem no texto do relatório
    blocos += [("titulo", f"{next(numero)}. NÚMEROS PARA O TEXTO DO RELATÓRIO"), ("vazio",)]
    quantas_de_cada = f"{len(alfa_beta)} de Alfa-Beta contra Alfa-Beta"
    if minimax:
        quantas_de_cada += f" e {len(minimax)} de Minimax contra Minimax"
    blocos.append(("item", f"Partidas: {len(partidas)} partidas completas entre IAs ({quantas_de_cada}), com "
                           f"{formatar_inteiro(sum(len(p.jogadas) for p in partidas))} jogadas e "
                           f"{formatar_duracao(sum(p.busca() for p in partidas))} de busca no total."))
    if diferentes:
        quantas, vitorias, empates, _, saldo = resumo_do_nivel_maior(diferentes)
        por_lado = []
        for lado in (1, 2):
            grupo = [p for p in diferentes if lado_do_nivel_maior(p) == lado]
            if grupo:
                por_lado.append(f"{resumo_do_nivel_maior(grupo)[1]} das {len(grupo)} em que era o J{lado}")
        blocos.append(("item", f"Nível maior contra nível menor: o nível maior venceu {vitorias} das {quantas} partidas "
                               f"({vitorias / quantas * 100:.0f}%){f' e empatou {empates}' if empates else ''}, com saldo médio "
                               f"de {texto_saldo(saldo)} pontos. Venceu {' e '.join(por_lado)}."))
        extremos = [p for p in diferentes if {p.niveis[1], p.niveis[2]} == {niveis[0], niveis[-1]}]
        if extremos and len(niveis) > 2:
            quantas, vitorias, _, _, saldo = resumo_do_nivel_maior(extremos)
            blocos.append(("item", f"Maior diferença de nível: contra o nível {niveis[0]}, o nível {niveis[-1]} venceu {vitorias} "
                                   f"das {quantas} partidas, com saldo médio de {texto_saldo(saldo)} pontos."))
    iguais = [p for p in alfa_beta.values() if p.mesmo_nivel()]
    if iguais:
        vitorias = {resultado: sum(p.vencedor() == resultado for p in iguais) for resultado in (0, 1, 2)}
        blocos.append(("item", f"Níveis iguais: nas {len(iguais)} partidas em que as duas IAs têm o mesmo nível, o J1 venceu "
                               f"{vitorias[1]} e o J2, {vitorias[2]}{f' ({vitorias[0]} empates)' if vitorias[0] else ''}."))
    if comparadas:
        diferem = [nivel for nivel, do_minimax, do_alfa_beta in comparadas
                   if do_minimax.jogadas != do_alfa_beta.jogadas or do_minimax.placar != do_alfa_beta.placar]
        nos_niveis = ("no nível " if len(comparadas) == 1 else "nos níveis ") + lista_de_niveis([nivel for nivel, _, _ in comparadas])
        if diferem:
            texto = (f"ATENÇÃO: {nos_niveis}, o Minimax e o Alfa-Beta deveriam jogar a mesma partida, mas as jogadas ou o placar "
                     f"foram diferentes ({'nível' if len(diferem) == 1 else 'níveis'} {lista_de_niveis(diferem)}).")
        else:
            texto = (f"{nos_niveis}, o Minimax e o Alfa-Beta jogaram exatamente a mesma partida (as mesmas jogadas e o mesmo "
                     "placar final).")
        nivel, do_minimax, do_alfa_beta = comparadas[-1]
        reducao = (1 - do_alfa_beta.busca() / do_minimax.busca()) * 100
        blocos.append(("item", f"Minimax e Alfa-Beta: {texto} No nível {nivel}, a partida inteira levou "
                               f"{formatar_duracao(do_minimax.busca())} de busca com o Minimax e "
                               f"{formatar_duracao(do_alfa_beta.busca())} com o Alfa-Beta (redução de {reducao:.0f}%)."))
    if (ab, niveis[-1]) in tempos:
        serie = tempos[(ab, niveis[-1])]
        texto = f"Tempo: no nível {niveis[-1]}, o Alfa-Beta levou em média {formatar_tempo(sum(serie) / len(serie))} por jogada"
        primeira = media_ou_nada(primeiras.get((ab, niveis[-1])))
        if primeira:
            texto += (f"; a primeira jogada da partida levou em média {formatar_tempo(primeira)} e a jogada mais lenta, "
                      f"{formatar_tempo(max(serie))} ({virgula(max(serie) / primeira, 1)} vezes mais)")
        else:
            texto += f", e a jogada mais lenta levou {formatar_tempo(max(serie))}"
        partida_inteira = media_ou_nada(com_niveis_iguais.get((ab, niveis[-1])))
        if partida_inteira:
            texto += f". Uma partida inteira entre duas IAs desse nível levou em média {formatar_duracao(partida_inteira)} de busca"
        blocos.append(("item", texto + "."))
    referencia = alfa_beta.get((PRIMEIRA_SEMENTE, 2, 2))
    if referencia:
        blocos.append(("item", "Partida dos testes de tempo: a partida de onde saem as três posições de teste (Alfa-Beta 2 contra "
                               f"Alfa-Beta 2, semente {PRIMEIRA_SEMENTE}) terminou {referencia.texto_placar()}, em "
                               f"{len(referencia.jogadas)} jogadas."))

    # Registro de cada partida (para conferir; não precisa ir para o relatório)
    def nome_da_ia(p, jogador):
        return f"{NOMES_TIPO[p.tipos[jogador]]} {p.niveis[jogador]}"

    blocos += [("vazio",), ("titulo", f"{next(numero)}. REGISTRO DAS PARTIDAS (para conferir)"), ("vazio",),
               ("tabela", ["Hora", "Semente", "J1", "J2", "Placar final", "Vencedor", "Jogadas", "Busca do J1", "Busca do J2",
                           "Jogada mais lenta"],
                [[p.hora, str(p.semente), nome_da_ia(p, 1), nome_da_ia(p, 2), p.texto_placar(), p.texto_vencedor(),
                  str(len(p.jogadas)), formatar_duracao(p.busca(1)), formatar_duracao(p.busca(2)), formatar_tempo(p.mais_lenta())]
                 for p in partidas],
                ["Hora", "Semente", "J1: algoritmo", "J1: nível", "J2: algoritmo", "J2: nível", "Pontos do J1", "Pontos do J2",
                 "Vencedor", "Jogadas", "Busca do J1 (s)", "Busca do J2 (s)", "Jogada mais lenta (s)"],
                [[p.hora, p.semente, NOMES_TIPO[p.tipos[1]], p.niveis[1], NOMES_TIPO[p.tipos[2]], p.niveis[2], p.placar[1],
                  p.placar[2], p.texto_vencedor(), len(p.jogadas), segundos_csv(p.busca(1)), segundos_csv(p.busca(2)),
                  segundos_csv(p.mais_lenta())] for p in partidas])]
    return blocos


def ler_niveis_e_sementes():
    """(níveis das IAs, número de sementes): vêm da linha de comando ou, se não vierem, de duas perguntas."""
    uso = "Uso: python diario_testes.py --partidas [níveis] [--sementes N]   (ex.: --partidas 2 4 6 8 10 --sementes 3)"
    textos = []
    for argumento in sys.argv[sys.argv.index("--partidas") + 1:]:
        if not argumento.isdigit():
            break
        textos.append(argumento)
    quantidade = None
    if "--sementes" in sys.argv:
        try:
            quantidade = int(sys.argv[sys.argv.index("--sementes") + 1])
        except (IndexError, ValueError):
            quantidade = 0
    if not textos and quantidade is None:
        padrao = " ".join(str(nivel) for nivel in NIVEIS_PARTIDAS)
        textos = input(f"Níveis das IAs, separados por espaço (Enter = {padrao}): ").replace(",", " ").split()
        resposta = input(f"Quantas sementes, ou seja, partidas diferentes por confronto (Enter = {SEMENTES_PARTIDAS}): ").strip()
        quantidade = int(resposta) if resposta.isdigit() else SEMENTES_PARTIDAS
    if quantidade is None:
        quantidade = SEMENTES_PARTIDAS
    try:
        niveis = sorted(set(int(texto) for texto in textos)) if textos else list(NIVEIS_PARTIDAS)
    except ValueError:
        niveis = []
    if not niveis or niveis[0] < 1 or niveis[-1] > NIVEL_MAXIMO or quantidade < 1:
        print(uso)
        print(f"Os níveis vão de 1 a {NIVEL_MAXIMO} e é preciso pelo menos uma semente.")
        sys.exit(1)
    return niveis, quantidade


def main_partidas():
    niveis, quantidade = ler_niveis_e_sementes()
    sementes = list(range(PRIMEIRA_SEMENTE, PRIMEIRA_SEMENTE + quantidade))
    previstas = lista_de_partidas(niveis, sementes)
    print(f"\n=== PARTIDAS IA x IA: {'nível' if len(niveis) == 1 else 'níveis'} {lista_de_niveis(niveis)}, "
          f"{texto_das_sementes(sementes)} ===")
    print(f"Máquina: {nome_do_sistema()}, {nome_do_processador()}, Python {platform.python_version()}")
    print(f"São {len(previstas)} partidas completas, da mais rápida para a mais demorada.")
    print("Tempo aproximado: até o nível 8, uns 2 minutos por semente e mais uns 10 minutos das partidas do Minimax;")
    print("com o nível 10, mais uns 15 minutos por semente; com o nível 12, mais umas 2 horas por semente.")
    print("Ctrl+C interrompe a partida em andamento: dá para pular só ela ou finalizar com as que já terminaram.\n")
    inicio = datetime.now()

    def salvar_parcial(terminadas):
        """Deixa o texto do que já terminou no arquivo, para nada se perder se o computador desligar no meio."""
        try:
            blocos = montar_resultado_partidas(terminadas, len(previstas), niveis, sementes, inicio, datetime.now())
            with open(ARQUIVO_PARTIDAS, "w", encoding="utf-8-sig") as saida:
                saida.write(para_texto(blocos) + "\n")
        except OSError:
            pass

    partidas = rodar_partidas(previstas, salvar_parcial)
    if not partidas:
        print("\nNenhuma partida terminou: nada foi salvo.")
        return
    blocos = montar_resultado_partidas(partidas, len(previstas), niveis, sementes, inicio, datetime.now())
    gravar_resultado(blocos, ARQUIVO_PARTIDAS, ARQUIVO_PARTIDAS_CSV)


if __name__ == "__main__":
    if "--partidas" in sys.argv:
        main_partidas()
    elif "--teste" in sys.argv:
        argumentos = sys.argv[sys.argv.index("--teste") + 1:]
        if len(argumentos) < 2:
            print("Uso: python diario_testes.py --teste <minimax|alfabeta> <nível> [início|meio|final|todas]")
            sys.exit(1)
        teste_avulso(*argumentos[:3])
    else:
        main()
