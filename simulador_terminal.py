"""
Simulador em modo texto do Rumble Nation (etapa 3).

Usa exatamente o mesmo motor (logica_jogo.py), o mesmo NavegadorDeArvore (arvore.py) e a mesma IA
(ia.py) da interface Pygame. Serve para:
  - jogar com qualquer combinação de Humano, Minimax e Alfa-Beta (inclusive IA x IA);
  - escolher o nível de antecipação de cada IA;
  - carregar uma árvore salva (com a heurística de cada nó) e continuar de qualquer estado;
  - ver, no fim de cada partida, o tempo médio de execução por algoritmo e nível.
"""
import sys

from logica_jogo import LogicaJogo
from arvore import ArvoreDeEstados, NavegadorDeArvore, ARQUIVO_ARVORE
import ia
from ia import TipoJogador, Participante, escolher_jogada, formatar_valor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace") # Evita erro com '→' e '·' em consoles antigos

ARQUIVO_JSON = ARQUIVO_ARVORE + ".json"
NIVEL_MAXIMO = 20
TEMPOS = ia.TemposMedios()  # tempo médio por algoritmo e nível, enquanto o simulador está aberto


# =============================================================================
#  CONFIGURAÇÃO DA PARTIDA
# =============================================================================

def escolher_participante(id_jogador):
    """Pergunta quem controla o jogador (Humano, Minimax ou Alfa-Beta) e, se for IA, o nível."""
    tipos = {"1": TipoJogador.HUMANO, "2": TipoJogador.MINIMAX, "3": TipoJogador.ALFA_BETA}
    while True:
        escolha = input(f"Jogador {id_jogador}: [1] Humano  [2] Minimax  [3] Alfa-Beta  (Enter = Humano): ").strip() or "1"
        if escolha in tipos:
            break
        print("  Opção inválida.")
    participante = Participante(tipos[escolha])
    if participante.e_ia():
        participante.nivel = ler_nivel(ia.NOMES_TIPO[participante.tipo])
    return participante


def ler_nivel(nome, padrao=3):
    while True:
        texto = input(f"  Nível de antecipação do {nome} (1 a {NIVEL_MAXIMO}) [{padrao}]: ").strip()
        if not texto:
            return padrao
        if texto.isdigit() and 1 <= int(texto) <= NIVEL_MAXIMO:
            return int(texto)
        print(f"  Digite um número de 1 a {NIVEL_MAXIMO}.")


def escolher_participantes():
    print("\n--- Quem joga? ---")
    return {1: escolher_participante(1), 2: escolher_participante(2)}


# =============================================================================
#  PARTIDA
# =============================================================================

def imprimir_tabuleiro(navegador, participantes):
    """Desenha a situação atual do jogo em formato de texto."""
    estado = navegador.motor.obter_estado()
    no = navegador.no_atual()
    print(f"\n{'=' * 64}")
    print(f" VEZ DO JOGADOR {estado['jogador_atual']} | nó {no.id_no[:6]} | nível {no.profundidade} ".center(64, '='))
    print(f"{'=' * 64}")
    print(f"J1: {participantes[1].nome()} | J2: {participantes[2].nome()}")
    print(f"Estoque -> J1: {estado['jogadores'][1]['tropas']} tropas | J2: {estado['jogadores'][2]['tropas']} tropas")
    print(f"Dados na mesa: {estado['dados_atuais']} | Rerrolagens: {estado['rerrolagens_disponiveis']}")

    mods = []
    if estado['modificador_castelo']: mods.append(f"castelo {estado['modificador_castelo']:+d}")
    if estado['modificador_tropas']: mods.append(f"tropas {estado['modificador_tropas']:+d}")
    if mods: print(f"Modificadores do turno: {', '.join(mods)}")

    nomes_mercado = ", ".join(carta['nome'] for carta in estado['mercado']) or "vazio"
    situacao = "fechado para você" if estado['mercado_bloqueado'] else "aberto"
    print(f"Mercado: {nomes_mercado} ({situacao})")
    if estado['carta_pendente']:
        print(f">>> Carta ativada: {estado['carta_pendente']['nome']}. Escolha o alvo.")

    print("\nCastelos Ocupados:")
    ocupados = [(id_c, info) for id_c, info in sorted(estado['castelos'].items())
                if info['tropas_j1'] > 0 or info['tropas_j2'] > 0]
    for id_c, info in ocupados:
        print(f"  [Castelo {id_c}] -> J1: {info['tropas_j1']} | J2: {info['tropas_j2']}")
    if not ocupados:
        print("  (Nenhuma tropa no mapa ainda)")

    pontos_j1, pontos_j2 = navegador.motor.placar_projetado()
    print(f"\nSe a partida acabasse agora: J1 {pontos_j1} x {pontos_j2} J2 (heurística h = {formatar_valor(no.heuristica)})")
    print(f"{'=' * 64}\n")


