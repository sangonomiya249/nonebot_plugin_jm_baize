"""NoneBot2 JM 漫画插件 - 搜索、详情、下载"""
import asyncio
import base64
from typing import Any, Dict

from nonebot import on_command, get_driver
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

from .config import download_path, plugin_config, SEARCH_SESSIONS, SEARCH_SORTS
from .client import search_albums, get_album_info
from .download import download_album, cleanup
from .render import (
    _image_message_from_bytes,
    render_search_result,
    render_info,
    render_help,
    render_download_status,
)

__plugin_meta__ = PluginMetadata(
    name="JM漫画",
    description="JM漫画搜索、详情查看与下载",
    usage=(
        "/jm搜索 关键词 搜索漫画\n"
        "/jm详情 ID 查看漫画详情\n"
        "/jm下载 ID 下载漫画PDF/ZIP\n"
        "/下一页 搜索结果翻到下一页\n"
        "/上一页 搜索结果翻到上一页\n"
        "/jm帮助 查看JM插件帮助\n"
    ),
)


def _get_session_key(event: GroupMessageEvent | PrivateMessageEvent) -> str:
    if isinstance(event, GroupMessageEvent):
        return f"group:{event.group_id}"
    return f"private:{event.user_id}"


async def _send_search_page(
    matcher,
    keyword: str,
    page: int,
    sort_key: str,
    time_key: str,
    sort_label: str,
    session_key: str,
):
    try:
        albums = await asyncio.to_thread(
            search_albums, keyword, page, sort_key, time_key
        )
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        await matcher.finish(f"❌ 搜索失败：{e}")

    if not albums:
        if page > 1:
            await matcher.finish(f"🔍 第 {page} 页没有更多结果了")
        await matcher.finish("🔍 未找到相关本子")

    SEARCH_SESSIONS[session_key] = {
        "keyword": keyword,
        "page": page,
        "sort_key": sort_key,
        "time_key": time_key,
        "sort_label": sort_label,
    }

    try:
        image = await asyncio.to_thread(
            render_search_result, keyword, albums, sort_label, page
        )
    except Exception as e:
        logger.error(f"搜索结果渲染失败: {e}")
        await matcher.finish("❌ 搜索结果渲染失败")

    await matcher.finish(_image_message_from_bytes(image))


# ── 下载 ──
jm_download = on_command("jm下载", aliases={"jm下载本子"}, priority=5, block=True)


@jm_download.handle()
async def handle_download(
    bot: Bot, event: GroupMessageEvent | PrivateMessageEvent, arg: Message = CommandArg()
):
    album_id = arg.extract_plain_text().strip()
    if not album_id.isdigit():
        await jm_download.finish("❌ 请输入正确的数字 ID，示例：/jm下载 422866")

    output_desc = "压缩包"
    if plugin_config.jm_output_format.lower() == "pdf":
        output_desc = "加密 PDF" if plugin_config.jm_pdf_encrypt else "PDF"

    try:
        start_image = await asyncio.to_thread(
            render_download_status, album_id, output_desc, "start", "", str(event.user_id)
        )
        await jm_download.send(_image_message_from_bytes(start_image))
    except Exception as e:
        logger.error(f"下载状态图片渲染失败: {e}")
        await jm_download.send(
            f"⌛ 开始下载本子 [{album_id}]，完成后会自动生成{output_desc}，请耐心等待..."
        )

    local_file = None
    try:
        local_file = await asyncio.to_thread(download_album, album_id)
    except ImportError as e:
        await jm_download.finish(f"❌ {e}")
    except Exception as e:
        logger.error(f"JM 下载错误: {e}")
        await jm_download.finish(f"❌ 下载失败：{e}")

    # 读文件为 base64，避免跨容器/跨主机路径不可达
    with open(local_file, "rb") as f:
        file_base64 = base64.b64encode(f.read()).decode()

    upload_success = False
    is_timeout = False
    try:
        if isinstance(event, GroupMessageEvent):
            await bot.call_api(
                "upload_group_file",
                group_id=event.group_id,
                file=f"base64://{file_base64}",
                name=local_file.name,
                timeout=600,
            )
        elif isinstance(event, PrivateMessageEvent):
            await bot.call_api(
                "upload_private_file",
                user_id=event.user_id,
                file=f"base64://{file_base64}",
                name=local_file.name,
                timeout=600,
            )
        upload_success = True
    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg or "超时" in error_msg:
            is_timeout = True
            logger.warning(f"文件上传超时，NapCat 可能仍在后台上传: {e}")
        else:
            logger.error(f"文件上传失败: {e}")
            await jm_download.finish(f"❌ 文件上传失败：{e}\n文件本地路径：{local_file}")

    if upload_success and local_file:
        await asyncio.to_thread(cleanup, album_id, local_file)

    tip = ""
    if plugin_config.jm_output_format.lower() == "pdf" and plugin_config.jm_pdf_encrypt:
        tip = f"\n📌 PDF 打开密码：{album_id}"

    if is_timeout:
        try:
            timeout_image = await asyncio.to_thread(
                render_download_status, album_id, output_desc, "timeout", tip, str(event.user_id)
            )
        except Exception as e:
            logger.error(f"下载状态图片渲染失败: {e}")
            await jm_download.finish(
                f"⌛ 本子 [{album_id}] 已提交上传，文件较大时可能需要一点时间，请稍后到群文件查看。{tip}"
            )
        await jm_download.finish(_image_message_from_bytes(timeout_image))

    try:
        done_image = await asyncio.to_thread(
            render_download_status, album_id, output_desc, "done", tip, str(event.user_id)
        )
    except Exception as e:
        logger.error(f"下载状态图片渲染失败: {e}")
        await jm_download.finish(f"✅ 本子 [{album_id}] 处理完成，文件已发送。{tip}")
    await jm_download.finish(_image_message_from_bytes(done_image))


