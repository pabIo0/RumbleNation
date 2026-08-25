import random

class Jogador:
    def __init__(self, nome, id_jogador):
        self.nome = nome
        self.id_jogador = id_jogador
        self.tropas = 36
        self.medalhas = 0

    def remover_tropas(self, quantidade_tropas):
        if self.tropas >= quantidade_tropas:
            self.tropas -= quantidade_tropas
            return True
        return False


class Castelo:
    def __init__(self, id_castelo, pontos_vitoria, vizinhos):
        self.id_castelo = id_castelo
        self.pontos_vitoria = pontos_vitoria
        self.vizinhos = vizinhos
        self.tropas = {1: 0, 2: 0}
        self.conquistado = False

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
        self.ordem_termino = []
        
    def _inicializar_castelos(self):
        return {
            2: Castelo(2, 2, [3, 4, 5, 10]),
            3: Castelo(3, 2, [2, 4, 10]),
            4: Castelo(4, 4, [2, 3, 8]),
            5: Castelo(5, 4, [2, 10, 11]),
            6: Castelo(6, 4, [7, 9, 12]),
            7: Castelo(7, 6, [6, 9, 11]),
            8: Castelo(8, 6, [4]),
            9: Castelo(9, 6, [6, 7, 11]),
            10: Castelo(10, 8, [2, 3, 5, 11]),
            11: Castelo(11, 8, [5, 7, 9, 10]),
            12: Castelo(12, 10, [6])
        }
    
    def rolar_dados(self):
        """Rola os 3 dados de 6 faces e salva no estado do jogo."""
        self.dados_atuais = [random.randint(1, 6) for _ in range(3)]
        return self.dados_atuais

    def jogar_turno(self, dados_para_castelo, dado_para_tropas):
        alvo_castelo = sum(dados_para_castelo)
        
        if dado_para_tropas == 1 or dado_para_tropas == 2:
            tropas_convertidas = 1
        elif dado_para_tropas == 3 or dado_para_tropas == 4:
            tropas_convertidas = 2
        else:
            tropas_convertidas = 3
            
        jogador = self.jogadores[self.id_jogador_atual]
        quantidade_tropas = min(tropas_convertidas, jogador.tropas)
        
        if alvo_castelo not in self.castelos:
            return False, "Erro: Castelo inválido."
        
        if not jogador.remover_tropas(quantidade_tropas):
            return False, "Erro: O jogador não tem tropas suficientes."
            
        self.castelos[alvo_castelo].adicionar_tropas(self.id_jogador_atual, quantidade_tropas)
        
        self.verificar_fim_de_jogo(self.id_jogador_atual)
        
        mensagem_sucesso = f"Jogador {self.id_jogador_atual} | {quantidade_tropas} tropas adicionadas no castelo {alvo_castelo}"
        
        if self.id_jogador_atual == 1:
            self.id_jogador_atual = 2
        else:
            self.id_jogador_atual = 1
            
        return True, mensagem_sucesso

    def verificar_fim_de_jogo(self, id_jogador):
        """Verifica quem zerou o estoque primeiro para a regra do desempate."""
        jogador = self.jogadores[id_jogador]
        if jogador.tropas == 0 and id_jogador not in self.ordem_termino:
            self.ordem_termino.append(id_jogador)
            if len(self.ordem_termino) == 1:
                jogador.medalhas = 3 
            elif len(self.ordem_termino) == 2:
                jogador.medalhas = 2

    def resolver_guerras(self):
        """
        Resolve as batalhas do castelo 2 ao 12 em ordem, calcula os pontos finais 
        e aplica o sistema de reforço em cascata aos castelos vizinhos maiores.
        """
        pontuacao_final = {1: 0, 2: 0}

        for id_castelo in range(2, 13):
            castelo = self.castelos[id_castelo]
            
            tropas_j1 = castelo.tropas[1]
            tropas_j2 = castelo.tropas[2]
            
            if tropas_j1 == 0 and tropas_j2 == 0:
                castelo.conquistado = True
                continue
                
            vencedor_id = None
            
            if tropas_j1 > tropas_j2:
                vencedor_id = 1
            elif tropas_j2 > tropas_j1:
                vencedor_id = 2
            else:
                medalhas_j1 = self.jogadores[1].medalhas
                medalhas_j2 = self.jogadores[2].medalhas
                
                if medalhas_j1 > medalhas_j2:
                    vencedor_id = 1
                else:
                    vencedor_id = 2
                    
            pontuacao_final[vencedor_id] = pontuacao_final[vencedor_id] + castelo.pontos_vitoria
            castelo.conquistado = True
            
            for id_vizinho in castelo.vizinhos:
                if id_vizinho > id_castelo:
                    quantidade_tropas_bonus = 1
                    self.castelos[id_vizinho].adicionar_tropas(vencedor_id, quantidade_tropas_bonus)
                    
        return pontuacao_final