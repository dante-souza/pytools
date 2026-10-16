# pytools — interface de comandos do monorepo (GNU Make).
# Cada ferramenta mantém seu Makefile próprio. Sem dependências externas de runtime.
.DEFAULT_GOAL := help
PYTHON ?= python
COLOR ?= always
FILE ?= examples/events.jsonl
PRETTY ?= 1
KIND ?= auto
HEADINGS ?= 1

.PHONY: help doctor test check demo pretty view notebook setup-notebook setup logger-help logger-doctor logger-test logger-check logger-demo logger-pretty logger-view logger-sample logger-integration-demo logger-notebook logger-setup-notebook logger-setup logger-clean clean

help:
	@echo "=== pytools: ferramentas Python ==="
	@echo "make test                        - Testar todas as ferramentas (atualmente logger)"
	@echo "make check                       - Smoke + testes de todas as ferramentas"
	@echo "make logger-help                - Ajuda detalhada do logger"
	@echo "make logger-demo                - Demonstracao offline"
	@echo "make logger-pretty FILE=...     - Pretty Print JSON/JSONL com ANSI"
	@echo "make logger-view FILE=...       - Visualizador com parametros"
	@echo "make logger-test                - Testes automatizados do logger"
	@echo "make logger-check               - Smoke test + unittest"
	@echo "make logger-notebook            - Abrir exemplos Jupyter"
	@echo "make logger-setup-notebook      - Instalar dependencias opcionais do Jupyter"
	@echo "make logger-setup               - Instalacao editavel opcional"
	@echo "make logger-sample              - Criar saidas demonstrativas"
	@echo "make logger-integration-demo    - Exemplo de integracao em aplicativo"
	@echo "make logger-clean               - Limpar outputs gerados do logger"

# Alvos genericos: expandir em projetos novos sem mudar o uso do usuario.
doctor: logger-doctor
test: logger-test
check: logger-check
demo: logger-demo
pretty: logger-pretty
view: logger-view
notebook: logger-notebook
setup-notebook: logger-setup-notebook
setup: logger-setup
clean: logger-clean

logger-help:
	@$(MAKE) -C logger help
logger-doctor:
	@$(MAKE) -C logger doctor PYTHON="$(PYTHON)"
logger-test:
	@$(MAKE) -C logger test PYTHON="$(PYTHON)"
logger-check:
	@$(MAKE) -C logger check PYTHON="$(PYTHON)"
logger-demo:
	@$(MAKE) -C logger demo PYTHON="$(PYTHON)" COLOR="$(COLOR)"
logger-pretty:
	@$(MAKE) -C logger pretty PYTHON="$(PYTHON)" FILE="$(FILE)" COLOR="$(COLOR)" KIND="$(KIND)" HEADINGS="$(HEADINGS)"
logger-view:
	@$(MAKE) -C logger view PYTHON="$(PYTHON)" FILE="$(FILE)" COLOR="$(COLOR)" KIND="$(KIND)" PRETTY="$(PRETTY)" HEADINGS="$(HEADINGS)"
logger-sample:
	@$(MAKE) -C logger sample PYTHON="$(PYTHON)"
logger-integration-demo:
	@$(MAKE) -C logger integration-demo PYTHON="$(PYTHON)" COLOR="$(COLOR)"
logger-notebook:
	@$(MAKE) -C logger notebook PYTHON="$(PYTHON)"
logger-setup-notebook:
	@$(MAKE) -C logger setup-notebook PYTHON="$(PYTHON)"
logger-setup:
	@$(MAKE) -C logger setup PYTHON="$(PYTHON)"
logger-clean:
	@$(MAKE) -C logger clean PYTHON="$(PYTHON)"
