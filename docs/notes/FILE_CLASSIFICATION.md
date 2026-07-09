# Classificação de arquivos — auditoria 2026-07-09

Categorias:

- **KEEP_SOURCE** — fonte de verdade ou código; nunca remover.
- **KEEP_FINAL_ARTIFACT** — artefato final do fluxo operacional atual.
- **KEEP_DOC** — documentação/relatórios/imagens documentais.
- **GENERATED_IGNORE** — regenerável; ignorar para NOVOS arquivos.
- **ARCHIVE_EXPERIMENT** — histórico de investigação; manter versionado
  (o repo é um laboratório — o histórico É o dado).
- **DELETE_CANDIDATE** — candidato a remoção FUTURA, com aprovação.

**Nada foi deletado nesta auditoria.** Itens marcados como
GENERATED_IGNORE que já estão rastreados CONTINUAM rastreados (o
`.gitignore` só vale para arquivos novos); a remoção do índice
(`git rm --cached`, sem apagar do disco) fica para uma rodada futura,
depois da validação do AHK de 150 pontos no VPRO.

## Tabela

| Caminho | Categoria | Justificativa |
|---|---|---|
| `section/DWG/*.dwg` | KEEP_SOURCE | Entrada canônica da geometria (questionário B.1/D.1) |
| `section/json/LA25.json`, `coordenada_la26.json` | KEEP_SOURCE | `dwgread -O JSON` da fonte; base de todo o pipeline |
| `scripts/*.py`, `src/section_pipeline/*` | KEEP_SOURCE | Código do pipeline |
| `scripts/run_vpro_ahk_from_wsl.sh`, `scripts/vpro_control_discovery.ahk` | KEEP_SOURCE | Ferramentas de execução/descoberta no Windows |
| `pyproject.toml`, `.gitignore`, `.claude/`, `.vscode/`, `CLAUDE.md` | KEEP_SOURCE | Configuração do projeto |
| `section/ahk/LA25.ahk` | KEEP_FINAL_ARTIFACT | **AHK operacional (150 pts)** — regeneração byte-idêntica comprovada a partir do JSON |
| `section/json/LA25_outer_ordered_160.json` | KEEP_FINAL_ARTIFACT | Fonte direta do AHK final (cópia canônica versionada; original em `outputs/`) |
| `section/DXF/LA25_vpro_simplified_160.dxf` | KEEP_FINAL_ARTIFACT | DXF da geometria operacional (rota DXF, se um dia for usada) |
| `README.md`, `docs/notes/*.md` | KEEP_DOC | Documentação, decisões, achados black-box, requisitos |
| `section/reports/*.md` | KEEP_DOC | Relatórios de validação (o `.md` é o que fica; logs não) |
| `section/reports/*.png`, `section/preview/*.png` | KEEP_DOC | Previews documentais citados nos relatórios |
| `scripts/README_*.md` | KEEP_DOC | Instruções das ferramentas AHK |
| `outputs/**` (12 arquivos) | GENERATED_IGNORE | Scratch de build; tudo regenerável pelos scripts; a exceção útil (JSON 160) já tem cópia canônica em `section/json/` |
| `*.log` (ex.: `outputs/autohotkey/*.log`) | GENERATED_IGNORE | Flight recorder local; achados transcritos em `BLACKBOX_FINDINGS.md` (já era ignorado) |
| `audit_pack/` | GENERATED_IGNORE | Pacote de auditoria externa; o questionário respondido foi versionado em `docs/notes/` |
| Novos `*_roundtrip.*` | GENERATED_IGNORE | Subproduto de validação; o relatório `.md` é o registro |
| `section/DXF/LA25_vpro*.dxf` (variantes r12/slots/region/20gon) | ARCHIVE_EXPERIMENT | Experimentos da rota DXF (hipótese 1.4 do BLACKBOX); manter — são o histórico da investigação |
| `section/DXF/LA25_vpro_safe_ordered.dxf`, `LA25_vpro_safe_simplified.dxf` | ARCHIVE_EXPERIMENT | Variantes densa (1030) e 190 pts — geometricamente válidas, não operacionais (teto ~180) |
| `section/DXF/*.BAK`, `*_bare.DWG` | ARCHIVE_EXPERIMENT | Dado histórico pré-existente (DECISOES §11) |
| `section/reports/*_roundtrip.{dwg,json}` (21 rastreados) | ARCHIVE_EXPERIMENT → DELETE_CANDIDATE | Regeneráveis pelos scripts; remover do índice numa rodada futura |
| `scripts/generate_vpro_ahk_from_libredwg.py` | ARCHIVE_EXPERIMENT | Gerador AHK antigo (precedente que definiu as convenções); substituído por `export_autohotkey.py` |
| `scripts/generate_la25_20gon_variants.py`, `write_bare_r12_polyline.py` | ARCHIVE_EXPERIMENT | Geradores dos experimentos 20gon/bare |
| `outputs/**` rastreados (11 arquivos) | DELETE_CANDIDATE | `git rm --cached` (mantém no disco) após validação do AHK 150 no VPRO |

## Arquivo histórico notável (recuperável, não presente no disco)

O `section/ahk/LA25.ahk` **manual/histórico** (324 linhas, constantes de
tela originais) foi sobrescrito pelo gerado em `6a802fe` (a pedido).
Recuperação a qualquer momento:

```bash
git show 6a802fe~1:section/ahk/LA25.ahk > section/ahk/LA25_manual_historico.ahk
```

## Política de Git sugerida (repo pessoal de caracterização)

Respostas às perguntas em aberto do questionário (G.2, G.3, H.1):

- **Branches (G.2):** existe apenas `main` (+ `origin/main`) — nada a
  deletar. Para um laboratório solo, seguir em `main` com commits pequenos
  é suficiente. Se quiser isolar um experimento arriscado, criar
  `exp/<nome>` e fazer merge (ou abandonar SEM deletar) — o branch
  abandonado vira registro do experimento.
- **Histórico (G.3):** manter **indefinidamente**. Em characterization
  testing o histórico É o caderno de laboratório (ex.: os commits de hoje
  documentam Tab→setas e o teto de ~180). O repo tem poucos MB.
- **Marcos:** usar tags anotadas para estados validados no VPRO real, ex.:
  `git tag -a vpro-ok-150pts -m "150 pts preenchidos e conferidos no VPRO"`.
  Tag só DEPOIS da conferência manual (taxa de erro aceita: 0%).
- **O que versionar (H.1):** DWG fonte, código, `.md`, AHK final, DXF
  final, JSON fonte-do-AHK, previews documentais. NÃO versionar: `.log`,
  `outputs/` novo, roundtrips, `.venv/`, `audit_pack/`.
- **Temas para estudar (pedido em G.1):** characterization/golden-master
  testing; `git tag`/`git bisect` (achar em qual commit um comportamento
  mudou); `git rm --cached` vs `git rm`; lab notebook discipline
  (registrar status CONFIRMADO/HIPÓTESE como em `BLACKBOX_FINDINGS.md`).
