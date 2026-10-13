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

ARQUIVO_ARVORE = "arvore_rumble"   # nome base dos arquivos gerados: .json, .dot e .png
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

    @property
    def ids_filhos(self):
        return [aresta["id"] for aresta in self.filhos.values()]

    @property
    def titulo(self):
        """Texto curto da jogada que criou o nó (é o que aparece em negrito no Graphviz)."""
        if self.jogada is None:
            return "Início da partida"
        return f"J{self.jogada['jogador']} · {self.jogada['rotulo']}"

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

    @classmethod
    def de_dict(cls, dados):
        no = cls(dados["estado"], dados["id_pai"], dados["jogada"], dados["profundidade"], dados["ordem"])
        no.expandido = dados["expandido"]
        no.filhos = dados["filhos"]
        return no


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

    @property
    def id_atual(self):
        return self.caminho[-1] if self.caminho else None

    @property
    def no_atual(self):
        return self.nos.get(self.id_atual)

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
        aresta = self.no_atual.filhos.get(chave_jogada)
        if aresta is None:
            raise KeyError(f"A jogada '{chave_jogada}' não sai do nó atual.")
        self.caminho.append(aresta["id"])
        return self.no_atual

    def voltar(self):
        """Desfaz a última jogada do caminho (desempilha). Retorna o novo nó atual, ou None na raiz."""
        if len(self.caminho) <= 1:
            return None
        self.caminho.pop()
        return self.no_atual

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
        return self.no_atual

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
                if pai is None or id_no not in pai.ids_filhos:
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
            if anterior in self.nos and seguinte not in self.nos[anterior].ids_filhos:
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
            no = NoArvore.de_dict(info)
            if no.id_no != id_no:
                raise ValueError(f"Arquivo corrompido: o nó {id_no[:6]} não corresponde ao estado guardado.")
            self.nos[id_no] = no

        self.id_raiz = dados["id_raiz"]
        self.caminho = list(dados.get("caminho_atual") or [self.id_raiz])
        self.repeticoes_evitadas = dados.get("repeticoes_evitadas", 0)

        problemas = self.validar()
        if problemas:
            raise ValueError("Árvore inconsistente no arquivo: " + problemas[0])
        return self

    # --- Apresentação (Graphviz) -----------------------------------------------

    def exportar_graphviz(self, caminho_arquivo=ARQUIVO_ARVORE + ".dot", resumir=None,
                          titulo="Rumble Nation · Árvore de Estados"):
        """
        Gera o arquivo .dot da árvore:
          - verde: caminho da partida (jogadas realizadas), desenhado como uma coluna vertical
            (atributo group); amarelo: estado atual;
          - cinza: jogadas que foram feitas e depois desfeitas (voltar no tempo);
          - tracejado: previsões de 1 nível abaixo (jogadas possíveis que não foram feitas);
          - seta laranja tracejada: jogada que leva a um estado que já existe (repetição evitada).
        :param resumir: Função opcional estado -> texto (ex.: LogicaJogo.resumir_estado).
        """
        id_atual = self.id_atual
        nos_do_caminho = set(self.caminho)
        arestas_do_caminho = set(zip(self.caminho, self.caminho[1:]))
        nome = {id_no: f"n{no.ordem}" for id_no, no in self.nos.items()}
        nos_ordenados = sorted(self.nos.values(), key=lambda no: no.ordem)
        estat = self.estatisticas()

        subtitulo = (f"{estat['nos']} estados · {estat['estados_alcancados']} alcançados pela partida · "
                     f"{estat['estados_previstos']} previsões · {estat['jogadas_no_caminho_atual']} jogadas no caminho atual")
        linhas = [
            "digraph ArvoreRumbleNation {",
            '    graph [rankdir=TB, fontname="Arial", fontsize=14, labelloc=t, nodesep=0.25, ranksep=0.45, pad=0.3,',
            f'           label=<<B>{_html(titulo)}</B><BR/><FONT POINT-SIZE="10">{_html(subtitulo)}</FONT><BR/> >];',
            '    node [shape=box, style="rounded,filled", fontname="Arial", fontsize=10, margin="0.10,0.05"];',
            '    edge [fontname="Arial", fontsize=8, arrowsize=0.6];',
            "",
        ]

        for no in nos_ordenados:
            partes = [f"<B>{_html(no.titulo)}</B>"]
            if resumir is not None:
                for linha in resumir(no.estado).split("\n"):
                    partes.append(f'<FONT POINT-SIZE="9">{_html(linha)}</FONT>')
            partes.append(f'<FONT POINT-SIZE="8" COLOR="#6c757d">id {no.id_no[:6]} · nível {no.profundidade}</FONT>')
            rotulo = "<" + "<BR/>".join(partes) + ">"
            linhas.append(f"    {nome[no.id_no]} [label={rotulo}, {self._estilo_do_no(no, id_atual, nos_do_caminho)}];")

        linhas.append("")
        for no in nos_ordenados:
            ligados = set()
            for aresta in no.filhos.values():
                destino = self.nos[aresta["id"]]
                par = (no.id_no, destino.id_no)
                repeticao = destino.id_pai != no.id_no or par in ligados
                ligados.add(par)

                if par in arestas_do_caminho:
                    atributos = ['color="#2d6a4f"', "penwidth=2.6", "weight=20"]
                elif repeticao:
                    atributos = ['color="#e76f51"']
                elif destino.expandido:
                    atributos = ['color="#6c757d"', "penwidth=1.2"]
                else:
                    atributos = ['color="#b5bcc3"']
                if repeticao:
                    texto = f"J{aresta['jogada']['jogador']} · {aresta['jogada']['rotulo']}"
                    atributos += ["style=dashed", "constraint=false", 'fontcolor="#c2410c"',
                                  f"label=<{_html(texto)}<BR/>(estado já existente)>"]
                linhas.append(f"    {nome[no.id_no]} -> {nome[destino.id_no]} [{', '.join(atributos)}];")

        linhas += [
            "",
            "    subgraph cluster_legenda {",
            '        label=<<B>Legenda</B>>; fontsize=10; style="rounded"; color="#ced4da";',
            '        node [fontsize=9, margin="0.08,0.03"];',
            '        legenda_caminho [label="Jogada realizada\\n(caminho da partida)", fillcolor="#d8f3dc", color="#2d6a4f", penwidth=2];',
            '        legenda_atual [label="Estado atual", fillcolor="#ffd166", color="#9c6500", penwidth=3];',
            '        legenda_desfeita [label="Jogada desfeita\\n(voltou no tempo)", fillcolor="#e9ecef", color="#6c757d"];',
            '        legenda_prevista [label="Previsão: 1 nível abaixo\\n(não jogada)", style="rounded,filled,dashed", fillcolor="#ffffff", color="#9aa0a6"];',
            "        { rank=same; legenda_caminho; legenda_atual; legenda_desfeita; legenda_prevista; }",
            "        legenda_caminho -> legenda_atual -> legenda_desfeita -> legenda_prevista [style=invis];",
            "    }",
            "}",
        ]

        with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
            arquivo.write("\n".join(linhas))
        return caminho_arquivo

    @staticmethod
    def _estilo_do_no(no, id_atual, nos_do_caminho):
        if no.id_no == id_atual:
            estilo = 'fillcolor="#ffd166", color="#9c6500", penwidth=3, group="caminho"'
        elif no.id_no in nos_do_caminho:
            estilo = 'fillcolor="#d8f3dc", color="#2d6a4f", penwidth=2, group="caminho"'
        elif no.expandido:
            estilo = 'fillcolor="#e9ecef", color="#6c757d", penwidth=1.2'
        else:
            estilo = 'style="rounded,filled,dashed", fillcolor="#ffffff", color="#9aa0a6", fontcolor="#495057"'
        if no.expandido and not no.filhos:
            estilo += ", peripheries=2"  # Estado final: não há mais jogadas possíveis
        return estilo


