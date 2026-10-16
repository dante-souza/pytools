# Logger General — módulo portátil de logging e Pretty Print de JSON

Um mini-projeto em Python para **reutilizar em qualquer aplicação**, sem precisar
copiar o `Logger`, o `EventRecorder` ou a estrutura do `curso_claude`.

- **Módulo principal:** [`logger_general.py`](logger_general.py) — **um único arquivo**, Python >= 3.10, **somente biblioteca padrão**.
- **Logs humanos:** cores por severidade no terminal e gravação de `.log` sem códigos ANSI.
- **JSON genérico:** chaves, strings, números, `true`/`false`, `null`, objetos aninhados e listas.
- **Semântica opcional:** `level`, `status`, `result`, `resultado`, `severity` etc.; permite adicionar campos específicos da sua aplicação, sem acoplá-los ao módulo.
- **JSONL/NDJSON:** writer append sem ANSI, visualizador em streaming (linha por linha), erros de sintaxe informados sem interromper as demais linhas.
- **Jupyter:** saída ANSI e, sobretudo, **HTML com cores renderizadas pelo notebook**, com escape dos dados para evitar injeção de HTML.
- **Experimentos:** demo via `main()`, smoke test em runtime, testes `unittest`, projeto de exemplo e notebook executável.
- **Interface de comandos:** tudo via **`make`**, inclusive inicialização do notebook.

**Este módulo é independente do `curso_claude` e não depende de Anthropic, OpenTelemetry, Pydantic, Rich ou Pygments. Está distribuído dentro do repositório `pytools` sob a licença AGPL-3.0 (veja `../LICENSE`).**

## 1. Estrutura

```text
logger/
├── logger_general.py                # único arquivo necessário para acoplar
├── Makefile                         # interface padrão no terminal
├── pyproject.toml                   # instalação editável opcional
├── README.md                        # documentação do módulo e das cores
├── docs/
│   └── ARQUITETURA.md              # contratos, integração e limites
├── examples/
│   ├── __init__.py
│   ├── events.jsonl                 # amostra fictícia de eventos
│   ├── event.json                   # JSON único, tradicional
│   ├── application.log             # amostra de log de texto
│   ├── integration_example.py       # módulo usado por uma aplicação fictícia
│   └── cleanup.py                   # limpeza multiplataforma
├── notebooks/
│   └── logger_general_exemplos.ipynb
└── tests/
    ├── test_logger_general.py
    └── test_notebook.py
```

Arquivos criados em `examples/output/` ficam fora do controle de versão.

## 2. Começar — apenas Makefile

Abra o terminal **na pasta `logger/` do repositório `pytools`**. Não é necessário instalar o módulo
nem configurar ambiente Conda para os exemplos offline: use um Python >= 3.10 e
GNU Make. Se preferir, execute os alvos no ambiente virtual de sua escolha.

```powershell
make help
make doctor
make demo
make smoke
make test
make check
```

**`make demo`** executa `main()` com níveis INFO/WARNING/ERROR, grava logs e
JSONL temporários, exibe JSON Pretty colorido e valida a ausência de ANSI
nos arquivos gravados. Não chama nenhuma API ou rede.

**`make smoke`** executa verificações com `assert` na própria aplicação;
**`make test`** roda a suíte offline completa. **`make check`** executa ambos.

## 3. Pretty Print de JSON/JSONL no terminal

```powershell
# JSONL: uma linha de origem vira um bloco JSON indentado.
make pretty FILE=examples/events.jsonl COLOR=always

# Sem cores, ótimo para inspeção ou copiar o conteúdo.
make pretty FILE=examples/events.jsonl COLOR=never

# Versão compacta, ainda destacando sintaxe quando colorida.
make view FILE=examples/events.jsonl PRETTY=0 COLOR=always

# JSON tradicional (um documento inteiro, com listas e objetos).
make view FILE=examples/event.json KIND=json PRETTY=1

# Arquivo de logs humanos: colorir WARNING/ERROR na leitura.
make view FILE=examples/application.log

# Alias que nunca insere ANSI na saída.
make view-plain FILE=examples/events.jsonl
```

