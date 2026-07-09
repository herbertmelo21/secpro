# Questionário para Auditoria Externa — secpro (RESPONDIDO)

Data: 2026-07-09
Respondido por: Herbert Cézar Leite Melo em 2026-07-09

> Cópia versionada do questionário respondido (original em `audit_pack/`,
> que não é versionado). Este arquivo é o **registro de requisitos** do
> projeto — as decisões de organização e documentação da auditoria de
> 2026-07-09 derivam destas respostas. Duas edições em relação ao
> original: a data de preenchimento no rodapé foi corrigida de
> "09/07/2025" para "09/07/2026" (erro de digitação; o questionário foi
> criado e respondido em 2026-07-09) e a resposta livre de I.4, de
> natureza pessoal, foi mantida apenas na cópia local.

---

## A. Objetivo real do projeto

**A.1** Qual é o propósito principal deste repositório?
- [ ] Armazenar e processar geometrias de seções transversais estruturais
- [ ] Converter arquivos DWG/DXF para um sistema específico (qual?)
- [x] Automatizar entrada de dados em um software (VPRO)
- [ ] Outro: _______________

**A.2** Quem são os usuários finais?
- [x] Engenheiros estruturais
- [ ] Técnicos de entrada de dados
- [ ] Sistema automatizado (MIDAS/VPRO)
- [ ] Outro: _______________

**A.3** Este repo será mantido depois que você sair da empresa?
- [ ] Sim, por _______________
- [x] Não
- [ ] Incerto
esse repo é só para mim, segredo de estado only
---

## B. Arquivo de entrada e saída esperada

**B.1** Qual é o arquivo de entrada primário?
- [x] `.dwg` (AutoCAD)
- [ ] `.dxf` (CAD genérico)
- [ ] `.json` (intermediário)
- [ ] Outro: _______________

**B.2** Qual é o arquivo de saída esperado?
- [ ] `.dxf` validado para importação no VPRO
- [x] `.ahk` (AutoHotkey) para automação de digitação
- [ ] `.csv` com coordenadas
- [ ] Todos os acima
- [ ] Outro: _______________

**B.3** O processo é:
- [ ] Manual (usuário roda scripts conforme necessário)
- [x] Semi-automático (script roda, usuário valida)
- [ ] Totalmente automático (sem intervenção)

---

## C. Limite máximo aceitável de pontos no VPro

**C.1** Qual é o limite rígido de pontos que o VPRO aceita?
- [x] 160 pontos (padrão atual)
- [ ] 180 pontos
- [ ] 200 pontos
- [ ] Sem limite
- [ ] Desconheço: _______________

**C.2** Por que existe esse limite?
- [ ] Performance (velocidade de renderização)
- [ ] Limitação do formato/banco de dados
- [ ] Validação de entrada
- [x] Outro: ainda não sei, to fazendo uma Black-box reverse engineering ou Debugging sistemático, depois eu decido a melhor forma de automatizar

**C.3** Se o limite for atingido, qual é a ação esperada?
- [ ] Recusar a importação (erro)
- [ ] Importar com aviso (parcialmente)
- [ ] Simplificar automaticamente
- [x] Outro: como a repo é só para mim, a intenção do git e github não é trabalhar com outros engenheiros, é fazer o haiku de agente básico antes de trinar um modelo pq não posso ter um agente enquanto faço um Debugging sistemático

---

## D. O que deve ser fonte única de verdade

**D.1** Para a geometria (coordenadas dos pontos), qual é a fonte?
- [x] Arquivo DWG original (entrada)
- [ ] JSON do LibreDWG (intermediário)
- [ ] DXF R12 validado (saída)
- [ ] Outro: _______________

**D.2** Para a automação de digitação (AHK), qual é a fonte?
- [ ] JSON ordenado (outputs/LA25_outer_ordered_160.json)
- [ ] Script Python (export_autohotkey.py)
- [ ] Arquivo .ahk gerado (section/ahk/LA25.ahk)
- [x] Outro: o que se mostrar mais eficiente, eu ainda não sei

**D.3** Se houver discrepâncias, qual prevalece?
- [x] Arquivo de entrada (.dwg/.dxf bruto)
- [ ] Relatório de validação (.md)
- [ ] Testes/checagens automáticas
- [ ] Validação manual do usuário

---

## E. Como validar geometria

**E.1** Quais são os critérios de aceitação de uma geometria simplificada?
- [x] Erro de área <= 0,5%
- [x] Erro de inércia (Ix/Iy) <= 1,0%
- [ ] Sem self-intersections
- [ ] Canal dos alvéolos preservado (folga > 1 mm)
- [ ] Topologia contínua (nenhuma corda/salto)
- [ ] Outro: _______________

**E.2** Qual é a ferramenta de verdade para validação?
- [ ] LibreDWG (round-trip dxf2dwg + dwgread)
- [ ] shapely (is_simple, is_valid)
- [x] Validação manual no VPRO
- [ ] Outro: _______________

**E.3** Se houver erro de geometria, quem decide se é aceitável?
- [x] Engenheiro estrutural
- [ ] Técnico de dados
- [ ] Sistema (rejeita automaticamente)
- [ ] Outro: _______________

