"""
Inteligência Artificial do Rumble Nation (etapa 3): Minimax com antecipação limitada e poda alfa-beta.

    heuristica(motor)        avaliação de um estado: pontos do J1 menos pontos do J2 no placar
                             projetado (o que a auditoria daria se a partida terminasse agora)
    minimax(...)             busca com antecipação limitada, sem poda
    alfa_beta(...)           a mesma busca, com poda alfa-beta
    escolher_jogada(...)     ponto de entrada: decide a jogada do jogador da vez
    TemposMedios             tempo médio de execução da busca por algoritmo e nível

Convenções:
  - O J1 é sempre o MAX e o J2 é sempre o MIN (valor positivo = bom para o J1).
  - Um turno pode ter várias jogadas seguidas do mesmo jogador (rerrolar, usar carta, alocar).
    Por isso quem maximiza ou minimiza em cada nó é o jogador da vez daquele estado, e não a
    profundidade ser par ou ímpar.
  - O nível de antecipação é o número de jogadas olhadas à frente, ou seja, níveis da árvore de
    estados (as mesmas arestas da etapa 2).
  - Os dados são determinísticos (vêm da semente), então a IA enxerga os dados futuros: a árvore
    de busca é exatamente a árvore de estados do jogo.

Este arquivo usa só o motor (LogicaJogo). Não conhece a interface nem a árvore de estados.
"""
import time

from logica_jogo import LogicaJogo

INFINITO = float("inf")


class TipoJogador:
    """Quem controla cada jogador da partida."""
    HUMANO = "humano"
    MINIMAX = "minimax"
    ALFA_BETA = "alfabeta"


NOMES_TIPO = {
    TipoJogador.HUMANO: "Humano",
    TipoJogador.MINIMAX: "Minimax",
    TipoJogador.ALFA_BETA: "Alfa-Beta",
}


class Participante:
    def __init__(self, tipo=TipoJogador.HUMANO, nivel=3):
        """
        Configuração de um jogador da partida.
        :param tipo: Um dos valores de TipoJogador.
        :param nivel: Nível de antecipação (quantas jogadas a IA olha à frente). Ignorado para humanos.
        """
        self.tipo = tipo
        self.nivel = nivel

    def e_ia(self):
        return self.tipo != TipoJogador.HUMANO

    def nome(self):
        if self.e_ia():
            return f"{NOMES_TIPO[self.tipo]} (nível {self.nivel})"
        return NOMES_TIPO[self.tipo]


# =============================================================================
#  HEURÍSTICA
# =============================================================================

def heuristica(motor):
    """
    Função de avaliação de um estado, do ponto de vista do J1 (MAX).
    É a diferença de pontos no placar projetado: quanto o J1 faria a mais que o J2 se a partida
    fosse auditada agora. Num estado final (todas as tropas no tabuleiro) é o resultado exato.
    """
    pontos_j1, pontos_j2 = motor.placar_projetado()
    return pontos_j1 - pontos_j2


def avaliar_estado(estado):
    """A mesma heurística, a partir do dicionário de estado (é o que cada nó da árvore guarda)."""
    return heuristica(LogicaJogo(estado=estado))


# =============================================================================
#  BUSCA
# =============================================================================

class Contadores:
    """Estatísticas de uma busca."""
    def __init__(self):
        self.nos_visitados = 0  # estados alcançados pela busca (a raiz e cada chamada recursiva)
        self.avaliacoes = 0     # quantas vezes a heurística foi calculada (folhas e estados finais)
        self.cortes = 0         # podas alfa-beta (laços interrompidos antes de ver todos os irmãos)


def _filho(motor, jogada):
    """Estado resultante da jogada, numa cópia independente (o motor recebido não muda)."""
    copia = motor.clonar()
    copia.aplicar_jogada(jogada, conferir=False)  # a jogada veio do gerar_jogadas_possiveis() do pai
    return copia


def minimax(motor, nivel, contadores):
    """
    Valor minimax do estado, olhando 'nivel' jogadas à frente.
    No nível 0, ou num estado final, o valor é a heurística.
    """
    contadores.nos_visitados += 1
    jogadas = motor.gerar_jogadas_possiveis()
    if nivel == 0 or not jogadas:
        contadores.avaliacoes += 1
        return heuristica(motor)

    if motor.id_jogador_atual == 1:  # MAX
        melhor = -INFINITO
        for jogada in jogadas:
            valor = minimax(_filho(motor, jogada), nivel - 1, contadores)
            if valor > melhor:
                melhor = valor
        return melhor

    melhor = INFINITO  # MIN
    for jogada in jogadas:
        valor = minimax(_filho(motor, jogada), nivel - 1, contadores)
        if valor < melhor:
            melhor = valor
    return melhor


