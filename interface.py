import pygame
import sys
import random
import math
import os
from logica_jogo import LogicaJogo

pygame.init()

LARGURA_TELA = 1000
ALTURA_TELA = 700
tela = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
pygame.display.set_caption("Rumble Nation - IA")

COR_FUNDO = (240, 240, 240)
COR_PRETA = (0, 0, 0)
COR_BRANCA = (255, 255, 255)
COR_JOGADOR_1 = (255, 80, 80)
COR_JOGADOR_2 = (80, 150, 255)

pygame.font.init()
FONTE_CASTELO = pygame.font.SysFont('Arial', 20, bold=True)
FONTE_TROPAS = pygame.font.SysFont('Arial', 16, bold=True)

POSICOES_CASTELOS = {
    0:  (680, 440),  
    1:  (760, 520),  
    2:  (840, 320),  
    3:  (580, 280),  
    4:  (100, 220),  
    5:  (320, 200),  
    6:  (940, 100),  
    7:  (200, 400),  
    8:  (520, 520),  
    9:  (430, 400),  
    10: (120, 600)   
}

def carregar_imagem(caminho, tamanho):
    if os.path.exists(caminho):
        img = pygame.image.load(caminho).convert_alpha()
        return pygame.transform.smoothscale(img, tamanho)
    return None

def desenhar_texto_com_fundo(superficie, texto, fonte, cor_texto, cor_fundo, pos_center):
    surf_texto = fonte.render(texto, True, cor_texto)
    rect_texto = surf_texto.get_rect(center=pos_center)
    
    surf_fundo = pygame.Surface((rect_texto.width + 16, rect_texto.height + 8))
    surf_fundo.set_alpha(180) 
    surf_fundo.fill(cor_fundo)
    
    superficie.blit(surf_fundo, (rect_texto.x - 8, rect_texto.y - 4))
    superficie.blit(surf_texto, rect_texto)
    return rect_texto

