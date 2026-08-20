"""Medição de texto com as MÉTRICAS REAIS da fonte.

Por que existe: o PowerPoint é quem faz o layout do texto, não o python-pptx.
Para prometer "nada cortado, nada sobreposto" é preciso saber a altura que um
parágrafo vai ocupar ANTES de escrever. A conta antiga usava um número fixo de
caracteres por linha — cega para a fonte, e portanto errada para qualquer
modelo que não fosse o do desenvolvedor.

Aqui medimos com o arquivo TTF instalado (via Pillow): largura real de cada
palavra, quebra de linha igual à do PowerPoint, e altura a partir de ascent +
descent da própria fonte.

Uma honestidade importante: a fonte pode NÃO existir na máquina. O
PowerPoint substitui por outra e o layout muda. `resolve_font` diz quando isso
acontece (`exact=False`) para a geração AVISAR antes, em vez de o usuário
descobrir no deck pronto.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

PT_PER_INCH = 72.0
# Corpo mínimo antes de desistir de encolher: abaixo disso vira ilegível.
MIN_FONT_PT = 8.0
# Passo da redução automática de corpo.
SHRINK_STEP_PT = 0.5

# Diretórios de fontes por sistema. O deploy é Windows 11 (onde as fontes
# corporativas realmente existem); os demais ajudam em teste/dev.
FONT_DIRS = (
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
    Path.home() / ".fonts",
    Path.home() / ".local/share/fonts",
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts"),
)

# Nomes de arquivo do Windows para as fontes oferecidas no editor.
# (regular, bold, italic, bold-italic)
WINDOWS_FILES: dict[str, tuple[str, str, str, str]] = {
    "arial": ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
    "calibri": ("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf"),
    "georgia": ("georgia.ttf", "georgiab.ttf", "georgiai.ttf", "georgiaz.ttf"),
    "tahoma": ("tahoma.ttf", "tahomabd.ttf", "tahoma.ttf", "tahomabd.ttf"),
    "times new roman": ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"),
    "trebuchet ms": ("trebuc.ttf", "trebucbd.ttf", "trebucit.ttf", "trebucbi.ttf"),
    "verdana": ("verdana.ttf", "verdanab.ttf", "verdanai.ttf", "verdanaz.ttf"),
    "courier new": ("cour.ttf", "courbd.ttf", "couri.ttf", "courbi.ttf"),
}

# Último recurso: presente em praticamente toda instalação Linux/Pillow.
FALLBACKS = ("DejaVuSans.ttf", "LiberationSans-Regular.ttf", "NotoSans-Regular.ttf")


@dataclass(frozen=True)
class FontRef:
    path: str | None
    family: str
    exact: bool          # False = a máquina não tem a fonte; houve substituição


@dataclass
class TextFit:
    """Resultado de encaixar um texto numa caixa do modelo."""
    lines: list[str]
    font_size: float     # pt (pode ter sido reduzido para caber)
    height: float        # polegadas ocupadas
    overflow: bool       # não coube nem no corpo mínimo
    truncated: bool      # linhas foram cortadas


def _variant_index(bold: bool, italic: bool) -> int:
    return (1 if bold else 0) + (2 if italic else 0)


def _find_in_dirs(filename: str) -> str | None:
    alvo = filename.lower()
    for base in FONT_DIRS:
        try:
            if not base.exists():
                continue
            direto = base / filename
            if direto.exists():
                return str(direto)
            for found in base.rglob("*"):
                if found.name.lower() == alvo:
                    return str(found)
        except (OSError, PermissionError):
            continue
    return None


def _fc_match(family: str, bold: bool, italic: bool) -> tuple[str | None, bool]:
    """Consulta o fontconfig (Linux/macOS).

    Cuidado: o `fc-match` SEMPRE devolve alguma fonte — pedir "Georgia" numa
    máquina sem Georgia devolve outra família. Por isso comparamos a família
    devolvida com a pedida para saber se foi substituição.
    """
    padrao = family
    if bold:
        padrao += ":bold"
    if italic:
        padrao += ":italic"
    try:
        saida = subprocess.run(
            ["fc-match", "-f", "%{family}|%{file}", padrao],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None, False
    if "|" not in saida:
        return None, False
    familias, arquivo = saida.rsplit("|", 1)
    pedida = family.strip().lower()
    achou = any(pedida == parte.strip().lower() for parte in familias.split(","))
    return (arquivo or None), achou


@lru_cache(maxsize=64)
def resolve_font(family: str, bold: bool = False, italic: bool = False) -> FontRef:
    """Arquivo da fonte instalada — e se é mesmo a pedida."""
    nome = (family or "").strip() or "Calibri"
    chave = nome.lower()

    arquivos = WINDOWS_FILES.get(chave)
    if arquivos:
        caminho = _find_in_dirs(arquivos[_variant_index(bold, italic)])
        if caminho:
            return FontRef(caminho, nome, True)

    caminho, exato = _fc_match(nome, bold, italic)
    if caminho and exato:
        return FontRef(caminho, nome, True)

    substituto = caminho
    if not substituto:
        for alternativa in FALLBACKS:
            substituto = _find_in_dirs(alternativa)
            if substituto:
                break
    logger.info("Fonte '%s' não encontrada; medindo com substituta.", nome)
    return FontRef(substituto, nome, False)


def missing_fonts(families) -> list[str]:
    """Famílias do modelo que a máquina NÃO tem (o PowerPoint vai substituir)."""
    faltando = []
    for family in dict.fromkeys(f for f in families if f):
        if not resolve_font(family).exact:
            faltando.append(family)
    return faltando


@lru_cache(maxsize=256)
def _pil_font(path: str | None, size_pt: int):
    from PIL import ImageFont

    if not path:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(path, size_pt)
    except (OSError, ValueError):
        return ImageFont.load_default()


def _font_for(family: str, size_pt: float, bold: bool, italic: bool):
    ref = resolve_font(family, bold, italic)
    # Medimos numa escala grande e reduzimos: métrica de fonte é linear, e
    # assim o cache guarda poucos objetos em vez de um por corpo.
    return _pil_font(ref.path, 100), 100.0 / max(size_pt, 0.1)


def text_width(text: str, family: str, size_pt: float,
               bold: bool = False, italic: bool = False) -> float:
    """Largura do texto em POLEGADAS, na fonte e corpo informados."""
    if not text:
        return 0.0
    font, divisor = _font_for(family, size_pt, bold, italic)
    try:
        largura = font.getlength(text)
    except AttributeError:  # Pillow antigo
        largura = font.getsize(text)[0]
    return (largura / divisor) / PT_PER_INCH


def line_height(family: str, size_pt: float,
                bold: bool = False, italic: bool = False) -> float:
    """Altura de UMA linha em polegadas (ascent + descent da própria fonte)."""
    font, divisor = _font_for(family, size_pt, bold, italic)
    try:
        ascent, descent = font.getmetrics()
        altura = (ascent + descent) / divisor
    except (AttributeError, OSError):
        altura = size_pt * 1.2
    return altura / PT_PER_INCH


def wrap_text(text: str, width: float, family: str, size_pt: float,
              bold: bool = False, italic: bool = False) -> list[str]:
    """Quebra o texto na largura da caixa (polegadas), como o PowerPoint faz."""
    linhas: list[str] = []
    for paragrafo in (text or "").splitlines() or [""]:
        if not paragrafo.strip():
            linhas.append("")
            continue
        atual = ""
        for palavra in paragrafo.split():
            tentativa = f"{atual} {palavra}".strip()
            if atual and text_width(tentativa, family, size_pt, bold, italic) > width:
                linhas.append(atual)
                atual = palavra
            else:
                atual = tentativa
            # Palavra sozinha maior que a caixa: quebra no caractere.
            while text_width(atual, family, size_pt, bold, italic) > width and len(atual) > 1:
                corte = len(atual)
                while corte > 1 and text_width(atual[:corte], family, size_pt,
                                               bold, italic) > width:
                    corte -= 1
                linhas.append(atual[:corte])
                atual = atual[corte:]
        if atual:
            linhas.append(atual)
    return linhas or [""]


def text_height(text: str, width: float, family: str, size_pt: float,
                bold: bool = False, italic: bool = False) -> float:
    """Altura em polegadas que o texto ocupa numa caixa desta largura."""
    linhas = wrap_text(text, width, family, size_pt, bold, italic)
    return len(linhas) * line_height(family, size_pt, bold, italic)


def fit_text(
    text: str,
    width: float,
    height: float,
    family: str,
    size_pt: float,
    bold: bool = False,
    italic: bool = False,
    min_size_pt: float = MIN_FONT_PT,
    allow_shrink: bool = True,
) -> TextFit:
    """Encaixa o texto na caixa do modelo.

    Tenta no corpo original; se não couber, reduz até `min_size_pt`; se ainda
    assim não couber, corta as linhas que sobram e marca `truncated` — o
    chamador precisa avisar, não deixar o texto vazar por cima do resto.
    """
    corpo = float(size_pt)
    while True:
        linhas = wrap_text(text, width, family, corpo, bold, italic)
        altura_linha = line_height(family, corpo, bold, italic)
        total = len(linhas) * altura_linha
        if total <= height or not allow_shrink or corpo - SHRINK_STEP_PT < min_size_pt:
            break
        corpo -= SHRINK_STEP_PT

    if total <= height:
        return TextFit(linhas, corpo, total, overflow=False, truncated=False)

    cabem = max(1, int(height // altura_linha)) if altura_linha else 1
    if cabem >= len(linhas):
        return TextFit(linhas, corpo, total, overflow=True, truncated=False)

    cortadas = linhas[:cabem]
    if cortadas:
        cortadas[-1] = cortadas[-1].rstrip() + "…"
    return TextFit(cortadas, corpo, cabem * altura_linha, overflow=True, truncated=True)
