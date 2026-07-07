# Regras permanentes deste repositorio (secpro)

Este repositorio guarda geometrias de secoes transversais estruturais (lajes/almas/pecas)
e os scripts de conversao/validacao entre DWG, DXF e JSON. E o ponto de partida para uso
posterior em MIDAS/VPRO/outros scripts - mas este repo NAO edita arquivos MIDAS.

## Regras de geracao de DXF/DWG

- Nunca escrever DXF final manualmente por concatenacao de strings ou template de texto.
  Toda geracao/edicao de DXF/DWG passa pelo LibreDWG (`dwgread`, `dwg2dxf`, `dxf2dwg`,
  `dxfwrite`, `dwgadd`), via `src/section_pipeline/libredwg.py` ou pelos scripts em `scripts/`.
- `ezdxf` pode ser usado para LEITURA e validacao auxiliar (contar entidades, bounding box,
  checar `$INSUNITS`), mas nao deve ser o escritor principal do DXF final destinado ao VPRO.
  Se alguma etapa gerar pontos/geometria nova, o arquivo final deve passar por round-trip
  do LibreDWG (`dxf2dwg` -> `dwgread`) antes de ser considerado valido.
- Antes de substituir um DXF existente em `section/DXF/`, validar com `dxf2dwg` (abre sem
  erro) e depois `dwgread -O JSON` (JSON resultante parseia). So sobrescrever com `--force`
  explicito, e preferencialmente depois de gerar relatorio comparando antes/depois.
- O VPRO so aceita DXF - nunca considerar um JSON ou script Python como substituto do DXF
  para esse fluxo.

## Unidades e escala

- Preservar unidades em metros (`$INSUNITS` = 6 nos DXF desta repo). Nao aplicar fator de
  escala (ex.: x0.01, x1000) sem instrucao explicita do usuario.
- Se uma secao tiver bounding box muito menor que o esperado (ex.: maior dimensao < 0.05 m
  quando deveria estar na casa do metro), tratar como suspeita de erro de unidade/escala,
  nao aplicar correcao automatica silenciosa.

## Arquivos temporarios e persistencia

- Nao deixar arquivos uteis (scripts, DXF, DWG, JSON, logs, relatorios) apenas em `/tmp`.
  Tudo que for util deve ser copiado para dentro desta repo (`section/`, `scripts/`,
  `src/section_pipeline/`).
- Nao tratar arquivos temporarios como unica fonte de verdade. A fonte de verdade e o que
  esta versionado na repo.
- Toda conversao (DWG->DXF, DWG->JSON, DXF->DWG) deve gerar um relatorio correspondente em
  `section/reports/` (por arquivo processado, mais um resumo agregado quando aplicavel).

## Escopo

- Nao alterar arquivos do projeto MIDAS Civil (outro repositorio) a partir daqui, salvo
  instrucao explicita do usuario nesta conversa.
- Este repo e sobre secoes transversais: geometria 2D, conversao e validacao. Nao adicionar
  logica de analise estrutural, calculo ou integracao direta com MIDAS/VPRO aqui.