def _html(texto):
    """Escapa texto para os rótulos HTML do Graphviz."""
    return (str(texto).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


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
    """
    É o ÚNICO ponto por onde jogadas reais e simulações passam.

    Contrato do motor (duck typing):
        obter_estado() -> dict                  carregar_estado(estado)
        gerar_jogadas_possiveis() -> [Jogada]   todas as ramificações do estado atual
        simular_jogada(jogada) -> dict          estado resultante, SEM alterar o motor
        aplicar_jogada(jogada)                  jogada real
        explicar_jogada_invalida(jogada) -> str
        de_estado(estado)  (classmethod)        resumir_estado(estado) -> str  (opcional)
    Contrato da Jogada: atributo .chave (texto único entre irmãos) e método .para_dict().
    """

    def __init__(self, motor, arvore=None):
        self.motor = motor
        if arvore is None:
            arvore = ArvoreDeEstados(motor.obter_estado())
        else:
            motor.carregar_estado(arvore.no_atual.estado)
        self.arvore = arvore
        self._expandir(arvore.id_atual)

    @classmethod
    def carregar(cls, caminho_json, classe_motor):
        """Carrega uma árvore salva e posiciona o motor no estado atual que foi salvo."""
        arvore = ArvoreDeEstados().carregar_json(caminho_json)
        motor = classe_motor.de_estado(arvore.no_atual.estado)
        return cls(motor, arvore)

    @property
    def no_atual(self):
        return self.arvore.no_atual

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
        no_anterior = self.arvore.no_atual
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
        rascunho = self.motor.de_estado(no.estado)
        for jogada in rascunho.gerar_jogadas_possiveis():
            self.arvore.adicionar_filho(id_no, jogada, rascunho.simular_jogada(jogada))
        no.expandido = True

    def salvar(self, base=ARQUIVO_ARVORE, imagem="png"):
        """Salva <base>.json e <base>.dot; gera <base>.png se o Graphviz estiver instalado."""
        arquivos = [
            self.arvore.salvar_json(base + ".json"),
            self.arvore.exportar_graphviz(base + ".dot", resumir=getattr(self.motor, "resumir_estado", None)),
        ]
        if imagem:
            caminho_imagem = renderizar_graphviz(base + ".dot", imagem)
            if caminho_imagem:
                arquivos.append(caminho_imagem)
        return arquivos
