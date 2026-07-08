# Relatorio - LA25_vpro_slots_r12_20gon_2mm.dxf

Fonte: `section/json/LA25.json`
Saida: `section/DXF/LA25_vpro_slots_r12_20gon_2mm.dxf`
slot_width: 0.002 m (2mm)
Finalidade: candidato simplificado (sem circulo/bulge) para importar no VPRO.

- Numero de pontos (apos limpeza de duplicatas): 134

## Validacao geometrica basica (local)

  - OK - sem pontos consecutivos coincidentes
  - OK - sem segmentos de comprimento zero

## Leitura estrutural com ezdxf

- Versao DXF: AC1009
- Entidades: {'POLYLINE': 1}
- POLYLINE: 1 (esperado 1)
- Fechada: [True]
- Bounding box: (-0.62504023783913, 0.0, 0.62504023783913, 0.2502175179652113)

## Round-trip LibreDWG (dxf2dwg + dwgread -O JSON + jq empty)

- Comandos executados: ['dxf2dwg -y -o section/reports/LA25_vpro_slots_r12_20gon_2mm_roundtrip.dwg section/DXF/LA25_vpro_slots_r12_20gon_2mm.dxf', 'dwgread -O JSON -o section/reports/LA25_vpro_slots_r12_20gon_2mm_roundtrip.json section/reports/LA25_vpro_slots_r12_20gon_2mm_roundtrip.dwg', 'jq empty section/reports/LA25_vpro_slots_r12_20gon_2mm_roundtrip.json']
- Entidades no round-trip: {'BLOCK': 2, 'ENDBLK': 2, 'POLYLINE_2D': 1, 'SEQEND': 1, 'VERTEX_2D': 134}
- POLYLINE/POLYLINE_2D no round-trip: 1 (esperado 1)
- Fechada (round-trip): [True]
- SEQEND: 1, VERTEX: 134
  - dwgread -O JSON reportou 'ERROR: iconv' (limitacao conhecida do LibreDWG para JSON de origem R12, ver process_vpro_dxf.roundtrip_validate_r12): comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o section/reports/LA25_vpro_slots_r12_20gon_2mm_roundtrip.json section/reports/LA25_vpro_slots_r12_20gon_2mm_roundtrip.dwg
veja log em section/reports/LA25_vpro_slots_r12_20gon_2mm_roundtrip.dwgread.log
  - jq empty / json.load: OK - validado com jq

## Shapely (poligono simples, anel unico)

- Valido (is_valid): True
- Simples / sem auto-intersecao (is_simple): True
- Area: 0.146954 m^2
- Centroide: (8.516174043864258e-05, 0.12347015969352917)

## Perda de area causada pelas fendas (comparado a LA25_region_r12_20gon.dxf)

- Area region (contorno - 5 furos 20-gon, sem fendas): 0.147130 m^2
- Area 2mm (contorno com fendas conectando os furos): 0.146954 m^2
- Perda de area por causa das fendas: 0.000176 m^2 (0.1197%)

Preview gerado em `section/preview/LA25_vpro_slots_r12_20gon_2mm.png`.

**Resultado: estrutura OK - VPRO legacy candidate (NAO declarar VPRO-safe; validar importando no VPRO antes de confiar neste arquivo)**