Parâmetros de Makefile: `COLOR=always|auto|never`, `PRETTY=1|0`,
`KIND=auto|json|jsonl|log`, `HEADINGS=1|0`, `FILE=caminho`.

A resolução do tipo por extensão (`.json`, `.jsonl`, `.ndjson`, `.log`) pode ser
substituída por `KIND`. JSONL é **streaming**; um `.json` integral é lido como
um documento único. `view_file()` não altera os arquivos de origem.

## 4. API para incorporar em outra aplicação

Para a integração mais simples, **copie somente `logger_general.py`** para a
pasta importável do seu projeto. As importações abaixo continuam funcionando,
independentemente do framework usado pela aplicação.

### 4.1 Logging de mensagens humanas

```python
from logger_general import GeneralLogger

with GeneralLogger(
    name="minha.aplicacao",
    level="DEBUG",
    color="auto",             # auto | always | never
    log_file="logs/app.log",   # arquivo sem escape ANSI
) as logger:
    logger.info("Aplicação iniciada")
    logger.debug("Carregando configuração")
    logger.warning("Tentativa 2/3")
    logger.error("Falha simulada")
```

O logger usa uma instância **privada** de `logging.Logger`; não configura
`logging.basicConfig()` nem modifica os handlers globais. Instâncias
independentes não removem handlers uma da outra. Saída por padrão:
`stderr`; arquivo somente quando `log_file` é informado.

### 4.2 Formatação de JSON Python nativo

```python
from logger_general import render_json, print_json

objeto = {
    "servico": "pedidos",
    "status": "denied",
    "latencia_ms": 12.5,
    "ativo": True,
    "itens": [1, 2, 3],
    "motivo": None,
}

print(render_json(objeto, pretty=True, indent=2, color="always"))
print_json(objeto, color="auto")
```

`render_json()` **serializa corretamente com `json.dumps()` antes de colorir**.
Não usamos simples substituições globais que confundiriam uma string contendo
`"true"` com o literal `true`.

O argumento `default=...` permite adaptar objetos Python que não são tipos
JSON nativos, usando o contrato de `json.dumps`. Valores `NaN` e infinito
são rejeitados por padrão para manter JSON válido.

Há também uma configuração opcional **imutável** (`DisplayOptions`), útil para
reutilizar a mesma apresentação em diferentes chamadas:

```python
from dataclasses import asdict
from logger_general import DisplayOptions, render_json

aparencia = DisplayOptions(color="always", indent=4, pretty=True)
print(render_json({"status": "ok"}, **asdict(aparencia)))
```

### 4.3 Cores semânticas para campos da sua aplicação

Além do tipo JSON, podemos colorir **significados**. Por padrão, reconhecemos:

| Campo | Exemplos de valores reconhecidos | Cor |
|---|---|---|
| `status`, `result`, `resultado`, `outcome` | `success`, `ok`, `sucesso`, `autorizado` | Verde |
| os mesmos | `warning`, `denied`, `negado`, `pending` | Amarelo |
| os mesmos | `error`, `erro`, `failed`, `falha` | Vermelho |
| `level`, `severity`, `state` | valores equivalentes aos anteriores | Conforme severidade |

Esse vocabulário é apenas **um padrão de apresentação**, não uma política de
negócio. Para termos próprios, passe `semantic_rules`:

```python
from logger_general import render_json

minhas_regras = {
    "deployment": {"deployed": "success", "rollback": "error"},
    "pipeline": {"waiting": "warning"},
}

print(render_json(
    {"deployment": "rollback", "pipeline": "waiting", "tentativas": 3},
    color="always",
    semantic_rules=minhas_regras,
))
```

Papéis de cores disponíveis: `key`, `string`, `number`, `boolean`, `null`,
`success`, `warning`, `error`, `debug`, `info`, `critical`. Uma regra que
especifique um papel inexistente é rejeitada; não aceitamos sequências ANSI
ou CSS arbitrárias por esse parâmetro.

