# Resumo - variantes 20-gon da LA25

## Qual arquivo usar para o que

- **CAD / REGION / SUBTRACT / MASSPROP**: `section/DXF/LA25_region_r12_20gon.dxf` (6 POLYLINE fechadas independentes: 1 contorno externo CCW + 5 furos 20-gon CW).
- **Teste de importacao no VPRO**: `section/DXF/LA25_vpro_slots_r12_20gon_5mm.dxf` e `section/DXF/LA25_vpro_slots_r12_20gon_2mm.dxf` (1 unica POLYLINE fechada, furos conectados a face inferior por fendas finas).

## Erro da aproximacao 20-gon vs furos circulares ideais (diametro 0.196 m)

- Erro relativo de area: 1.7026%
- Erro relativo de Ix: 0.9662%
- Erro relativo de Iy: 1.5266%

- Area da secao (region, sem fendas): 0.147130 m^2
- Area da secao (2mm, com fendas): 0.146954 m^2 (134 pontos) - estrutura OK
- Area da secao (5mm, com fendas): 0.146530 m^2 (134 pontos) - estrutura OK

## Recomendacao de ordem de teste no VPRO

1. `LA25_region_r12_20gon.dxf` no AutoCAD primeiro (REGION+SUBTRACT+MASSPROP) - confirma que a geometria 20-gon esta correta antes de mexer com o VPRO.
2. `LA25_vpro_slots_r12_20gon_5mm.dxf` no VPRO - fenda mais larga, maior chance de o importador aceitar sem problema numerico.
3. `LA25_vpro_slots_r12_20gon_2mm.dxf` no VPRO - fenda mais estreita (mais fiel ao desenho original), testar depois de confirmar que a 5mm importa bem.

Ver `section/reports/LA25_manual_test_20gon.md` para o passo a passo detalhado.

**Resultado geral: region OK, slots 2mm OK, slots 5mm OK**
