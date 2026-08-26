import pygame
import sys
from logica_jogo import LogicaJogo

pygame.init()

LARGURA_TELA = 1000
ALTURA_TELA = 700
tela = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
pygame.display.set_caption("Rumble Nation - IA")

COR_FUNDO = (240, 240, 240)
COR_PRETA = (0, 0, 0)
COR_JOGADOR_1 = (200, 50, 50)
COR_JOGADOR_2 = (50, 50, 200)

pygame.font.init()
FONTE_CASTELO = pygame.font.SysFont('Arial', 24, bold=True)
FONTE_TROPAS = pygame.font.SysFont('Arial', 16, bold=True)

POSICOES_CASTELOS = {
    8:  (850, 150),
    4:  (750, 300),
    3:  (800, 450),
    5:  (600, 250),
    2:  (650, 375),
    10: (500, 450),
    11: (450, 350),
    7:  (400, 250),
    9:  (250, 350),
    6:  (150, 200),
    12: (150, 500)
}

def iniciar_jogo():
    relogio = pygame.time.Clock()
    jogo = None 
    executando = True
    
    estado_jogo = "MENU"
    pontuacao_final = {}
    
    dados_na_tela = []
    indices_selecionados = []
    
    fonte_botao = pygame.font.SysFont('Arial', 24, bold=True)
    fonte_dado = pygame.font.SysFont('Arial', 40, bold=True)
    fonte_titulo = pygame.font.SysFont('Arial', 50, bold=True)
    
    rect_botao_18 = pygame.Rect(300, 300, 400, 60)
    rect_botao_36 = pygame.Rect(300, 400, 400, 60)
    
    rect_botao_rolar = pygame.Rect(400, 610, 200, 50)
    rect_botao_reiniciar = pygame.Rect(350, 640, 300, 50)
    rect_botao_auditoria = pygame.Rect(350, 630, 300, 50)
    
    rects_dados = [
        pygame.Rect(350, 520, 60, 60),
        pygame.Rect(470, 520, 60, 60),
        pygame.Rect(590, 520, 60, 60)
    ]

    while executando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                executando = False
                
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    pos_mouse = evento.pos
                    
                    if estado_jogo == "MENU":
                        if rect_botao_18.collidepoint(pos_mouse):
                            jogo = LogicaJogo(2)
                            estado_jogo = "RODANDO"
                        elif rect_botao_36.collidepoint(pos_mouse):
                            jogo = LogicaJogo(36)
                            estado_jogo = "RODANDO"
                            
                    elif estado_jogo == "RODANDO":
                        if rect_botao_rolar.collidepoint(pos_mouse):
                            if len(dados_na_tela) == 0:
                                dados_na_tela = jogo.rolar_dados()
                                indices_selecionados = []
                            
                        if len(dados_na_tela) > 0:
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
                                                
                                                sucesso, mensagem = jogo.jogar_turno(dados_castelo, dado_tropa)
                                                print(mensagem)
                                                
                                                dados_na_tela = []
                                                indices_selecionados = []
                                                
                                                if jogo.jogadores[1].tropas == 0 and jogo.jogadores[2].tropas == 0:
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
                            pontuacao_final = {}

        tela.fill(COR_FUNDO)
        
        if estado_jogo == "MENU":
            texto_titulo = fonte_titulo.render("RUMBLE NATION", True, COR_PRETA)
            tela.blit(texto_titulo, texto_titulo.get_rect(center=(LARGURA_TELA // 2, 150)))
            
            pygame.draw.rect(tela, (200, 200, 200), rect_botao_18)
            pygame.draw.rect(tela, COR_PRETA, rect_botao_18, 2)
            texto_18 = fonte_botao.render("Partida Rápida (18 Tropas)", True, COR_PRETA)
            tela.blit(texto_18, texto_18.get_rect(center=rect_botao_18.center))
            
            pygame.draw.rect(tela, (200, 200, 200), rect_botao_36)
            pygame.draw.rect(tela, COR_PRETA, rect_botao_36, 2)
            texto_36 = fonte_botao.render("Partida Completa (36 Tropas)", True, COR_PRETA)
            tela.blit(texto_36, texto_36.get_rect(center=rect_botao_36.center))
            
        elif estado_jogo == "RODANDO" or estado_jogo == "AUDITORIA":
            for id_castelo, castelo in jogo.castelos.items():
                posicao_atual = POSICOES_CASTELOS[id_castelo]
                for id_vizinho in castelo.vizinhos:
                    posicao_vizinho = POSICOES_CASTELOS[id_vizinho]
                    pygame.draw.line(tela, (150, 150, 150), posicao_atual, posicao_vizinho, 4)

            for id_castelo, castelo in jogo.castelos.items():
                posicao_atual = POSICOES_CASTELOS[id_castelo]
                
                if castelo.conquistado:
                    pygame.draw.circle(tela, (200, 200, 200), posicao_atual, 35)
                else:
                    pygame.draw.circle(tela, COR_PRETA, posicao_atual, 35)
                    
                pygame.draw.circle(tela, (255, 255, 255), posicao_atual, 32)
                
                texto = FONTE_CASTELO.render(str(id_castelo), True, COR_PRETA)
                retangulo_texto = texto.get_rect(center=posicao_atual)
                tela.blit(texto, retangulo_texto)
                
                tropas_j1 = castelo.tropas[1]
                tropas_j2 = castelo.tropas[2]
                
                if tropas_j1 > 0:
                    pos_x_j1 = posicao_atual[0] - 25
                    pos_y_j1 = posicao_atual[1] - 25
                    pygame.draw.circle(tela, COR_JOGADOR_1, (pos_x_j1, pos_y_j1), 15)
                    pygame.draw.circle(tela, COR_PRETA, (pos_x_j1, pos_y_j1), 15, 2)
                    texto_t1 = FONTE_TROPAS.render(str(tropas_j1), True, (255, 255, 255))
                    retangulo_t1 = texto_t1.get_rect(center=(pos_x_j1, pos_y_j1))
                    tela.blit(texto_t1, retangulo_t1)
                    
                if tropas_j2 > 0:
                    pos_x_j2 = posicao_atual[0] + 25
                    pos_y_j2 = posicao_atual[1] - 25
                    pygame.draw.circle(tela, COR_JOGADOR_2, (pos_x_j2, pos_y_j2), 15)
                    pygame.draw.circle(tela, COR_PRETA, (pos_x_j2, pos_y_j2), 15, 2)
                    texto_t2 = FONTE_TROPAS.render(str(tropas_j2), True, (255, 255, 255))
                    retangulo_t2 = texto_t2.get_rect(center=(pos_x_j2, pos_y_j2))
                    tela.blit(texto_t2, retangulo_t2)
            
            if estado_jogo == "RODANDO":
                if len(dados_na_tela) == 0:
                    cor_fundo_botao = (200, 200, 200)
                    cor_texto_botao = COR_PRETA
                else:
                    cor_fundo_botao = (150, 150, 150)
                    cor_texto_botao = (100, 100, 100)

                pygame.draw.rect(tela, cor_fundo_botao, rect_botao_rolar) 
                pygame.draw.rect(tela, COR_PRETA, rect_botao_rolar, 2)    
                texto_botao = fonte_botao.render("Rolar Dados", True, cor_texto_botao)
                tela.blit(texto_botao, texto_botao.get_rect(center=rect_botao_rolar.center))

                if len(dados_na_tela) > 0:
                    for i in range(3):
                        if i in indices_selecionados:
                            cor_fundo_dado = (150, 255, 150)
                        else:
                            cor_fundo_dado = (255, 255, 255)
                            
                        pygame.draw.rect(tela, cor_fundo_dado, rects_dados[i])
                        pygame.draw.rect(tela, COR_PRETA, rects_dados[i], 2)
                        texto_dado = fonte_dado.render(str(dados_na_tela[i]), True, COR_PRETA)
                        tela.blit(texto_dado, texto_dado.get_rect(center=rects_dados[i].center))
                        
            elif estado_jogo == "AUDITORIA":
                pygame.draw.rect(tela, (200, 200, 200), rect_botao_auditoria)
                pygame.draw.rect(tela, COR_PRETA, rect_botao_auditoria, 2)
                texto_auditoria = fonte_botao.render("Próximo Castelo", True, COR_PRETA)
                tela.blit(texto_auditoria, texto_auditoria.get_rect(center=rect_botao_auditoria.center))
                
                texto_msg = fonte_botao.render(jogo.mensagem_auditoria, True, COR_PRETA)
                tela.blit(texto_msg, texto_msg.get_rect(center=(LARGURA_TELA // 2, 580)))
                
                texto_placar = fonte_botao.render(f"Placar: J1 {jogo.pontuacao_parcial[1]} x {jogo.pontuacao_parcial[2]} J2", True, COR_PRETA)
                tela.blit(texto_placar, texto_placar.get_rect(center=(LARGURA_TELA // 2, 50)))

        elif estado_jogo == "FIM":
            fonte_fim = pygame.font.SysFont('Arial', 40, bold=True)
            
            if pontuacao_final[1] > pontuacao_final[2]:
                texto_vencedor = "Vitória do Jogador 1!"
                cor_vencedor = COR_JOGADOR_1
            elif pontuacao_final[2] > pontuacao_final[1]:
                texto_vencedor = "Vitória do Jogador 2!"
                cor_vencedor = COR_JOGADOR_2
            else:
                texto_vencedor = "Empate!"
                cor_vencedor = COR_PRETA
                
            superficie_vencedor = fonte_fim.render(texto_vencedor, True, cor_vencedor)
            tela.blit(superficie_vencedor, superficie_vencedor.get_rect(center=(LARGURA_TELA // 2, 300)))
            
            texto_pontos = fonte_botao.render(f"J1: {pontuacao_final[1]} pontos  |  J2: {pontuacao_final[2]} pontos", True, COR_PRETA)
            tela.blit(texto_pontos, texto_pontos.get_rect(center=(LARGURA_TELA // 2, 380)))
            
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