### 4.4 Gravação JSONL desacoplada do log humano

```python
from logger_general import JsonlWriter

with JsonlWriter("logs/eventos.jsonl") as sink:
    sink.write({"trace_id": "abc", "status": "success", "duracao_ms": 1.23})
    sink.write({"trace_id": "abc", "status": "denied", "motivo": "regra"})
```

O `JsonlWriter` **não depende** de `GeneralLogger`, não modifica `EventRecorder`
ou outros conceitos de aplicações de terceiros e grava **JSONL compacto sem ANSI**.
Usa modo append; cada escrita é um registro completo por linha.

### 4.5 Ler arquivos sem modificá-los

```python
from logger_general import view_file

view_file("logs/eventos.jsonl", pretty=True, color="always")
view_file("logs/app.log", color="auto")
```

Uma linha JSONL malformada produz aviso com o número da linha, mostra o
conteúdo original e **não impede** a leitura das demais.

## 5. Como a colorização ANSI funciona, de fato

O terminal interpreta **sequências de controle**, não formatação armazenada em
um JSON. Em Python, `"\033"` representa o caractere **ESC** (octal 033, decimal
27, hexadecimal `0x1B`). A sequência `ESC [` é chamada **CSI** (*Control
Sequence Introducer*). Quando termina em `m`, é uma sequência **SGR**
(*Select Graphic Rendition*), usada para escolher cores e atributos de texto.

Exemplo:

```python
AMARELO = "\033[93m"  # muda o primeiro plano para amarelo claro
RESET = "\033[0m"   # restaura o padrão

print(f"{AMARELO}Acesso negado{RESET}")
```

A string enviada contém `ESC[93m`, depois o texto e `ESC[0m`. Um terminal
compatível desenha apenas o texto na cor escolhida.

### Tabela dos códigos utilizados

| Papel | Código Python | SGR ANSI | Efeito |
|---|---|---|---|
| Reset | `"\033[0m"` | `0` | Redefine a formatação |
| Chaves JSON | `"\033[94m"` | `94` | Azul claro |
| Strings | `"\033[93m"` | `93` | Amarelo claro |
| Números | `"\033[96m"` | `96` | Ciano claro |
| Booleanos | `"\033[95m"` | `95` | Magenta claro |
| `null` | `"\033[90m"` | `90` | Cinza/bright black |
| Sucesso / INFO | `"\033[92m"` | `92` | Verde claro |
| Aviso / WARNING | `"\033[93m"` | `93` | Amarelo claro |
| Erro / ERROR | `"\033[91m"` | `91` | Vermelho claro |

Outros grupos usuais de SGR: `30–37` são cores básicas de primeiro plano,
`40–47` fundos básicos, `90–97` primeiros planos claros, `100–107` fundos
claros, `1` negrito, `4` sublinhado, `22` remove negrito, `39` restaura cor
de primeiro plano, `49` restaura cor de fundo. Terminais mais modernos
podem aceitar `38;5;N` (256 cores) e `38;2;R;G;B` (True Color), mas
**nosso módulo usa apenas o conjunto ANSI simples** para portabilidade.

### Como identificamos chaves, tipos e valores

1. `json.dumps(..., ensure_ascii=False)` cria uma representação JSON válida.
2. A expressão regular `_JSON_TOKEN` reconhece **tokens completos** de strings
   JSON, números e literais (`true`, `false`, `null`).
3. Strings seguidas de `:` são chaves; as demais são valores.
4. O texto é dividido em fragmentos com papéis (`key`, `string`, `number`...).
5. `_decorate()` adiciona ANSI **apenas na saída de terminal**.
6. Opcionalmente, os nomes de campo fornecem realce semântico (`status=denied`
   recebe amarelo; `status=failed` recebe vermelho).
7. `\033[0m` restaura a cor após **cada fragmento**, evitando contaminar a
   formatação de trechos posteriores.