def heuristica_do_filho(navegador, jogada):
    """Heurística guardada no nó para onde a jogada leva (calculada quando o nó foi criado)."""
    id_filho = navegador.no_atual().filhos[jogada.chave]["id"]
    return navegador.arvore.obter_no(id_filho).heuristica


def jogada_da_ia(navegador, participante):
    """A IA da vez decide, a decisão fica guardada no nó atual, o tempo entra na média e a jogada é feita."""
    decisao = escolher_jogada(navegador.motor, participante.tipo, participante.nivel)
    navegador.registrar_decisao(decisao.para_dict())
    TEMPOS.registrar(decisao)
    print(f"J{decisao.jogador} {participante.nome()}: {decisao.resumo()}")
    navegador.jogar(decisao.jogada)


def jogar_terminal(navegador, participantes):
    """
    O laço principal. Na vez de um humano, mostra o nível abaixo do nó atual (com a heurística de cada
    opção); na vez de uma IA, ela decide sozinha. Ctrl+C interrompe uma partida entre IAs.
    """
    aguardar_ia = False  # depois de voltar no tempo, a IA espera um Enter (senão repetiria a jogada na hora)
    try:
        while True:
            jogadas = navegador.jogadas_disponiveis()
            if not jogadas:
                finalizar_partida(navegador)
                return

            participante = participantes[navegador.motor.id_jogador_atual]
            if participante.e_ia() and not aguardar_ia:
                jogada_da_ia(navegador, participante)
                continue

            imprimir_tabuleiro(navegador, participantes)
            if participante.e_ia():
                print(f"Vez da IA (J{navegador.motor.id_jogador_atual}: {participante.nome()}).")
                print("  [Enter] Deixar a IA jogar    [v] Voltar mais uma jogada    [s] Salvar e voltar ao menu")
            else:
                print(f"Jogadas possíveis ({len(navegador.no_atual().filhos)} filhos deste nó já gravados na árvore):")
                for i, jogada in enumerate(jogadas):
                    texto = jogada.rotulo.replace("\n", " ")
                    print(f"  [{i}] {texto:<48s} h = {formatar_valor(heuristica_do_filho(navegador, jogada))}")
                print("  [v] Voltar uma jogada    [s] Salvar e voltar ao menu")

            escolha = input("\nDigite a opção: ").strip().lower()
            if escolha == "s":
                salvar(navegador)
                return
            if escolha == "v":
                if navegador.voltar() is None:
                    print("\n[!] Você já está no início da partida.")
                aguardar_ia = True
                continue
            if participante.e_ia():
                aguardar_ia = escolha != ""
                continue

            try:
                jogada = jogadas[int(escolha)]
            except (ValueError, IndexError):
                print("\n[ERRO] Opção inválida.")
                continue
            navegador.jogar(jogada)
            aguardar_ia = False
            try:
                navegador.arvore.salvar_json(ARQUIVO_JSON) # Salva a cada jogada humana para não perder a árvore
            except OSError as erro:
                print(f"\n[AVISO] Não foi possível salvar {ARQUIVO_JSON}: {erro}")
    except KeyboardInterrupt:
        print("\n\n[!] Partida interrompida.")
        salvar(navegador)


def finalizar_partida(navegador):
    """Mostra a auditoria final (numa cópia do motor), a tabela de tempo médio das IAs e salva a árvore final."""
    print("\n*** TODAS AS TROPAS FORAM ALOCADAS: AUDITORIA DOS CASTELOS ***")
    auditoria = navegador.motor.clonar()
    terminou = False
    while not terminou:
        terminou, mensagem = auditoria.resolver_batalha_atual()
        print("  " + mensagem)
    placar = auditoria.pontuacao_parcial
    print(f"\nPlacar final: J1 {placar[1]} x {placar[2]} J2")
    if TEMPOS.dados:
        print("\nTempo médio de execução (todas as jogadas de IA desde que o simulador abriu):")
        for linha in TEMPOS.tabela():
            print("  " + linha)
    salvar(navegador)