def iniciar_jogo():
    relogio = pygame.time.Clock()
    jogo = None 
    executando = True
    
    estado_jogo = "MENU"
    pontuacao_final = {}
    
    dados_na_tela = []
    indices_selecionados = []
    aviso_interface = "" 
    
    modo_mira = None
    origem_selecionada = -1
    carta_mira_indice = -1
    
    mercado_expandido = False
    
    assets = {
        'fundo': carregar_imagem("assets/fundo.png", (LARGURA_TELA, ALTURA_TELA)),
        'dados': {
            i: carregar_imagem(f"assets/dado_{i}.png", (60, 60)) for i in range(1, 7)
        }
    }
    
    fonte_botao = pygame.font.SysFont('Arial', 24, bold=True)
    fonte_dado = pygame.font.SysFont('Arial', 40, bold=True)
    fonte_titulo = pygame.font.SysFont('Arial', 40, bold=True)
    fonte_aviso = pygame.font.SysFont('Arial', 20, bold=True)
    
    rect_botao_18 = pygame.Rect(300, 300, 400, 60)
    rect_botao_36 = pygame.Rect(300, 400, 400, 60)
    
    rect_botao_rolar = pygame.Rect(770, 620, 200, 50)
    rects_dados = [
        pygame.Rect(770, 540, 60, 60),
        pygame.Rect(840, 540, 60, 60),
        pygame.Rect(910, 540, 60, 60)
    ]
    
    rect_botao_reiniciar = pygame.Rect(350, 640, 300, 50)
    rect_botao_auditoria = pygame.Rect(350, 630, 300, 50)

    while executando:
        
        pos_mouse_atual = pygame.mouse.get_pos()
        aba_rect = pygame.Rect(20, 20, 120, 35)
        area_total_mercado = pygame.Rect(15, 20, 300, 185)
        
        if aba_rect.collidepoint(pos_mouse_atual):
            mercado_expandido = True
        elif not area_total_mercado.collidepoint(pos_mouse_atual):
            mercado_expandido = False
            
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                executando = False
                
            if evento.type == pygame.MOUSEBUTTONDOWN:
                pos_mouse = evento.pos
                
                if evento.button == 3 and modo_mira is not None:
                    modo_mira = None
                    origem_selecionada = -1
                    carta_mira_indice = -1
                    aviso_interface = "Ação de carta cancelada."
                    
                elif evento.button == 1:
                    
                    if estado_jogo == "MENU":
                        if rect_botao_18.collidepoint(pos_mouse):
                            x = random.randint(1, 999999)
                            jogo = LogicaJogo(18, seed=x)
                            estado_jogo = "RODANDO"
                            aviso_interface = ""
                        elif rect_botao_36.collidepoint(pos_mouse):
                            x = random.randint(1, 999999)
                            jogo = LogicaJogo(36, seed=x)
                            estado_jogo = "RODANDO"
                            aviso_interface = ""
                            
                    elif estado_jogo == "RODANDO":
                        estado_atual = jogo.obter_estado()
                        
                        if modo_mira == "MARCHA_ORIGEM":
                            clicou_castelo = False
                            for id_castelo, castelo_info in estado_atual['castelos'].items():
                                pos_c = POSICOES_CASTELOS[castelo_info['id_local']]
                                if math.hypot(pos_mouse[0] - pos_c[0], pos_mouse[1] - pos_c[1]) <= 25:
                                    if castelo_info[f'tropas_j{estado_atual["jogador_atual"]}'] > 0:
                                        origem_selecionada = id_castelo
                                        modo_mira = "MARCHA_DESTINO"
                                        aviso_interface = "MARCHA: Selecione o castelo de DESTINO."
                                    else:
                                        aviso_interface = "Você não tem tropas neste castelo."
                                    clicou_castelo = True
                                    break
                            if not clicou_castelo:
                                aviso_interface = "Clique em um castelo válido para a ORIGEM."
                                
                        elif modo_mira == "MARCHA_DESTINO":
                            clicou_castelo = False
                            for id_castelo, castelo_info in estado_atual['castelos'].items():
                                pos_c = POSICOES_CASTELOS[castelo_info['id_local']]
                                if math.hypot(pos_mouse[0] - pos_c[0], pos_mouse[1] - pos_c[1]) <= 25:
                                    vizinhos = estado_atual['castelos'][origem_selecionada]['vizinhos']
                                    if id_castelo in vizinhos:
                                        estado_novo = jogo.executar_marcha(estado_atual['jogador_atual'], carta_mira_indice, origem_selecionada, id_castelo)
                                        if not estado_novo['sucesso']:
                                            aviso_interface = estado_novo['erro']
                                        else:
                                            aviso_interface = "Marcha realizada com sucesso!"
                                            dados_na_tela = [] 
                                            indices_selecionados = []
                                            if estado_novo['fim_de_jogo']:
                                                estado_jogo = "AUDITORIA"
                                        modo_mira = None
                                        origem_selecionada = -1
                                        carta_mira_indice = -1
                                    else:
                                        aviso_interface = "O destino deve ser vizinho da origem."
                                    clicou_castelo = True
                                    break
                            if not clicou_castelo:
                                aviso_interface = "Clique em um castelo vizinho válido."
                                
                        elif modo_mira == "MIRA_DADO":
                            clicou_dado = False
                            for i in range(3):
                                if rects_dados[i].collidepoint(pos_mouse):
                                    estado_novo = jogo.executar_alteracao_dado(estado_atual['jogador_atual'], carta_mira_indice, i)
                                    if not estado_novo['sucesso']:
                                        aviso_interface = estado_novo['erro']
                                    else:
                                        aviso_interface = "Dado alterado com sucesso!"
                                        dados_na_tela = estado_novo['dados_atuais']
                                        indices_selecionados = []
                                        modo_mira = None
                                        carta_mira_indice = -1
                                    clicou_dado = True
                                    break
                            if not clicou_dado:
                                aviso_interface = "Clique no dado alvo (Botão Direito cancela)."

                        else:
                            clicou_algo = False
                            
                            if rect_botao_rolar.collidepoint(pos_mouse):
                                jogador_da_vez = estado_atual['jogador_atual']
                                if estado_atual['jogadores'][jogador_da_vez]['tropas'] == 0:
                                    estado_novo = jogo.passar_vez(jogador_da_vez)
                                    if not estado_novo['sucesso']:
                                        aviso_interface = estado_novo['erro']
                                    else:
                                        aviso_interface = ""
                                        dados_na_tela = []
                                        indices_selecionados = []
                                        if estado_novo['fim_de_jogo']:
                                            estado_jogo = "AUDITORIA"
                                else:
                                    if len(dados_na_tela) == 0:
                                        dados_na_tela = jogo.rolar_dados()
                                        indices_selecionados = []
                                        aviso_interface = ""
                                clicou_algo = True
                                
                            if not clicou_algo:
                                mercado_atual = estado_atual['mercado']
                                jogador_da_vez = estado_atual['jogador_atual']
                                mercado_bloqueado = estado_atual['mercado_bloqueado']
                                pode_comprar = not estado_atual['jogadores'][jogador_da_vez]['usou_carta'] and not mercado_bloqueado
                                
                                if pode_comprar and mercado_expandido:
                                    for i in range(len(mercado_atual)):
                                        rect_carta = pygame.Rect(20 + i * 100, 65, 90, 130)
                                        if rect_carta.collidepoint(pos_mouse):
                                            efeito = mercado_atual[i]['efeito']
                                            
                                            if efeito != 'marchar' and len(dados_na_tela) == 0:
                                                aviso_interface = "Você precisa rolar os dados primeiro!"
                                            elif efeito == 'marchar':
                                                modo_mira = "MARCHA_ORIGEM"
                                                carta_mira_indice = i
                                                aviso_interface = "MARCHA: Selecione a ORIGEM (Direito cancela)"
                                            elif efeito in ['+1_dado', '-1_dado', 'inverter_dado']:
                                                modo_mira = "MIRA_DADO"
                                                carta_mira_indice = i
                                                aviso_interface = "Selecione o dado que deseja alterar (Direito cancela)"
                                            else:
                                                estado_novo = jogo.usar_carta(jogador_da_vez, i)
                                                if not estado_novo['sucesso']:
                                                    aviso_interface = estado_novo['erro']
                                                else:
                                                    aviso_interface = ""
                                                    dados_na_tela = estado_novo['dados_atuais']
                                                    indices_selecionados = []
                                            clicou_algo = True
                                            break
                            
                            if not clicou_algo and len(dados_na_tela) > 0:
                                for i in range(3):
                                    if rects_dados[i].collidepoint(pos_mouse):
                                        if i in indices_selecionados:
                                            indices_selecionados.remove(i)
                                        else:
                                            if len(indices_selecionados) < 2:
                                                indices_selecionados.append(i)
                                                
                                                if len(indices_selecionados) == 2:
                                                    indice_tropa = -1
                                                    for j in range(3):
                                                        if j not in indices_selecionados:
                                                            indice_tropa = j
                                                    
                                                    dados_castelo = [dados_na_tela[indices_selecionados[0]], dados_na_tela[indices_selecionados[1]]]
                                                    dado_tropa = dados_na_tela[indice_tropa]
                                                    
                                                    estado_novo = jogo.jogar_turno(dados_castelo, dado_tropa)
                                                    
                                                    if not estado_novo['sucesso']:
                                                        aviso_interface = estado_novo['erro']
                                                        indices_selecionados.remove(i) 
                                                    else:
                                                        aviso_interface = ""
                                                        dados_na_tela = []
                                                        indices_selecionados = []
                                                    
                                                    if estado_novo['fim_de_jogo']:
                                                        estado_jogo = "AUDITORIA"
                                                    
                    elif estado_jogo == "AUDITORIA":
                        if rect_botao_auditoria.collidepoint(pos_mouse):
                            terminou, msg = jogo.resolver_batalha_atual()
                            jogo.mensagem_auditoria = msg
                            if terminou:
                                estado_jogo = "FIM"
                                pontuacao_final = jogo.pontuacao_parcial
                                                    
                    elif estado_jogo == "FIM":
                        if rect_botao_reiniciar.collidepoint(pos_mouse):
                            estado_jogo = "MENU"
                            jogo = None
                            dados_na_tela = []
                            indices_selecionados = []
                            aviso_interface = ""
                            pontuacao_final = {}

        if assets['fundo'] is not None:
            tela.blit(assets['fundo'], (0, 0))
        else:
            tela.fill(COR_FUNDO)
        
        if estado_jogo == "MENU":
            desenhar_texto_com_fundo(tela, "RUMBLE NATION", fonte_titulo, COR_BRANCA, COR_PRETA, (LARGURA_TELA // 2, 150))
            
            pygame.draw.rect(tela, (200, 200, 200), rect_botao_18)
            pygame.draw.rect(tela, COR_PRETA, rect_botao_18, 2)
            texto_18 = fonte_botao.render("Partida Rápida (18 Tropas)", True, COR_PRETA)
            tela.blit(texto_18, texto_18.get_rect(center=rect_botao_18.center))
            
            pygame.draw.rect(tela, (200, 200, 200), rect_botao_36)
            pygame.draw.rect(tela, COR_PRETA, rect_botao_36, 2)
            texto_36 = fonte_botao.render("Partida Completa (36 Tropas)", True, COR_PRETA)
            tela.blit(texto_36, texto_36.get_rect(center=rect_botao_36.center))
            
        elif estado_jogo == "RODANDO" or estado_jogo == "AUDITORIA":
            estado_desenho = jogo.obter_estado()

            for id_castelo, castelo_info in estado_desenho['castelos'].items():
                posicao_atual = POSICOES_CASTELOS[castelo_info['id_local']]
                
                cor_borda = (200, 200, 200) if castelo_info['conquistado'] else COR_PRETA
                pygame.draw.circle(tela, cor_borda, posicao_atual, 25)
                pygame.draw.circle(tela, (255, 255, 255), posicao_atual, 23)
                
                texto = FONTE_CASTELO.render(str(id_castelo), True, COR_PRETA)
                tela.blit(texto, texto.get_rect(center=posicao_atual))
                
                tropas_j1 = castelo_info['tropas_j1']
                tropas_j2 = castelo_info['tropas_j2']
                
                if tropas_j1 > 0:
                    pos_j1 = (posicao_atual[0] - 25, posicao_atual[1] - 25)
                    pygame.draw.circle(tela, COR_JOGADOR_1, pos_j1, 15)
                    pygame.draw.circle(tela, COR_PRETA, pos_j1, 15, 2)
                    texto_t1 = FONTE_TROPAS.render(str(tropas_j1), True, COR_BRANCA)
                    tela.blit(texto_t1, texto_t1.get_rect(center=pos_j1))
                    
                if tropas_j2 > 0:
                    pos_j2 = (posicao_atual[0] + 25, posicao_atual[1] - 25)
                    pygame.draw.circle(tela, COR_JOGADOR_2, pos_j2, 15)
                    pygame.draw.circle(tela, COR_PRETA, pos_j2, 15, 2)
                    texto_t2 = FONTE_TROPAS.render(str(tropas_j2), True, COR_BRANCA)
                    tela.blit(texto_t2, texto_t2.get_rect(center=pos_j2))

            if origem_selecionada != -1:
                local_id = estado_desenho['castelos'][origem_selecionada]['id_local']
                pygame.draw.circle(tela, (255, 200, 0), POSICOES_CASTELOS[local_id], 30, 4)
            
            if estado_jogo == "RODANDO":
                cor_vez = COR_JOGADOR_1 if jogo.id_jogador_atual == 1 else COR_JOGADOR_2
                desenhar_texto_com_fundo(tela, f"Jogador {jogo.id_jogador_atual}", fonte_titulo, cor_vez, COR_PRETA, (LARGURA_TELA // 2, 40))

                jogador_da_vez = estado_desenho['jogador_atual']
                tropas_atuais = estado_desenho['jogadores'][jogador_da_vez]['tropas']
                
                if tropas_atuais == 0:
                    pygame.draw.rect(tela, (255, 200, 50), rect_botao_rolar)
                    pygame.draw.rect(tela, COR_PRETA, rect_botao_rolar, 2)    
                    texto_botao = fonte_botao.render("Passar Vez", True, COR_PRETA)
                else:
                    cor_fundo_botao = (200, 200, 200) if len(dados_na_tela) == 0 else (150, 150, 150)
                    cor_texto_botao = COR_PRETA if len(dados_na_tela) == 0 else (100, 100, 100)
                    pygame.draw.rect(tela, cor_fundo_botao, rect_botao_rolar) 
                    pygame.draw.rect(tela, COR_PRETA, rect_botao_rolar, 2)    
                    texto_botao = fonte_botao.render("Rolar Dados", True, cor_texto_botao)
                    
                tela.blit(texto_botao, texto_botao.get_rect(center=rect_botao_rolar.center))

                if len(dados_na_tela) > 0:
                    for i in range(3):
                        val_dado = dados_na_tela[i]
                        rect_d = rects_dados[i]
                        
                        if assets['dados'][val_dado] is not None:
                            tela.blit(assets['dados'][val_dado], rect_d.topleft)
                            if i in indices_selecionados:
                                pygame.draw.rect(tela, (50, 220, 50), rect_d, 4)
                            else:
                                pygame.draw.rect(tela, COR_PRETA, rect_d, 2)
                        else:
                            cor_fundo_dado = (150, 255, 150) if i in indices_selecionados else (255, 255, 255)
                            pygame.draw.rect(tela, cor_fundo_dado, rect_d)
                            pygame.draw.rect(tela, COR_PRETA, rect_d, 2)
                            texto_dado = fonte_dado.render(str(val_dado), True, COR_PRETA)
                            tela.blit(texto_dado, texto_dado.get_rect(center=rect_d.center))
                        
                    mercado_bloqueado = estado_desenho['mercado_bloqueado']
                    pode_comprar_carta = not estado_desenho['jogadores'][jogador_da_vez]['usou_carta'] and not mercado_bloqueado
                    
                    cor_fundo_aba = (150, 50, 50) if mercado_bloqueado else (50, 50, 50)
                    surf_aba = pygame.Surface((aba_rect.width, aba_rect.height))
                    surf_aba.set_alpha(220)
                    surf_aba.fill(cor_fundo_aba)
                    tela.blit(surf_aba, aba_rect.topleft)
                    pygame.draw.rect(tela, COR_BRANCA, aba_rect, 2)
                    
                    if mercado_bloqueado:
                        texto_aba = "Fechado"
                    else:
                        texto_aba = "▲ Ocultar" if mercado_expandido else "▼ Cartas"
                        
                    txt_aba = fonte_aviso.render(texto_aba, True, COR_BRANCA)
                    tela.blit(txt_aba, txt_aba.get_rect(center=aba_rect.center))

                    if mercado_expandido:
                        area_fundo_cartas = pygame.Rect(15, 60, 300, 140)
                        surf_fundo_cartas = pygame.Surface((area_fundo_cartas.width, area_fundo_cartas.height))
                        surf_fundo_cartas.set_alpha(180)
                        surf_fundo_cartas.fill(COR_PRETA)
                        tela.blit(surf_fundo_cartas, area_fundo_cartas.topleft)

                        mercado = estado_desenho['mercado']
                        for i in range(len(mercado)):
                            rect_carta = pygame.Rect(20 + i * 100, 65, 90, 130)
                            
                            if pode_comprar_carta or modo_mira is not None:
                                if carta_mira_indice == i:
                                    pygame.draw.rect(tela, (255, 250, 200), rect_carta) 
                                    pygame.draw.rect(tela, (255, 200, 0), rect_carta, 4)
                                else:
                                    pygame.draw.rect(tela, (250, 240, 220), rect_carta)
                                    pygame.draw.rect(tela, COR_PRETA, rect_carta, 2)
                                cor_texto_carta = COR_PRETA
                            else:
                                pygame.draw.rect(tela, (210, 210, 210), rect_carta)
                                pygame.draw.rect(tela, (150, 150, 150), rect_carta, 2)
                                cor_texto_carta = (150, 150, 150)
                                
                            palavras = mercado[i]['nome'].split()
                            if len(palavras) == 1:
                                texto_carta = FONTE_TROPAS.render(palavras[0], True, cor_texto_carta)
                                tela.blit(texto_carta, texto_carta.get_rect(center=rect_carta.center))
                            else:
                                texto_1 = FONTE_TROPAS.render(palavras[0], True, cor_texto_carta)
                                texto_2 = FONTE_TROPAS.render(" ".join(palavras[1:]), True, cor_texto_carta)
                                tela.blit(texto_1, texto_1.get_rect(center=(rect_carta.centerx, rect_carta.centery - 10)))
                                tela.blit(texto_2, texto_2.get_rect(center=(rect_carta.centerx, rect_carta.centery + 10)))

                    mod_castelo = estado_desenho['modificador_castelo']
                    mod_tropa = estado_desenho['modificador_tropas']
                    textos_mod = []
                    
                    if mod_castelo != 0:
                        sinal = "+" if mod_castelo > 0 else ""
                        textos_mod.append(f"{sinal}{mod_castelo} Castelo")
                    if mod_tropa != 0:
                        sinal = "+" if mod_tropa > 0 else ""
                        textos_mod.append(f"{sinal}{mod_tropa} Tropa")
                        
                    if textos_mod:
                        desenhar_texto_com_fundo(tela, f"Modificador: {' | '.join(textos_mod)}", fonte_botao, (255, 200, 50), COR_PRETA, (LARGURA_TELA // 2, 600))
                        
                    status_j1 = "Sim" if estado_desenho['jogadores'][1]['usou_carta'] else "Não"
                    status_j2 = "Sim" if estado_desenho['jogadores'][2]['usou_carta'] else "Não"
                    desenhar_texto_com_fundo(tela, f"Carta Usada: J1({status_j1}) | J2({status_j2})", fonte_aviso, COR_BRANCA, COR_PRETA, (LARGURA_TELA // 2, 640))
                
                if aviso_interface != "":
                    desenhar_texto_com_fundo(tela, aviso_interface, fonte_aviso, (255, 100, 100), COR_PRETA, (LARGURA_TELA // 2, 680))
                        
            elif estado_jogo == "AUDITORIA":
                pygame.draw.rect(tela, (200, 200, 200), rect_botao_auditoria)
                pygame.draw.rect(tela, COR_PRETA, rect_botao_auditoria, 2)
                texto_auditoria = fonte_botao.render("Próximo Castelo", True, COR_PRETA)
                tela.blit(texto_auditoria, texto_auditoria.get_rect(center=rect_botao_auditoria.center))
                
                desenhar_texto_com_fundo(tela, jogo.mensagem_auditoria, fonte_botao, COR_BRANCA, COR_PRETA, (LARGURA_TELA // 2, 580))
                
                rect_placar = pygame.Rect(0, 0, 300, 60)
                rect_placar.center = (LARGURA_TELA // 2, 50)
                surf_fundo = pygame.Surface((rect_placar.width, rect_placar.height))
                surf_fundo.set_alpha(180)
                surf_fundo.fill(COR_PRETA)
                tela.blit(surf_fundo, rect_placar.topleft)
                
                txt_placar = fonte_botao.render("Placar: ", True, COR_BRANCA)
                txt_j1 = fonte_botao.render(f"J1 {jogo.pontuacao_parcial[1]}", True, COR_JOGADOR_1)
                txt_x = fonte_botao.render(" x ", True, COR_BRANCA)
                txt_j2 = fonte_botao.render(f"{jogo.pontuacao_parcial[2]} J2", True, COR_JOGADOR_2)
                
                largura_total = txt_placar.get_width() + txt_j1.get_width() + txt_x.get_width() + txt_j2.get_width()
                pos_x = (LARGURA_TELA - largura_total) // 2
                pos_y = 50 - txt_placar.get_height() // 2
                
                tela.blit(txt_placar, (pos_x, pos_y))
                pos_x += txt_placar.get_width()
                tela.blit(txt_j1, (pos_x, pos_y))
                pos_x += txt_j1.get_width()
                tela.blit(txt_x, (pos_x, pos_y))
                pos_x += txt_x.get_width()
                tela.blit(txt_j2, (pos_x, pos_y))

        elif estado_jogo == "FIM":
            if pontuacao_final[1] > pontuacao_final[2]:
                texto_vencedor = "Vitória do Jogador 1!"
                cor_vencedor = COR_JOGADOR_1
            elif pontuacao_final[2] > pontuacao_final[1]:
                texto_vencedor = "Vitória do Jogador 2!"
                cor_vencedor = COR_JOGADOR_2
            else:
                texto_vencedor = "Empate!"
                cor_vencedor = COR_BRANCA
                
            desenhar_texto_com_fundo(tela, texto_vencedor, fonte_titulo, cor_vencedor, COR_PRETA, (LARGURA_TELA // 2, 300))
            
            rect_pts = pygame.Rect(0, 0, 400, 50)
            rect_pts.center = (LARGURA_TELA // 2, 380)
            surf_fundo_pts = pygame.Surface((rect_pts.width, rect_pts.height))
            surf_fundo_pts.set_alpha(180)
            surf_fundo_pts.fill(COR_PRETA)
            tela.blit(surf_fundo_pts, rect_pts.topleft)
            
            txt_pts_j1 = fonte_botao.render(f"J1: {pontuacao_final[1]} pontos", True, COR_JOGADOR_1)
            txt_div = fonte_botao.render("  |  ", True, COR_BRANCA)
            txt_pts_j2 = fonte_botao.render(f"J2: {pontuacao_final[2]} pontos", True, COR_JOGADOR_2)
            
            largura_total_fim = txt_pts_j1.get_width() + txt_div.get_width() + txt_pts_j2.get_width()
            pos_x_fim = (LARGURA_TELA - largura_total_fim) // 2
            pos_y_fim = 380 - txt_pts_j1.get_height() // 2
            
            tela.blit(txt_pts_j1, (pos_x_fim, pos_y_fim))
            pos_x_fim += txt_pts_j1.get_width()
            tela.blit(txt_div, (pos_x_fim, pos_y_fim))
            pos_x_fim += txt_div.get_width()
            tela.blit(txt_pts_j2, (pos_x_fim, pos_y_fim))
            
            pygame.draw.rect(tela, (200, 200, 200), rect_botao_reiniciar)
            pygame.draw.rect(tela, COR_PRETA, rect_botao_reiniciar, 2)
            texto_reiniciar = fonte_botao.render("Jogar Novamente", True, COR_PRETA)
            tela.blit(texto_reiniciar, texto_reiniciar.get_rect(center=rect_botao_reiniciar.center))
            
        pygame.display.flip()
        relogio.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    iniciar_jogo()