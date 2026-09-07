from logica_jogo import LogicaJogo

def simular_partida_ia():
    # 1. Instancia o ambiente
    jogo = LogicaJogo(tropas_iniciais=36, seed=123)
    
    print("=== INÍCIO DA PARTIDA SIMULADA ===")
    
    # 2. Loop principal: roda enquanto a partida não acabar
    while not jogo.obter_estado()['fim_de_jogo']:
        estado = jogo.obter_estado()
        jogador_atual = estado['jogador_atual']
        tropas = estado['jogadores'][jogador_atual]['tropas']
        
        print(f"\n--- Turno do Jogador {jogador_atual} ---")
        print(f"Tropas em estoque: {tropas}")
        
        # 3. Leitura de Estado (A IA olha para as tropas antes de agir)
        if tropas == 0:
            print("Sem tropas. Passando a vez automaticamente.")
            jogo.passar_vez(jogador_atual)
            continue
            
        # 4. Ação 1: Rolar Dados
        dados = jogo.rolar_dados()
        print(f"Dados rolados: {dados}")
        
        # 5. Tomada de Decisão (Aqui entrará o "cérebro" da sua IA futuramente)
        # Neste simulador, a "IA" é burra e sempre escolhe os dois primeiros dados para o castelo
        dados_castelo = [dados[0], dados[1]]
        dado_tropa = dados[2]
        
        # 6. Ação 2: Jogar Turno
        alvo_castelo = sum(dados_castelo)
        print(f"A IA decidiu: Atacar o castelo {alvo_castelo} usando o dado de valor {dado_tropa} para recrutamento.")
        
        resultado = jogo.jogar_turno(dados_castelo, dado_tropa)
        
        # Validação do ambiente (se a IA tentar um movimento ilegal)
        if not resultado['sucesso']:
            print(f"ERRO DA IA: {resultado['erro']}")
            # Como a IA falhou, passamos a vez dela para evitar loop infinito no terminal
            jogo.passar_vez(jogador_atual)

    # 7. Fase de Auditoria (Fim de Jogo)
    print("\n=== FIM DE JOGO: INICIANDO AUDITORIA ===")
    terminou = False
    while not terminou:
        terminou, mensagem = jogo.resolver_batalha_atual()
        print(mensagem)

    print(f"\nPlacar Final: {jogo.pontuacao_parcial}")
    
    if jogo.pontuacao_parcial[1] > jogo.pontuacao_parcial[2]:
        print("Vencedor: Jogador 1!")
    elif jogo.pontuacao_parcial[2] > jogo.pontuacao_parcial[1]:
        print("Vencedor: Jogador 2!")
    else:
        print("Empate!")

if __name__ == "__main__":
    simular_partida_ia()