def alfa_beta(motor, nivel, alfa, beta, contadores):
    """
    O mesmo valor do minimax, sem visitar os ramos que não podem mudar a decisão.
    :param alfa: Melhor valor que o MAX já tem garantido no caminho até este nó.
    :param beta: Melhor valor que o MIN já tem garantido no caminho até este nó.
    Quando alfa >= beta, o jogador de cima nunca deixaria a partida chegar a este nó, então os
    irmãos que faltam são podados.
    """
    contadores.nos_visitados += 1
    jogadas = motor.gerar_jogadas_possiveis()
    if nivel == 0 or not jogadas:
        contadores.avaliacoes += 1
        return heuristica(motor)

    if motor.id_jogador_atual == 1:  # MAX
        melhor = -INFINITO
        for jogada in jogadas:
            valor = alfa_beta(_filho(motor, jogada), nivel - 1, alfa, beta, contadores)
            if valor > melhor:
                melhor = valor
            if melhor > alfa:
                alfa = melhor
            if alfa >= beta:
                contadores.cortes += 1
                break
        return melhor

    melhor = INFINITO  # MIN
    for jogada in jogadas:
        valor = alfa_beta(_filho(motor, jogada), nivel - 1, alfa, beta, contadores)
        if valor < melhor:
            melhor = valor
        if melhor < beta:
            beta = melhor
        if alfa >= beta:
            contadores.cortes += 1
            break
    return melhor


# =============================================================================
#  DECISÃO (raiz da busca)
# =============================================================================

class Decisao:
    def __init__(self, jogador, tipo, nivel, jogada, valor, valores, contadores, tempo):
        """
        Resultado de uma busca feita no estado atual da partida.
        :param valores: [(jogada, valor, exato), ...] para cada jogada possível da raiz. Com poda,
                        'exato' é False quando o ramo foi podado e o número é só um limite: o valor
                        real é menor ou igual (raiz do J1) ou maior ou igual (raiz do J2).
        :param tempo: Segundos gastos na busca.
        """
        self.jogador = jogador
        self.tipo = tipo
        self.nivel = nivel
        self.jogada = jogada
        self.valor = valor
        self.valores = valores
        self.nos_visitados = contadores.nos_visitados
        self.avaliacoes = contadores.avaliacoes
        self.cortes = contadores.cortes
        self.tempo = tempo

    def resumo(self):
        """Uma linha para a interface e o terminal."""
        jogada = self.jogada.rotulo.replace("\n", " ")
        return (f"{jogada} · v = {formatar_valor(self.valor)} · {formatar_inteiro(self.nos_visitados)} nós · "
                f"{formatar_tempo(self.tempo)} ({NOMES_TIPO[self.tipo]} nível {self.nivel})")

    def para_dict(self):
        """Formato da decisão dentro do JSON da árvore (fica no nó onde a IA decidiu)."""
        return {
            "jogador": self.jogador,
            "algoritmo": NOMES_TIPO[self.tipo],
            "nivel": self.nivel,
            "jogada": self.jogada.chave,
            "valor": self.valor,
            "nos_visitados": self.nos_visitados,
            "avaliacoes": self.avaliacoes,
            "cortes": self.cortes,
            "tempo_s": round(self.tempo, 6),
            "valores": [{"jogada": jogada.chave, "valor": valor, "exato": exato}
                        for jogada, valor, exato in self.valores],
        }


