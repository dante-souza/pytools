# Arquitetura e contratos de integração

## Independência do componente

O projeto é intencionalmente **monolítico de arquivo único para distribuição**,
mas separado internamente em componentes com responsabilidade definida:

```text
                     ┌─────────────────────────┐
                     │ Aplicação (qualquer)     │
                     └──────────┬──────────────┘
                                │ importa logger_general.py
             ┌──────────────────┼────────────────────────┐
             ▼                  ▼                        ▼
    ┌────────────────┐  ┌────────────────────┐  ┌────────────────────┐
    │ GeneralLogger  │  │ render_json()      │  │ JsonlWriter        │
    │ texto + ANSI   │  │ render_json_html() │  │ append compacto    │
    └───────┬────────┘  └─────────┬──────────┘  └─────────┬──────────┘
            ▼                     │                       ▼
       stderr / .log             │                    .jsonl
                                  │                       │
                                  └──────┬────────────────┘
                                         ▼
                              view_file(.json/.jsonl/.log)
```

Não há ligação entre `GeneralLogger` e `JsonlWriter`. Um agente com
`EventRecorder`, uma API FastAPI ou um script batch pode injetar dados
JSON-serializáveis em `JsonlWriter.write()` e deixar a renderização opcional.

## API essencial

| Unidade | Entrada | Saída | Estado |
|---|---|---|---|
| `GeneralLogger` | nível, mensagem, stream, caminho opcional | terminal e arquivo `.log` | handlers privados por instância |
| `JsonlWriter` | valor JSON, caminho, serializer opcional | linha JSON compacta, UTF-8 | arquivo append controlado |
| `render_json` | valor Python JSON, tema por nome, indentação | `str` ANSI ou plain | puro, sem I/O |
| `render_json_html` | valor Python JSON e regras semânticas | `str` HTML escapado | puro, sem I/O |
| `print_json` | valor JSON + stream | impressão de JSON | usa renderizador |
| `view_file` | arquivo `.json`, `.jsonl`, `.log` | stdout/stream | somente leitura |
| `run_demo()` | modo de cor | demonstração em diretório temporário | não afeta projeto externo |
| `run_selftest()` | modo de cor | asserts e diagnóstico | não publica artefatos |
| `main()` | CLI via Makefile | códigos de saída 0/2 | depende apenas de stdlib |

A função `_segments()` recebe JSON já serializado e classifica tokens.
Não tenta validar JSON arbitrário diretamente com regex. O formato continua
válido quando escapamos os trechos ANSI novamente.

## Acoplamento mínimo em projetos futuros

Copie `logger_general.py` para um diretório importável ou instale este pacote
em modo editável com **`make setup`**. Reaproveite `GeneralLogger` para mensagens
humanas; `JsonlWriter` para dados estruturados; `render_json_html` no Jupyter.

Se for integrar com um framework de instrumentação, a aplicação define um
*adapter* próprio para mapear os eventos para estruturas JSON nativas. O módulo
não importa OpenTelemetry nem conhecimento específico de eventos de agentes.

## Limites intencionais

Sem persistência de segredos, controle de acesso, fila, async, multiprocess,
interpretação de stack traces de terceiros, arquivo rotativo, agregadores
remotos ou garantias transacionais. Para produção, introduza políticas de
retenção, limites de tamanho, testes de performance, locking e filtragem de
informação antes da gravação.

A extração de sintaxe aplica fragmentos ANSI ao **texto renderizado**, não aos
dados originais. Ao gerar HTML, fragmentos são escapados com `html.escape()`
e as cores são retiradas de uma paleta de estilos conhecida.
