import random

class Jogador:
    def __init__(self, nome, id_jogador):
        self.nome = nome
        self.id_jogador = id_jogador
        self.tropas = 36 # Cada jogador começa com 36 tropas
        self.medalhas = 0 # Vai armazenar o valor da iniciativa (3 espadas ou 2 espadas)

    def remover_tropas(self, quantidade_tropas):
        # Garante que o jogador não tente jogar mais tropas do que possui
        if self.tropas >= quantidade_tropas:
            self.tropas -= quantidade_tropas
            return True
        return False


class Castelo:
    def __init__(self, id_castelo, pontos_vitoria, vizinhos):
        self.id_castelo = id_castelo
        self.pontos_vitoria = pontos_vitoria
        self.vizinhos = vizinhos # Lista de conexões do tabuleiro
        self.tropas = {1: 0, 2: 0} # Dicionario: {id_do_jogador: quantidade_de_tropas}
        self.conquistado = False # True quando for pontuado na Guerra

    def adicionar_tropas(self, id_jogador, quantidade_tropas):
        self.tropas[id_jogador] += quantidade_tropas


class LogicaJogo:
    def __init__(self):
        self.jogadores = {
            1: Jogador("Jogador 1", 1),
            2: Jogador("Jogador 2", 2)
        }
        self.id_jogador_atual = 1
        self.castelos = self._inicializar_castelos()
        self.dados_atuais = []
        self.ordem_termino = [] # Guarda quem esvaziou o estoque primeiro
        
    def _inicializar_castelos(self):
        # Mapeamento do tabuleiro (ID, VP, [Vizinhos])
        return {
            2: Castelo(2, 2, [3, 4, 5]),
            3: Castelo(3, 2, [2, 4, 6]),
            4: Castelo(4, 4, [2, 3, 5, 6, 7]),
            5: Castelo(5, 4, [2, 4, 7, 8]),
            6: Castelo(6, 4, [3, 4, 7, 9]),
            7: Castelo(7, 6, [4, 5, 6, 8, 9, 10]),
            8: Castelo(8, 6, [5, 7, 10, 11]),
            9: Castelo(9, 6, [6, 7, 10, 12]),
            10: Castelo(10, 8, [7, 8, 9, 11, 12]),
            11: Castelo(11, 8, [8, 10, 12]),
            12: Castelo(12, 10, [9, 10, 11])
        }

    def rolar_dados(self):
        """Rola os 3 dados de 6 faces e salva no estado do jogo."""
        self.dados_atuais = [random.randint(1, 6) for _ in range(3)]
        return self.dados_atuais

    def jogar_turno(self, dados_para_castelo, dado_para_tropas):
        """
        Executa a jogada e desconta os recursos.
        """
        alvo_castelo = sum(dados_para_castelo)
        
        # Regra de ajuste: se o jogador rolar um 5 mas só tiver 3 tropas no estoque, ele joga 3.
        jogador = self.jogadores[self.id_jogador_atual]
        quantidade_tropas = min(dado_para_tropas, jogador.tropas)
        
        if alvo_castelo not in self.castelos:
            return False, "Erro: Castelo inválido."
        
        if not jogador.remover_tropas(quantidade_tropas):
            return False, "Erro: O jogador não tem tropas suficientes."
            
        # Adiciona as tropas no castelo escolhido
        self.castelos[alvo_castelo].adicionar_tropas(self.id_jogador_atual, quantidade_tropas)
        
        # Checa se o jogador zerou os tropas para ganhar o medalhão
        self.verificar_fim_de_jogo(self.id_jogador_atual)
        
        # Passa a vez
        if self.id_jogador_atual == 1:
            self.id_jogador_atual = 2
        else:
            self.id_jogador_atual = 1

        return True, "Jogada realizada com sucesso."

    def verificar_fim_de_jogo(self, id_jogador):
        """Verifica quem zerou o estoque primeiro para a regra do desempate."""
        jogador = self.jogadores[id_jogador]
        if jogador.tropas == 0 and id_jogador not in self.ordem_termino:
            self.ordem_termino.append(id_jogador)
            
            # O primeiro a acabar ganha 3 espadas (peso maior). O segundo ganha 2 espadas.
            if len(self.ordem_termino) == 1:
                jogador.medalhas = 3 
            elif len(self.ordem_termino) == 2:
                jogador.medalhas = 2