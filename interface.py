import pygame
import sys
from logica_jogo import LogicaJogo

pygame.init()

# Configurações da Janela
LARGURA_TELA = 1000
ALTURA_TELA = 700
tela = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
pygame.display.set_caption("Rumble Nation - IA")

COR_FUNDO = (240, 240, 240)  # Cinza claro
COR_PRETA = (0, 0, 0)
COR_JOGADOR_1 = (200, 50, 50)  # Vermelho
COR_JOGADOR_2 = (50, 50, 200)  # Azul

def iniciar_jogo():
    # Trava o FPS do jogo
    relogio = pygame.time.Clock()
    
    jogo = LogicaJogo()
    
    # Mantém a janela aberta
    executando = True
    
    # --- GAME LOOP ---
    while executando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                executando = False

        # Preenche a tela com uma cor
        tela.fill(COR_FUNDO)
                
        # Pega tudo o que foi desenhado na memória e joga para o monitor
        pygame.display.flip()
        
        # Trava o laço em 60 FPS
        relogio.tick(60)

    # Encerra a janela com segurança
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    iniciar_jogo()