"""
Simulador em modo texto do Rumble Nation.

Usa exatamente o mesmo motor (logica_jogo.py) e o mesmo NavegadorDeArvore (arvore.py)
da interface Pygame: serve para jogar, inspecionar a árvore e viajar no tempo pelo terminal.
"""
import random
import sys
from logica_jogo import LogicaJogo
from arvore import NavegadorDeArvore, ARQUIVO_ARVORE

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace") # Evita erro com '→' e '·' em consoles antigos

ARQUIVO_JSON = ARQUIVO_ARVORE + ".json"


def imprimir_tabuleiro(navegador):
    """Desenha a situação atual do jogo em formato de texto."""
    estado = navegador.motor.obter_estado()
    no = navegador.no_atual
    print(f"\n{'=' * 64}")
    print(f" VEZ DO JOGADOR {estado['jogador_atual']} | nó {no.id_no[:6]} | nível {no.profundidade} ".center(64, '='))
    print(f"{'=' * 64}")
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
    print(f"{'=' * 64}\n")


def jogar_terminal(navegador):
    """O laço principal: mostra o nível abaixo do nó atual, executa a escolha e salva a árvore."""
    while True:
        jogadas = navegador.jogadas_disponiveis()
        if not jogadas:
            finalizar_partida(navegador)
            return

        imprimir_tabuleiro(navegador)
        print(f"Jogadas possíveis ({len(navegador.no_atual.filhos)} filhos deste nó já gravados na árvore):")
        for i, jogada in enumerate(jogadas):
            texto = jogada.rotulo.replace("\n", " ")
            print(f"  [{i}] {texto}")
        print("  [v] Voltar uma jogada    [s] Salvar e voltar ao menu")

        escolha = input("\nDigite a opção: ").strip().lower()
        if escolha == "s":
            salvar(navegador)
            return
        if escolha == "v":
            if navegador.voltar() is None:
                print("\n[!] Você já está no início da partida.")
            continue

        try:
            jogada = jogadas[int(escolha)]
        except (ValueError, IndexError):
            print("\n[ERRO] Opção inválida.")
            continue

        navegador.jogar(jogada)
        try:
            navegador.arvore.salvar_json(ARQUIVO_JSON) # Salva a cada jogada para você nunca perder a árvore
        except OSError as erro:
            print(f"\n[AVISO] Não foi possível salvar {ARQUIVO_JSON}: {erro}")


def finalizar_partida(navegador):
    """Mostra a auditoria final (numa cópia do motor) e salva a árvore final."""
    imprimir_tabuleiro(navegador)
    print("*** TODAS AS TROPAS FORAM ALOCADAS: AUDITORIA DOS CASTELOS ***")
    auditoria = navegador.motor.clonar()
    terminou = False
    while not terminou:
        terminou, mensagem = auditoria.resolver_batalha_atual()
        print("  " + mensagem)
    placar = auditoria.pontuacao_parcial
    print(f"\nPlacar final: J1 {placar[1]} x {placar[2]} J2")
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


def carregar_terminal():
    """Abre o JSON, lista os estados da árvore e permite a viagem no tempo."""
    try:
        navegador = NavegadorDeArvore.carregar(ARQUIVO_JSON, LogicaJogo)
    except FileNotFoundError:
        print(f"\n[ERRO] Nenhum arquivo '{ARQUIVO_JSON}' encontrado.")
        return
    except ValueError as erro:
        print(f"\n[ERRO] {erro}")
        return

    arvore = navegador.arvore
    caminho = set(arvore.caminho)
    print("\n--- ESTADOS SALVOS NA ÁRVORE ---")
    for no in sorted(arvore.nos.values(), key=lambda n: n.ordem):
        if no.id_no == arvore.id_atual: marca = ">>"
        elif no.id_no in caminho: marca = "* "
        elif no.expandido: marca = "+ "
        else: marca = "  "
        titulo = no.titulo.replace("\n", " ")
        print(f"{marca} {no.id_no[:6]} | nível {no.profundidade:>2} | {titulo}")
    print("Legenda: >> estado atual | * caminho da partida | + jogada desfeita | sem marca = previsão")

    escolha = input("\nDigite o ID (6 caracteres) do estado de onde quer continuar (Enter = estado atual salvo): ").strip()
    if escolha:
        encontrados = [id_no for id_no in arvore.nos if id_no.startswith(escolha)]
        if len(encontrados) != 1:
            print("\n[ERRO] ID não encontrado na árvore de estados.")
            return
        navegador.ir_para(encontrados[0])
        print(f"\n[SUCESSO] Máquina do tempo ativada! Retornando ao estado {escolha}.")

    jogar_terminal(navegador)


def partida_automatica(tropas=18, semente_partida=123, chance_de_voltar=0.15, semente_escolhas=None):
    """Joga sozinho (escolhas aleatórias, às vezes voltando no tempo) e salva a árvore final."""
    escolhas = random.Random(semente_escolhas)
    navegador = NavegadorDeArvore(LogicaJogo(tropas, seed=semente_partida))
    jogadas_feitas = 0
    while navegador.jogadas_disponiveis():
        if navegador.no_atual.profundidade > 2 and escolhas.random() < chance_de_voltar:
            navegador.voltar()
            continue
        navegador.jogar(escolhas.choice(navegador.jogadas_disponiveis()))
        jogadas_feitas += 1
    print(f"\nPartida automática concluída: {jogadas_feitas} jogadas feitas (algumas desfeitas no caminho).")
    finalizar_partida(navegador)


def menu_principal():
    while True:
        print("\n=== RUMBLE NATION: SIMULADOR DA ÁRVORE DE ESTADOS ===")
        print("1. Nova partida (18 tropas)")
        print("2. Nova partida (36 tropas)")
        print(f"3. Carregar '{ARQUIVO_JSON}' e continuar de qualquer estado")
        print("4. Partida automática de demonstração (com voltas no tempo)")
        print("5. Sair do Programa")

        escolha = input("\nEscolha uma opção: ").strip()

        if escolha == '1':
            jogar_terminal(NavegadorDeArvore(LogicaJogo(18)))
        elif escolha == '2':
            jogar_terminal(NavegadorDeArvore(LogicaJogo(36)))
        elif escolha == '3':
            carregar_terminal()
        elif escolha == '4':
            partida_automatica()
        elif escolha == '5':
            print("Encerrando simulador...")
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    menu_principal()
