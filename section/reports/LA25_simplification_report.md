# Relatorio de simplificacao VPRO-safe - LA25

Fonte primaria: `section/json/LA25.json`; referencia densa: 1030 pontos (100 seg/semicirculo). Metodo: rediscretizacao dos arcos dos alveolos NA ORDEM da entidade com compensacao de raio (area do setor preservada), ancoras (cantos/canais/extremos de arco) intocadas; sem ordenacao global por angulo.

## Reducao de pontos

- Pontos originais: 1030
- Pontos simplificados: 190
- Reducao: 81.6%
- circle_points usado: 32 (pedido: 32; tentativas: [(32, 190)])

## Propriedades seccionais (originais vs simplificadas)

| Propriedade | Original | Simplificada | Erro rel. | Limite |
|---|---|---|---|---|
| Area A (m^2) | 0.18181066 | 0.18179209 | 0.0102% | 0.10% |
| Ix (m^4) | 1.367915e-03 | 1.367924e-03 | 0.0007% | 0.20% |
| Iy (m^4) | 2.331066e-02 | 2.330871e-02 | 0.0084% | 0.20% |
| Ixy (m^4) | 3.767466e-06 | 3.767272e-06 | (informativo) | - |
| Cx (m) | -0.000002 | -0.000002 | dif abs 3.13e-09 m | - |
| Cy (m) | 0.123800 | 0.123789 | dif abs 1.11e-05 m | - |

- [OK] erro de area dentro do limite
- [OK] erro de Ix dentro do limite
- [OK] erro de Iy dentro do limite

## Topologia e caminhada (mesma bateria do export denso)

- Maior salto entre pontos consecutivos: 1.200071 m (indice 0; aresta real da borda: True)
- [OK] 1 loop global fechado (graus: {2: 190})
- [OK] caminhada continua sem cordas
- [OK] sem self-intersection
- [OK] canal dos alveolos preservado: folga minima 1.000 mm (indices 9 e 43)
- [OK] inicio no canto superior esquerdo: (-0.600072, 0.250018)
- [OK] sentido: horario (CW)
- [OK] sem duplicatas/segmentos nulos
- [OK] DXF R12 com 1 POLYLINE fechada: {'POLYLINE': 1}
- [OK] round-trip LibreDWG: 190 vertices
  - dwgread -O JSON reportou 'ERROR: iconv' (limitacao conhecida do LibreDWG para JSON de origem R12 - ver nota da funcao); comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o section/reports/LA25_vpro_safe_simplified_roundtrip.json section/reports/LA25_vpro_safe_simplified_roundtrip.dwg
veja log em section/reports/LA25_vpro_safe_simplified_roundtrip.dwgread.log
  - jq empty / json.load: OK - validado com jq
  - round-trip: OK - sem pontos consecutivos coincidentes
  - round-trip: OK - sem segmentos de comprimento zero

## Saidas

- DXF: `outputs/dxf/LA25_vpro_safe_simplified.dxf` (copia canonica `section/DXF/LA25_vpro_safe_simplified.dxf`)
- JSON ordenado: `outputs/LA25_outer_ordered_simplified.json`
- CSV: `section/reports/LA25_simplified_coords.csv`
- PNG: `section/reports/LA25_simplified_vpro_safe.png`

**Resultado: PASSOU - gerar o AHK a partir do JSON simplificado e validar import no VPRO**
