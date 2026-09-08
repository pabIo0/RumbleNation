import random

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
    def __init__(self, id_castelo, pontos_vitoria, vizinhos, id_local):
        """
        Representa um território (nó) no mapa do jogo.
        :param id_castelo: Número do castelo (2 a 12), que é o valor alvo a ser tirado nos dados.
        :param pontos_vitoria: Quanto vale este castelo no final do jogo.
        :param vizinhos: Lista de IDs dos castelos adjacentes (usado para a carta marcha e para a cascata final).
        :param id_local: O ID fixo da coordenada geográfica na interface (onde ele será desenhado na tela).
        :var self.tropas: Dicionário que rastreia quantas peças cada jogador colocou aqui {1: X, 2: Y}.
        :var self.conquistado: Booleano que muda para True durante a auditoria final após os pontos serem distribuídos.
        """
        self.id_castelo = id_castelo
        self.pontos_vitoria = pontos_vitoria
        self.vizinhos = vizinhos
        self.id_local = id_local
        self.tropas = {1: 0, 2: 0}
        self.conquistado = False

    def adicionar_tropas(self, id_jogador, quantidade_tropas):
        """Soma as tropas recém-alocadas ao total já existente no território."""
        self.tropas[id_jogador] += quantidade_tropas


class LogicaJogo:
    def __init__(self, tropas_iniciais=36, seed=None):
        """
        Inicializa o estado global (Environment) da partida.
        :param seed: Permite gerar partidas diferentes a cada execução.
        """
        if seed is not None:
            random.seed(seed)
            
        self.tropas_iniciais = tropas_iniciais
        self.jogadores = {
            1: Jogador("Jogador 1", 1, tropas_iniciais),
            2: Jogador("Jogador 2", 2, tropas_iniciais)
        }
        self.id_jogador_atual = 1 # O Jogador 1 sempre começa
        
        self.castelos = self._inicializar_castelos()
        
        self.dados_atuais = [] # Guarda a última rolagem (3 inteiros)
        self.ordem_termino = [] # Fila que registra quem zerou as tropas primeiro
        
        # Variáveis de controle para a fase de fim de jogo (Auditoria)
        self.castelo_resolucao_atual = 2 # Começa validando o castelo 2, depois o 3, etc.
        self.pontuacao_parcial = {1: 0, 2: 0}
        self.mensagem_auditoria = "Pronto para iniciar a contagem."
        
        # Modificadores temporários aplicados pelas cartas e que expiram no fim do turno
        self.modificador_castelo = 0
        self.modificador_tropas = 0
        
        self.mercado_aberto = []
        self._inicializar_mercado()

    def _inicializar_mercado(self):
        """
        Cria o deck de 11 cartas originais e sorteia 3 para ficarem visíveis no mercado.
        A variável baralho_completo é descartada após o sample.
        """
        baralho_completo = [
            Carta(1, "Rerrolar", "rerrolar"),
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
        self.mercado_aberto = random.sample(baralho_completo, 3)
        
    def _inicializar_castelos(self):
        """
        Mistura os valores numéricos dos castelos e os espalha geograficamente pelo mapa,
        garantindo que as conexões físicas (vizinhos) permaneçam matematicamente corretas.
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
        
        # Tabela de premiação fixa: O castelo de valor X vale Y Pontos de Vitória (pv)
        pv = {2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 6, 8: 6, 9: 6, 10: 8, 11: 8, 12: 10}
        
        locais = list(topologia.keys())
        valores = list(pv.keys())
        random.shuffle(valores) # Embaralha apenas os números alvo
        
        # Cria um dicionário tradutor: Terreno físico -> Número sorteado do castelo
        mapa_valores = {}
        for i in range(len(locais)):
            mapa_valores[locais[i]] = valores[i]
            
        castelos = {}
        for local in locais:
            valor = mapa_valores[local]
            vizinhos = []
            
            # Traduz os vizinhos físicos para os seus novos valores matemáticos sorteados
            for vizinho_local in topologia[local]:
                vizinhos.append(mapa_valores[vizinho_local])
                
            castelos[valor] = Castelo(valor, pv[valor], vizinhos, local)
            
        return castelos
    
    def rolar_dados(self):
        """Sobrescreve a lista de dados atual com 3 novos inteiros de 1 a 6."""
        self.dados_atuais = []
        for _ in range(3):
            self.dados_atuais.append(random.randint(1, 6))
        return self.dados_atuais

    def usar_carta(self, id_jogador, indice_mercado):
        """
        Aplica os efeitos imediatos (não-direcionais) do mercado.
        Levanta exceções nativas (ValueError) caso a ação infrinja regras.
        :param indice_mercado: Posição (0, 1 ou 2) da carta que foi clicada.
        """
        if id_jogador != self.id_jogador_atual:
            raise ValueError("Não é a vez deste jogador.")
            
        jogador = self.jogadores[id_jogador]
        if jogador.usou_carta:
            raise ValueError("Você já utilizou uma carta nesta partida.")
            
        t1 = self.jogadores[1].tropas
        t2 = self.jogadores[2].tropas
        
        # Validações estritas de abertura/fechamento do mercado de cartas
        if t1 == self.tropas_iniciais or t2 == self.tropas_iniciais:
            raise ValueError("Mercado fechado: aguarde o 2º turno.")
           
        if indice_mercado < 0 or indice_mercado >= len(self.mercado_aberto):
            raise ValueError("Carta indisponível no mercado.")
            
        carta_alvo = self.mercado_aberto[indice_mercado]
        
        # Filtra as cartas complexas (Marcha e Dados) para suas próprias funções exclusivas
        if carta_alvo.efeito not in ["rerrolar", "+2_castelo", "-2_castelo", "+1_reforco"]:
            raise ValueError("Esta carta requer a seleção de um alvo no mapa.")
            
        carta = self.mercado_aberto.pop(indice_mercado)
        jogador.usou_carta = True
        
        # Aplicação direta do efeito na memória
        if carta.efeito == "rerrolar":
            self.rolar_dados()
        elif carta.efeito == "+2_castelo":
            self.modificador_castelo += 2
        elif carta.efeito == "-2_castelo":
            self.modificador_castelo -= 2
        elif carta.efeito == "+1_reforco":
            self.modificador_tropas += 1

    def executar_marcha(self, id_jogador, indice_mercado, origem, destino):
        """
        Processa a carta 'Marchar'. Requer alvos pré-selecionados.
        Mover uma tropa consome todo o turno do jogador (ele não rola dados depois).
        :param origem: ID numérico do castelo de onde a tropa sai.
        :param destino: ID numérico do castelo para onde a tropa vai.
        """
        if id_jogador != self.id_jogador_atual:
            raise ValueError("Não é a vez deste jogador.")
            
        jogador = self.jogadores[id_jogador]
        if jogador.usou_carta:
            raise ValueError("Você já utilizou uma carta nesta partida.")
            
        if origem not in self.castelos or destino not in self.castelos:
            raise ValueError("Castelo inválido.")
            
        castelo_origem = self.castelos[origem]
        if castelo_origem.tropas[id_jogador] <= 0:
            raise ValueError("Você não tem tropas na origem selecionada.")
            
        if destino not in castelo_origem.vizinhos:
            raise ValueError("O destino deve ser vizinho da origem.")
            
        self.mercado_aberto.pop(indice_mercado)
        jogador.usou_carta = True
        
        # Transferência física da peça no dicionário
        castelo_origem.tropas[id_jogador] -= 1
        self.castelos[destino].tropas[id_jogador] += 1
        
        self._limpar_modificadores_e_passar_vez()

    def executar_alteracao_dado(self, id_jogador, indice_mercado, indice_dado):
        """
        Processa as cartas de manipulação de resultado de rolagem (+1, -1, Inversor).
        :param indice_dado: Posição do dado alterado na lista (0, 1 ou 2).
        """
        if id_jogador != self.id_jogador_atual:
            raise ValueError("Não é a vez deste jogador.")
            
        jogador = self.jogadores[id_jogador]
        if jogador.usou_carta:
            raise ValueError("Você já utilizou uma carta nesta partida.")
            
        if not self.dados_atuais:
            raise ValueError("Dado inválido.")
            
        if indice_dado < 0 or indice_dado > 2:
            raise ValueError("Dado inválido.")
            
        carta = self.mercado_aberto[indice_mercado]
        valor_atual = self.dados_atuais[indice_dado]
        
        # Evita a criação de dados fora das bordas (7 ou 0)
        if carta.efeito == "+1_dado":
            if valor_atual == 6: 
                raise ValueError("O dado já está no valor máximo (6).")
            self.dados_atuais[indice_dado] += 1
            
        elif carta.efeito == "-1_dado":
            if valor_atual == 1: 
                raise ValueError("O dado já está no valor mínimo (1).")
            self.dados_atuais[indice_dado] -= 1
            
        elif carta.efeito == "inverter_dado":
            # Truque matemático clássico: faces opostas de um D6 sempre somam 7.
            self.dados_atuais[indice_dado] = 7 - valor_atual
            
        else:
            raise ValueError("Efeito inválido para alteração de dados.")
            
        self.mercado_aberto.pop(indice_mercado)
        jogador.usou_carta = True

    def jogar_turno(self, dados_para_castelo, dado_para_tropas):
        """
        O cerne mecânico do jogo. Aloca peças no tabuleiro consumindo a rolagem.
        :param dados_para_castelo: Array com os 2 dados selecionados para definir o castelo-alvo.
        :param dado_para_tropas: O 1 dado restante, que dita o volume do exército.
        """
        # Aplica o bônus/pênalti de carta na soma base
        alvo_castelo = sum(dados_para_castelo) + self.modificador_castelo
        
        # Conversão de força do dado para volume de recrutamento
        if dado_para_tropas == 1 or dado_para_tropas == 2:
            tropas_convertidas = 1
        elif dado_para_tropas == 3 or dado_para_tropas == 4:
            tropas_convertidas = 2
        else:
            tropas_convertidas = 3
            
        jogador = self.jogadores[self.id_jogador_atual]
        
        # Usa min() para evitar gerar peças do nada se o jogador tiver menos em estoque do que o dado mandou
        quantidade = min(tropas_convertidas + self.modificador_tropas, jogador.tropas)

        if alvo_castelo not in self.castelos:
            raise ValueError("Castelo inválido.")

        if not jogador.remover_tropas(quantidade):
            raise ValueError("O jogador não tem tropas suficientes.")
            
        self.castelos[alvo_castelo].adicionar_tropas(self.id_jogador_atual, quantidade)
        
        # Checa e anota na hora se este foi o último turno válido deste jogador
        if jogador.tropas == 0 and self.id_jogador_atual not in self.ordem_termino:
            self.ordem_termino.append(self.id_jogador_atual)
            if len(self.ordem_termino) == 1:
                jogador.medalhas = 2
            else:
                jogador.medalhas = 1
            
        self._limpar_modificadores_e_passar_vez()

    def passar_vez(self, id_jogador):
        """Botão de escape caso o jogador esteja zerado mas o jogo ainda não tenha acabado."""
        if id_jogador != self.id_jogador_atual:
            raise ValueError("Não é a vez deste jogador.")
            
        if self.jogadores[id_jogador].tropas > 0:
            raise ValueError("Você ainda tem tropas, não pode passar a vez.")
            
        self._limpar_modificadores_e_passar_vez()
        
    def _limpar_modificadores_e_passar_vez(self):
        """Helper interno que zera o acúmulo de cartas de um turno para o outro."""
        self.modificador_castelo = 0
        self.modificador_tropas = 0
        self.dados_atuais = []
        if self.id_jogador_atual == 1:
            self.id_jogador_atual = 2
        else:
            self.id_jogador_atual = 1

    def obter_estado(self):
        """
        O coração do 'Environment' para a IA e Interface. 
        Gera um retrato exato do jogo neste milissegundo, blindando as variáveis originais contra alterações.
        Retorna um dicionário padronizado.
        """
        estado_castelos = {}
        for id_castelo, c in self.castelos.items():
            estado_castelos[id_castelo] = {
                'id_local': c.id_local,
                'tropas_j1': c.tropas[1],
                'tropas_j2': c.tropas[2],
                'conquistado': c.conquistado,
                'vizinhos': c.vizinhos
            }
            
        estado_jogadores = {}
        for id_j, j in self.jogadores.items():
            estado_jogadores[id_j] = {
                'tropas': j.tropas, 
                'medalhas': j.medalhas,
                'usou_carta': j.usou_carta
            }
            
        t1 = self.jogadores[1].tropas
        t2 = self.jogadores[2].tropas
        
        mercado_fechado = False
        if t1 == self.tropas_iniciais or t2 == self.tropas_iniciais:
            mercado_fechado = True
            
        partida_fim = False
        if t1 == 0 and t2 == 0:
            partida_fim = True

        lista_mercado = []
        for carta in self.mercado_aberto:
            lista_mercado.append({'nome': carta.nome, 'efeito': carta.efeito})

        return {
            'jogador_atual': self.id_jogador_atual,
            'castelos': estado_castelos,
            'jogadores': estado_jogadores,
            'fim_de_jogo': partida_fim,
            'modificador_castelo': self.modificador_castelo,
            'modificador_tropas': self.modificador_tropas,
            'dados_atuais': self.dados_atuais,
            'mercado': lista_mercado,
            'mercado_bloqueado': mercado_fechado
        }

    def resolver_batalha_atual(self):
        """
        Lógica final de pontuação chamada sucessivamente ao final do jogo.
        Resolve castelo por castelo, em ordem ascendente (2 ao 12), gerando as cascatas de reforço.
        Retorna (True, mensagem) quando tudo foi resolvido, ou (False, mensagem) se ainda houverem castelos pendentes.
        """
        if self.castelo_resolucao_atual > 12:
            return True, "Fim do jogo."

        castelo = self.castelos[self.castelo_resolucao_atual]
        t1 = castelo.tropas[1]
        t2 = castelo.tropas[2]
        
        # Ignora castelos intocados
        if t1 == 0 and t2 == 0:
            castelo.conquistado = True
            msg = f"Castelo {self.castelo_resolucao_atual} vazio."
            self.castelo_resolucao_atual += 1
            return False, msg
            
        # Determina o vencedor da maioria e avalia as medalhas em caso de empate
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
                
        self.pontuacao_parcial[vencedor] += castelo.pontos_vitoria
        castelo.conquistado = True
        
        # Mecânica de Cascata: Envia uma tropa bônus grátis para todos os vizinhos de numeração MAIOR
        cascatas = []
        for vizinho in castelo.vizinhos:
            if vizinho > self.castelo_resolucao_atual:
                self.castelos[vizinho].adicionar_tropas(vencedor, 1)
                cascatas.append(str(vizinho))
                
        msg = f"C{self.castelo_resolucao_atual}: J{vencedor} venceu (+{castelo.pontos_vitoria} pts)."
        
        if len(cascatas) > 0:
            msg += f" Cascata: {', '.join(cascatas)}"
            
        self.castelo_resolucao_atual += 1
        return False, msg