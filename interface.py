import pygame
import sys
import os
import math
from logica_jogo import LogicaJogo, TipoJogada, CARTA_MARCHA
from arvore import ArvoreDeEstados, NavegadorDeArvore, ARQUIVO_ARVORE

# Dicionário estático: mapeia o ID do terreno (0 a 10) para suas coordenadas exatas (X, Y) na tela.
POSICOES_CASTELOS = {
    0: (680, 440), 1: (760, 520), 2: (840, 320), 3: (580, 280),
    4: (100, 220), 5: (320, 200), 6: (940, 100), 7: (200, 400),
    8: (520, 520), 9: (430, 400), 10: (120, 600)
}

# Paleta de cores padrão
COR_FUNDO = (240, 240, 240)
COR_PRETA = (0, 0, 0)
COR_BRANCA = (255, 255, 255)
COR_JOGADOR_1 = (255, 80, 80)
COR_JOGADOR_2 = (80, 150, 255)
COR_ALVO = (255, 200, 0)

class InterfaceJogo:
    """
    Controlador Pygame. Não conhece regras nem a estrutura da árvore:
      - cada clique é traduzido pelo motor em uma Jogada (jogada_de_alocacao, jogada_de_carta, ...);
      - toda Jogada passa por um único método, _executar_jogada(), que chama navegador.jogar();
      - voltar, salvar e carregar também são pedidos ao navegador.
    """
    def __init__(self):
        pygame.init()
        self.tela = pygame.display.set_mode((1000, 700))
        pygame.display.set_caption("Rumble Nation")
        self.relogio = pygame.time.Clock()

        self.fontes = {
            'castelo': pygame.font.SysFont('Arial', 20, bold=True),
            'tropas': pygame.font.SysFont('Arial', 16, bold=True),
            'botao': pygame.font.SysFont('Arial', 24, bold=True),
            'dado': pygame.font.SysFont('Arial', 40, bold=True),
            'titulo': pygame.font.SysFont('Arial', 40, bold=True),
            'aviso': pygame.font.SysFont('Arial', 20, bold=True),
            'status': pygame.font.SysFont('Arial', 15, bold=True)
        }

        self.assets = self._carregar_assets()
        self._resetar_estado()

    def _carregar_assets(self):
        arquivos_carregados = {}
        caminho_fundo = "assets/fundo.png"
        if os.path.exists(caminho_fundo):
            imagem = pygame.image.load(caminho_fundo).convert_alpha()
            arquivos_carregados['fundo'] = pygame.transform.smoothscale(imagem, (1000, 700))
        else:
            arquivos_carregados['fundo'] = None

        caminho_capa = "assets/capa.png"
        if os.path.exists(caminho_capa):
            imagem_capa = pygame.image.load(caminho_capa).convert_alpha()
            arquivos_carregados['capa'] = pygame.transform.smoothscale(imagem_capa, (1000, 700))
        else:
            arquivos_carregados['capa'] = None

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
        self.navegador = None # Motor + árvore sincronizados (criado ao iniciar ou carregar uma partida)
        self.jogo = None # Atalho para o motor ao vivo (é o mesmo objeto que self.navegador.motor)
        self.tela_atual = "MENU"
        self.mensagem_aviso = ""
        self.indices_selecionados = []
        self.origem_mira = -1 # 1º clique da carta Marchar (a jogada só nasce no clique do destino)
        self.mercado_expandido = False
        self.rects_dados = [
            pygame.Rect(770, 540, 60, 60),
            pygame.Rect(840, 540, 60, 60),
            pygame.Rect(910, 540, 60, 60)
        ]
        self.rect_rolar = pygame.Rect(770, 620, 200, 50)

    def iniciar(self):
        while True:
            self._processar_eventos()
            self._desenhar_tela()
            self.relogio.tick(60)

    def _processar_eventos(self):
        pos_mouse = pygame.mouse.get_pos()
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
                if evento.button == 3:
                    self._clique_direito()
                elif evento.button == 1:
                    self._rotear_clique(evento.pos)

            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_LEFT:
                    self._voltar_no_tempo()
                elif evento.key == pygame.K_s:
                    self._salvar_arvore()
                elif evento.key == pygame.K_l:
                    self._carregar_arvore()

    def _rotear_clique(self, pos):
        self.mensagem_aviso = ""

        if self.tela_atual == "MENU":
            rect_botao_18 = pygame.Rect(300, 520, 400, 50)
            rect_botao_36 = pygame.Rect(300, 590, 400, 50)

            if rect_botao_18.collidepoint(pos):
                self._nova_partida(18)
            elif rect_botao_36.collidepoint(pos):
                self._nova_partida(36)

        elif self.tela_atual == "RODANDO":
            self._processar_clique_rodando(pos)

        elif self.tela_atual == "AUDITORIA":
            rect_auditoria = pygame.Rect(350, 630, 300, 50)
            if rect_auditoria.collidepoint(pos):
                terminou, msg = self.jogo.resolver_batalha_atual() # o motor guarda a mensagem sozinho
                if terminou:
                    self.tela_atual = "FIM"

        elif self.tela_atual == "FIM":
            rect_reiniciar = pygame.Rect(350, 640, 300, 50)
            if rect_reiniciar.collidepoint(pos):
                self._resetar_estado()

    # =========================================================================
    #  ÁRVORE DE ESTADOS: tudo passa pelo navegador
    # =========================================================================

    def _nova_partida(self, tropas):
        """Cria o motor e a árvore juntos. A raiz já nasce com o seu nível de jogadas possíveis."""
        self.navegador = NavegadorDeArvore(LogicaJogo(tropas))
        self.jogo = self.navegador.motor
        self.indices_selecionados = []
        self.origem_mira = -1
        self.tela_atual = "RODANDO"

    def _executar_jogada(self, jogada):
        """
        ÚNICO ponto por onde uma jogada real passa.
        O navegador aplica a jogada no motor, confere que o resultado é exatamente o nó que
        já estava previsto e move o ponteiro da árvore até ele. Nenhum nó é criado aqui.
        """
        self.navegador.jogar(jogada)
        self.indices_selecionados = []
        self.origem_mira = -1
        if self.jogo.obter_estado()['fim_de_jogo']:
            self.tela_atual = "AUDITORIA"
            self._salvar_arvore(automatico=True)

    def _voltar_no_tempo(self):
        """Rebobina a fita: o navegador desempilha o caminho e recarrega o estado no motor."""
        if self.navegador is None or self.tela_atual == "MENU":
            return
        jogada_desfeita = self.navegador.no_atual().titulo.split("\n")[0]
        if self.navegador.voltar() is None:
            self.mensagem_aviso = "Você já está no início da partida."
            return
        self.indices_selecionados = []
        self.origem_mira = -1
        if self.tela_atual == "AUDITORIA" or self.tela_atual == "FIM":
            self.tela_atual = "RODANDO"
        self.mensagem_aviso = f"Jogada desfeita: {jogada_desfeita}"

    def _salvar_arvore(self, automatico=False):
        if self.navegador is None:
            self.mensagem_aviso = "Nenhuma partida em andamento para salvar."
            return
        try:
            arquivos = self.navegador.salvar(ARQUIVO_ARVORE)
        except OSError as erro:
            self.mensagem_aviso = f"Não foi possível salvar a árvore: {erro}"
            return
        extensoes = ", ".join(os.path.splitext(arquivo)[1][1:].upper() for arquivo in arquivos)
        prefixo = "Fim de jogo! Árvore final salva" if automatico else "Árvore salva"
        self.mensagem_aviso = f"{prefixo} ({extensoes})"

    def _carregar_arvore(self):
        arvore = ArvoreDeEstados()
        try:
            arvore.carregar_json(ARQUIVO_ARVORE + ".json")
        except FileNotFoundError:
            self.mensagem_aviso = f"Arquivo {ARQUIVO_ARVORE}.json não encontrado."
            return
        except (ValueError, KeyError) as erro:
            self.mensagem_aviso = f"Não foi possível carregar: {erro}"
            return

        # O motor é montado direto no estado em que a partida salva parou
        self.navegador = NavegadorDeArvore(LogicaJogo(estado=arvore.no_atual().estado), arvore)
        self.jogo = self.navegador.motor
        self.indices_selecionados = []
        self.origem_mira = -1
        self.tela_atual = "AUDITORIA" if self.jogo.obter_estado()['fim_de_jogo'] else "RODANDO"
        self.mensagem_aviso = f"Árvore carregada: {len(arvore.nos)} nós"

    # =========================================================================
    #  CLIQUES → JOGADAS
    # =========================================================================

    def _processar_clique_rodando(self, pos):
        estado = self.jogo.obter_estado()
        try:
            if estado['carta_pendente'] is not None:
                self._clique_alvo_da_carta(pos, estado)
            elif self.rect_rolar.collidepoint(pos):
                self._clique_botao_rolar()
            elif not self._clique_no_mercado(pos, estado):
                self._clique_nos_dados(pos, estado)
        except ValueError as e:
            self.mensagem_aviso = str(e)

    def _clique_botao_rolar(self):
        """O botão vira 'Passar Vez' ou 'Rerrolar' conforme as jogadas que existem no nó atual."""
        tipos = {jogada.tipo for jogada in self.navegador.jogadas_disponiveis()}
        if TipoJogada.PASSAR in tipos:
            self._executar_jogada(self.jogo.obter_jogada(TipoJogada.PASSAR))
        elif TipoJogada.RERROLAR in tipos:
            self._executar_jogada(self.jogo.obter_jogada(TipoJogada.RERROLAR))
        else:
            self.mensagem_aviso = "Você já utilizou sua rerrolagem livre neste turno."

    def _clique_no_mercado(self, pos, estado):
        """Retorna True se o clique caiu em uma carta do mercado (expandido)."""
        if not self.mercado_expandido:
            return False
        for i in range(len(estado['mercado'])):
            rect_carta = pygame.Rect(20 + i * 100, 65, 90, 130)
            if rect_carta.collidepoint(pos):
                self.indices_selecionados = []
                self._executar_jogada(self.jogo.jogada_de_carta(i))
                return True
        return False

    def _clique_nos_dados(self, pos, estado):
        # --- TRAVA DE SEGURANÇA 2: os dados só respondem se o motor listar alguma alocação ---
        if not any(jogada.tipo == TipoJogada.ALOCAR for jogada in self.navegador.jogadas_disponiveis()):
            return
        for i in range(len(self.rects_dados)):
            rect = self.rects_dados[i]
            if rect.collidepoint(pos):
                if i in self.indices_selecionados:
                    self.indices_selecionados.remove(i)
                else:
                    if len(self.indices_selecionados) < 2:
                        self.indices_selecionados.append(i)
                        if len(self.indices_selecionados) == 2:
                            self._tentar_alocar_tropas()
                return

    def _tentar_alocar_tropas(self):
        try:
            self._executar_jogada(self.jogo.jogada_de_alocacao(self.indices_selecionados))
        except ValueError:
            self.indices_selecionados.pop()
            raise

    def _clique_alvo_da_carta(self, pos, estado):
        """Com uma carta de alvo ativada, o clique escolhe o alvo (que é a próxima jogada da árvore)."""
        if estado['carta_pendente']['efeito'] == CARTA_MARCHA:
            id_castelo = self._castelo_em(pos, estado)
            if id_castelo is None:
                return
            if self.origem_mira == -1:
                origens = [jogada.args[0] for jogada in self.navegador.jogadas_disponiveis() if jogada.tipo == TipoJogada.MARCHA]
                if id_castelo not in origens:
                    raise ValueError("Sem tropas neste castelo.")
                self.origem_mira = id_castelo
            elif id_castelo == self.origem_mira:
                self.origem_mira = -1
            else:
                self._executar_jogada(self.jogo.jogada_de_marcha(self.origem_mira, id_castelo))
        else:
            for i in range(len(self.rects_dados)):
                if self.rects_dados[i].collidepoint(pos):
                    self._executar_jogada(self.jogo.jogada_de_alvo_dado(i))
                    return

    def _clique_direito(self):
        """Limpa a seleção. Com uma carta ativada, cancela a carta (= volta 1 nó na árvore)."""
        if self.tela_atual != "RODANDO":
            return
        if self.origem_mira != -1:
            self.origem_mira = -1
        elif self.jogo.obter_estado()['carta_pendente'] is not None:
            self._voltar_no_tempo()
        else:
            self.indices_selecionados = []

    def _castelo_em(self, pos, estado):
        for id_c, info_c in estado['castelos'].items():
            pos_castelo = POSICOES_CASTELOS[info_c['id_local']]
            if math.hypot(pos[0] - pos_castelo[0], pos[1] - pos_castelo[1]) <= 25:
                return id_c
        return None

    # =========================================================================
    #  DESENHO
    # =========================================================================

    def _desenhar_texto_caixa(self, texto, fonte, cor_texto, pos, alinhar_esquerda=False):
        surf_txt = fonte.render(texto, True, cor_texto)
        if alinhar_esquerda:
            rect = surf_txt.get_rect(midleft=pos) # pos é onde o texto começa (borda esquerda)
        else:
            rect = surf_txt.get_rect(center=pos)
        fundo = pygame.Surface((rect.width + 16, rect.height + 8))
        fundo.set_alpha(180)
        fundo.fill(COR_PRETA)
        self.tela.blit(fundo, (rect.x - 8, rect.y - 4))
        self.tela.blit(surf_txt, rect)

    def _desenhar_tela(self):
        if self.tela_atual == "MENU":
            if self.assets.get('capa'): self.tela.blit(self.assets['capa'], (0, 0))
            else: self.tela.fill(COR_FUNDO)
        else:
            if self.assets.get('fundo'): self.tela.blit(self.assets['fundo'], (0, 0))
            else: self.tela.fill(COR_FUNDO)

        if self.tela_atual == "MENU":
            for btn_y, txt, cmd in [(520, "Partida Rápida (18)", 18), (590, "Partida Completa (36)", 36)]:
                rect = pygame.Rect(300, btn_y, 400, 50)
                surf = pygame.Surface(rect.size, pygame.SRCALPHA)
                surf.fill((0, 0, 0, 180))
                self.tela.blit(surf, rect.topleft)
                pygame.draw.rect(self.tela, (255, 200, 50), rect, 1)
                t_rend = self.fontes['botao'].render(txt, True, COR_BRANCA)
                self.tela.blit(t_rend, t_rend.get_rect(center=rect.center))
            self._desenhar_texto_caixa("L: carregar a última árvore salva", self.fontes['status'], COR_BRANCA, (500, 668))
            if self.mensagem_aviso: self._desenhar_texto_caixa(self.mensagem_aviso, self.fontes['aviso'], (255, 100, 100), (500, 485))

        elif self.tela_atual in ["RODANDO", "AUDITORIA"]:
            estado = self.jogo.obter_estado()

            for id_c, info_c in estado['castelos'].items():
                pos = POSICOES_CASTELOS[info_c['id_local']]
                pygame.draw.circle(self.tela, (200, 200, 200) if info_c['conquistado'] else COR_PRETA, pos, 25)
                pygame.draw.circle(self.tela, COR_BRANCA, pos, 23)
                txt_id = self.fontes['castelo'].render(str(id_c), True, COR_PRETA)
                self.tela.blit(txt_id, txt_id.get_rect(center=pos))

                for j_id, dx, cor in [(1, -25, COR_JOGADOR_1), (2, 25, COR_JOGADOR_2)]:
                    if info_c[f'tropas_j{j_id}'] > 0:
                        pos_t = (pos[0] + dx, pos[1] - 25)
                        pygame.draw.circle(self.tela, cor, pos_t, 15)
                        pygame.draw.circle(self.tela, COR_PRETA, pos_t, 15, 2)
                        t_qtd = self.fontes['tropas'].render(str(info_c[f'tropas_j{j_id}']), True, COR_BRANCA)
                        self.tela.blit(t_qtd, t_qtd.get_rect(center=pos_t))

            if self.origem_mira != -1:
                pygame.draw.circle(self.tela, COR_ALVO, POSICOES_CASTELOS[estado['castelos'][self.origem_mira]['id_local']], 30, 4)
                # Destinos possíveis da marcha (são as arestas 'marcha:origem,destino' do nó atual)
                for jogada in self.navegador.jogadas_disponiveis():
                    if jogada.tipo == TipoJogada.MARCHA and jogada.args[0] == self.origem_mira:
                        pos_destino = POSICOES_CASTELOS[estado['castelos'][jogada.args[1]]['id_local']]
                        pygame.draw.circle(self.tela, (120, 220, 120), pos_destino, 30, 3)

            if self.tela_atual == "RODANDO": self._desenhar_hud_rodando(estado)
            else: self._desenhar_hud_auditoria()

        elif self.tela_atual == "FIM":
            self._desenhar_hud_fim()

        pygame.display.flip()

    def _texto_instrucao(self, estado):
        pendente = estado['carta_pendente']
        if pendente is None:
            return ""
        if pendente['efeito'] == CARTA_MARCHA:
            if self.origem_mira == -1:
                return "Marchar: clique na ORIGEM (direito cancela)"
            return "Marchar: clique no DESTINO (direito volta)"
        return f"{pendente['nome']}: clique no dado (direito cancela)"

    def _desenhar_hud_rodando(self, estado):
        jogadas = self.navegador.jogadas_disponiveis()
        tipos = {jogada.tipo for jogada in jogadas}
        pendente = estado['carta_pendente']

        self._desenhar_texto_caixa(f"Estoque J1: {estado['jogadores'][1]['tropas']} tropas", self.fontes['aviso'], COR_JOGADOR_1, (23, 680), alinhar_esquerda=True)
        self._desenhar_texto_caixa(f"Estoque J2: {estado['jogadores'][2]['tropas']} tropas", self.fontes['aviso'], COR_JOGADOR_2, (870, 20))
        self._desenhar_texto_caixa(f"Jogador {estado['jogador_atual']}", self.fontes['titulo'], COR_JOGADOR_1 if estado['jogador_atual']==1 else COR_JOGADOR_2, (500, 40))

        # O texto do botão vem das jogadas que existem no nó atual da árvore
        if pendente is not None:
            btn_t, bg_c, txt_c = ("Escolha o alvo", (150, 150, 150), (90, 90, 90))
        elif TipoJogada.PASSAR in tipos:
            btn_t, bg_c, txt_c = ("Passar Vez", (255, 200, 50), COR_PRETA)
        elif TipoJogada.RERROLAR in tipos:
            btn_t, bg_c, txt_c = (f"Rerrolar ({estado['rerrolagens_disponiveis']})", (200, 200, 200), COR_PRETA)
        else:
            btn_t, bg_c, txt_c = ("0 Rerrolagens", (150, 150, 150), (100, 100, 100))
        pygame.draw.rect(self.tela, bg_c, self.rect_rolar)
        pygame.draw.rect(self.tela, COR_PRETA, self.rect_rolar, 2)
        txt_r = self.fontes['botao'].render(btn_t, True, txt_c)
        self.tela.blit(txt_r, txt_r.get_rect(center=self.rect_rolar.center))

        # Com uma carta de dado ativada, os dados que podem ser alvo ganham borda amarela
        valores_alvo = {jogada.args[0] for jogada in jogadas if jogada.tipo == TipoJogada.ALVO_DADO}
        for i, val in enumerate(estado['dados_atuais']):
            rect = self.rects_dados[i]
            selecionado = i in self.indices_selecionados
            alvo = val in valores_alvo
            if self.assets['dados'][val]:
                self.tela.blit(self.assets['dados'][val], rect.topleft)
                cor_borda = (50, 220, 50) if selecionado else COR_ALVO if alvo else COR_PRETA
                pygame.draw.rect(self.tela, cor_borda, rect, 4 if (selecionado or alvo) else 2)
            else:
                pygame.draw.rect(self.tela, (150, 255, 150) if selecionado else (255, 240, 180) if alvo else COR_BRANCA, rect)
                pygame.draw.rect(self.tela, COR_ALVO if alvo else COR_PRETA, rect, 4 if alvo else 2)
                t_num = self.fontes['dado'].render(str(val), True, COR_PRETA)
                self.tela.blit(t_num, t_num.get_rect(center=rect.center))

        aba = pygame.Rect(20, 20, 120, 35)
        surf_aba = pygame.Surface(aba.size)
        surf_aba.set_alpha(220)
        surf_aba.fill((150, 50, 50) if estado['mercado_bloqueado'] else (50, 50, 50))
        self.tela.blit(surf_aba, aba)
        pygame.draw.rect(self.tela, COR_BRANCA, aba, 2)
        texto_aba = "Carta ativa" if pendente else "Fechado" if estado['mercado_bloqueado'] else "▲ Ocultar" if self.mercado_expandido else "▼ Cartas"
        t_aba = self.fontes['aviso'].render(texto_aba, True, COR_BRANCA)
        self.tela.blit(t_aba, t_aba.get_rect(center=aba.center))

        if self.mercado_expandido:
            fundo_c = pygame.Surface((300, 140))
            fundo_c.set_alpha(180)
            fundo_c.fill(COR_PRETA)
            self.tela.blit(fundo_c, (15, 60))

            indice_pendente = pendente['indice'] if pendente else -1
            for i, carta in enumerate(estado['mercado']):
                r_c = pygame.Rect(20 + i * 100, 65, 90, 130)
                ativo = not estado['mercado_bloqueado'] or i == indice_pendente

                if ativo:
                    pygame.draw.rect(self.tela, (255, 250, 200) if i == indice_pendente else (250, 240, 220), r_c)
                    pygame.draw.rect(self.tela, COR_ALVO if i == indice_pendente else COR_PRETA, r_c, 4 if i == indice_pendente else 2)
                    cor_txt = COR_PRETA
                else:
                    pygame.draw.rect(self.tela, (210, 210, 210), r_c)
                    pygame.draw.rect(self.tela, (150, 150, 150), r_c, 2)
                    cor_txt = (150, 150, 150)

                pals = carta['nome'].split()
                if len(pals) == 1: self.tela.blit(self.fontes['tropas'].render(pals[0], True, cor_txt), self.fontes['tropas'].render(pals[0], True, cor_txt).get_rect(center=r_c.center))
                else:
                    self.tela.blit(self.fontes['tropas'].render(pals[0], True, cor_txt), self.fontes['tropas'].render(pals[0], True, cor_txt).get_rect(center=(r_c.centerx, r_c.centery - 10)))
                    self.tela.blit(self.fontes['tropas'].render(" ".join(pals[1:]), True, cor_txt), self.fontes['tropas'].render(" ".join(pals[1:]), True, cor_txt).get_rect(center=(r_c.centerx, r_c.centery + 10)))

        mods = []
        if estado['modificador_castelo'] != 0: mods.append(f"{'+' if estado['modificador_castelo'] > 0 else ''}{estado['modificador_castelo']} Castelo")
        if estado['modificador_tropas'] != 0: mods.append(f"{'+' if estado['modificador_tropas'] > 0 else ''}{estado['modificador_tropas']} Tropa")
        if mods: self._desenhar_texto_caixa(f"Modificador: {' | '.join(mods)}", self.fontes['botao'], (255, 200, 50), (500, 600))

        if self.mensagem_aviso: self._desenhar_texto_caixa(self.mensagem_aviso, self.fontes['aviso'], (255, 100, 100), (500, 680))
        elif pendente: self._desenhar_texto_caixa(self._texto_instrucao(estado), self.fontes['aviso'], COR_ALVO, (500, 680))

    def _desenhar_hud_auditoria(self):
        pygame.draw.rect(self.tela, (200, 200, 200), (350, 630, 300, 50))
        pygame.draw.rect(self.tela, COR_PRETA, (350, 630, 300, 50), 2)
        txt = self.fontes['botao'].render("Próximo Castelo", True, COR_PRETA)
        self.tela.blit(txt, txt.get_rect(center=(500, 655)))
        self._desenhar_texto_caixa(self.jogo.obter_estado()['mensagem_auditoria'], self.fontes['botao'], COR_BRANCA, (500, 580))
        self._desenhar_placar(50)
        if self.mensagem_aviso: self._desenhar_texto_caixa(self.mensagem_aviso, self.fontes['status'], (255, 220, 120), (500, 100))

    def _desenhar_hud_fim(self):
        vencedor = self.jogo.obter_vencedor()
        if vencedor == 1: txt, cor = ("Vitória do Jogador 1!", COR_JOGADOR_1)
        elif vencedor == 2: txt, cor = ("Vitória do Jogador 2!", COR_JOGADOR_2)
        else: txt, cor = ("Empate!", COR_BRANCA)
        self._desenhar_texto_caixa(txt, self.fontes['titulo'], cor, (500, 300))
        self._desenhar_placar(380)

        pygame.draw.rect(self.tela, (200, 200, 200), (350, 640, 300, 50))
        pygame.draw.rect(self.tela, COR_PRETA, (350, 640, 300, 50), 2)
        btn_txt = self.fontes['botao'].render("Jogar Novamente", True, COR_PRETA)
        self.tela.blit(btn_txt, btn_txt.get_rect(center=(500, 665)))

    def _desenhar_placar(self, y_pos):
        pontuacao = self.jogo.obter_estado()['pontuacao_parcial']
        pts1, pts2 = pontuacao[1], pontuacao[2]
        r = pygame.Rect(0, 0, 300 if y_pos == 50 else 400, 60 if y_pos == 50 else 50)
        r.center = (500, y_pos)
        f = pygame.Surface(r.size)
        f.set_alpha(180)
        f.fill(COR_PRETA)
        self.tela.blit(f, r.topleft)

        t_base = self.fontes['botao'].render("Placar: " if y_pos == 50 else "  |  ", True, COR_BRANCA)
        t_j1 = self.fontes['botao'].render(f"J1 {pts1}" if y_pos == 50 else f"J1: {pts1} pontos", True, COR_JOGADOR_1)
        t_x = self.fontes['botao'].render(" x " if y_pos == 50 else "  |  ", True, COR_BRANCA) if y_pos == 50 else t_base
        t_j2 = self.fontes['botao'].render(f"{pts2} J2" if y_pos == 50 else f"J2: {pts2} pontos", True, COR_JOGADOR_2)

        w_tot = t_j1.get_width() + t_x.get_width() + t_j2.get_width() + (t_base.get_width() if y_pos == 50 else 0)
        x, y = (1000 - w_tot) // 2, y_pos - (t_j1.get_height() // 2)

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