def escolher_jogada(motor, tipo, nivel):
    """
    Decide a jogada do jogador da vez com o algoritmo pedido (Minimax ou Alfa-Beta).
    O motor recebido não muda: cada jogada é simulada numa cópia.
    :param tipo: TipoJogador.MINIMAX ou TipoJogador.ALFA_BETA.
    :param nivel: Nível de antecipação (>= 1): quantas jogadas a busca olha à frente.
    :return: Decisao com a jogada escolhida, o valor minimax e as estatísticas da busca.
    """
    if nivel < 1:
        raise ValueError("O nível de antecipação deve ser pelo menos 1.")
    jogadas = motor.gerar_jogadas_possiveis()
    if not jogadas:
        raise ValueError("Não há jogadas possíveis: a partida terminou.")

    inicio = time.perf_counter()
    contadores = Contadores()
    contadores.nos_visitados += 1  # a própria raiz
    maximizando = motor.id_jogador_atual == 1
    alfa, beta = -INFINITO, INFINITO
    melhor_jogada = None
    melhor_valor = -INFINITO if maximizando else INFINITO
    valores = []

    for jogada in jogadas:
        filho = _filho(motor, jogada)
        if tipo == TipoJogador.ALFA_BETA:
            valor = alfa_beta(filho, nivel - 1, alfa, beta, contadores)
            # Fora da janela (alfa, beta) o número devolvido é só um limite do valor real
            exato = valor > alfa if maximizando else valor < beta
        else:
            valor = minimax(filho, nivel - 1, contadores)
            exato = True
        valores.append((jogada, valor, exato))

        # Empate fica com a primeira jogada: assim Minimax e Alfa-Beta escolhem a mesma jogada
        if (maximizando and valor > melhor_valor) or (not maximizando and valor < melhor_valor):
            melhor_jogada, melhor_valor = jogada, valor
        if maximizando and melhor_valor > alfa:
            alfa = melhor_valor
        if not maximizando and melhor_valor < beta:
            beta = melhor_valor

    tempo = time.perf_counter() - inicio
    return Decisao(motor.id_jogador_atual, tipo, nivel, melhor_jogada, melhor_valor, valores, contadores, tempo)


# =============================================================================
#  TEMPO MÉDIO DE EXECUÇÃO (por algoritmo e nível)
# =============================================================================

class TemposMedios:
    """Soma o tempo de busca de cada decisão, separado por algoritmo e nível, enquanto o programa está aberto."""
    def __init__(self):
        self.dados = {}  # (tipo, nivel) -> (jogadas, tempo total em segundos)

    def registrar(self, decisao):
        jogadas, total = self.dados.get((decisao.tipo, decisao.nivel), (0, 0.0))
        self.dados[(decisao.tipo, decisao.nivel)] = (jogadas + 1, total + decisao.tempo)

    def media(self, tipo, nivel):
        """(tempo médio em segundos, número de jogadas), ou None se esse algoritmo e nível ainda não jogaram."""
        if (tipo, nivel) not in self.dados:
            return None
        jogadas, total = self.dados[(tipo, nivel)]
        return total / jogadas, jogadas

    def texto(self, participante):
        """Linha para a tela: 'Alfa-Beta nível 4 · tempo médio 12,3 ms (23 jogadas)'."""
        nome = f"{NOMES_TIPO[participante.tipo]} nível {participante.nivel}"
        media = self.media(participante.tipo, participante.nivel)
        if media is None:
            return f"{nome} · tempo médio: ainda sem jogadas"
        tempo, jogadas = media
        return f"{nome} · tempo médio {formatar_tempo(tempo)} ({jogadas} {'jogada' if jogadas == 1 else 'jogadas'})"

    def tabela(self):
        """A tabela algoritmo | nível | jogadas | tempo médio, em linhas de texto."""
        linhas = [f"{'Algoritmo':<10s} | {'Nível':>5s} | {'Jogadas':>7s} | Tempo médio"]
        for (tipo, nivel) in sorted(self.dados, key=lambda chave: (NOMES_TIPO[chave[0]], chave[1])):
            tempo, jogadas = self.media(tipo, nivel)
            linhas.append(f"{NOMES_TIPO[tipo]:<10s} | {nivel:>5d} | {jogadas:>7d} | {formatar_tempo(tempo)}")
        return linhas


# =============================================================================
#  FORMATAÇÃO
# =============================================================================

def formatar_tempo(segundos):
    """Tempo legível: '850 µs', '12,3 ms' ou '4,56 s'."""
    if segundos < 0.001:
        return f"{segundos * 1e6:.0f} µs"
    if segundos < 1:
        return f"{segundos * 1000:.1f} ms".replace(".", ",")
    return f"{segundos:.2f} s".replace(".", ",")


def formatar_inteiro(numero):
    """Número com separador de milhar: 12345 -> '12.345'."""
    return f"{numero:,}".replace(",", ".")


def formatar_valor(valor):
    """Valor da heurística com sinal: '+5', '-3' e '0' ('?' se o valor não existir)."""
    if valor is None:
        return "?"
    if valor == 0:
        return "0"
    return f"{valor:+}"