---

## F. Como validar automação

**F.1** Como você valida que o AHK preencheu os pontos corretamente?
- [x] Visual no VPRO (confere linha por linha)
- [ ] Relatório gerado pelo AHK (.log)
- [ ] Exporta dados do VPRO e compara com JSON
- [ ] Testa um ponto de cada seção
- [ ] Outro: _______________

**F.2** Qual é a taxa de erro aceitável?
- [x] 0% (nenhuma célula errada)
- [ ] < 1% (máximo 1-2 erros em 150 pontos)
- [ ] < 5%
- [ ] Outro: _______________

**F.3** Se o AHK falhar no meio da automação, qual é o procedimento?
- [x] Apagar e refazer tudo
- [ ] Resumir do ponto onde parou (INICIO_EM)
- [ ] Manual input das células faltantes
- [ ] Outro: _______________

---

## G. O que pode ser descartado

**G.1** Quais arquivos/pastas podem ser deletados do repositório sem perder informação?

- [x] `output/` (entregáveis antigos)
- [ ] `section/DXF/LA25_vpro_safe.{dxf,dwg}` (artefatos polares antigos)
- [ ] `section/reports/LA25_vpro_safe_*.{csv,txt,plot}` (relatórios desatualizados)
- [ ] `scripts/*.py` que não são executados
- [ ] `scripts/generate_vpro_ahk_from_libredwg.py` (precedente histórico)
- [x] `.venv/` (regenerável)
- [x] Outro: preciso de sugestões, nunca trabalhei a fundo com github em fases de testes de caracterização, talvez o gpt possa me sugerir assuntos a estudar nas próximas semanas, mas por enquanto eu to validando pra isso fazer sentido logico neurocognitivo.

**G.2** Quais branches Git podem ser deletadas?
- [ ] Nenhuma (manter histórico completo)
- [ ] Branches que não são main/develop
- [ ] Branches mais antigas que X semanas
- [x] Outro: gpt me informe

**G.3** Quanto tempo manter histórico de Git?
- [ ] Indefinido
- [ ] 1 ano
- [ ] 3 meses
- [x] Outro: gpt me sugira

---

## H. O que precisa ficar versionado

**H.1** Quais arquivos/extensões DEVEM estar sempre no Git?

- [x] `*.dwg` (DWG originais de entrada)
- [x] `*.dxf` (DXF validados)
- [ ] `*.json` (JSON intermediários do LibreDWG)
- [x] `*.ahk` (Scripts AutoHotkey gerados)
- [x] `*.md` (Relatórios e documentação)
- [ ] `.csv` (Coordenadas exportadas)
- [ ] `*.log` (Logs de automação)
- [ ] `.env` (Variáveis de ambiente)
- [x] Outro: gpt me sugira

**H.2** Por quantas seções (secções) o repo precisa lidar?
- [ ] 1 (apenas LA25)
- [ ] 2-5
- [ ] 10+
- [x] Dinâmico (mais são adicionadas conforme necessário)

**H.3** Há dados confidenciais que precisam ser protegidos?
- [ ] Sim, qual tipo? _______________
- [x] Não, essas seções sãol tabeladas por tipo de fabricante, se eu souber lidar com geometria alveolar, eu posso lidar a medida que eu for aumentando minha bagagem de projetos estruturais

---

## I. Critérios de sucesso

**I.1** Quando você considera um "release" do repo pronto?

- [x] Quando `section/ahk/LA25.ahk` funciona sem erros no VPRO
- [ ] Quando todos os testes passam (pytest, validação)
- [ ] Quando documentação está completa
- [ ] Quando erros de geometria estão dentro dos limites
- [ ] Quando a automação consegue preencher 160+ pontos sem parar
- [ ] Outro: _______________

**I.2** Qual é a métrica de "sucesso" final?
- [ ] Redução de tempo de digitação (quanto economiza?)
- [ ] Redução de erros (quantos erros evita?)
- [x] Compatibilidade total com VPRO (100% das seções importam?)
- [ ] Outro: _______________

**I.3** Se tudo funcionar, o que é esperado que seja feito depois?

- [ ] Integração com pipeline maior (qual?)
- [x] Replicação para outras seções (aqui não posso te dar ao certo, eu posso até num futuro pegar varias tabelas de fabricantes de seções pré moldadas e fazer um importador de geometria)
- [ ] Publicação/release
- [ ] Documentação técnica externa
- [ ] Outro: _______________

---

## Observações adicionais

**I.4** Há algo que você gostaria que fosse esclarecido nesta auditoria?

Resposta pessoal do autor mantida fora do controle de versão (ver cópia
local em `audit_pack/QUESTIONS_FOR_HERBERT.md`). Síntese operacional
relevante para o projeto: o repositório é um espaço seguro e privado de
testes de automação; a comunicação com assistentes de IA funciona melhor
com questionários objetivos e registro explícito de contexto — manter
esse formato nas próximas rodadas.

---

**Data de preenchimento**: 09/07/2026

**Assinatura**: Herbert Cézar Leite Melo
