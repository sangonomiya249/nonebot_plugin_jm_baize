"""JM 插件 - API 客户端（搜索、详情）"""
from typing import Any, Dict, Iterable, List

import jmcomic

from .config import plugin_config, download_path


def _build_option() -> jmcomic.JmOption:
    client_impl = "api" if plugin_config.jm_use_api_client else "html"
    download_dir = download_path.as_posix()

    proxy_block = ""
    if plugin_config.jm_proxy:
        proxy_block = f"""
  proxies:
    http: {plugin_config.jm_proxy}
    https: {plugin_config.jm_proxy}
"""

    yaml_config = f"""
dir_rule:
  rule: Bd_Aid
  base_dir: {download_dir}

client:
  impl: {client_impl}{proxy_block}

download:
  image:
    suffix: {plugin_config.jm_image_suffix}
  cache: false
""".strip()

    return jmcomic.create_option_by_str(yaml_config, "yml")


def _get_client(option: jmcomic.JmOption):
    if hasattr(option, "build_jm_client"):
        return option.build_jm_client()
    if hasattr(option, "new_jm_client"):
        return option.new_jm_client()
    raise AttributeError("当前 jmcomic 版本未提供 build_jm_client/new_jm_client")


def _call_first_available(target: Any, method_names: Iterable[str], *args, **kwargs):
    last_error = None
    for method_name in method_names:
        method = getattr(target, method_name, None)
        if method is None:
            continue
        try:
            return method(*args, **kwargs)
        except TypeError as e:
            last_error = e
    if last_error is not None:
        raise last_error
    raise AttributeError(f"可用方法不存在: {', '.join(method_names)}")


def search_albums(
    keyword: str, page: int = 1, sort_key: str = "mr", time_key: str = "a"
) -> List[Dict]:
    option = _build_option()
    client = _get_client(option)

    result = None
    attempts = [
        ("search", (keyword, page, 0, sort_key, time_key, "0", None), {}),
        ("search", (keyword, page, 0), {}),
        ("search", (keyword, page), {}),
        ("search_album", (keyword, page), {}),
    ]

    for method_name, args, kwargs in attempts:
        method = getattr(client, method_name, None)
        if method is None:
            continue
        try:
            result = method(*args, **kwargs)
            break
        except TypeError:
            continue

    if result is None:
        raise AttributeError("当前 jmcomic 客户端不支持搜索接口")

    if hasattr(result, "content"):
        albums = []
        for item in result.content:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            album_id, album_info = item[0], item[1]
            if not isinstance(album_info, dict):
                album_info = {}
            albums.append({
                "id": str(album_id),
                "title": album_info.get("name") or album_info.get("title") or "未知标题",
                "author": album_info.get("author") or "未知",
            })
        return albums

    album_list = getattr(result, "album_list", None) or getattr(result, "albums", [])
    return [
        {
            "id": album.id,
            "title": getattr(album, "name", getattr(album, "title", "未知标题")),
            "author": getattr(album, "author", "未知") or "未知",
        }
        for album in album_list
    ]


def get_album_info(album_id: str) -> Dict:
    option = _build_option()
    client = _get_client(option)
    album = _call_first_available(client, ["get_album_detail", "get_album"], album_id)
    if hasattr(album, "single_album"):
        album = album.single_album

    episode_list = getattr(album, "episode_list", None) or getattr(album, "photo_list", [])
    chapters = []
    for episode in episode_list:
        if isinstance(episode, (list, tuple)):
            chapter_id = str(episode[0]) if len(episode) >= 1 else ""
            chapter_title = str(episode[2]) if len(episode) >= 3 else "未命名章节"
        else:
            chapter_id = str(
                getattr(episode, "id", None)
                or getattr(episode, "photo_id", None)
                or getattr(episode, "album_id", None)
                or ""
            )
            chapter_title = (
                getattr(episode, "name", None)
                or getattr(episode, "title", None)
                or "未命名章节"
            )
        chapters.append({"id": chapter_id, "title": chapter_title})

    def normalize_list(value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if item not in (None, "")]
        return [str(value)]

    authors = normalize_list(getattr(album, "authors", None))

    def pick(*names):
        for name in names:
            value = getattr(album, name, None)
            if value not in (None, "", [], ()):
                return value
        return None

    return {
        "id": album.id,
        "title": getattr(album, "name", getattr(album, "title", "未知标题")),
        "author": getattr(album, "author", "未知") or "未知",
        "authors": authors,
        "link": pick("link", "url", "album_url") or f"https://18comic.vip/album/{album.id}/",
        "pub_date": getattr(album, "pub_date", None) or pick("publish_date", "created_at"),
        "update_date": getattr(album, "update_date", None) or pick("updated_at", "last_update_date"),
        "page_count": getattr(album, "page_count", None) or pick("total_page", "images_count"),
        "views": pick("views", "view_count"),
        "likes": pick("likes", "like_count"),
        "comment_count": pick("comment_count", "comments", "comment_num"),
        "chapter_count": len(episode_list),
        "tags": normalize_list(getattr(album, "tags", []) or []),
        "actors": normalize_list(
            getattr(album, "actors", []) or getattr(album, "works_actor", []) or []
        ),
        "works": normalize_list(
            getattr(album, "works", []) or getattr(album, "related_works", []) or []
        ),
        "chapters": chapters,
        "description": getattr(album, "description", "无简介"),
    }
