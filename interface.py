import pygame
import sys
import random
import math
import os
from logica_jogo import LogicaJogo

# Dicionário estático: mapeia o ID do terreno (0 a 10) para suas coordenadas exatas (X, Y) na tela.
POSICOES_CASTELOS = {
    0: (680, 440),
    1: (760, 520),
    2: (840, 320),
    3: (580, 280),
    4: (100, 220),
    5: (320, 200),
    6: (940, 100),
    7: (200, 400),
    8: (520, 520),
    9: (430, 400),
    10: (120, 600)
}

# Paleta de cores padrão
COR_FUNDO = (240, 240, 240)
COR_PRETA = (0, 0, 0)
COR_BRANCA = (255, 255, 255)
COR_JOGADOR_1 = (255, 80, 80)
COR_JOGADOR_2 = (80, 150, 255)

class InterfaceJogo:
    def __init__(self):
        """
        Construtor da interface gráfica. Inicializa o motor do Pygame, a janela principal,
        o relógio de FPS e as fontes de texto que serão usadas para renderizar a HUD.
        """
        pygame.init()
        self.tela = pygame.display.set_mode((1000, 700))
        pygame.display.set_caption("Rumble Nation - IA")
        self.relogio = pygame.time.Clock()
        
        self.fontes = {
            'castelo': pygame.font.SysFont('Arial', 20, bold=True),
            'tropas': pygame.font.SysFont('Arial', 16, bold=True),
            'botao': pygame.font.SysFont('Arial', 24, bold=True),
            'dado': pygame.font.SysFont('Arial', 40, bold=True),
            'titulo': pygame.font.SysFont('Arial', 40, bold=True),
            'aviso': pygame.font.SysFont('Arial', 20, bold=True)
        }
        
        self.assets = self._carregar_assets()
        self._resetar_estado()

    def _carregar_assets(self):
        """
        Busca as imagens na pasta 'assets'. Se o arquivo existir, converte preservando
        o canal Alpha (transparência) e redimensiona. Se não existir, retorna None
        para que o jogo desenhe formas geométricas simples como fallback.
        """
        arquivos_carregados = {}
        
        caminho_fundo = "assets/fundo.png"
        if os.path.exists(caminho_fundo):
            imagem = pygame.image.load(caminho_fundo).convert_alpha()
            arquivos_carregados['fundo'] = pygame.transform.smoothscale(imagem, (1000, 700))
        else:
            arquivos_carregados['fundo'] = None
            
        arquivos_carregados['dados'] = {}
        for i in range(1, 7):
            caminho_dado = f"assets/dado_{i}.png"
            if os.path.exists(caminho_dado):
                imagem_dado = pygame.image.load(caminho_dado).convert_alpha()
                arquivos_carregados['dados'][i] = pygame.transform.smoothscale(imagem_dado, (60, 60))
            else:
                arquivos_carregados['dados'][i] = None
                
        return arquivos_carregados

    def _resetar_estado(self):
        """
        Limpa as variáveis temporárias da interface gráfica. 
        Usada ao abrir o jogo e também ao clicar em "Jogar Novamente".
        """
        self.jogo = None # Instância da LogicaJogo (Backend)
        self.tela_atual = "MENU" # Controla o roteamento ("MENU", "RODANDO", "AUDITORIA", "FIM")
        self.mensagem_aviso = "" # String para exibir erros (ex: "Você não tem tropas")
        
        self.dados_na_tela = [] # Valores dos dados após rolar
        self.indices_selecionados = [] # Quais dados o jogador clicou para usar no castelo
        
        # Variáveis de controle para o uso de cartas táticas
        self.modo_mira = None # Pode ser "MARCHA_ORIGEM", "MARCHA_DESTINO", "MIRA_DADO" ou None
        self.origem_mira = -1 # ID do castelo selecionado como ponto de partida da marcha
        self.carta_mira_indice = -1 # ID da carta que ativou a mira
        self.mercado_expandido = False # Booleano que controla o Menu Retrátil (Hover) das cartas
        
        # Hitboxes físicas na tela (Retângulos invisíveis para detectar cliques)
        self.rects_dados = [
            pygame.Rect(770, 540, 60, 60), 
            pygame.Rect(840, 540, 60, 60), 
            pygame.Rect(910, 540, 60, 60)
        ]
        self.rect_rolar = pygame.Rect(770, 620, 200, 50)

    def iniciar(self):
        """O laço infinito que mantém a janela aberta atualizando 60 vezes por segundo."""
        while True:
            self._processar_eventos()
            self._desenhar_tela()
            self.relogio.tick(60)

    def _processar_eventos(self):
        """Analisa movimentos do mouse e cliques físicos capturados pelo sistema operacional."""
        pos_mouse = pygame.mouse.get_pos()
        
        # Mecânica de Hover: Se o mouse invadir a área da aba, expanda o mercado.
        aba_rect = pygame.Rect(20, 20, 120, 35)
        area_mercado = pygame.Rect(15, 20, 300, 185)
        
        if aba_rect.collidepoint(pos_mouse):
            self.mercado_expandido = True
        elif not area_mercado.collidepoint(pos_mouse):
            self.mercado_expandido = False

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 3: # Clique com o Botão Direito
                    if self.modo_mira is not None:
                        self._cancelar_mira()
                elif evento.button == 1: # Clique com o Botão Esquerdo
                    self._rotear_clique(evento.pos)

    def _rotear_clique(self, pos):
        """
        Direciona o clique do mouse para a função correta, baseando-se na tela atual.
        Isso evita que o jogador clique em elementos invisíveis.
        """
        self.mensagem_aviso = "" # Limpa qualquer aviso antigo
        
        if self.tela_atual == "MENU":
            rect_botao_18 = pygame.Rect(300, 300, 400, 60)
            rect_botao_36 = pygame.Rect(300, 400, 400, 60)
            
            if rect_botao_18.collidepoint(pos):
                self.jogo = LogicaJogo(18, seed=random.randint(1, 999999))
                self.tela_atual = "RODANDO"
            elif rect_botao_36.collidepoint(pos):
                self.jogo = LogicaJogo(36, seed=random.randint(1, 999999))
                self.tela_atual = "RODANDO"
                
        elif self.tela_atual == "RODANDO":
            self._processar_clique_rodando(pos)
            
        elif self.tela_atual == "AUDITORIA":
            rect_auditoria = pygame.Rect(350, 630, 300, 50)
            if rect_auditoria.collidepoint(pos):
                terminou, msg = self.jogo.resolver_batalha_atual()
                self.jogo.mensagem_auditoria = msg
                if terminou:
                    self.tela_atual = "FIM"
                    
        elif self.tela_atual == "FIM":
            rect_reiniciar = pygame.Rect(350, 640, 300, 50)
            if rect_reiniciar.collidepoint(pos):
                self._resetar_estado()

    def _processar_clique_rodando(self, pos):
        """Lida com as interações principais do tabuleiro: mira de cartas, botão de rolar e seleção de dados."""
        estado = self.jogo.obter_estado()

        # Prioridade 1: Se estiver mirando uma carta, o clique deve atingir o alvo no tabuleiro
        if self.modo_mira is not None:
            self._tentar_mira(pos, estado)
            return

        # Prioridade 2: Botão Principal (Rolar Dados / Passar Vez)
        if self.rect_rolar.collidepoint(pos):
            try:
                jogador_da_vez = estado['jogador_atual']
                tropas_atuais = estado['jogadores'][jogador_da_vez]['tropas']
                
                if tropas_atuais == 0:
                    self.jogo.passar_vez(jogador_da_vez)
                    self._encerrar_turno()
                elif len(self.dados_na_tela) == 0:
                    self.dados_na_tela = self.jogo.rolar_dados()
            except ValueError as e:
                self.mensagem_aviso = str(e)
            return

        # Prioridade 3: Mercado de Cartas (se visível)
        jogador_da_vez = estado['jogador_atual']
        usou_carta = estado['jogadores'][jogador_da_vez]['usou_carta']
        
        pode_comprar = False
        if not estado['mercado_bloqueado']:
            if not usou_carta:
                pode_comprar = True
                
        if self.mercado_expandido and pode_comprar:
            for i in range(len(estado['mercado'])):
                carta = estado['mercado'][i]
                rect_carta = pygame.Rect(20 + i * 100, 65, 90, 130)
                if rect_carta.collidepoint(pos):
                    self._tentar_comprar_carta(i, carta['efeito'], estado)
                    return

        # Prioridade 4: Seleção dos Dados após a rolagem
        if len(self.dados_na_tela) > 0:
            for i in range(len(self.rects_dados)):
                rect = self.rects_dados[i]
                if rect.collidepoint(pos):
                    # Se clicou num dado já selecionado, desmarca ele
                    if i in self.indices_selecionados:
                        self.indices_selecionados.remove(i)
                    else:
                        # Se ainda tem vaga, seleciona o dado. Se chegou em 2, aloca no castelo automaticamente.
                        if len(self.indices_selecionados) < 2:
                            self.indices_selecionados.append(i)
                            if len(self.indices_selecionados) == 2:
                                self._tentar_alocar_tropas()
                    return

    def _tentar_mira(self, pos, estado):
        """Interpreta os cliques durante o uso de uma carta que exige escolher Castelos ou Dados."""
        try:
            if self.modo_mira == "MARCHA_ORIGEM":
                # Verifica colisões nos 11 castelos usando teorema de Pitágoras (distância radial)
                for id_c, info_c in estado['castelos'].items():
                    pos_castelo = POSICOES_CASTELOS[info_c['id_local']]
                    distancia = math.hypot(pos[0] - pos_castelo[0], pos[1] - pos_castelo[1])
                    
                    if distancia <= 25:
                        tropas_do_jogador = info_c[f'tropas_j{estado["jogador_atual"]}']
                        if tropas_do_jogador <= 0:
                            raise ValueError("Você não tem tropas neste castelo.")
                            
                        self.origem_mira = id_c
                        self.modo_mira = "MARCHA_DESTINO"
                        self.mensagem_aviso = "MARCHA: Selecione o castelo de DESTINO."
                        return
                        
                raise ValueError("Clique em um castelo válido.")
                
            elif self.modo_mira == "MARCHA_DESTINO":
                for id_c, info_c in estado['castelos'].items():
                    pos_castelo = POSICOES_CASTELOS[info_c['id_local']]
                    distancia = math.hypot(pos[0] - pos_castelo[0], pos[1] - pos_castelo[1])
                    
                    if distancia <= 25:
                        jogador_da_vez = estado['jogador_atual']
                        self.jogo.executar_marcha(jogador_da_vez, self.carta_mira_indice, self.origem_mira, id_c)
                        self._encerrar_turno()
                        return
                        
                raise ValueError("Clique no castelo de destino.")
                
            elif self.modo_mira == "MIRA_DADO":
                for i in range(len(self.rects_dados)):
                    rect = self.rects_dados[i]
                    if rect.collidepoint(pos):
                        jogador_da_vez = estado['jogador_atual']
                        self.jogo.executar_alteracao_dado(jogador_da_vez, self.carta_mira_indice, i)
                        # Atualiza a interface com a lista de dados modificada pelo backend
                        self.dados_na_tela = self.jogo.dados_atuais 
                        self._cancelar_mira()
                        return
                        
                raise ValueError("Clique no dado alvo.")
                
        except ValueError as e:
            self.mensagem_aviso = str(e)

    def _tentar_comprar_carta(self, indice, efeito, estado):
        """Avalia se a carta comprada resolve imediatamente ou se exige ativação de modo mira."""
        try:
            if efeito != 'marchar':
                if len(self.dados_na_tela) == 0:
                    raise ValueError("Você precisa rolar os dados primeiro!")
                
            if efeito == 'marchar':
                self.modo_mira = "MARCHA_ORIGEM"
                self.carta_mira_indice = indice
                self.mensagem_aviso = "MARCHA: Selecione a ORIGEM (Direito cancela)"
            elif efeito == '+1_dado' or efeito == '-1_dado' or efeito == 'inverter_dado':
                self.modo_mira = "MIRA_DADO"
                self.carta_mira_indice = indice
                self.mensagem_aviso = "Selecione o dado que deseja alterar (Direito cancela)"
            else:
                jogador_da_vez = estado['jogador_atual']
                self.jogo.usar_carta(jogador_da_vez, indice)
                self.dados_na_tela = self.jogo.dados_atuais
                self.indices_selecionados = []
        except ValueError as e:
            self.mensagem_aviso = str(e)

    def _tentar_alocar_tropas(self):
        """Descobre qual dado sobrou na seleção para enviar ao backend como força da tropa."""
        idx_tropa = -1
        for i in range(3):
            if i not in self.indices_selecionados:
                idx_tropa = i
                break
                
        dado_1 = self.dados_na_tela[self.indices_selecionados[0]]
        dado_2 = self.dados_na_tela[self.indices_selecionados[1]]
        dados_castelo = [dado_1, dado_2]
        dado_tropa = self.dados_na_tela[idx_tropa]
        
        try:
            self.jogo.jogar_turno(dados_castelo, dado_tropa)
            self._encerrar_turno()
        except ValueError as e:
            self.mensagem_aviso = str(e)
            self.indices_selecionados.pop() # Remove a última seleção para o jogador tentar de novo

    def _encerrar_turno(self):
        """Limpa as váriaveis locais para receber o turno do próximo jogador."""
        self.dados_na_tela = []
        self.indices_selecionados = []
        self._cancelar_mira()
        
        estado = self.jogo.obter_estado()
        if estado['fim_de_jogo']:
            self.tela_atual = "AUDITORIA"

    def _cancelar_mira(self):
        """Aborta a ação da carta se o jogador clicar com o botão direito."""
        self.modo_mira = None
        self.origem_mira = -1
        self.carta_mira_indice = -1

    def _desenhar_texto_caixa(self, texto, fonte, cor_texto, pos):
        """Função utilitária que pinta um fundo preto semi-transparente atrás das strings."""
        surf_txt = fonte.render(texto, True, cor_texto)
        rect = surf_txt.get_rect(center=pos)
        
        fundo = pygame.Surface((rect.width + 16, rect.height + 8))
        fundo.set_alpha(180)
        fundo.fill(COR_PRETA)
        
        self.tela.blit(fundo, (rect.x - 8, rect.y - 4))
        self.tela.blit(surf_txt, rect)

    def _desenhar_tela(self):
        """Direciona a renderização gráfica de acordo com a tela atual."""
        if self.assets['fundo'] is not None:
            self.tela.blit(self.assets['fundo'], (0, 0))
        else:
            self.tela.fill(COR_FUNDO)

        if self.tela_atual == "MENU":
            self._desenhar_texto_caixa("RUMBLE NATION", self.fontes['titulo'], COR_BRANCA, (500, 150))
            
            pygame.draw.rect(self.tela, (200, 200, 200), (300, 300, 400, 60))
            pygame.draw.rect(self.tela, COR_PRETA, (300, 300, 400, 60), 2)
            texto_18 = self.fontes['botao'].render("Partida Rápida (18 Tropas)", True, COR_PRETA)
            self.tela.blit(texto_18, texto_18.get_rect(center=(500, 330)))
            
            pygame.draw.rect(self.tela, (200, 200, 200), (300, 400, 400, 60))
            pygame.draw.rect(self.tela, COR_PRETA, (300, 400, 400, 60), 2)
            texto_36 = self.fontes['botao'].render("Partida Completa (36 Tropas)", True, COR_PRETA)
            self.tela.blit(texto_36, texto_36.get_rect(center=(500, 430)))
                
        elif self.tela_atual == "RODANDO" or self.tela_atual == "AUDITORIA":
            estado = self.jogo.obter_estado()
            
            # Desenha as bases físicas: Os castelos e as tropas em cima deles
            for id_c, info_c in estado['castelos'].items():
                pos = POSICOES_CASTELOS[info_c['id_local']]
                
                if info_c['conquistado']:
                    cor_borda = (200, 200, 200) # Fica cinza quando a auditoria pontua o castelo
                else:
                    cor_borda = COR_PRETA
                    
                pygame.draw.circle(self.tela, cor_borda, pos, 25)
                pygame.draw.circle(self.tela, COR_BRANCA, pos, 23)
                
                texto_id = self.fontes['castelo'].render(str(id_c), True, COR_PRETA)
                self.tela.blit(texto_id, texto_id.get_rect(center=pos))
                
                # Renderiza o meeple/círculo do Jogador 1 à esquerda do castelo
                tropas_j1 = info_c['tropas_j1']
                if tropas_j1 > 0:
                    pos_t1 = (pos[0] - 25, pos[1] - 25)
                    pygame.draw.circle(self.tela, COR_JOGADOR_1, pos_t1, 15)
                    pygame.draw.circle(self.tela, COR_PRETA, pos_t1, 15, 2)
                    texto_t1 = self.fontes['tropas'].render(str(tropas_j1), True, COR_BRANCA)
                    self.tela.blit(texto_t1, texto_t1.get_rect(center=pos_t1))

                # Renderiza o meeple/círculo do Jogador 2 à direita do castelo
                tropas_j2 = info_c['tropas_j2']
                if tropas_j2 > 0:
                    pos_t2 = (pos[0] + 25, pos[1] - 25)
                    pygame.draw.circle(self.tela, COR_JOGADOR_2, pos_t2, 15)
                    pygame.draw.circle(self.tela, COR_PRETA, pos_t2, 15, 2)
                    texto_t2 = self.fontes['tropas'].render(str(tropas_j2), True, COR_BRANCA)
                    self.tela.blit(texto_t2, texto_t2.get_rect(center=pos_t2))

            # Desenha um halo amarelo sobre o castelo sendo selecionado para a Marcha
            if self.origem_mira != -1:
                id_local = estado['castelos'][self.origem_mira]['id_local']
                pos_mira = POSICOES_CASTELOS[id_local]
                pygame.draw.circle(self.tela, (255, 200, 0), pos_mira, 30, 4)

            # Sobrepõe os elementos específicos do estado atual (Menus de baixo)
            if self.tela_atual == "RODANDO":
                self._desenhar_hud_rodando(estado)
            else:
                self._desenhar_hud_auditoria()

        elif self.tela_atual == "FIM":
            self._desenhar_hud_fim()

        pygame.display.flip()

    def _desenhar_hud_rodando(self, estado):
        """Pinta o nome do jogador do turno, os dados rolados e as cartas táticas."""
        if estado['jogador_atual'] == 1:
            cor_vez = COR_JOGADOR_1
        else:
            cor_vez = COR_JOGADOR_2
            
        texto_vez = f"Jogador {estado['jogador_atual']}"
        self._desenhar_texto_caixa(texto_vez, self.fontes['titulo'], cor_vez, (500, 40))

        # --- AVALIA O STATUS PARA RENDERIZAR O BOTÃO PRINCIPAL ---
        jogador_da_vez = estado['jogador_atual']
        tropas_atuais = estado['jogadores'][jogador_da_vez]['tropas']
        
        if tropas_atuais == 0:
            pygame.draw.rect(self.tela, (255, 200, 50), self.rect_rolar)
            txt_btn = "Passar Vez"
            cor_texto_botao = COR_PRETA
        else:
            if len(self.dados_na_tela) == 0:
                cor_fundo_botao = (200, 200, 200) # Ativo (Claridade)
                cor_texto_botao = COR_PRETA
            else:
                cor_fundo_botao = (150, 150, 150) # Inativo (Escuro)
                cor_texto_botao = (100, 100, 100)
            pygame.draw.rect(self.tela, cor_fundo_botao, self.rect_rolar)
            txt_btn = "Rolar Dados"
            
        pygame.draw.rect(self.tela, COR_PRETA, self.rect_rolar, 2)
        
        texto_render = self.fontes['botao'].render(txt_btn, True, cor_texto_botao)
        self.tela.blit(texto_render, texto_render.get_rect(center=self.rect_rolar.center))

        # --- RENDERIZAÇÃO DOS DADOS ---
        if len(self.dados_na_tela) > 0:
            for i in range(len(self.dados_na_tela)):
                val = self.dados_na_tela[i]
                rect_dado = self.rects_dados[i]
                
                # Tenta desenhar a imagem da face do dado
                if self.assets['dados'][val] is not None:
                    self.tela.blit(self.assets['dados'][val], rect_dado.topleft)
                    
                    if i in self.indices_selecionados:
                        pygame.draw.rect(self.tela, (50, 220, 50), rect_dado, 4) # Moldura de seleção
                    else:
                        pygame.draw.rect(self.tela, COR_PRETA, rect_dado, 2)
                else:
                    # Desenho geométrico substituto (Fallback)
                    if i in self.indices_selecionados:
                        cor_fundo_dado = (150, 255, 150)
                    else:
                        cor_fundo_dado = (255, 255, 255)
                    pygame.draw.rect(self.tela, cor_fundo_dado, rect_dado)
                    pygame.draw.rect(self.tela, COR_PRETA, rect_dado, 2)
                    
                    texto_num = self.fontes['dado'].render(str(val), True, COR_PRETA)
                    self.tela.blit(texto_num, texto_num.get_rect(center=rect_dado.center))

        # --- RENDERIZAÇÃO DO MERCADO RETRÁTIL ---
        aba = pygame.Rect(20, 20, 120, 35)
        surf_aba = pygame.Surface(aba.size)
        surf_aba.set_alpha(220)
        
        if estado['mercado_bloqueado']:
            surf_aba.fill((150, 50, 50))
            txt_aba = "Fechado"
        else:
            surf_aba.fill((50, 50, 50))
            if self.mercado_expandido:
                txt_aba = "▲ Ocultar"
            else:
                txt_aba = "▼ Cartas"
                
        self.tela.blit(surf_aba, aba)
        pygame.draw.rect(self.tela, COR_BRANCA, aba, 2)
        
        texto_render = self.fontes['aviso'].render(txt_aba, True, COR_BRANCA)
        self.tela.blit(texto_render, texto_render.get_rect(center=aba.center))

        if self.mercado_expandido:
            # Fundo que protege a leitura das cartas (Hover)
            fundo_c = pygame.Surface((300, 140))
            fundo_c.set_alpha(180)
            fundo_c.fill(COR_PRETA)
            self.tela.blit(fundo_c, (15, 60))
            
            usou_carta = estado['jogadores'][estado['jogador_atual']]['usou_carta']
            
            pode_comprar = False
            if not estado['mercado_bloqueado']:
                if not usou_carta:
                    pode_comprar = True
            
            for i in range(len(estado['mercado'])):
                carta = estado['mercado'][i]
                r_c = pygame.Rect(20 + i * 100, 65, 90, 130)
                
                ativo = False
                if pode_comprar:
                    ativo = True
                elif self.modo_mira is not None:
                    ativo = True
                    
                if ativo:
                    if self.carta_mira_indice == i:
                        cor_fundo_carta = (255, 250, 200)
                        cor_borda_carta = (255, 200, 0) # Destaca a carta sendo ativada
                        espessura = 4
                    else:
                        cor_fundo_carta = (250, 240, 220)
                        cor_borda_carta = COR_PRETA
                        espessura = 2
                        
                    pygame.draw.rect(self.tela, cor_fundo_carta, r_c)
                    pygame.draw.rect(self.tela, cor_borda_carta, r_c, espessura)
                    cor_txt = COR_PRETA
                else:
                    pygame.draw.rect(self.tela, (210, 210, 210), r_c)
                    pygame.draw.rect(self.tela, (150, 150, 150), r_c, 2)
                    cor_txt = (150, 150, 150)
                
                palavras = carta['nome'].split()
                if len(palavras) == 1:
                    texto_linha = self.fontes['tropas'].render(palavras[0], True, cor_txt)
                    self.tela.blit(texto_linha, texto_linha.get_rect(center=r_c.center))
                else:
                    texto_linha1 = self.fontes['tropas'].render(palavras[0], True, cor_txt)
                    texto_linha2 = self.fontes['tropas'].render(" ".join(palavras[1:]), True, cor_txt)
                    self.tela.blit(texto_linha1, texto_linha1.get_rect(center=(r_c.centerx, r_c.centery - 10)))
                    self.tela.blit(texto_linha2, texto_linha2.get_rect(center=(r_c.centerx, r_c.centery + 10)))

        # --- AVISOS CONSTANTES E NOTIFICAÇÕES ---
        mods = []
        mod_c = estado['modificador_castelo']
        if mod_c != 0:
            if mod_c > 0:
                sinal = "+"
            else:
                sinal = ""
            mods.append(f"{sinal}{mod_c} Castelo")
            
        mod_t = estado['modificador_tropas']
        if mod_t != 0:
            if mod_t > 0:
                sinal = "+"
            else:
                sinal = ""
            mods.append(f"{sinal}{mod_t} Tropa")
            
        if len(mods) > 0: 
            texto_mod = f"Modificador: {' | '.join(mods)}"
            self._desenhar_texto_caixa(texto_mod, self.fontes['botao'], (255, 200, 50), (500, 600))
            
        usou_j1 = estado['jogadores'][1]['usou_carta']
        usou_j2 = estado['jogadores'][2]['usou_carta']
        
        if usou_j1:
            texto_j1 = "Sim"
        else:
            texto_j1 = "Não"
            
        if usou_j2:
            texto_j2 = "Sim"
        else:
            texto_j2 = "Não"
            
        texto_uso = f"Carta Usada: J1({texto_j1}) | J2({texto_j2})"
        self._desenhar_texto_caixa(texto_uso, self.fontes['aviso'], COR_BRANCA, (500, 640))
        
        if self.mensagem_aviso != "":
            self._desenhar_texto_caixa(self.mensagem_aviso, self.fontes['aviso'], (255, 100, 100), (500, 680))

    def _desenhar_hud_auditoria(self):
        """Mostra o painel com os pontos de vitória ganhos a cada 'Próximo Castelo'."""
        pygame.draw.rect(self.tela, (200, 200, 200), (350, 630, 300, 50))
        pygame.draw.rect(self.tela, COR_PRETA, (350, 630, 300, 50), 2)
        
        texto_botao = self.fontes['botao'].render("Próximo Castelo", True, COR_PRETA)
        self.tela.blit(texto_botao, texto_botao.get_rect(center=(500, 655)))
        
        self._desenhar_texto_caixa(self.jogo.mensagem_auditoria, self.fontes['botao'], COR_BRANCA, (500, 580))
        self._desenhar_placar(50)

    def _desenhar_hud_fim(self):
        """Encerra a partida e desenha o botão de retornar ao menu."""
        pts1 = self.jogo.pontuacao_parcial[1]
        pts2 = self.jogo.pontuacao_parcial[2]
        
        if pts1 > pts2: 
            txt = "Vitória do Jogador 1!"
            cor = COR_JOGADOR_1
        elif pts2 > pts1: 
            txt = "Vitória do Jogador 2!"
            cor = COR_JOGADOR_2
        else: 
            txt = "Empate!"
            cor = COR_BRANCA
            
        self._desenhar_texto_caixa(txt, self.fontes['titulo'], cor, (500, 300))
        self._desenhar_placar(380)
        
        pygame.draw.rect(self.tela, (200, 200, 200), (350, 640, 300, 50))
        pygame.draw.rect(self.tela, COR_PRETA, (350, 640, 300, 50), 2)
        
        texto_botao = self.fontes['botao'].render("Jogar Novamente", True, COR_PRETA)
        self.tela.blit(texto_botao, texto_botao.get_rect(center=(500, 665)))

    def _desenhar_placar(self, y_pos):
        """Monta o banner retangular com a pontuação 'J1 X x Y J2'."""
        pts1 = self.jogo.pontuacao_parcial[1]
        pts2 = self.jogo.pontuacao_parcial[2]
        
        if y_pos == 50:
            largura_rect = 300
            altura_rect = 60
        else:
            largura_rect = 400
            altura_rect = 50
            
        r = pygame.Rect(0, 0, largura_rect, altura_rect)
        r.center = (500, y_pos)
        
        f = pygame.Surface(r.size)
        f.set_alpha(180)
        f.fill(COR_PRETA)
        self.tela.blit(f, r.topleft)
        
        if y_pos == 50:
            texto_base = "Placar: "
            texto_j1 = f"J1 {pts1}"
            texto_meio = " x "
            texto_j2 = f"{pts2} J2"
        else:
            texto_base = "  |  "
            texto_j1 = f"J1: {pts1} pontos"
            texto_meio = "  |  "
            texto_j2 = f"J2: {pts2} pontos"
        
        t_base = self.fontes['botao'].render(texto_base, True, COR_BRANCA)
        t_j1 = self.fontes['botao'].render(texto_j1, True, COR_JOGADOR_1)
        
        if y_pos == 50:
            t_x = self.fontes['botao'].render(texto_meio, True, COR_BRANCA)
        else:
            t_x = t_base
            
        t_j2 = self.fontes['botao'].render(texto_j2, True, COR_JOGADOR_2)
        
        if y_pos == 50:
            largura_total = t_base.get_width() + t_j1.get_width() + t_x.get_width() + t_j2.get_width()
        else:
            largura_total = t_j1.get_width() + t_x.get_width() + t_j2.get_width()
            
        x = (1000 - largura_total) // 2
        y = y_pos - (t_j1.get_height() // 2)
        
        if y_pos == 50:
            self.tela.blit(t_base, (x, y))
            x += t_base.get_width()
            
        self.tela.blit(t_j1, (x, y))
        x += t_j1.get_width()
        self.tela.blit(t_x, (x, y))
        x += t_x.get_width()
        self.tela.blit(t_j2, (x, y))

if __name__ == "__main__":
    app = InterfaceJogo()
    app.iniciar()