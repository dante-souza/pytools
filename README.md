# pytools — ferramentas Python reutilizáveis

Repositório para pequenos componentes Python portáteis, testáveis e independentes entre si. Cada ferramenta mantém documentação, exemplos, testes e um Makefile próprios.

## Ferramentas

| Ferramenta | Descrição | Documentação |
| --- | --- | --- |
| **[logger](logger/)** | Logging humano, JSON/JSONL Pretty Print, cores ANSI no terminal, HTML colorido no Jupyter e integração em outras aplicações sem dependências de runtime | **[README do logger](logger/README.md)** |

## Executar pela raiz do repositório

É necessário Python 3.10+ e GNU Make. O logger usa somente a biblioteca padrão em runtime.

```powershell
make help
make doctor
make test
make check
make logger-demo
make logger-pretty FILE=examples/events.jsonl COLOR=always
make logger-setup-notebook
make logger-notebook
```

Também é possível executar os alvos diretamente no diretório `logger/`, onde há outro Makefile com a interface completa.

## Legado e histórico

O logger original que serviu de ponto de partida está preservado sem alterações
em **[legacy/logger.py](legacy/logger.py)**. Confira a
[documentação da pasta legacy](legacy/README.md), incluindo o checksum do arquivo
original e a observação sobre a demonstração intencionalmente falha.

## Portabilidade

Para incorporar apenas o motor de logging/coloração a outra aplicação, copie [`logger/logger_general.py`](logger/logger_general.py) e importe as funções/classes desejadas. Não é necessário instalar este repositório inteiro. Consulte a [documentação de integração e códigos ANSI](logger/README.md) e a [arquitetura](logger/docs/ARQUITETURA.md).

## Licença

Consulte [LICENSE](LICENSE) (GNU AGPL-3.0).