def salvar(navegador):
    try:
        arquivos = navegador.salvar(ARQUIVO_ARVORE)
    except OSError as erro:
        print(f"\n[ERRO] Não foi possível salvar a árvore: {erro}")
        return
    print(f"\n[!] Árvore salva em: {', '.join(arquivos)}")
    problemas = navegador.arvore.validar()
    if problemas:
        print("    [ATENÇÃO] Problemas encontrados:", *problemas, sep="\n      - ")
    else:
        print("    Verificação: OK (nenhum estado repetido, só 1 nível abaixo das jogadas realizadas)")
    estat = navegador.arvore.estatisticas()
    print(f"    {estat['nos']} estados | {estat['estados_alcancados']} alcançados | "
          f"{estat['estados_previstos']} previsões | caminho atual com {estat['jogadas_no_caminho_atual']} jogadas")
    print(f"    {estat['nos_com_heuristica']} nós com heurística | {estat['decisoes_da_ia']} decisões de IA guardadas")


def nova_partida():
    while True:
        tropas = input("\nTropas por jogador: [1] 18 (rápida)  [2] 36 (completa)  (Enter = 18): ").strip() or "1"
        if tropas in ("1", "2"):
            break
        print("Opção inválida.")
    tropas = 18 if tropas == "1" else 36
    participantes = escolher_participantes()
    navegador = NavegadorDeArvore(LogicaJogo(tropas), avaliar=ia.avaliar_estado)
    print(f"\nPartida: J1 {participantes[1].nome()} x J2 {participantes[2].nome()}, {tropas} tropas.")
    jogar_terminal(navegador, participantes)


def carregar_terminal():
    """Abre o JSON (com a heurística de cada nó), lista os estados e permite continuar de qualquer um."""
    arvore = ArvoreDeEstados()
    try:
        arvore.carregar_json(ARQUIVO_JSON)
    except FileNotFoundError:
        print(f"\n[ERRO] Nenhum arquivo '{ARQUIVO_JSON}' encontrado.")
        return
    except (ValueError, KeyError) as erro:
        print(f"\n[ERRO] Não foi possível carregar: {erro}")
        return

    navegador = NavegadorDeArvore(LogicaJogo(estado=arvore.no_atual().estado), arvore, avaliar=ia.avaliar_estado)
    caminho = set(arvore.caminho)
    print("\n--- ESTADOS SALVOS NA ÁRVORE ---")
    for no in sorted(arvore.nos.values(), key=lambda n: n.ordem):
        if no.id_no == arvore.id_atual(): marca = ">>"
        elif no.id_no in caminho: marca = "* "
        elif no.expandido: marca = "+ "
        else: marca = "  "
        titulo = no.titulo.replace("\n", " ")
        linha = f"{marca} {no.id_no[:6]} | nível {no.profundidade:>2} | h = {formatar_valor(no.heuristica):>4s} | {titulo}"
        if no.decisao:
            linha += f"   [{no.decisao['algoritmo']} nível {no.decisao['nivel']}: v = {formatar_valor(no.decisao['valor'])}]"
        print(linha)
    print("Legenda: >> estado atual | * caminho da partida | + jogada desfeita | sem marca = previsão")
    print("         h = heurística guardada no nó | [ ] = decisão de uma IA neste estado")
    if navegador.heuristicas_calculadas:
        print(f"[!] {navegador.heuristicas_calculadas} nós vieram sem heurística (árvore antiga) e foram calculados agora.")
    else:
        print(f"[!] As heurísticas dos {len(arvore.nos)} nós vieram prontas do arquivo (nenhuma foi recalculada).")

    escolha = input("\nDigite o ID (6 caracteres) do estado de onde quer continuar (Enter = estado atual salvo): ").strip()
    if escolha:
        encontrados = [id_no for id_no in arvore.nos if id_no.startswith(escolha)]
        if len(encontrados) != 1:
            print("\n[ERRO] ID não encontrado na árvore de estados.")
            return
        navegador.ir_para(encontrados[0])
        print(f"\n[SUCESSO] Máquina do tempo ativada! Retornando ao estado {escolha}.")

    participantes = escolher_participantes()
    jogar_terminal(navegador, participantes)


def menu_principal():
    while True:
        print("\n=== RUMBLE NATION: MINIMAX E ALFA-BETA (ETAPA 3) ===")
        print("1. Nova partida (escolher os jogadores e os níveis)")
        print(f"2. Carregar '{ARQUIVO_JSON}' e continuar de qualquer estado")
        print("3. Sair do Programa")

        escolha = input("\nEscolha uma opção: ").strip()

        if escolha == '1':
            nova_partida()
        elif escolha == '2':
            carregar_terminal()
        elif escolha == '3':
            print("Encerrando simulador...")
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    menu_principal()
