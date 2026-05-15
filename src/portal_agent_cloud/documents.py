from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .config import AppConfig


IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


def pdf_path(config: AppConfig, law_number: int) -> Path:
    return config.downloads_dir / f"LAW-{law_number}.pdf"


def zip_path(config: AppConfig, law_number: int) -> Path:
    return config.downloads_dir / f"LAW-{law_number}.zip"


def ensure_law_pdf(
    *,
    config: AppConfig,
    law_number: int,
    dry_run: bool,
) -> Path:
    pdf = pdf_path(config, law_number)
    if pdf.exists() and pdf.stat().st_size > 0:
        return pdf

    archive = zip_path(config, law_number)
    if dry_run:
        print("Document preparation")
        print(f"ZIP: {archive}")
        print(f"PDF: {pdf}")
        if archive.exists():
            print("Dry run: ZIP would be converted to PDF.\n")
        else:
            print("Dry run: ZIP not found; conversion would fail without it.\n")
        return pdf

    if not archive.exists():
        raise FileNotFoundError(
            f"PDF does not exist and ZIP source was not found: {pdf}, {archive}"
        )

    print("Document preparation")
    print(f"ZIP: {archive}")
    print(f"PDF: {pdf}\n")

    pdf.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zip_file:
        pdf_infos = sorted(
            (
                info
                for info in zip_file.infolist()
                if not info.is_dir()
                and Path(info.filename).suffix.lower() == ".pdf"
            ),
            key=lambda info: natural_sort_key(info.filename),
        )
        if len(pdf_infos) == 1:
            with zip_file.open(pdf_infos[0]) as source, pdf.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            print(f"Copied PDF from ZIP: {pdf}\n")
            return pdf
        if len(pdf_infos) > 1:
            raise RuntimeError(
                f"ZIP contains multiple PDFs; keep only one PDF or use image pages: {archive}"
            )

        image_infos = sorted(
            (
                info
                for info in zip_file.infolist()
                if not info.is_dir()
                and Path(info.filename).suffix.lower() in IMAGE_EXTENSIONS
            ),
            key=lambda info: natural_sort_key(info.filename),
        )
        if not image_infos:
            raise RuntimeError(f"ZIP contains no PDF or supported image files: {archive}")

        _zip_images_to_pdf(zip_file, image_infos, pdf)
        print(f"Converted {len(image_infos)} image(s) to PDF: {pdf}\n")
        return pdf


def _zip_images_to_pdf(
    zip_file: zipfile.ZipFile,
    image_infos: list[zipfile.ZipInfo],
    output_path: Path,
) -> None:
    images: list[Image.Image] = []
    try:
        for image_info in image_infos:
            try:
                with zip_file.open(image_info) as source:
                    image = Image.open(source)
                    image.load()
            except UnidentifiedImageError as exc:
                raise RuntimeError(
                    f"Could not read image from ZIP: {image_info.filename}"
                ) from exc
            try:
                images.append(_to_rgb(image))
            finally:
                image.close()

        first, *rest = images
        first.save(output_path, "PDF", save_all=True, append_images=rest)
    finally:
        for image in images:
            image.close()


def _to_rgb(image: Image.Image) -> Image.Image:
    if image.mode == "RGB":
        return image.copy()
    if image.mode in {"RGBA", "LA"}:
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.getchannel("A"))
        return background
    return image.convert("RGB")


def natural_sort_key(filename: str) -> tuple[object, ...]:
    name_without_ext = Path(filename).stem
    letter_match = re.match(r"^([A-Za-z])(\d*)$", name_without_ext)
    if letter_match:
        letter = letter_match.group(1).lower()
        number_str = letter_match.group(2)
        number = 0 if number_str == "" else int(number_str)
        return (letter, number)

    parts: list[object] = []
    for part in re.split(r"(\d+)", name_without_ext):
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(part.lower())
    return tuple(parts)
