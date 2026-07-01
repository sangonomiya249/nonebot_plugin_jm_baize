"""JM 插件 - 下载与文件处理"""
import shutil
from pathlib import Path
from typing import List

from nonebot.log import logger

from .config import plugin_config, download_path


def _collect_images(album_dir: Path) -> List[Path]:
    images: List[Path] = []
    chapters = sorted(
        (d for d in album_dir.iterdir() if d.is_dir()), key=lambda x: x.name
    )
    if chapters:
        for chapter in chapters:
            chapter_images = sorted(
                chapter.glob(f"*{plugin_config.jm_image_suffix}"),
                key=lambda x: x.stem,
            )
            images.extend(chapter_images)
    else:
        images = sorted(
            album_dir.glob(f"*{plugin_config.jm_image_suffix}"), key=lambda x: x.stem
        )
    return images


def _encrypt_pdf(pdf_path: Path, password: str) -> None:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter(clone_from=reader)
    writer.encrypt(user_password=password, owner_password=password, algorithm="AES-256")
    with open(pdf_path, "wb") as f:
        writer.write(f)


def _generate_pdf(album_dir: Path, album_id: str) -> Path:
    import img2pdf

    images = _collect_images(album_dir)
    if not images:
        for suffix in [".jpg", ".webp", ".png"]:
            images = sorted(album_dir.rglob(f"*{suffix}"), key=lambda x: x.stem)
            if images:
                break
    if not images:
        raise FileNotFoundError(f"未找到可合并的图片文件: {album_dir}")

    pdf_path = download_path / f"JM{album_id}.pdf"
    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert([str(img) for img in images]))

    if plugin_config.jm_pdf_encrypt:
        try:
            _encrypt_pdf(pdf_path, album_id)
        except ImportError:
            raise ImportError("未安装 pypdf，请执行 pip install pypdf 以启用 PDF 加密功能")
        except Exception as e:
            logger.warning(f"PDF 加密失败，将发送未加密文件: {e}")
    return pdf_path


def _cleanup_files(album_id: str, output_file: Path) -> None:
    if not plugin_config.jm_delete_after_upload:
        return
    try:
        if output_file.exists():
            output_file.unlink()
        album_dir = download_path / album_id
        if album_dir.exists():
            shutil.rmtree(album_dir)
        logger.info(f"本子 {album_id} 本地文件已清理完成")
    except Exception as e:
        logger.warning(f"清理本地文件失败: {e}")


def _get_upload_path(local_path: Path) -> str:
    # Linux 绝对路径需要 file:// 前缀，NapCat 才能识别
    prefix = ""
    if plugin_config.jm_upload_path_prefix:
        prefix = plugin_config.jm_upload_path_prefix.replace("\\", "/").rstrip("/")
        path = f"{prefix}/{local_path.name}"
    else:
        path = local_path.resolve().as_posix()
    return path if path.startswith("file://") else f"file://{path}"


def download_album(album_id: str) -> Path:
    """下载本子并转换为 PDF/ZIP，返回输出文件路径"""
    from .client import _build_option

    option = _build_option()
    option.download_album(album_id)

    album_dir = download_path / album_id
    if not album_dir.exists():
        for candidate in download_path.rglob("*"):
            if candidate.is_dir() and (
                candidate.name.startswith(album_id) or album_id in candidate.name
            ):
                album_dir = candidate
                break
        else:
            dirs = [d.name for d in download_path.iterdir() if d.is_dir()]
            raise FileNotFoundError(
                f"未找到本子目录: {album_id}\n当前目录子文件夹: {dirs}"
            )

    output_format = plugin_config.jm_output_format.lower().strip()
    if output_format == "pdf":
        return _generate_pdf(album_dir, album_id)
    if output_format == "zip":
        zip_path = album_dir.with_suffix(".zip")
        shutil.make_archive(str(album_dir), "zip", str(album_dir))
        return zip_path
    raise ValueError(f"不支持的输出格式: {output_format}，仅支持 zip / pdf")


def cleanup(album_id: str, output_file: Path) -> None:
    _cleanup_files(album_id, output_file)
