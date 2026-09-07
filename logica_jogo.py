import random

class Carta:
    def __init__(self, id_carta, nome, efeito):
        self.id_carta = id_carta
        self.nome = nome
        self.efeito = efeito

class Jogador:
    def __init__(self, nome, id_jogador, tropas_iniciais):
        self.nome = nome
        self.id_jogador = id_jogador
        self.tropas = tropas_iniciais
        self.medalhas = 0
        self.usou_carta = False

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
            
        self.tropas_iniciais = tropas_iniciais
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
        
        self.modificador_castelo = 0
        self.modificador_tropas = 0
        self.mercado_aberto = []
        self._inicializar_mercado()

    def _inicializar_mercado(self):
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

    def usar_carta(self, id_jogador, indice_mercado):
        if id_jogador != self.id_jogador_atual:
            return self.obter_estado(erro="Não é a vez deste jogador.")
            
        jogador = self.jogadores[id_jogador]
        
        if jogador.usou_carta:
            return self.obter_estado(erro="Você já utilizou uma carta nesta partida.")
            
        t_j1 = self.jogadores[1].tropas
        t_j2 = self.jogadores[2].tropas
        if t_j1 == self.tropas_iniciais or t_j2 == self.tropas_iniciais:
            return self.obter_estado(erro="Mercado fechado: aguarde o 2º turno.")
        if t_j1 <= 3 or t_j2 <= 3:
            return self.obter_estado(erro="Mercado fechado: fim de jogo iminente.")
            
        if indice_mercado < 0 or indice_mercado >= len(self.mercado_aberto):
            return self.obter_estado(erro="Carta indisponível no mercado.")
            
        carta_alvo = self.mercado_aberto[indice_mercado]
        
        efeitos_simples = ["rerrolar", "+2_castelo", "-2_castelo", "+1_reforco"]
        if carta_alvo.efeito not in efeitos_simples:
            return self.obter_estado(erro="Esta carta requer a seleção de um alvo no mapa.")
            
        carta = self.mercado_aberto.pop(indice_mercado)
        jogador.usou_carta = True
        
        if carta.efeito == "rerrolar":
            self.rolar_dados()
        elif carta.efeito == "+2_castelo":
            self.modificador_castelo += 2
        elif carta.efeito == "-2_castelo":
            self.modificador_castelo -= 2
        elif carta.efeito == "+1_reforco":
            self.modificador_tropas += 1
            
        return self.obter_estado()

    def executar_marcha(self, id_jogador, indice_mercado, origem, destino):
        if id_jogador != self.id_jogador_atual:
            return self.obter_estado(erro="Não é a vez deste jogador.")
            
        jogador = self.jogadores[id_jogador]
        
        if jogador.usou_carta:
            return self.obter_estado(erro="Você já utilizou uma carta nesta partida.")
            
        if origem not in self.castelos or destino not in self.castelos:
            return self.obter_estado(erro="Castelo inválido.")
            
        castelo_origem = self.castelos[origem]
        castelo_destino = self.castelos[destino]
        
        if castelo_origem.tropas[id_jogador] <= 0:
            return self.obter_estado(erro="Você não tem tropas na origem selecionada.")
            
        if destino not in castelo_origem.vizinhos:
            return self.obter_estado(erro="O destino deve ser vizinho da origem.")
            
        self.mercado_aberto.pop(indice_mercado)
        jogador.usou_carta = True
        
        castelo_origem.tropas[id_jogador] -= 1
        castelo_destino.tropas[id_jogador] += 1
        
        self.modificador_castelo = 0
        self.modificador_tropas = 0
        self.dados_atuais = []
        
        if self.id_jogador_atual == 1:
            self.id_jogador_atual = 2
        else:
            self.id_jogador_atual = 1
            
        return self.obter_estado()

    def executar_alteracao_dado(self, id_jogador, indice_mercado, indice_dado):
        if id_jogador != self.id_jogador_atual:
            return self.obter_estado(erro="Não é a vez deste jogador.")
            
        jogador = self.jogadores[id_jogador]
        
        if jogador.usou_carta:
            return self.obter_estado(erro="Você já utilizou uma carta nesta partida.")
            
        if not self.dados_atuais or indice_dado < 0 or indice_dado > 2:
            return self.obter_estado(erro="Dado inválido.")
            
        carta = self.mercado_aberto[indice_mercado]
        valor_atual = self.dados_atuais[indice_dado]
        
        if carta.efeito == "+1_dado":
            if valor_atual == 6:
                return self.obter_estado(erro="O dado já está no valor máximo (6).")
            self.dados_atuais[indice_dado] += 1
        elif carta.efeito == "-1_dado":
            if valor_atual == 1:
                return self.obter_estado(erro="O dado já está no valor mínimo (1).")
            self.dados_atuais[indice_dado] -= 1
        elif carta.efeito == "inverter_dado":
            self.dados_atuais[indice_dado] = 7 - valor_atual
        else:
            return self.obter_estado(erro="Efeito inválido para alteração de dados.")
            
        self.mercado_aberto.pop(indice_mercado)
        jogador.usou_carta = True
        
        return self.obter_estado()

    def obter_estado(self, erro=None):
        estado_castelos = {}
        for id_castelo, castelo in self.castelos.items():
            estado_castelos[id_castelo] = {
                'id_local': castelo.id_local,
                'tropas_j1': castelo.tropas[1],
                'tropas_j2': castelo.tropas[2],
                'conquistado': castelo.conquistado,
                'vizinhos': castelo.vizinhos
            }
            
        estado_jogadores = {
            1: {
                'tropas': self.jogadores[1].tropas, 
                'medalhas': self.jogadores[1].medalhas,
                'usou_carta': self.jogadores[1].usou_carta
            },
            2: {
                'tropas': self.jogadores[2].tropas, 
                'medalhas': self.jogadores[2].medalhas,
                'usou_carta': self.jogadores[2].usou_carta
            }
        }
        
        if erro == None:
            jogada_valida = True
        else:
            jogada_valida = False
            
        if self.jogadores[1].tropas == 0 and self.jogadores[2].tropas == 0:
            partida_acabou = True
        else:
            partida_acabou = False
            
        t_j1 = self.jogadores[1].tropas
        t_j2 = self.jogadores[2].tropas
        if (t_j1 == self.tropas_iniciais or t_j2 == self.tropas_iniciais) or (t_j1 <= 3 or t_j2 <= 3):
            mercado_bloqueado = True
        else:
            mercado_bloqueado = False

        estado_do_jogo = {
            'sucesso': jogada_valida,
            'erro': erro,
            'jogador_atual': self.id_jogador_atual,
            'castelos': estado_castelos,
            'jogadores': estado_jogadores,
            'fim_de_jogo': partida_acabou,
            'modificador_castelo': self.modificador_castelo,
            'modificador_tropas': self.modificador_tropas,
            'dados_atuais': self.dados_atuais,
            'mercado': [{'nome': c.nome, 'efeito': c.efeito} for c in self.mercado_aberto],
            'mercado_bloqueado': mercado_bloqueado
        }

        return estado_do_jogo

    def jogar_turno(self, dados_para_castelo, dado_para_tropas):
        alvo_castelo = sum(dados_para_castelo) + self.modificador_castelo
        
        if dado_para_tropas == 1 or dado_para_tropas == 2:
            tropas_convertidas = 1
        elif dado_para_tropas == 3 or dado_para_tropas == 4:
            tropas_convertidas = 2
        else:
            tropas_convertidas = 3
            
        jogador = self.jogadores[self.id_jogador_atual]
        
        quantidade_tropas = min(tropas_convertidas + self.modificador_tropas, jogador.tropas)

        if alvo_castelo not in self.castelos:
            return self.obter_estado(erro="Castelo inválido.")

        if not jogador.remover_tropas(quantidade_tropas):
            return self.obter_estado(erro="O jogador não tem tropas suficientes.")
            
        self.castelos[alvo_castelo].adicionar_tropas(self.id_jogador_atual, quantidade_tropas)
        
        self.verificar_fim_de_jogo(self.id_jogador_atual)
        
        self.modificador_castelo = 0
        self.modificador_tropas = 0
        
        if self.id_jogador_atual == 1:
            self.id_jogador_atual = 2
        else:
            self.id_jogador_atual = 1
            
        return self.obter_estado()

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