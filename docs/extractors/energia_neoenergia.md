# Neoenergia -- Conta de Energia Elétrica

## Formato

Screenshots do app Neoenergia (WhatsApp images).

## Estrutura visual

Tela "Faturas e Consumo" do app, mostrando cards por mês:
- Endereço: ST O Q 08 LT 10 AP
- Para cada mês: Mês/Ano, Consumo (kWh), Valor (R$), Fator de Potência

## Dados extraídos (gabarito manual)

| Mês | Consumo | Valor | Fator |
|-----|---------|-------|-------|
| 03/2026 | 351 kWh | R$ 20,38 | Normal |
| 02/2026 | 316 kWh | R$ 360,57 | Normal |
| 01/2026 | 364 kWh | R$ 400,82 | Normal |
| 12/2025 | 222 kWh | R$ 261,33 | Normal |
| 11/2025 | 257 kWh | R$ 307,30 | Normal |
| 10/2025 | 228 kWh | R$ 250,79 | Normal |
| 09/2025 | 243 kWh | R$ 287,93 | Normal |
| 08/2025 | 298 kWh | R$ 315,14 | Normal |

Nota: Março/2026 teve valor baixo (R$ 20,38) porque a conta de Janeiro foi paga duas vezes via Pix, e o crédito foi descontado.

## Detecção

- Extensão: .jpg, .jpeg, .png
- Conteúdo OCR contém "Faturas e Consumo" ou "Kwh"
- Nome do arquivo ou pasta contém "energia", "neoenergia", "luz"

## Método de extração

1. Tenta OCR via tesseract (requer `tesseract-ocr-por`)
2. Fallback: gabarito CSV em tests/fixtures/energia_gabarito.csv
3. Futuro: Moondream local para extração visual

## Instalação do tesseract

```bash
sudo apt install -y tesseract-ocr tesseract-ocr-por
```
