# Relatorio VPRO-safe ordered - LA25

Fonte primaria: `section/json/LA25.json` (LibreDWG `dwgread -O JSON`)
Saida DXF: `outputs/dxf/LA25_vpro_safe_ordered.dxf` (copia canonica em `section/DXF/LA25_vpro_safe_ordered.dxf`)
Formato: DXF R12/AC1009, 1 POLYLINE 2D fechada (VERTEX+SEQEND), $INSUNITS=6

## Geometria e caminhada

- Vertices originais da LWPOLYLINE: 39 (bulges nao-zero: 9)
- Vertices apos discretizacao dos arcos NA ORDEM da entidade: 1030
- Vertices na polilinha final: 1030
- Arestas no grafo da caminhada: 1030
- Loops fechados encontrados no grafo: 1 (graus dos vertices: {2: 1030})
- Area orientada: -0.181811 m^2 (|area| = 0.181811 m^2)
- Sentido: horario (CW)
- Ponto inicial (superior esquerdo, banda y_tol=2.50e-04 m): (-0.600072, 0.250018)
- Maior segmento consecutivo: 1.200071 m (indice 0; aresta real da borda: True)
- Bounding box local: x=[-0.6250, 0.6250] y=[0.0000, 0.2502]

## Validacoes topologicas (grafo de arestas)

- [OK] exatamente 1 loop global fechado, todo vertice com grau 2
- [OK] caminhada continua: todo segmento vi->vi+1 e aresta original
- [OK] sem self-intersection transversal
- [OK] canal/gap dos alveolos preservado: folga minima 1.000 mm entre vertices nao adjacentes (indices 9 e 211)
- [OK] alveolos NAO fechados como loops independentes (fazem parte do unico ciclo global, ligados pelos canais)
- [OK] primeiro ponto na face superior, metade esquerda
- [OK] sem duplicatas consecutivas / segmentos nulos
  - OK - sem pontos consecutivos coincidentes
  - OK - sem segmentos de comprimento zero
  - shapely LinearRing.is_simple = True
  - shapely Polygon.is_valid = True
  - shapely Polygon.area = 0.181811 m^2

## Estrutura do DXF final (ezdxf, leitura auxiliar)

- [OK] unica entidade POLYLINE fechada; entidades: {'POLYLINE': 1}; CIRCLE/ARC/LWPOLYLINE proibidas ausentes
- Versao: AC1009 (AC1009 = R12)

## Round-trip LibreDWG (dxf2dwg + dwgread -O JSON)

- [OK] round-trip com 1030 vertices (esperado 1030: OK)
  - dwgread -O JSON reportou 'ERROR: iconv' (limitacao conhecida do LibreDWG para JSON de origem R12 - ver nota da funcao); comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o section/reports/LA25_vpro_safe_ordered_roundtrip.json section/reports/LA25_vpro_safe_ordered_roundtrip.dwg
veja log em section/reports/LA25_vpro_safe_ordered_roundtrip.dwgread.log
  - jq empty / json.load: OK - validado com jq
  - round-trip: OK - sem pontos consecutivos coincidentes
  - round-trip: OK - sem segmentos de comprimento zero

## Saidas

- DXF: `outputs/dxf/LA25_vpro_safe_ordered.dxf` e `section/DXF/LA25_vpro_safe_ordered.dxf`
- JSON ordenado: `outputs/LA25_outer_ordered.json`
- Previews: `outputs/previews/LA25_order_check.png`, `outputs/previews/LA25_order_check.svg`

**Resultado: PASSOU - estrutura validada; importar no VPRO para validacao final manual**
