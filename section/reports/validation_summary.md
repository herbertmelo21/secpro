# Relatorio de validacao de secoes

## LA25.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): OK - dxf2dwg + dwgread -O JSON OK, JSON valido
- Entidades: {'LINE': 1, 'LWPOLYLINE': 1}
- LWPOLYLINE: 1
- CIRCLE: False, ARC: False, LINE: True
- $INSUNITS: 4 (6 = metros)
- Bounding box: x=[3725.4361, 3726.6862] y=[1753.6819, 1753.9321] (largura=1.2501 m, altura=0.2502 m)
- AVISO: \$INSUNITS diferente de 6 (metros) - conferir unidade do desenho.
  - ERRO: pontos consecutivos coincidentes nos indices [1, 6, 11, 16]
  - ERRO: segmentos de comprimento zero nos indices [1, 6, 11, 16]

**Resultado: FALHOU**

## LA25_region_r12_20gon.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): FALHOU - round-trip LibreDWG falhou: comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o /tmp/section_pipeline_validate_18n8cunl/LA25_region_r12_20gon.json /tmp/section_pipeline_validate_18n8cunl/LA25_region_r12_20gon.dwg
veja log em section/reports/LA25_region_r12_20gon.dwgread.log
- Entidades: {'POLYLINE': 6}
- LWPOLYLINE: 0
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)

**Resultado: FALHOU**

## LA25_vpro.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): FALHOU - round-trip LibreDWG falhou: comando reportou erro na saida: /usr/local/bin/dxf2dwg -y -o /tmp/section_pipeline_validate_ff76qdso/LA25_vpro.dwg section/DXF/LA25_vpro.dxf
veja log em section/reports/LA25_vpro.dxf2dwg.log
- Entidades: {'LWPOLYLINE': 1}
- LWPOLYLINE: 1
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)
- Bounding box: x=[-0.6250, 0.6250] y=[0.0000, 0.2502] (largura=1.2501 m, altura=0.2502 m)
  - OK - sem pontos consecutivos coincidentes
  - OK - sem segmentos de comprimento zero

**Resultado: FALHOU**

## LA25_vpro_r12_lines_lowres.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): FALHOU - round-trip LibreDWG falhou: comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o /tmp/section_pipeline_validate_poevzu85/LA25_vpro_r12_lines_lowres.json /tmp/section_pipeline_validate_poevzu85/LA25_vpro_r12_lines_lowres.dwg
veja log em section/reports/LA25_vpro_r12_lines_lowres.dwgread.log
- Entidades: {'LINE': 230}
- LWPOLYLINE: 0
- CIRCLE: False, ARC: False, LINE: True
- $INSUNITS: 6 (6 = metros)

**Resultado: FALHOU**

## LA25_vpro_r12_polyline.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): FALHOU - round-trip LibreDWG falhou: comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o /tmp/section_pipeline_validate_tbudb2us/LA25_vpro_r12_polyline.json /tmp/section_pipeline_validate_tbudb2us/LA25_vpro_r12_polyline.dwg
veja log em section/reports/LA25_vpro_r12_polyline.dwgread.log
- Entidades: {'POLYLINE': 1}
- LWPOLYLINE: 0
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)

**Resultado: FALHOU**

## LA25_vpro_r12_polyline_lowres.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): FALHOU - round-trip LibreDWG falhou: comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o /tmp/section_pipeline_validate_hx66srku/LA25_vpro_r12_polyline_lowres.json /tmp/section_pipeline_validate_hx66srku/LA25_vpro_r12_polyline_lowres.dwg
veja log em section/reports/LA25_vpro_r12_polyline_lowres.dwgread.log
- Entidades: {'POLYLINE': 1}
- LWPOLYLINE: 0
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)

**Resultado: FALHOU**

## LA25_vpro_safe_ordered.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): FALHOU - round-trip LibreDWG falhou: comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o /tmp/section_pipeline_validate_qsqiyz95/LA25_vpro_safe_ordered.json /tmp/section_pipeline_validate_qsqiyz95/LA25_vpro_safe_ordered.dwg
veja log em section/reports/LA25_vpro_safe_ordered.dwgread.log
- Entidades: {'POLYLINE': 1}
- LWPOLYLINE: 0
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)

