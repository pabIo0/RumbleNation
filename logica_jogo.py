import random


# =============================================================================
#  JOGADAS: as arestas da Árvore de Estados
# =============================================================================

class TipoJogada:
    """Todos os tipos de ramificação que podem sair de um estado do jogo."""
    ALOCAR = "alocar"        # 2 dados viram o castelo, o 3º vira tropas (encerra o turno)
    RERROLAR = "rerrolar"    # rerrolagem livre do turno
    CARTA = "carta"          # usar (carta imediata) ou ativar (carta com alvo) uma carta do mercado
    ALVO_DADO = "dado"       # escolher o dado alvo da carta +1 / -1 / Inverter já ativada
    MARCHA = "marcha"        # escolher origem -> destino da carta Marchar já ativada
    PASSAR = "passar"        # passar a vez (estoque zerado, ou nenhum castelo válido e sem rerrolagem)


# Classificação das cartas pelo tipo de efeito
CARTAS_IMEDIATAS = ("+2_castelo", "-2_castelo", "+1_reforco")   # efeito aplicado na hora
CARTAS_DE_DADO = ("+1_dado", "-1_dado", "inverter_dado")         # pedem um dado como alvo
CARTA_MARCHA = "marchar"                                         # pede origem e destino

# Escolher 2 dados dentre 3 gera exatamente estas 3 combinações de índices
COMBINACOES_DE_DADOS = ((0, 1), (0, 2), (1, 2))


class Jogada:
    def __init__(self, tipo, jogador, args=(), rotulo=""):
        """
        Uma transição da árvore (aresta pai -> filho).
        :param tipo: Um dos valores de TipoJogada (ex: "alocar").
        :param jogador: Jogador que faz a jogada (1 ou 2).
        :param args: O que muda no jogo, e não o que foi clicado:
                         alocar -> (castelo,)          ex: (7,)
                         carta  -> (efeito,)           ex: ("+2_castelo",)
                         dado   -> (valor_do_dado,)    ex: (5,)
                         marcha -> (origem, destino)   ex: (5, 8)
                         rerrolar / passar -> ()
                     Assim, cliques diferentes que dão o mesmo resultado viram a mesma jogada.
        :param rotulo: Texto mostrado no Graphviz (ex: "[J1] Castelo 7\\n(Dados 3+4) | Tropa: 5").
        :var chave: Nome da aresta na árvore, único entre os irmãos de um nó (ex: "alocar:7").
                    Duas jogadas são a mesma jogada quando têm a mesma chave.
        """
        self.tipo = tipo
        self.jogador = jogador
        self.args = tuple(args)
        self.rotulo = rotulo

        if self.args:
            self.chave = self.tipo + ":" + ",".join(str(arg) for arg in self.args)
        else:
            self.chave = self.tipo

    def para_dict(self):
        """Formato da jogada dentro do JSON da árvore."""
        return {"tipo": self.tipo, "jogador": self.jogador, "args": list(self.args), "rotulo": self.rotulo}


# =============================================================================
#  ENTIDADES DO TABULEIRO
# =============================================================================

class Carta:
    def __init__(self, id_carta, nome, efeito):
        """
        Estrutura básica de uma carta tática.
        :param id_carta: Identificador único numérico da carta.
        :param nome: Nome de exibição (ex: "+2 Castelo").
        :param efeito: String chave (ex: "+2_castelo") usada pelo motor para aplicar a regra correta.
        """
        self.id_carta = id_carta
        self.nome = nome
        self.efeito = efeito

class Jogador:
    def __init__(self, nome, id_jogador, tropas_iniciais):
        """
        Armazena o estado individual de cada competidor.
        :param tropas_iniciais: Quantidade de tropas que o jogador tem no estoque (começa em 18 ou 36).
        :var self.medalhas: Guarda as medalhas de término. Serve como critério de desempate.
        :var self.usou_carta: Booleano que garante a regra de que o jogador só pode usar 1 carta por partida inteira.
        """
        self.nome = nome
        self.id_jogador = id_jogador
        self.tropas = tropas_iniciais
        self.medalhas = 0
        self.usou_carta = False

    def remover_tropas(self, quantidade_tropas):
        """
        Deduz as tropas do estoque do jogador antes de enviá-las ao tabuleiro.
        Retorna True se houver saldo suficiente, e False para bloquear a jogada caso tente gastar mais do que tem.
        """
        if self.tropas >= quantidade_tropas:
            self.tropas -= quantidade_tropas
            return True
        return False