**Por que após a serialização?** Porque já temos aspas escapadas corretamente
pela biblioteca `json`; números dentro de uma string JSON jamais são tratados
como tokens numéricos separados. Os dados também não podem injetar sequências
ANSI arbitrárias: caracteres ESC em strings são escapados na serialização.

### Quando as cores aparecem?

- `COLOR=always`: força ANSI, inclusive em redirecionamentos de saída.
- `COLOR=never`: garante saída sem cores ANSI.
- `COLOR=auto`: detecta terminal interativo; também considera o contexto
  `ipykernel`, quando disponível. Respeita a variável de ambiente `NO_COLOR`.
- Em PowerShell/Windows Terminal/PyCharm, depende do suporte do terminal a
  escapes ANSI. No Jupyter, a solução mais robusta é usar **HTML**.

**Importante:** `COLOR=always` ao redirecionar para um arquivo *pode* colocar
escapes ANSI nesse arquivo de saída. Isso **não** altera os dados originais
armazenados por `JsonlWriter` ou `GeneralLogger` em `log_file`.

## 6. Jupyter: ANSI e HTML são apresentações diferentes

O Jupyter pode mostrar cores ANSI na saída de células, mas nem todos os
frontends representam escapes da mesma maneira. Por isso incluímos também:

```python
from IPython.display import HTML, display
from logger_general import render_json_html

objeto = {"status": "success", "duracao_ms": 2.75}
display(HTML(render_json_html(objeto)))
```

O código gera `<pre>` e `<span>` com **estilos CSS pré-definidos** e usa
`html.escape()` em todo o conteúdo original. Assim, os valores da aplicação
não são interpretados como tags HTML. **O módulo principal não importa
IPython**; somente quem decide exibir HTML no notebook o faz.

O notebook incluído tem duas células com **pré-visualizações HTML de dados
fictícios** já salvas: ao abrir, você vê cores mesmo antes de executá-las.
Executar as células demonstra a renderização em tempo real.

```powershell
make setup-notebook
make notebook
```

Os demais exemplos do notebook mostram ANSI, persistência sem ANSI, leituras
JSONL, integração com `GeneralLogger`, regras semânticas e escape de HTML.

## 7. Integração simulada e testes

```powershell
# Uma aplicação de exemplo importando logger_general.py
make integration-demo COLOR=always

# Gerar os exemplos permanentes localmente em examples/output/
make sample

# Validar todos os casos principais e smoke do main()
make check

# Limpar caches/arquivos derivados (cross-platform)
make clean
```

Teste e demonstração **não** precisam de chave, credencial nem chamadas pagas.

## 8. Limites e recomendações de segurança

- O módulo é **um componente de apresentação e logging**, não um gerenciador
  de política, validação de caminhos ou *trace collector* de produção.
- Logging **não anonimiza nem redige dados automaticamente**. Quem integra é
  responsável por não registrar segredos, PII, payloads, prompts ou tokens.
- Arquivos JSONL e `.log` têm gravação simples de processo único, sem rotação,
  compressão, locking, retenção ou garantia de atomicidade entre processos.
- Mensagens de texto e cabeçalhos são saneados para escapes ANSI comuns;
  objetos JSON passam pelo serializador antes da colorização.
- Em geral, não coloque `COLOR=always` em pipelines que esperam texto puro;
  prefira `COLOR=never`.
- Um arquivo `.json` grande é lido integralmente; JSONL é lido incrementalmente.
- O parser visual trabalha sobre **JSON serializado válido**, não é um parser
  genérico para qualquer arquivo arbitrário.
- HTML para o notebook utiliza estilos fixos e texto escapado; **não** renderiza
  HTML bruto proveniente dos dados do JSON.
- Não há testes de compatibilidade com todo terminal ou versão de Jupyter.
- Distribuição: este módulo está no repositório `pytools` e usa a licença AGPL-3.0 disponível em [`../LICENSE`](../LICENSE).

Consulte [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) para conhecer os contratos
de cada classe/função e as opções de evolução.
