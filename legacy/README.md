# Legacy — implementações históricas

Esta pasta guarda versões **originais, sem alterações**, de ferramentas que
inspiraram ou antecederam os módulos reutilizáveis do repositório.

## logger.py

- **Origem:** arquivo `logger.py` fornecido pelo autor durante a criação do
  logger genérico deste projeto.
- **Preservação:** cópia byte a byte do arquivo original, incluindo quebras de
  linha CRLF (Windows). Não há refatoração, correção de estilo nem mudança no
  conteúdo ou no `__main__`.
- **SHA-256 original:** `66495a1bb86836a60a7746d340fc2ad9fe0492b61150f5b4f655110c024f7a82`.
- **Funções presentes:** `Logger`, `log_with_logger` e
  `logger_decorator`, com cores ANSI por nível de log e extras opcionais.
- **Atenção ao executar:** o exemplo final em `__main__` chama
  `failed_function()`, que provoca propositalmente divisão por zero. Portanto,
  executar o arquivo diretamente termina com exceção. Ele **não** é chamado
  pelos alvos normais do Makefile nem pelas suítes do logger novo.

Para o componente genérico e reutilizável, com Pretty Print de JSON/JSONL e
HTML para notebooks, veja **[logger/README.md](../logger/README.md)**.

O conteúdo de `logger.py` é mantido apenas como referência histórica.