class Castelo:
    def __init__(self, id_castelo, vizinhos, id_local):
        """
        Representa um território (nó) no mapa do jogo.
        :param id_castelo: Número do castelo (2 a 12), que é o valor alvo a ser tirado nos dados.
        :param vizinhos: Lista de IDs dos castelos adjacentes (usado para a carta marcha e para a cascata final).
        :param id_local: O ID fixo da coordenada geográfica na interface (onde ele será desenhado na tela).
        :var self.tropas: Dicionário que rastreia quantas peças cada jogador colocou aqui {1: X, 2: Y}.
        :var self.conquistado: Booleano que muda para True durante a auditoria final após os pontos serem distribuídos.
        """
        self.id_castelo = id_castelo
        self.vizinhos = vizinhos
        self.id_local = id_local
        self.tropas = {1: 0, 2: 0}
        self.conquistado = False

    def adicionar_tropas(self, id_jogador, quantidade_tropas):
        """Soma as tropas recém-alocadas ao total já existente no território."""
        self.tropas[id_jogador] += quantidade_tropas


# =============================================================================
#  MOTOR DO JOGO
# =============================================================================

class LogicaJogo:
    def __init__(self, tropas_iniciais=36, seed=123, estado=None):
        """
        Inicializa o estado global (Environment) da partida.
        :param seed: Semente da partida. A mesma semente gera o mesmo mapa, o mesmo mercado e a mesma
                     sequência de dados. Use seed=None para sortear uma partida diferente a cada execução.
        :param estado: Se for passado, o motor é montado a partir desse estado (vindo da árvore ou do
                       JSON) em vez de começar uma partida nova. Nesse caso nada é sorteado.
        """
        if estado is not None:
            self.carregar_estado(estado)
            return

        if seed is None:
            seed = random.randrange(1, 1_000_000)
        self.semente = seed
        self.seed_atual = seed

        # Gerador LOCAL apenas para a preparação do tabuleiro: não mexe no 'random' global do Python.
        sorteio = random.Random(seed)

        self.tropas_iniciais = tropas_iniciais
        self.jogadores = {
            1: Jogador("Jogador 1", 1, tropas_iniciais),
            2: Jogador("Jogador 2", 2, tropas_iniciais)
        }
        self.id_jogador_atual = 1 # O Jogador 1 sempre começa

        self.castelos = self._inicializar_castelos(sorteio)

        self.dados_atuais = [] # Guarda a última rolagem (3 inteiros, sempre ordenados)
        self.rolagens_realizadas = 0 # Quantas rolagens já aconteceram (torna os dados reproduzíveis)
        self.ordem_termino = [] # Fila que registra quem zerou as tropas primeiro

        # Variáveis de controle para a fase de fim de jogo (Auditoria)
        self.castelo_resolucao_atual = 2 # Começa validando o castelo 2, depois o 3, etc.
        self.pontuacao_parcial = {1: 0, 2: 0}
        self.mensagem_auditoria = "Pronto para iniciar a contagem."

        # Modificadores temporários aplicados pelas cartas e que expiram no fim do turno
        self.modificador_castelo = 0
        self.modificador_tropas = 0
        self.rerrolagens_disponiveis = 1 # Limite de rerrolagens gratuitas por turno

        # Carta com alvo (dados ou Marchar) que foi ativada e está esperando o alvo ser escolhido
        self.carta_pendente = None

        self.mercado_aberto = self._inicializar_mercado(sorteio)

        # A mecânica não depende da interface: o jogo já começa rolando os dados automaticamente
        self.rolar_dados()

    def clonar(self, estado=None):
        """
        Cria um motor totalmente independente (nenhuma lista é compartilhada).
        Sem argumento, copia o estado atual; com um estado, o motor novo já começa nele.
        É assim que a árvore simula jogadas sem mexer na partida de verdade.
        """
        if estado is None:
            estado = self.obter_estado()
        return LogicaJogo(estado=estado)

    def _inicializar_mercado(self, sorteio):
        """
        Cria o deck de 10 cartas e sorteia 3 para ficarem visíveis no mercado.
        A carta de Rerrolar foi removida pois agora é uma mecânica nativa.
        """
        baralho_completo = [
            Carta(2, "+2 Castelo", "+2_castelo"),
            Carta(3, "+2 Castelo", "+2_castelo"),
            Carta(4, "-2 Castelo", "-2_castelo"),
            Carta(5, "-2 Castelo", "-2_castelo"),
            Carta(6, "+1 Reforço", "+1_reforco"),
            Carta(7, "+1 Reforço", "+1_reforco"),
            Carta(8, "+1 Dado", "+1_dado"),
            Carta(9, "-1 Dado", "-1_dado"),
            Carta(10, "Inverter Dado", "inverter_dado"),
            Carta(11, "Marchar", "marchar")
        ]
        return sorteio.sample(baralho_completo, 3)

    def _inicializar_castelos(self, sorteio):
        """
        Mistura os valores numéricos dos castelos e os espalha geograficamente pelo mapa,
        garantindo que as conexões físicas (vizinhos) permaneçam corretas.
        """
        # Matriz fixa: O terreno X é vizinho dos terrenos contidos na lista.
        topologia = {
            0: [1, 2, 3, 8],
            1: [0, 2, 8],
            2: [0, 1, 6],
            3: [0, 8, 9],
            4: [5, 7, 10],
            5: [4, 7, 9],
            6: [2],
            7: [4, 5, 9],
            8: [0, 1, 3, 9],
            9: [3, 5, 7, 8],
            10: [4]
        }

        locais = list(topologia.keys())
        valores = list(range(2, 13))
        sorteio.shuffle(valores) # Embaralha apenas os números alvo

        mapa_valores = {}
        for i in range(len(locais)):
            mapa_valores[locais[i]] = valores[i]

        castelos = {}
        for local in locais:
            valor = mapa_valores[local]
            vizinhos = []
            for vizinho_local in topologia[local]:
                vizinhos.append(mapa_valores[vizinho_local])

            castelos[valor] = Castelo(valor, vizinhos, local)

        return castelos

    # -------------------------------------------------------------------------
    #  DADOS (determinísticos)
    # -------------------------------------------------------------------------

    def rolar_dados(self):
        """
        Sobrescreve a lista de dados atual com 3 novos inteiros de 1 a 6.

        A rolagem é DETERMINÍSTICA: a n-ésima rolagem da partida é sempre gerada por Random("semente:n").
        Como 'rolagens_realizadas' faz parte do estado, simular uma jogada numa cópia do motor produz
        exatamente os mesmos dados que a jogada real vai produzir depois (e voltar no tempo também
        "volta" o gerador). Não é mais preciso salvar/restaurar o random global.

        Os dados ficam ORDENADOS (forma canônica): a ordem não muda nenhuma regra, então dois estados
        com os mesmos valores têm a mesma representação e o mesmo hash.
        """
        gerador = random.Random(f"{self.semente}:{self.rolagens_realizadas}")
        self.rolagens_realizadas += 1
        self.dados_atuais = sorted(gerador.randint(1, 6) for _ in range(3))
        return self.dados_atuais

    # -------------------------------------------------------------------------
    #  AÇÕES PRIMITIVAS (validam e alteram o motor; levantam ValueError se a regra for violada)
    # -------------------------------------------------------------------------

    def _validar_vez(self, id_jogador):
        if id_jogador != self.id_jogador_atual:
            raise ValueError("Não é a vez deste jogador.")

    def _validar_sem_carta_pendente(self):
        if self.carta_pendente is not None:
            raise ValueError(f"Escolha primeiro o alvo da carta {self.carta_pendente['nome']} (ou volte uma jogada).")

    def solicitar_rerrolagem(self, id_jogador):
        """Permite ao jogador tentar uma nova sorte nos dados, limitando a 1 vez por turno."""
        self._validar_vez(id_jogador)
        self._validar_sem_carta_pendente()
        if self.jogadores[id_jogador].tropas == 0:
            raise ValueError("Sem tropas no estoque: não há o que rerrolar. Passe a vez.")
        if self.rerrolagens_disponiveis <= 0:
            raise ValueError("Você já utilizou sua rerrolagem livre neste turno.")

        self.rolar_dados()
        self.rerrolagens_disponiveis -= 1

    def usar_carta(self, id_jogador, indice_mercado):
        """
        Usa ou ativa a carta da posição indicada do mercado.
        - Cartas imediatas (+2/-2 Castelo, +1 Reforço): o efeito é aplicado na hora.
        - Cartas com alvo (+1/-1/Inverter Dado, Marchar): a carta fica PENDENTE e o próximo
          nível da árvore passa a ser a lista de alvos possíveis.
        :param indice_mercado: Posição (0, 1 ou 2) da carta que foi clicada.
        """
        self._validar_vez(id_jogador)
        self._validar_sem_carta_pendente()

        jogador = self.jogadores[id_jogador]
        if jogador.usou_carta:
            raise ValueError("Você já utilizou uma carta nesta partida.")

        if indice_mercado < 0 or indice_mercado >= len(self.mercado_aberto):
            raise ValueError("Carta indisponível no mercado.")

        carta = self.mercado_aberto[indice_mercado]
        motivo = self._motivo_carta_sem_efeito(carta.efeito)
        if motivo:
            raise ValueError(motivo)

        if carta.efeito in CARTAS_IMEDIATAS:
            self.mercado_aberto.pop(indice_mercado)
            jogador.usou_carta = True

            # Aplicação direta do efeito na memória
            if carta.efeito == "+2_castelo":
                self.modificador_castelo += 2
            elif carta.efeito == "-2_castelo":
                self.modificador_castelo -= 2
            elif carta.efeito == "+1_reforco":
                self.modificador_tropas += 1
        else:
            # A carta continua no mercado até o alvo ser escolhido (a interface destaca essa carta)
            self.carta_pendente = {"indice": indice_mercado, "nome": carta.nome, "efeito": carta.efeito}

    def executar_alteracao_dado(self, id_jogador, indice_dado):
        """
        Aplica a carta de dado pendente (+1, -1 ou Inverter) no dado escolhido.
        :param indice_dado: Posição do dado alterado na lista (0, 1 ou 2).
        """
        self._validar_vez(id_jogador)
        pendente = self.carta_pendente
        if pendente is None or pendente["efeito"] not in CARTAS_DE_DADO:
            raise ValueError("Ative uma carta de dado antes de escolher o dado.")

        if indice_dado < 0 or indice_dado >= len(self.dados_atuais):
            raise ValueError("Dado inválido.")

        novo_valor = self._novo_valor_do_dado(pendente["efeito"], self.dados_atuais[indice_dado])
        self.dados_atuais[indice_dado] = novo_valor
        self.dados_atuais.sort() # Mantém a forma canônica (dados ordenados)
        self._consumir_carta_pendente()

    def executar_marcha(self, id_jogador, origem, destino):
        """
        Aplica a carta 'Marchar' pendente: move 1 tropa da origem para um castelo vizinho.
        Mover uma tropa consome todo o turno do jogador (ele não aloca depois).
        :param origem: ID numérico do castelo de onde a tropa sai.
        :param destino: ID numérico do castelo para onde a tropa vai.
        """
        self._validar_vez(id_jogador)
        pendente = self.carta_pendente
        if pendente is None or pendente["efeito"] != CARTA_MARCHA:
            raise ValueError("Ative a carta Marchar antes de escolher o movimento.")

        if origem not in self.castelos or destino not in self.castelos:
            raise ValueError("Castelo inválido.")

        castelo_origem = self.castelos[origem]
        if castelo_origem.tropas[id_jogador] <= 0:
            raise ValueError("Você não tem tropas na origem selecionada.")

        if destino not in castelo_origem.vizinhos:
            raise ValueError("O destino deve ser vizinho da origem.")

        castelo_origem.tropas[id_jogador] -= 1
        self.castelos[destino].tropas[id_jogador] += 1

        self._consumir_carta_pendente()
        self._limpar_modificadores_e_passar_vez()

    def _consumir_carta_pendente(self):
        """Tira do mercado a carta que estava pendente e marca o uso único da partida."""
        self.mercado_aberto.pop(self.carta_pendente["indice"])
        self.jogadores[self.id_jogador_atual].usou_carta = True
        self.carta_pendente = None

    def jogar_turno(self, indices_castelo):
        """
        O cerne mecânico do jogo. Aloca peças no tabuleiro consumindo a rolagem.
        O Backend recebe apenas as posições clicadas na interface e calcula tudo sozinho.
        """
        self._validar_sem_carta_pendente()
        if (len(indices_castelo) != 2 or indices_castelo[0] == indices_castelo[1]
                or any(i not in (0, 1, 2) for i in indices_castelo)):
            raise ValueError("Selecione exatamente 2 dados diferentes para o castelo.")

        jogador = self.jogadores[self.id_jogador_atual]

        # --- TRAVA DE SEGURANÇA 1: Proíbe alocação se não houver tropas ---
        if jogador.tropas == 0:
            raise ValueError("Você não tem tropas para alocar. Passe a vez.")

        idx_tropa = 3 - indices_castelo[0] - indices_castelo[1] # O índice que sobrou (0+1+2 = 3)

        dado_castelo_1 = self.dados_atuais[indices_castelo[0]]
        dado_castelo_2 = self.dados_atuais[indices_castelo[1]]
        dado_para_tropas = self.dados_atuais[idx_tropa]

        alvo_castelo = dado_castelo_1 + dado_castelo_2 + self.modificador_castelo
        quantidade = self._quantidade_de_tropas(dado_para_tropas, jogador)

        if alvo_castelo not in self.castelos:
            raise ValueError(f"O castelo {alvo_castelo} não existe (os castelos vão de 2 a 12).")

        if not jogador.remover_tropas(quantidade):
            raise ValueError("O jogador não tem tropas suficientes.")

        self.castelos[alvo_castelo].adicionar_tropas(self.id_jogador_atual, quantidade)

        if jogador.tropas == 0 and self.id_jogador_atual not in self.ordem_termino:
            self.ordem_termino.append(self.id_jogador_atual)
            if len(self.ordem_termino) == 1:
                jogador.medalhas = 2
            else:
                jogador.medalhas = 1

        self._limpar_modificadores_e_passar_vez()

    def _quantidade_de_tropas(self, valor_dado, jogador):
        """Converte o dado de tropas (1-2 → 1, 3-4 → 2, 5-6 → 3) + reforço, limitado ao estoque."""
        if valor_dado <= 2:
            tropas_convertidas = 1
        elif valor_dado <= 4:
            tropas_convertidas = 2
        else:
            tropas_convertidas = 3
        return min(tropas_convertidas + self.modificador_tropas, jogador.tropas)

    def passar_vez(self, id_jogador):
        """
        Botão de escape caso o jogador esteja zerado mas o jogo ainda não tenha acabado.
        --- TRAVA DE SEGURANÇA 3: também libera a passagem quando um modificador de carta deixou
        todas as somas fora dos castelos (2 a 12) e não há mais rerrolagem. Sem isso o jogo travava.
        """
        self._validar_vez(id_jogador)
        self._validar_sem_carta_pendente()

        if not self._pode_passar():
            raise ValueError("Você ainda tem tropas, não pode passar a vez.")

        self._limpar_modificadores_e_passar_vez()

    def _pode_passar(self):
        jogador = self.jogadores[self.id_jogador_atual]
        if jogador.tropas == 0:
            return True
        return not self._jogadas_de_alocacao() and self.rerrolagens_disponiveis == 0

    def _limpar_modificadores_e_passar_vez(self):
        """Zera o acúmulo do turno, transfere a posse e rola os dados automaticamente para o próximo."""
        self.modificador_castelo = 0
        self.modificador_tropas = 0
        self.rerrolagens_disponiveis = 1
        self.carta_pendente = None

        if self.id_jogador_atual == 1:
            self.id_jogador_atual = 2
        else:
            self.id_jogador_atual = 1

        self.rolar_dados()

    def _partida_terminou(self):
        return all(j.tropas == 0 for j in self.jogadores.values())

    # -------------------------------------------------------------------------
    #  GERAÇÃO DE JOGADAS (o "nível abaixo" de um estado na árvore)
    # -------------------------------------------------------------------------

    def gerar_jogadas_possiveis(self):
        """
        Lista TODAS as ramificações legais do estado atual, na ordem em que aparecem na árvore:
          1. Alocações (combinações de 2 dados que apontam para um castelo existente);
          2. Rerrolar (se ainda houver rerrolagem neste turno);
          3. Cada carta do mercado (se o mercado estiver aberto e o jogador ainda não usou carta);
          4. Passar a vez (estoque zerado, ou nenhum castelo válido e sem rerrolagem).
        Com uma carta de alvo pendente, o nível abaixo passa a ser a lista de alvos.

        Jogadas com o MESMO efeito aparecem uma vez só. Ex.: dados 3-3-5 → "3+5 no castelo 8"
        vale para qualquer um dos dois 3, então vira uma única aresta.
        """
        if self._partida_terminou():
            return []
        if self.carta_pendente is not None:
            return self._jogadas_de_alvo()

        id_j = self.id_jogador_atual
        jogador = self.jogadores[id_j]
        jogadas = []

        if jogador.tropas > 0:
            jogadas.extend(self._jogadas_de_alocacao())
            if self.rerrolagens_disponiveis > 0:
                jogadas.append(Jogada(TipoJogada.RERROLAR, id_j, (), f"[J{id_j}] Rerrolou Dados"))

        jogadas.extend(self._jogadas_de_carta())

        if self._pode_passar():
            rotulo = f"[J{id_j}] Passou a Vez"
            if jogador.tropas > 0:
                rotulo += "\n(Nenhum castelo válido)"
            jogadas.append(Jogada(TipoJogada.PASSAR, id_j, (), rotulo))

        return jogadas

    def _jogadas_de_alocacao(self):
        id_j = self.id_jogador_atual
        jogador = self.jogadores[id_j]
        if jogador.tropas == 0 or len(self.dados_atuais) != 3:
            return []

        jogadas = []
        castelos_vistos = set()
        for par in COMBINACOES_DE_DADOS:
            dado_1 = self.dados_atuais[par[0]]
            dado_2 = self.dados_atuais[par[1]]
            castelo = dado_1 + dado_2 + self.modificador_castelo

            # Filtro de Validade: a jogada só existe se a soma apontar para um castelo real (2 a 12).
            # Mesmo castelo = mesmo dado de tropas = mesmo resultado → uma aresta só.
            if castelo not in self.castelos or castelo in castelos_vistos:
                continue
            castelos_vistos.add(castelo)

            dado_tropa = self.dados_atuais[3 - par[0] - par[1]]
            rotulo = f"[J{id_j}] Castelo {castelo}\n(Dados {dado_1}+{dado_2}) | Tropa: {dado_tropa}"
            jogadas.append(Jogada(TipoJogada.ALOCAR, id_j, (castelo,), rotulo))
        return jogadas

    def _jogadas_de_carta(self):
        id_j = self.id_jogador_atual
        jogador = self.jogadores[id_j]
        if jogador.usou_carta or self.carta_pendente is not None:
            return []

        jogadas = []
        efeitos_vistos = set()
        for carta in self.mercado_aberto:
            # Duas cartas iguais no mercado (ex.: dois "+2 Castelo") geram o mesmo estado → uma aresta só
            if carta.efeito in efeitos_vistos or self._motivo_carta_sem_efeito(carta.efeito):
                continue
            efeitos_vistos.add(carta.efeito)
            verbo = "Usou" if carta.efeito in CARTAS_IMEDIATAS else "Ativou"
            jogadas.append(Jogada(TipoJogada.CARTA, id_j, (carta.efeito,), f"[J{id_j}] {verbo} Carta\n({carta.nome})"))
        return jogadas

    def _jogadas_de_alvo(self):
        id_j = self.id_jogador_atual
        pendente = self.carta_pendente
        if pendente["efeito"] == CARTA_MARCHA:
            return [Jogada(TipoJogada.MARCHA, id_j, (origem, destino),
                           f"[J{id_j}] Marchou (Carta)\n(Castelo {origem} → {destino})")
                    for origem, destino in self._alvos_de_marcha()]
        return [Jogada(TipoJogada.ALVO_DADO, id_j, (valor,),
                       f"[J{id_j}] Alterou Dado (Carta)\n({pendente['nome']}: {valor} → {novo})")
                for valor, novo in self._alvos_de_dado(pendente["efeito"])]

    def _motivo_carta_sem_efeito(self, efeito):
        """Retorna None se a carta pode ser usada agora, ou o motivo de ela não ter efeito."""
        jogador = self.jogadores[self.id_jogador_atual]
        if efeito == CARTA_MARCHA:
            return None if self._alvos_de_marcha() else "Você não tem tropas no tabuleiro para marchar."
        if jogador.tropas == 0:
            return "Sem tropas no estoque: esta carta não teria efeito."
        if efeito in CARTAS_DE_DADO and not self._alvos_de_dado(efeito):
            return "Nenhum dado pode receber o efeito desta carta."
        return None

    def _alvos_de_dado(self, efeito):
        """Pares (valor_atual, valor_novo) válidos. Dados de mesmo valor contam uma vez só."""
        alvos = []
        for valor in sorted(set(self.dados_atuais)):
            try:
                alvos.append((valor, self._novo_valor_do_dado(efeito, valor)))
            except ValueError:
                pass
        return alvos

    def _novo_valor_do_dado(self, efeito, valor_atual):
        if efeito == "+1_dado":
            if valor_atual == 6:
                raise ValueError("O dado já está no valor máximo (6).")
            return valor_atual + 1
        if efeito == "-1_dado":
            if valor_atual == 1:
                raise ValueError("O dado já está no valor mínimo (1).")
            return valor_atual - 1
        if efeito == "inverter_dado":
            return 7 - valor_atual
        raise ValueError("Efeito inválido para alteração de dados.")

    def _alvos_de_marcha(self):
        """Pares (origem, destino): castelos com tropa do jogador da vez → cada vizinho."""
        id_j = self.id_jogador_atual
        alvos = []
        for id_castelo in sorted(self.castelos):
            castelo = self.castelos[id_castelo]
            if castelo.tropas[id_j] > 0:
                for vizinho in sorted(castelo.vizinhos):
                    alvos.append((id_castelo, vizinho))
        return alvos

    # -------------------------------------------------------------------------
    #  APLICAR / SIMULAR JOGADAS (usado pela árvore)
    # -------------------------------------------------------------------------

    def aplicar_jogada(self, jogada):
        """Executa uma Jogada no motor. É o mesmo caminho para a jogada real e para a simulação."""
        if not self._jogada_permitida(jogada):
            raise ValueError(self.explicar_jogada_invalida(jogada))
        self._executar(jogada)

    def _jogada_permitida(self, jogada):
        """A jogada é permitida se for do jogador da vez e estiver entre as jogadas possíveis."""
        if jogada.jogador != self.id_jogador_atual:
            return False
        for possivel in self.gerar_jogadas_possiveis():
            if possivel.chave == jogada.chave:
                return True
        return False

    def simular_jogada(self, jogada):
        """
        Retorna o estado que a jogada produziria, SEM alterar este motor.
        A simulação roda numa cópia isolada; como os dados são determinísticos,
        o resultado é idêntico ao que aplicar_jogada() produzirá na partida real.
        """
        copia = self.clonar()
        copia.aplicar_jogada(jogada)
        return copia.obter_estado()

    def _executar(self, jogada):
        """Traduz a Jogada (semântica) para as ações primitivas do motor."""
        id_j = self.id_jogador_atual
        if jogada.tipo == TipoJogada.ALOCAR:
            self.jogar_turno(self._indices_do_castelo(jogada.args[0]))
        elif jogada.tipo == TipoJogada.RERROLAR:
            self.solicitar_rerrolagem(id_j)
        elif jogada.tipo == TipoJogada.CARTA:
            self.usar_carta(id_j, self._indice_da_carta(jogada.args[0]))
        elif jogada.tipo == TipoJogada.ALVO_DADO:
            self.executar_alteracao_dado(id_j, self._indice_do_dado(jogada.args[0]))
        elif jogada.tipo == TipoJogada.MARCHA:
            self.executar_marcha(id_j, jogada.args[0], jogada.args[1])
        elif jogada.tipo == TipoJogada.PASSAR:
            self.passar_vez(id_j)
        else:
            raise ValueError(f"Tipo de jogada desconhecido: {jogada.tipo}")

    def _indices_do_castelo(self, castelo):
        for par in COMBINACOES_DE_DADOS:
            if self.dados_atuais[par[0]] + self.dados_atuais[par[1]] + self.modificador_castelo == castelo:
                return list(par)
        raise ValueError(f"Nenhuma combinação dos dados atuais leva ao castelo {castelo}.")

    def _indice_da_carta(self, efeito):
        for indice, carta in enumerate(self.mercado_aberto):
            if carta.efeito == efeito:
                return indice
        raise ValueError("Carta indisponível no mercado.")

    def _indice_do_dado(self, valor):
        if valor in self.dados_atuais:
            return self.dados_atuais.index(valor)
        raise ValueError("Dado inválido.")

    def explicar_jogada_invalida(self, jogada):
        """Mensagem amigável dizendo por que uma jogada não pode ser feita agora."""
        if jogada.jogador != self.id_jogador_atual:
            return "Não é a vez deste jogador."
        try:
            self.clonar()._executar(jogada) # As ações primitivas já sabem explicar o erro
        except (ValueError, IndexError, KeyError) as erro:
            return str(erro)
        return "Jogada não permitida neste momento."

    # --- Tradutores de clique → Jogada (a interface nunca monta jogadas sozinha) ---

    def obter_jogada(self, tipo, *args):
        """Devolve a Jogada legal equivalente à intenção do jogador, ou ValueError com o motivo."""
        candidata = Jogada(tipo, self.id_jogador_atual, args)
        for jogada in self.gerar_jogadas_possiveis():
            if jogada.chave == candidata.chave:
                return jogada
        raise ValueError(self.explicar_jogada_invalida(candidata))

    def jogada_de_alocacao(self, indices_castelo):
        if (len(indices_castelo) != 2 or indices_castelo[0] == indices_castelo[1]
                or any(i not in (0, 1, 2) for i in indices_castelo)):
            raise ValueError("Selecione exatamente 2 dados diferentes para o castelo.")
        soma = self.dados_atuais[indices_castelo[0]] + self.dados_atuais[indices_castelo[1]] + self.modificador_castelo
        return self.obter_jogada(TipoJogada.ALOCAR, soma)

    def jogada_de_carta(self, indice_mercado):
        if indice_mercado < 0 or indice_mercado >= len(self.mercado_aberto):
            raise ValueError("Carta indisponível no mercado.")
        return self.obter_jogada(TipoJogada.CARTA, self.mercado_aberto[indice_mercado].efeito)

    def jogada_de_alvo_dado(self, indice_dado):
        if indice_dado < 0 or indice_dado >= len(self.dados_atuais):
            raise ValueError("Dado inválido.")
        return self.obter_jogada(TipoJogada.ALVO_DADO, self.dados_atuais[indice_dado])

    def jogada_de_marcha(self, origem, destino):
        return self.obter_jogada(TipoJogada.MARCHA, origem, destino)

    # -------------------------------------------------------------------------
    #  ESTADO (o conteúdo de cada nó da árvore)
    # -------------------------------------------------------------------------

    def obter_estado(self):
        """
        Gera um retrato exato do jogo neste milissegundo.
        Retorna um dicionário padronizado para alimentar IAs e a Interface.
        Tudo é copiado: alterar o dicionário retornado nunca altera o motor.
        """
        estado_castelos = {}
        for id_castelo, c in self.castelos.items():
            estado_castelos[id_castelo] = {
                'id_local': c.id_local,
                'tropas_j1': c.tropas[1],
                'tropas_j2': c.tropas[2],
                'conquistado': c.conquistado,
                'vizinhos': list(c.vizinhos)
            }

        estado_jogadores = {}
        for id_j, j in self.jogadores.items():
            estado_jogadores[id_j] = {
                'tropas': j.tropas,
                'medalhas': j.medalhas,
                'usou_carta': j.usou_carta
            }

        jogador_atual_obj = self.jogadores[self.id_jogador_atual]
        mercado_fechado = (jogador_atual_obj.usou_carta or len(self.mercado_aberto) == 0
                           or self.carta_pendente is not None)

        lista_mercado = []
        for carta in self.mercado_aberto:
            lista_mercado.append({'nome': carta.nome, 'efeito': carta.efeito})

        return {
            'semente': self.semente,
            'tropas_iniciais': self.tropas_iniciais,
            'rolagens_realizadas': self.rolagens_realizadas,
            'jogador_atual': self.id_jogador_atual,
            'castelos': estado_castelos,
            'jogadores': estado_jogadores,
            'fim_de_jogo': self._partida_terminou(),
            'modificador_castelo': self.modificador_castelo,
            'modificador_tropas': self.modificador_tropas,

            'dados_atuais': self.dados_atuais[:],
            'rerrolagens_disponiveis': self.rerrolagens_disponiveis,
            'mercado': lista_mercado,
            'mercado_bloqueado': mercado_fechado,
            'carta_pendente': dict(self.carta_pendente) if self.carta_pendente else None,
            'pontuacao_parcial': self.pontuacao_parcial.copy(),
            'castelo_resolucao_atual': self.castelo_resolucao_atual,
            'ordem_termino': self.ordem_termino[:],
            'mensagem_auditoria': self.mensagem_auditoria
        }

    def carregar_estado(self, estado):
        """
        Injeção Reversa: Pega um dicionário (JSON) e sobrescreve as variáveis locais do motor.
        Isso permite a 'viagem no tempo' pela árvore de estados.

        IMPORTANTE: todas as listas e dicionários são COPIADOS. A versão anterior fazia
        self.ordem_termino = estado['ordem_termino'] (mesma lista!) e a simulação seguinte
        alterava o estado "congelado" com append() — era a origem do nó "Alocação Real (Interna)".
        O JSON converte chaves inteiras em strings ("1", "2"), por isso o int() nas chaves.
        """
        self.semente = estado['semente']
        self.seed_atual = self.semente
        self.tropas_iniciais = estado.get('tropas_iniciais')
        self.rolagens_realizadas = estado['rolagens_realizadas']
        self.id_jogador_atual = int(estado['jogador_atual'])
        self.dados_atuais = list(estado['dados_atuais'])
        self.modificador_castelo = estado['modificador_castelo']
        self.modificador_tropas = estado['modificador_tropas']
        self.rerrolagens_disponiveis = estado['rerrolagens_disponiveis']
        self.castelo_resolucao_atual = estado['castelo_resolucao_atual']
        self.ordem_termino = [int(id_j) for id_j in estado['ordem_termino']]
        self.mensagem_auditoria = estado['mensagem_auditoria']
        self.pontuacao_parcial = {int(k): v for k, v in estado['pontuacao_parcial'].items()}
        self.carta_pendente = dict(estado['carta_pendente']) if estado.get('carta_pendente') else None

        # O mapa também vem do estado: assim um JSON salvo funciona mesmo com outra semente
        self.castelos = {}
        for id_c_str, info in estado['castelos'].items():
            id_c = int(id_c_str)
            castelo = Castelo(id_c, [int(v) for v in info['vizinhos']], info['id_local'])
            castelo.tropas = {1: info['tropas_j1'], 2: info['tropas_j2']}
            castelo.conquistado = info['conquistado']
            self.castelos[id_c] = castelo

        self.jogadores = {}
        for id_j_str, info in estado['jogadores'].items():
            id_j = int(id_j_str)
            jogador = Jogador(f"Jogador {id_j}", id_j, info['tropas'])
            jogador.medalhas = info['medalhas']
            jogador.usou_carta = info['usou_carta']
            self.jogadores[id_j] = jogador

        # Reconstrói a lista de objetos Carta a partir dos dicionários salvos
        self.mercado_aberto = []
        for idx, c_info in enumerate(estado['mercado']):
            self.mercado_aberto.append(Carta(idx, c_info['nome'], c_info['efeito']))

    # -------------------------------------------------------------------------
    #  AUDITORIA FINAL
    # -------------------------------------------------------------------------

    def resolver_batalha_atual(self):
        """
        Lógica final de pontuação chamada sucessivamente ao final do jogo.
        Retorna (True, mensagem) quando tudo foi resolvido, ou (False, mensagem) se pendente.
        A mensagem também fica guardada em self.mensagem_auditoria (aparece no obter_estado()).
        """
        if self.castelo_resolucao_atual > 12:
            self.mensagem_auditoria = "Fim do jogo."
            return True, self.mensagem_auditoria

        castelo = self.castelos[self.castelo_resolucao_atual]
        t1 = castelo.tropas[1]
        t2 = castelo.tropas[2]

        if t1 == 0 and t2 == 0:
            castelo.conquistado = True
            msg = f"Castelo {self.castelo_resolucao_atual} vazio."
            self.castelo_resolucao_atual += 1
            self.mensagem_auditoria = msg
            return False, msg

        vencedor = None
        if t1 > t2:
            vencedor = 1
        elif t2 > t1:
            vencedor = 2
        else:
            if self.jogadores[1].medalhas > self.jogadores[2].medalhas:
                vencedor = 1
            else:
                vencedor = 2

        self.pontuacao_parcial[vencedor] += castelo.id_castelo
        castelo.conquistado = True

        cascatas = []
        for vizinho in castelo.vizinhos:
            if vizinho > self.castelo_resolucao_atual:
                self.castelos[vizinho].adicionar_tropas(vencedor, 1)
                cascatas.append(str(vizinho))

        msg = f"C{self.castelo_resolucao_atual}: J{vencedor} venceu (+{castelo.id_castelo} pts)."
        if len(cascatas) > 0:
            msg += f" Cascata: {', '.join(cascatas)}"

        self.castelo_resolucao_atual += 1
        self.mensagem_auditoria = msg
        return False, msg

    def obter_vencedor(self):
        """
        Resultado da partida depois da auditoria: 1 ou 2 (jogador com mais pontos) ou 0 (empate).
        Retorna None enquanto a auditoria ainda não terminou.
        """
        if self.castelo_resolucao_atual <= 12:
            return None
        if self.pontuacao_parcial[1] > self.pontuacao_parcial[2]:
            return 1
        if self.pontuacao_parcial[2] > self.pontuacao_parcial[1]:
            return 2
        return 0
