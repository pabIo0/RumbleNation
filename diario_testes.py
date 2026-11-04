"""
Diário de testes da etapa 3: mede o tempo de execução do Minimax e do Alfa-Beta nível a nível, até
descobrir o limite de viabilidade de cada um, e deixa os números prontos para o relatório.

Como os testes funcionam:
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

Rodar:  python diario_testes.py               (pergunta o limite; Enter = 60 s)
        python diario_testes.py --limite 300  (mede níveis mais altos, mas demora bem mais)

Durante um teste, Ctrl+C desiste daquele teste e passa para o próximo algoritmo ou posição.
O resultado aparece na tela e fica salvo em dois arquivos, na pasta de onde o Python foi chamado:
    resultado_testes.txt   texto, para ler e copiar para o relatório
    resultado_testes.csv   planilha para o Excel (separador ';' e vírgula decimal), com uma tabela em segundos para gráficos
"""
import csv
import platform
import sys
from datetime import datetime

from logica_jogo import LogicaJogo
from ia import TipoJogador, NOMES_TIPO, escolher_jogada, formatar_tempo, formatar_inteiro

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")  # Evita erro com 'µ' e '—' em consoles antigos

ARQUIVO_RESULTADO = "resultado_testes.txt"
ARQUIVO_CSV = "resultado_testes.csv"
LIMITE_PADRAO_S = 60.0
FAIXAS = [(1.0, "Jogável (até 1 s)"), (10.0, "Aceitável (até 10 s)"), (60.0, "Lento (até 60 s)")]
LIMITE_INVIAVEL_S = 60.0           # acima disso a jogada é lenta demais para jogar
LIMITE_INEXEQUIVEL_S = 8 * 3600.0  # acima disso nem como teste dá para executar
NIVEL_MAXIMO = 20                  # o mesmo máximo da interface e do simulador
ALGORITMOS = (TipoJogador.MINIMAX, TipoJogador.ALFA_BETA)
POSICOES = ("início", "meio", "final")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro")


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


def posicoes_de_teste(tropas=36, semente=123):
    """
    Três posições fixas da mesma partida (Alfa-Beta nível 2 contra ele mesmo): o início, o meio e o final.
    :return: ({"início": (número da jogada, motor), "meio": ..., "final": ...}, total de jogadas da partida)
    """
    motor = LogicaJogo(tropas, seed=semente)
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
    data = f"{inicio.day} de {MESES[inicio.month - 1]} de {inicio.year}, das {inicio:%H:%M} às {fim:%H:%M}"
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

    blocos = montar_resultado(medidas, posicoes, limite, inicio, fim)
    texto = para_texto(blocos)
    print("\n" + "=" * 80 + "\n" + texto + "\n")

    def escrever_texto(arquivo):
        with open(arquivo, "w", encoding="utf-8-sig") as saida:
            saida.write(texto + "\n")

    def escrever_planilha(arquivo):
        gravar_csv(blocos, arquivo)

    for escrever, arquivo, descricao in ((escrever_texto, ARQUIVO_RESULTADO, "Texto salvo em"),
                                         (escrever_planilha, ARQUIVO_CSV, "Planilha salva em")):
        salvo = salvar(escrever, arquivo)
        print(f"{descricao} {salvo}" if salvo else f"[AVISO] Não foi possível salvar {arquivo}.")


if __name__ == "__main__":
    main()
