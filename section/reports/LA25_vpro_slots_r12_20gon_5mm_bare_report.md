# Relatorio - LA25_vpro_slots_r12_20gon_5mm_bare

Entrada: `section/DXF/LA25_vpro_slots_r12_20gon_5mm.dxf`
Saida: `section/DXF/LA25_vpro_slots_r12_20gon_5mm_bare.dxf`

## Geometria

- Numero de vertices original: 134
- Numero de vertices final (apos limpeza tol=1e-12): 134
- Bounding box: (-0.62504023783913, 0.0, 0.62504023783913, 0.2502175179652113)
- Largura: 1.250080 m
- Altura: 0.250218 m

## Presenca de secoes/entidades proibidas (validacao textual)

- Contagem de entidades/secoes no arquivo: {'SECTION': 2, 'ENDSEC': 2, 'POLYLINE': 1, 'VERTEX': 134, 'SEQEND': 1, 'EOF': 1}
- TABLES presente: False
- BLOCKS presente: False
- OBJECTS presente: False
- CLASSES presente: False
- LWPOLYLINE presente: False
- LINE presente: False
- ARC presente: False
- CIRCLE presente: False
- SPLINE presente: False
  - validacao textual OK (POLYLINE unica, sem TABLES/BLOCKS/OBJECTS/CLASSES/AcDb/entidades proibidas)

## Validacao geometrica basica (sem pontos duplicados / segmentos nulos)

  - OK - sem pontos consecutivos coincidentes
  - OK - sem segmentos de comprimento zero

## Resultado ezdxf

- Versao DXF: AC1009 (esperado AC1009)
- Entidades: {'POLYLINE': 1}
- POLYLINE: 1 (esperado 1)
- Fechada: [True]
- Bounding box (ezdxf): (-0.62504023783913, 0.0, 0.62504023783913, 0.2502175179652113)

## Resultado LibreDWG (dxf2dwg + dwgread -O JSON + jq empty)

- Comandos executados: ['dxf2dwg -y -o section/reports/LA25_vpro_slots_r12_20gon_5mm_bare_roundtrip.dwg section/DXF/LA25_vpro_slots_r12_20gon_5mm_bare.dxf', 'dwgread -O JSON -o section/reports/LA25_vpro_slots_r12_20gon_5mm_bare_roundtrip.json section/reports/LA25_vpro_slots_r12_20gon_5mm_bare_roundtrip.dwg', 'jq empty section/reports/LA25_vpro_slots_r12_20gon_5mm_bare_roundtrip.json']
- Entidades no round-trip: {'POLYLINE_2D': 1, 'VERTEX_2D': 134, 'SEQEND': 1}
- POLYLINE/POLYLINE_2D no round-trip: 1 (esperado 1)
- Fechada (round-trip): [True]
- SEQEND: 1, VERTEX: 134
- Bounding box (round-trip): (-0.62504023783913, 0.0, 0.62504023783913, 0.25021751796521)
  - dxf2dwg AVISO (conhecido, nao fatal): 'HEADER.BLOCK_CONTROL_OBJECT missing' - esperado para um DXF R12 sem secao BLOCKS/TABLES (pedido explicitamente neste perfil bare); rc=0 e DWG gerado normalmente - ver section/reports/LA25_vpro_slots_r12_20gon_5mm_bare.dxf2dwg.log
  - jq empty / json.load: OK - validado com jq
  - round-trip: OK - sem pontos consecutivos coincidentes
  - round-trip: OK - sem segmentos de comprimento zero

## Tamanho do arquivo

- Antes (entrada, LA25_vpro_slots_r12_20gon_5mm.dxf): 16789 bytes
- Depois (saida, LA25_vpro_slots_r12_20gon_5mm_bare.dxf): 8403 bytes
- Reducao: 8386 bytes (49.9%)

Preview gerado em `section/preview/LA25_vpro_slots_r12_20gon_5mm_bare.png`.

**Resultado: estrutura OK - bare R12 single-polyline candidate (NAO declarar VPRO-safe; validar importando no VPRO antes de confiar neste arquivo)**