# ── 搜索 ──
jm_search = on_command("jm搜索", priority=5, block=True)


@jm_search.handle()
async def handle_search(
    bot: Bot, event: GroupMessageEvent | PrivateMessageEvent, arg: Message = CommandArg()
):
    raw = arg.extract_plain_text().strip()
    if not raw:
        await jm_search.finish(
            "❌ 请输入搜索关键词，示例：/jm搜索 关键词 或 /jm搜索 最新 关键词"
        )

    tokens = raw.split()
    sort_key, time_key, _, sort_label = SEARCH_SORTS["默认"]

    if tokens and tokens[0] in SEARCH_SORTS:
        sort_key, time_key, _, sort_label = SEARCH_SORTS[tokens.pop(0)]

    keyword = " ".join(tokens).strip()
    if not keyword:
        await jm_search.finish("❌ 请输入搜索关键词")

    session_key = _get_session_key(event)
    await _send_search_page(
        jm_search, keyword, 1, sort_key, time_key, sort_label, session_key
    )


# ── 详情 ──
jm_info = on_command("jm详情", priority=5, block=True)


@jm_info.handle()
async def handle_info(bot: Bot, arg: Message = CommandArg()):
    album_id = arg.extract_plain_text().strip()
    if not album_id.isdigit():
        await jm_info.finish("❌ 请输入正确的数字 ID，示例：/jm详情 422866")

    try:
        info = await asyncio.to_thread(get_album_info, album_id)
    except Exception as e:
        logger.error(f"获取详情失败: {e}")
        await jm_info.finish(f"❌ 获取详情失败：{e}")

    try:
        image = await asyncio.to_thread(render_info, info)
    except Exception as e:
        logger.error(f"详情图片渲染失败: {e}")
        await jm_info.finish("❌ 详情图片渲染失败")

    await jm_info.finish(_image_message_from_bytes(image))


# ── 翻页 ──
jm_next_page = on_command("下一页", priority=5, block=True)
jm_prev_page = on_command("上一页", priority=5, block=True)


@jm_next_page.handle()
async def handle_next_page(event: GroupMessageEvent | PrivateMessageEvent):
    session_key = _get_session_key(event)
    session = SEARCH_SESSIONS.get(session_key)
    if not session:
        await jm_next_page.finish("❌ 没有可翻页的搜索记录，请先发送 /jm搜索 关键词")

    await _send_search_page(
        jm_next_page,
        session["keyword"],
        session["page"] + 1,
        session["sort_key"],
        session["time_key"],
        session["sort_label"],
        session_key,
    )


@jm_prev_page.handle()
async def handle_prev_page(event: GroupMessageEvent | PrivateMessageEvent):
    session_key = _get_session_key(event)
    session = SEARCH_SESSIONS.get(session_key)
    if not session:
        await jm_prev_page.finish("❌ 没有可翻页的搜索记录，请先发送 /jm搜索 关键词")

    if session["page"] <= 1:
        await jm_prev_page.finish("❌ 已经是第一页了")

    await _send_search_page(
        jm_prev_page,
        session["keyword"],
        session["page"] - 1,
        session["sort_key"],
        session["time_key"],
        session["sort_label"],
        session_key,
    )


# ── 帮助 ──
jm_help = on_command("jm帮助", priority=5, block=True)


@jm_help.handle()
async def handle_help():
    try:
        image = await asyncio.to_thread(render_help)
    except Exception as e:
        logger.error(f"帮助图片渲染失败: {e}")
        await jm_help.finish("❌ 帮助图片渲染失败")
    await jm_help.finish(_image_message_from_bytes(image))
