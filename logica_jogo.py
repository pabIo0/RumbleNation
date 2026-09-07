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
        topologia = {
            0: [1, 2, 3, 8],
            1: [0, 2, 8],
            2: [0, 1, 6],
            3: [0, 8, 9],
            4: [5, 7, 10],
            5: [4, 7, 9],
            6: [2], 7: [4, 5, 9],
            8: [0, 1, 3, 9],
            9: [3, 5, 7, 8],
            10: [4]
        }
        vps = {2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 6, 8: 6, 9: 6, 10: 8, 11: 8, 12: 10}
        
        locais = list(topologia.keys())
        valores = list(vps.keys())
        random.shuffle(valores)
        
        mapa_valores = {}
        for i in range(len(locais)):
            mapa_valores[locais[i]] = valores[i]
            
        castelos = {}
        for local in locais:
            valor = mapa_valores[local]
            vizinhos = []
            for vizinho_local in topologia[local]:
                vizinhos.append(mapa_valores[vizinho_local])
                
            castelos[valor] = Castelo(valor, vps[valor], vizinhos, local)
            
        return castelos
    
    def rolar_dados(self):
        self.dados_atuais = []
        for _ in range(3):
            self.dados_atuais.append(random.randint(1, 6))
        return self.dados_atuais

    def usar_carta(self, id_jogador, indice_mercado):
        if id_jogador != self.id_jogador_atual:
            raise ValueError("Não é a vez deste jogador.")
            
        jogador = self.jogadores[id_jogador]
        if jogador.usou_carta:
            raise ValueError("Você já utilizou uma carta nesta partida.")
            
        t1 = self.jogadores[1].tropas
        t2 = self.jogadores[2].tropas
        
        if t1 == self.tropas_iniciais or t2 == self.tropas_iniciais:
            raise ValueError("Mercado fechado: aguarde o 2º turno.")
            
        if t1 <= 3 or t2 <= 3:
            raise ValueError("Mercado fechado: fim de jogo iminente.")
            
        if indice_mercado < 0 or indice_mercado >= len(self.mercado_aberto):
            raise ValueError("Carta indisponível no mercado.")
            
        carta_alvo = self.mercado_aberto[indice_mercado]
        if carta_alvo.efeito not in ["rerrolar", "+2_castelo", "-2_castelo", "+1_reforco"]:
            raise ValueError("Esta carta requer a seleção de um alvo no mapa.")
            
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

    def executar_marcha(self, id_jogador, indice_mercado, origem, destino):
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
        
        castelo_origem.tropas[id_jogador] -= 1
        self.castelos[destino].tropas[id_jogador] += 1
        
        self._limpar_modificadores_e_passar_vez()

    def executar_alteracao_dado(self, id_jogador, indice_mercado, indice_dado):
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
        
        if carta.efeito == "+1_dado":
            if valor_atual == 6: 
                raise ValueError("O dado já está no valor máximo (6).")
            self.dados_atuais[indice_dado] += 1
            
        elif carta.efeito == "-1_dado":
            if valor_atual == 1: 
                raise ValueError("O dado já está no valor mínimo (1).")
            self.dados_atuais[indice_dado] -= 1
            
        elif carta.efeito == "inverter_dado":
            self.dados_atuais[indice_dado] = 7 - valor_atual
            
        else:
            raise ValueError("Efeito inválido para alteração de dados.")
            
        self.mercado_aberto.pop(indice_mercado)
        jogador.usou_carta = True

    def jogar_turno(self, dados_para_castelo, dado_para_tropas):
        alvo_castelo = sum(dados_para_castelo) + self.modificador_castelo
        
        if dado_para_tropas == 1 or dado_para_tropas == 2:
            tropas_convertidas = 1
        elif dado_para_tropas == 3 or dado_para_tropas == 4:
            tropas_convertidas = 2
        else:
            tropas_convertidas = 3
            
        jogador = self.jogadores[self.id_jogador_atual]
        quantidade = min(tropas_convertidas + self.modificador_tropas, jogador.tropas)

        if alvo_castelo not in self.castelos:
            raise ValueError("Castelo inválido.")

        if not jogador.remover_tropas(quantidade):
            raise ValueError("O jogador não tem tropas suficientes.")
            
        self.castelos[alvo_castelo].adicionar_tropas(self.id_jogador_atual, quantidade)
        
        if jogador.tropas == 0 and self.id_jogador_atual not in self.ordem_termino:
            self.ordem_termino.append(self.id_jogador_atual)
            if len(self.ordem_termino) == 1:
                jogador.medalhas = 3
            else:
                jogador.medalhas = 2
            
        self._limpar_modificadores_e_passar_vez()

    def passar_vez(self, id_jogador):
        if id_jogador != self.id_jogador_atual:
            raise ValueError("Não é a vez deste jogador.")
            
        if self.jogadores[id_jogador].tropas > 0:
            raise ValueError("Você ainda tem tropas, não pode passar a vez.")
            
        self._limpar_modificadores_e_passar_vez()
        
    def _limpar_modificadores_e_passar_vez(self):
        self.modificador_castelo = 0
        self.modificador_tropas = 0
        self.dados_atuais = []
        if self.id_jogador_atual == 1:
            self.id_jogador_atual = 2
        else:
            self.id_jogador_atual = 1

    def obter_estado(self):
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
        elif t1 <= 3 or t2 <= 3:
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
        if self.castelo_resolucao_atual > 12:
            return True, "Fim do jogo."

        castelo = self.castelos[self.castelo_resolucao_atual]
        t1 = castelo.tropas[1]
        t2 = castelo.tropas[2]
        
        if t1 == 0 and t2 == 0:
            castelo.conquistado = True
            msg = f"Castelo {self.castelo_resolucao_atual} vazio."
            self.castelo_resolucao_atual += 1
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
                
        self.pontuacao_parcial[vencedor] += castelo.pontos_vitoria
        castelo.conquistado = True
        
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