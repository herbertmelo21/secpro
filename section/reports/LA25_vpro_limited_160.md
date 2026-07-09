# Relatorio VPro Limited - LA25 (160 pontos max)

Limite rigido: 160 pontos. Circle_points escadado automaticamente.
Fonte: `section/json/LA25.json` (LibreDWG JSON).
Saida DXF: `outputs/dxf/LA25_vpro_simplified_160.dxf` (copia canonica `section/DXF/LA25_vpro_simplified_160.dxf`)
Formato: DXF R12, 1 POLYLINE 2D fechada, $INSUNITS=6

## Reducao de pontos

- Pontos originais (100 seg/semicirculo): 1030
- Pontos limitados: 150
- Reducao: 85.4%
- Circle_points usado: 24

## Propriedades seccionais (originais vs limitadas)

| Propriedade | Original | Limitada | Erro rel. | Limite |
|---|---|---|---|---|
| Area A (m^2) | 0.18181066 | 0.18179209 | 0.0102% | 0.10% |
| Ix (m^4) | 1.367915e-03 | 1.368027e-03 | 0.0082% | 0.20% |
| Iy (m^4) | 2.331066e-02 | 2.330859e-02 | 0.0089% | 0.20% |

- [OK] erro de area dentro do limite
- [OK] erro de Ix dentro do limite
- [OK] erro de Iy dentro do limite

## Topologia

- [OK] 1 loop global (graus: {2: 150})
- [OK] caminhada continua
- [OK] sem self-intersection
- [OK] canal preservado: folga 1.000 mm
- [OK] inicio no canto superior esquerdo
- [OK] sem duplicatas/segmentos nulos
- [OK] DXF com 1 POLYLINE fechada
- [OK] round-trip LibreDWG: 150 vertices

## Saidas

- DXF: `outputs/dxf/LA25_vpro_simplified_160.dxf`
- JSON: `outputs/LA25_outer_ordered_160.json`
- PNG: `section/reports/LA25_vpro_simplified_160.png`
- CSV: `section/reports/LA25_vpro_simplified_160.csv`
- AHK: `section/ahk/LA25.ahk`

**Resultado: PASSOU**
