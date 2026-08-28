import random

class Jogador:
    def __init__(self, nome, id_jogador, tropas_iniciais):
        self.nome = nome
        self.id_jogador = id_jogador
        self.tropas = tropas_iniciais
        self.medalhas = 0

    def remover_tropas(self, quantidade_tropas):
        if self.tropas >= quantidade_tropas:
            self.tropas -= quantidade_tropas
            return True
        return False

class Castelo:
    def __init__(self, id_castelo, pontos_vitoria, vizinhos, id_local):
        self.id_castelo = id_castelo
        self.pontos_vitoria = pontos_vitoria
        self.vizinhos = vizinhos
        self.id_local = id_local
        self.tropas = {1: 0, 2: 0}
        self.conquistado = False

    def adicionar_tropas(self, id_jogador, quantidade_tropas):
        self.tropas[id_jogador] += quantidade_tropas


class LogicaJogo:
    def __init__(self, tropas_iniciais=36, seed=None):
        if seed is not None:
            random.seed(seed)
            
        self.jogadores = {
            1: Jogador("Jogador 1", 1, tropas_iniciais),
            2: Jogador("Jogador 2", 2, tropas_iniciais)
        }
        self.id_jogador_atual = 1
        self.castelos = self._inicializar_castelos()
        self.dados_atuais = []
        self.ordem_termino = []
        self.castelo_resolucao_atual = 2
        self.pontuacao_parcial = {1: 0, 2: 0}
        self.mensagem_auditoria = "Pronto para iniciar a contagem."
        
    def _inicializar_castelos(self):
        topologia_geografica = {
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
        
        vps_por_valor = {2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 6, 8: 6, 9: 6, 10: 8, 11: 8, 12: 10}
        
        locais = list(topologia_geografica.keys())
        valores_disponiveis = list(vps_por_valor.keys())
        
        random.shuffle(valores_disponiveis)
        
        mapa_local_para_valor = {}
        for i in range(len(locais)):
            mapa_local_para_valor[locais[i]] = valores_disponiveis[i]
            
        castelos_criados = {}
        for local in locais:
            valor = mapa_local_para_valor[local]
            vizinhos_locais = topologia_geografica[local]
            vizinhos_valores = [mapa_local_para_valor[v_local] for v_local in vizinhos_locais]
            castelos_criados[valor] = Castelo(valor, vps_por_valor[valor], vizinhos_valores, local)
            
        return castelos_criados
    
    def rolar_dados(self):
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
        jogador = self.jogadores[id_jogador]
        if jogador.tropas == 0 and id_jogador not in self.ordem_termino:
            self.ordem_termino.append(id_jogador)
            if len(self.ordem_termino) == 1:
                jogador.medalhas = 3 
            elif len(self.ordem_termino) == 2:
                jogador.medalhas = 2

    def resolver_batalha_atual(self):
        if self.castelo_resolucao_atual > 12:
            return True, "Fim do jogo."

        castelo = self.castelos[self.castelo_resolucao_atual]
        tropas_j1 = castelo.tropas[1]
        tropas_j2 = castelo.tropas[2]
        
        if tropas_j1 == 0 and tropas_j2 == 0:
            castelo.conquistado = True
            mensagem = f"Castelo {self.castelo_resolucao_atual} vazio."
            self.castelo_resolucao_atual += 1
            return False, mensagem
            
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
                
        self.pontuacao_parcial[vencedor_id] += castelo.pontos_vitoria
        castelo.conquistado = True
        
        vizinhos_afetados = []
        for id_vizinho in castelo.vizinhos:
            if id_vizinho > self.castelo_resolucao_atual:
                self.castelos[id_vizinho].adicionar_tropas(vencedor_id, 1)
                vizinhos_afetados.append(str(id_vizinho))
                
        if vizinhos_afetados:
            texto_vizinhos = ", ".join(vizinhos_afetados)
            mensagem = f"C{self.castelo_resolucao_atual}: J{vencedor_id} venceu (+{castelo.pontos_vitoria} pts). Cascata: {texto_vizinhos}"
        else:
            mensagem = f"C{self.castelo_resolucao_atual}: J{vencedor_id} venceu (+{castelo.pontos_vitoria} pts)."
            
        self.castelo_resolucao_atual += 1
        return False, mensagem