**Resultado: FALHOU**

## LA25_vpro_safe_simplified.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): FALHOU - round-trip LibreDWG falhou: comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o /tmp/section_pipeline_validate_sfsyee0w/LA25_vpro_safe_simplified.json /tmp/section_pipeline_validate_sfsyee0w/LA25_vpro_safe_simplified.dwg
veja log em section/reports/LA25_vpro_safe_simplified.dwgread.log
- Entidades: {'POLYLINE': 1}
- LWPOLYLINE: 0
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)

**Resultado: FALHOU**

## LA25_vpro_simplified_160.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): FALHOU - round-trip LibreDWG falhou: comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o /tmp/section_pipeline_validate_4ggcob3w/LA25_vpro_simplified_160.json /tmp/section_pipeline_validate_4ggcob3w/LA25_vpro_simplified_160.dwg
veja log em section/reports/LA25_vpro_simplified_160.dwgread.log
- Entidades: {'POLYLINE': 1}
- LWPOLYLINE: 0
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)

**Resultado: FALHOU**

## LA25_vpro_slots_r12_20gon_2mm.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): FALHOU - round-trip LibreDWG falhou: comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o /tmp/section_pipeline_validate_ay9rpvn5/LA25_vpro_slots_r12_20gon_2mm.json /tmp/section_pipeline_validate_ay9rpvn5/LA25_vpro_slots_r12_20gon_2mm.dwg
veja log em section/reports/LA25_vpro_slots_r12_20gon_2mm.dwgread.log
- Entidades: {'POLYLINE': 1}
- LWPOLYLINE: 0
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)

**Resultado: FALHOU**

## LA25_vpro_slots_r12_20gon_5mm.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): FALHOU - round-trip LibreDWG falhou: comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o /tmp/section_pipeline_validate_zsj_kuh2/LA25_vpro_slots_r12_20gon_5mm.json /tmp/section_pipeline_validate_zsj_kuh2/LA25_vpro_slots_r12_20gon_5mm.dwg
veja log em section/reports/LA25_vpro_slots_r12_20gon_5mm.dwgread.log
- Entidades: {'POLYLINE': 1}
- LWPOLYLINE: 0
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)

**Resultado: FALHOU**

## LA25_vpro_slots_r12_20gon_5mm_bare.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): FALHOU - round-trip LibreDWG falhou: comando reportou erro na saida: /usr/local/bin/dxf2dwg -y -o /tmp/section_pipeline_validate_pcsq8xp6/LA25_vpro_slots_r12_20gon_5mm_bare.dwg section/DXF/LA25_vpro_slots_r12_20gon_5mm_bare.dxf
veja log em section/reports/LA25_vpro_slots_r12_20gon_5mm_bare.dxf2dwg.log
- Entidades: {'POLYLINE': 1}
- LWPOLYLINE: 0
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)

**Resultado: FALHOU**

## coordenada_la26.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): OK - dxf2dwg + dwgread -O JSON OK, JSON valido
- Entidades: {'LWPOLYLINE': 1}
- LWPOLYLINE: 1
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)
- Bounding box: x=[-0.6250, 0.6250] y=[0.0000, 0.2650] (largura=1.2500 m, altura=0.2650 m)
  - OK - sem pontos consecutivos coincidentes
  - OK - sem segmentos de comprimento zero

### Checagens especificas LA26
  - OK - sem pontos consecutivos coincidentes
  - OK - sem segmentos de comprimento zero
  - OK - largura 1.2500 m dentro da tolerancia de 1.25 m
  - OK - altura 0.2650 m dentro da tolerancia de 0.265 m
  - OK - sem diagonais grandes conectando alveolos
  - AVISO: 6 recortes/alveolos detectados, esperado 5 (heuristica de contagem, revisar visualmente se divergente)

**Resultado: PASSOU**

