"""
Árvore de Estados do Rumble Nation.

    NoArvore           um estado congelado do jogo + as arestas (jogadas) que saem dele
    ArvoreDeEstados    dicionário plano {hash_do_estado: NoArvore}, caminho da partida,
                       persistência em JSON e exportação para Graphviz (.dot)
    NavegadorDeArvore  liga o motor do jogo à árvore: gera 1 nível abaixo de cada estado
                       alcançado, faz a jogada real SEGUIR a aresta prevista, volta no tempo,
                       salva e carrega.

As duas primeiras classes não conhecem as regras do jogo. O navegador usa o motor apenas
pelo contrato descrito na sua docstring, então este arquivo não importa logica_jogo.py.
"""
import hashlib
import json
import os
import shutil
import subprocess

ARQUIVO_ARVORE = "arvore_rumble"
VERSAO_FORMATO = 2


# =============================================================================
#  COMPARAÇÃO DE ESTADOS
# =============================================================================

def _normalizar(valor):
    """Cópia profunda do estado com todas as chaves como texto (exatamente o que o JSON grava)."""
    if isinstance(valor, dict):
        return {str(chave): _normalizar(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_normalizar(item) for item in valor]
    return valor


def assinatura_do_estado(estado):
    """
    Forma canônica do estado: JSON com as chaves em ordem alfabética e sem espaços.
    Dois estados são iguais se, e somente se, têm a mesma assinatura.
    A normalização das chaves faz o estado vindo do motor ({1: ...}) e o mesmo estado
    relido do arquivo ({"1": ...}) gerarem a MESMA assinatura.
    """
    return json.dumps(_normalizar(estado), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def gerar_hash(estado):
    """Hash curto da assinatura (16 hex = 64 bits). É a chave do dicionário plano de nós."""
    return hashlib.sha256(assinatura_do_estado(estado).encode("utf-8")).hexdigest()[:16]


def estados_iguais(estado_a, estado_b):
    """Método de comparação entre estados: compara as assinaturas completas."""
    return assinatura_do_estado(estado_a) == assinatura_do_estado(estado_b)


# =============================================================================
#  ESTRUTURA DE DADOS
# =============================================================================

class NoArvore:
    def __init__(self, estado, id_pai=None, jogada=None, profundidade=0, ordem=0):
        """
        Representa um momento congelado no tempo.
        :param estado: O dicionário COMPLETO gerado por LogicaJogo.obter_estado() (guardado normalizado).
        :param id_pai: O hash do nó em que a jogada foi feita (None na raiz).
        :param jogada: Dicionário da jogada que levou a este estado (None na raiz).
        :var titulo: Texto da jogada que criou o nó (é o rótulo do nó no Graphviz).
        :var filhos: Arestas que saem deste nó: {chave_da_jogada: {"id": id_filho, "jogada": {...}}}.
        :var expandido: True quando a partida real chegou a este estado e o nível abaixo foi gerado.
        """
        self.estado = _normalizar(estado)
        self.id_no = gerar_hash(self.estado)
        self.id_pai = id_pai
        self.jogada = jogada
        self.profundidade = profundidade
        self.ordem = ordem
        self.filhos = {}
        self.expandido = False

        if jogada is None:
            self.titulo = "Início da Partida"
        else:
            self.titulo = jogada["rotulo"]

    def ids_filhos(self):
        """Lista com os hashes dos nós filhos."""
        return [aresta["id"] for aresta in self.filhos.values()]

    def para_dict(self):
        return {
            "ordem": self.ordem,
            "profundidade": self.profundidade,
            "id_pai": self.id_pai,
            "jogada": self.jogada,
            "expandido": self.expandido,
            "filhos": self.filhos,
            "estado": self.estado,
        }


class ArvoreDeEstados:
    def __init__(self, estado_inicial=None):
        """
        Gerencia o banco de dados da árvore.
        Usamos um dicionário plano (self.nos) para evitar recursão infinita ao salvar no arquivo.
        :var caminho: Pilha com os ids da partida real [raiz, ..., nó atual]. É o "ponteiro" de
                      navegação: voltar uma jogada = desempilhar.
        """
        self.nos = {}  # Formato: { "hash_do_estado": Objeto NoArvore }
        self.id_raiz = None
        self.caminho = []
        self.repeticoes_evitadas = 0

        if estado_inicial is not None:
            raiz = NoArvore(estado_inicial)
            self.nos[raiz.id_no] = raiz
            self.id_raiz = raiz.id_no
            self.caminho = [raiz.id_no]

    # --- Consulta ------------------------------------------------------------

    def id_atual(self):
        """Hash do nó em que a partida está agora (o último do caminho)."""
        if not self.caminho:
            return None
        return self.caminho[-1]

    def no_atual(self):
        return self.nos.get(self.id_atual())

    def obter_no(self, id_no):
        """Busca rápida de um nó na memória."""
        return self.nos.get(id_no)

    def buscar_estado(self, estado):
        """
        Procura um estado na árvore inteira (qualquer nível). Retorna o nó ou None.
        1ª etapa: o hash localiza o candidato em O(1).
        2ª etapa: a assinatura completa confirma a igualdade (protege contra colisão de hash).
        """
        no = self.nos.get(gerar_hash(estado))
        if no is None:
            return None
        if not estados_iguais(no.estado, estado):
            raise RuntimeError(f"Colisão de hash no nó {no.id_no}: estados diferentes com o mesmo hash.")
        return no

    # --- Construção ----------------------------------------------------------

    def adicionar_filho(self, id_pai, jogada, estado_filho):
        """
        Cria a aresta 'jogada' saindo de id_pai.
          - Estado inédito: cria o nó, com profundidade = pai + 1.
          - Estado que já existe em QUALQUER nível: não cria outro nó; a aresta aponta para o
            nó existente. Assim nenhum estado é inserido duas vezes.
        :param jogada: Objeto com .chave e .para_dict() (a Jogada do motor).
        :return: (id_filho, criado)
        """
        pai = self.nos[id_pai]
        if jogada.chave in pai.filhos:
            return pai.filhos[jogada.chave]["id"], False

        dados_jogada = jogada.para_dict()
        existente = self.buscar_estado(estado_filho)
        if existente is not None:
            self.repeticoes_evitadas += 1
            pai.filhos[jogada.chave] = {"id": existente.id_no, "jogada": dados_jogada}
            return existente.id_no, False

        filho = NoArvore(estado_filho, id_pai, dados_jogada, pai.profundidade + 1, len(self.nos))
        self.nos[filho.id_no] = filho
        pai.filhos[jogada.chave] = {"id": filho.id_no, "jogada": dados_jogada}
        return filho.id_no, True

    # --- Ponteiro de navegação (caminho da partida) -----------------------------

    def avancar(self, chave_jogada):
        """Move o ponteiro pela aresta da jogada feita (empilha o filho no caminho)."""
        aresta = self.no_atual().filhos.get(chave_jogada)
        if aresta is None:
            raise KeyError(f"A jogada '{chave_jogada}' não sai do nó atual.")
        self.caminho.append(aresta["id"])
        return self.no_atual()

    def voltar(self):
        """Desfaz a última jogada do caminho (desempilha). Retorna o novo nó atual, ou None na raiz."""
        if len(self.caminho) <= 1:
            return None
        self.caminho.pop()
        return self.no_atual()

    def ir_para(self, id_no):
        """Viagem no tempo direta para qualquer nó: o caminho é refeito subindo pelos pais."""
        if id_no not in self.nos:
            raise KeyError(f"Nó {id_no} não existe na árvore.")
        caminho = []
        atual = id_no
        while atual is not None:
            caminho.append(atual)
            atual = self.nos[atual].id_pai
        self.caminho = caminho[::-1]
        return self.no_atual()

    # --- Diagnóstico ----------------------------------------------------------

    def estatisticas(self):
        alcancados = sum(1 for no in self.nos.values() if no.expandido)
        return {
            "nos": len(self.nos),
            "estados_alcancados": alcancados,
            "estados_previstos": len(self.nos) - alcancados,
            "profundidade_maxima": max((no.profundidade for no in self.nos.values()), default=0),
            "jogadas_no_caminho_atual": max(len(self.caminho) - 1, 0),
            "repeticoes_evitadas": self.repeticoes_evitadas,
        }

    def validar(self):
        """
        Confere as regras do trabalho e a integridade da estrutura.
        Retorna a lista de problemas encontrados (lista vazia = árvore íntegra).
        """
        problemas = []
        assinaturas = {}
        for id_no, no in self.nos.items():
            assinatura = assinatura_do_estado(no.estado)
            if gerar_hash(no.estado) != id_no:
                problemas.append(f"nó {id_no[:6]}: o hash não corresponde ao estado guardado")
            if assinatura in assinaturas:
                problemas.append(f"estado repetido nos nós {assinaturas[assinatura][:6]} e {id_no[:6]}")
            assinaturas[assinatura] = id_no

            if no.filhos and not no.expandido:
                problemas.append(f"nó {id_no[:6]}: tem filhos sem ter sido jogado (fere a Regra de Ouro)")
            for chave, aresta in no.filhos.items():
                if aresta["id"] not in self.nos:
                    problemas.append(f"nó {id_no[:6]}: a aresta '{chave}' aponta para um nó inexistente")

            if no.id_pai is None:
                if id_no != self.id_raiz:
                    problemas.append(f"nó {id_no[:6]}: não tem pai e não é a raiz")
            else:
                pai = self.nos.get(no.id_pai)
                if pai is None or id_no not in pai.ids_filhos():
                    problemas.append(f"nó {id_no[:6]}: não está entre os filhos do seu pai")
                elif no.profundidade != pai.profundidade + 1:
                    problemas.append(f"nó {id_no[:6]}: profundidade inconsistente")
                elif not pai.expandido:
                    problemas.append(f"nó {id_no[:6]}: filho de um estado nunca jogado (fere a Regra de Ouro)")

        if not self.caminho or self.caminho[0] != self.id_raiz:
            problemas.append("o caminho da partida não começa na raiz")
        for id_no in self.caminho:
            if id_no not in self.nos:
                problemas.append(f"o caminho contém o nó inexistente {id_no[:6]}")
            elif not self.nos[id_no].expandido:
                problemas.append(f"o nó {id_no[:6]} do caminho não teve o nível abaixo gerado")
        for anterior, seguinte in zip(self.caminho, self.caminho[1:]):
            if anterior in self.nos and seguinte not in self.nos[anterior].ids_filhos():
                problemas.append(f"caminho quebrado entre {anterior[:6]} e {seguinte[:6]}")
        return problemas

    # --- Persistência ---------------------------------------------------------

    def salvar_json(self, caminho_arquivo=ARQUIVO_ARVORE + ".json"):
        """Converte todos os nós para um formato serializável e exporta."""
        dados_exportacao = {
            "formato": "arvore_de_estados_rumble_nation",
            "versao": VERSAO_FORMATO,
            "id_raiz": self.id_raiz,
            "caminho_atual": self.caminho,
            "repeticoes_evitadas": self.repeticoes_evitadas,
            "estatisticas": self.estatisticas(),
            "nos": {id_no: no.para_dict() for id_no, no in self.nos.items()},
        }
        with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
            json.dump(dados_exportacao, arquivo, ensure_ascii=False, indent=2)
        return caminho_arquivo

    def carregar_json(self, caminho_arquivo=ARQUIVO_ARVORE + ".json"):
        """Reconstrói a árvore inteira (inclusive o caminho da partida) a partir do arquivo JSON."""
        with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        if dados.get("versao") != VERSAO_FORMATO:
            raise ValueError("Arquivo gerado pela versão antiga da árvore. Jogue uma partida nova e salve de novo.")

        self.nos = {}
        for id_no, info in dados["nos"].items():
            no = NoArvore(info["estado"], info["id_pai"], info["jogada"], info["profundidade"], info["ordem"])
            no.expandido = info["expandido"]
            no.filhos = info["filhos"]
            if no.id_no != id_no:
                raise ValueError(f"Arquivo corrompido: o nó {id_no[:6]} não corresponde ao estado guardado.")
            self.nos[id_no] = no

        self.id_raiz = dados["id_raiz"]
        self.caminho = list(dados.get("caminho_atual") or [self.id_raiz])
        self.repeticoes_evitadas = dados.get("repeticoes_evitadas", 0)

        problemas = self.validar()
        if problemas:
            raise ValueError("Árvore inconsistente no arquivo: " + problemas[0])

    # --- Apresentação (Graphviz) -----------------------------------------------

    def exportar_graphviz(self, caminho_arquivo=ARQUIVO_ARVORE + ".dot"):
        """
        Gera o arquivo .dot usando apenas o texto da jogada de cada nó.
        O caminho jogado fica com setas mais grossas e alinhado em uma coluna (group),
        o que mostra o caminho escolhido no meio das previsões de 1 nível.
        O estado que encerrou a partida aponta para um nó "Final da Partida".
        O estado atual (onde a partida continua ao carregar o .json) fica pintado de laranja.
        """
        id_atual = self.id_atual()
        nos_do_caminho = set(self.caminho)
        arestas_do_caminho = set(zip(self.caminho, self.caminho[1:]))
        linhas = [
            "digraph ArvoreRumbleNation {",
            "    rankdir=TB;",
            '    node [shape=box, style=filled, fillcolor="lightyellow", fontname="Arial"];',
        ]

        for no in sorted(self.nos.values(), key=lambda n: n.ordem):
            atributos = ""
            if no.id_no in nos_do_caminho:
                atributos += ', group="caminho"'
            if no.id_no == id_atual:
                atributos += ', fillcolor="orange"'  # estado atual
            linhas.append(f'    "n{no.ordem}" [label="{_texto_dot(no.titulo)}"{atributos}];')

            for aresta in no.filhos.values():
                filho = self.nos[aresta["id"]]
                atributos = []
                if (no.id_no, filho.id_no) in arestas_do_caminho:
                    atributos.append("penwidth=3, weight=20")  # jogada realizada
                if filho.id_pai != no.id_no:
                    # A jogada leva a um estado que já existe (criado por outro caminho). A caixa de
                    # destino mostra a jogada do outro caminho, então a seta leva o nome desta jogada.
                    rotulo = _rotulo_com_fundo(aresta["jogada"]["rotulo"])
                    atributos.append(f'style=dashed, constraint=false, label={rotulo}, fontname="Arial", fontsize=10')
                estilo = ""
                if atributos:
                    estilo = " [" + ", ".join(atributos) + "]"
                linhas.append(f'    "n{no.ordem}" -> "n{filho.ordem}"{estilo};')

        # Se o último estado da partida não tem mais jogadas possíveis, ele levou ao fim do jogo.
        # O "Final da Partida" é só um marcador no desenho: não é um estado novo na árvore.
        ultimo = self.no_atual()
        if ultimo is not None and ultimo.expandido and not ultimo.filhos:
            linhas.append('    "final" [label="Final da Partida", group="caminho"];')
            linhas.append(f'    "n{ultimo.ordem}" -> "final" [penwidth=3, weight=20];')

        linhas.append("}")

        with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
            arquivo.write("\n".join(linhas))
        return caminho_arquivo


def _texto_dot(texto):
    """Escapa o texto para um rótulo entre aspas do Graphviz (a quebra de linha vira \\n)."""
    return str(texto).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _rotulo_com_fundo(texto):
    """
    Rótulo de seta com fundo branco (formato HTML do Graphviz), para o texto não se
    misturar com as linhas que passam por baixo dele.
    """
    partes = []
    for linha in str(texto).split("\n"):
        partes.append(linha.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return '<<TABLE BORDER="0" CELLBORDER="0" CELLPADDING="2" BGCOLOR="white"><TR><TD>' + "<BR/>".join(partes) + "</TD></TR></TABLE>>"


def renderizar_graphviz(caminho_dot, formato="png"):
    """
    Converte o .dot em imagem com o programa 'dot' do Graphviz, se estiver instalado no PATH.
    Retorna o caminho da imagem, ou None se o Graphviz não estiver disponível.
    """
    executavel = shutil.which("dot")
    if executavel is None:
        return None
    saida = os.path.splitext(caminho_dot)[0] + "." + formato
    try:
        subprocess.run([executavel, f"-T{formato}", caminho_dot, "-o", saida],
                       check=True, capture_output=True, timeout=120,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return None
    return saida


# =============================================================================
#  NAVEGADOR: motor do jogo + árvore sincronizados
# =============================================================================

class NavegadorDeArvore:
    def __init__(self, motor, arvore=None):
        """
        É o ÚNICO ponto por onde jogadas reais e simulações passam.
        :param motor: A LogicaJogo da partida. O navegador usa dela: obter_estado, carregar_estado,
                      clonar, gerar_jogadas_possiveis, simular_jogada, aplicar_jogada e
                      explicar_jogada_invalida.
        :param arvore: Uma árvore já carregada do JSON (opcional). Sem ela, a árvore começa
                       no estado atual do motor; com ela, o motor vai para o estado atual da árvore.
        """
        self.motor = motor
        if arvore is None:
            arvore = ArvoreDeEstados(motor.obter_estado())
        else:
            motor.carregar_estado(arvore.no_atual().estado)
        self.arvore = arvore
        self._expandir(arvore.id_atual())

    def no_atual(self):
        return self.arvore.no_atual()

    def jogadas_disponiveis(self):
        """Jogadas legais do estado atual (são exatamente as arestas que saem do nó atual)."""
        return self.motor.gerar_jogadas_possiveis()

    def jogar(self, jogada):
        """
        Executa uma jogada REAL:
          1. a jogada precisa ser uma das arestas já previstas no nó atual;
          2. o motor ao vivo aplica a jogada;
          3. o estado real é comparado com o nó previsto (têm que ser idênticos);
          4. o ponteiro segue a aresta (o nó previsto vira o nó atual; nada é criado);
          5. o novo nó atual ganha o seu nível de filhos.
        """
        no_anterior = self.arvore.no_atual()
        aresta = no_anterior.filhos.get(jogada.chave)
        if aresta is None:
            raise ValueError(self.motor.explicar_jogada_invalida(jogada))

        previsto = self.arvore.obter_no(aresta["id"])
        self.motor.aplicar_jogada(jogada)
        if not estados_iguais(self.motor.obter_estado(), previsto.estado):
            self.motor.carregar_estado(no_anterior.estado)
            raise RuntimeError(f"A jogada '{jogada.chave}' produziu um estado diferente do previsto: "
                               "o motor precisa ser determinístico.")

        self.arvore.avancar(jogada.chave)
        self._expandir(previsto.id_no)
        return previsto

    def voltar(self):
        """Desfaz a última jogada: desempilha o caminho e recarrega o estado no motor."""
        no = self.arvore.voltar()
        if no is not None:
            self.motor.carregar_estado(no.estado)
        return no

    def ir_para(self, id_no):
        """Viagem no tempo para qualquer nó da árvore (ex.: escolhido no terminal)."""
        no = self.arvore.ir_para(id_no)
        self.motor.carregar_estado(no.estado)
        self._expandir(no.id_no)
        return no

    def _expandir(self, id_no):
        """
        REGRA DE OURO: gera exatamente 1 nível abaixo de um estado alcançado pela partida.
        Cada jogada possível é simulada numa cópia do estado do nó; o motor ao vivo nunca é tocado.
        Estados que já existem (em qualquer nível) não são inseridos de novo.
        """
        no = self.arvore.obter_no(id_no)
        if no.expandido:
            return
        rascunho = self.motor.clonar(no.estado)
        for jogada in rascunho.gerar_jogadas_possiveis():
            self.arvore.adicionar_filho(id_no, jogada, rascunho.simular_jogada(jogada))
        no.expandido = True

    def salvar(self, base=ARQUIVO_ARVORE, imagem="png"):
        """Salva <base>.json e <base>.dot; gera <base>.png se o Graphviz estiver instalado."""
        arquivos = [
            self.arvore.salvar_json(base + ".json"),
            self.arvore.exportar_graphviz(base + ".dot"),
        ]
        if imagem:
            caminho_imagem = renderizar_graphviz(base + ".dot", imagem)
            if caminho_imagem:
                arquivos.append(caminho_imagem)
        return arquivos
