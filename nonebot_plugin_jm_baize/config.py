"""JM 插件 - 配置常量"""
import os
import re
from pathlib import Path
from typing import Any, Dict

# ---------- 插件目录 ----------
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_PLUGIN_DIR, "data")
os.makedirs(_DATA_DIR, exist_ok=True)

# ---------- 手动解析 .env ----------
_ENV_PREFIX = "JM_"
_env_values: Dict[str, str] = {}
_root = Path.cwd()
for _env_file in [_root / ".env", _root / f".env.{os.environ.get('ENVIRONMENT', '')}"]:
    try:
        if _env_file.exists():
            for _line in _env_file.read_text(encoding="utf-8").splitlines():
                _line = _line.strip()
                if not _line or _line.startswith("#"):
                    continue
                _m = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=\s*(.+)$', _line)
                if _m:
                    _env_values[_m.group(1)] = _m.group(2).strip().strip('"').strip("'")
    except Exception:
        pass


def _env(key: str, default):
    """优先读 .env (JM_XXX)，否则用默认值"""
    val = _env_values.get(f"{_ENV_PREFIX}{key}")
    if val is not None and val.strip():
        if isinstance(default, bool):
            return val.lower() in ("true", "1", "yes")
        if isinstance(default, int):
            return int(val)
        return val
    return default


# ---------- 配置项（Web UI 可识别 CONFIG 字典格式）----------
# 使用 _env() 包装，.env 中设置 JM_XXX 可覆盖默认值
CONFIG = {
    "JM_DOWNLOAD_DIR": _env("DOWNLOAD_DIR", os.path.join(_DATA_DIR, "downloads")),  # 下载目录
    "JM_UPLOAD_PATH_PREFIX": _env("UPLOAD_PATH_PREFIX", ""),  # 上传路径前缀
    "JM_USE_API_CLIENT": _env("USE_API_CLIENT", True),  # 使用 API 客户端
    "JM_PROXY": _env("PROXY", ""),  # HTTP 代理
    "JM_IMAGE_SUFFIX": _env("IMAGE_SUFFIX", ".jpg"),  # 图片后缀
    "JM_OUTPUT_FORMAT": _env("OUTPUT_FORMAT", "pdf"),  # 输出格式 pdf/zip
    "JM_PDF_ENCRYPT": _env("PDF_ENCRYPT", True),  # PDF 加密
    "JM_DELETE_AFTER_UPLOAD": _env("DELETE_AFTER_UPLOAD", False),  # 上传后删除本地文件
}


# ---------- 兼容旧代码的属性访问 ----------
class JMConfig:
    def __init__(self, cfg: dict):
        self.jm_download_dir = str(cfg["JM_DOWNLOAD_DIR"])
        self.jm_upload_path_prefix = str(cfg["JM_UPLOAD_PATH_PREFIX"])
        self.jm_use_api_client = bool(cfg["JM_USE_API_CLIENT"])
        self.jm_proxy = str(cfg["JM_PROXY"])
        self.jm_image_suffix = str(cfg["JM_IMAGE_SUFFIX"])
        self.jm_output_format = str(cfg["JM_OUTPUT_FORMAT"])
        self.jm_pdf_encrypt = bool(cfg["JM_PDF_ENCRYPT"])
        self.jm_delete_after_upload = bool(cfg["JM_DELETE_AFTER_UPLOAD"])


plugin_config = JMConfig(CONFIG)

download_path = Path(CONFIG["JM_DOWNLOAD_DIR"]).resolve()
download_path.mkdir(parents=True, exist_ok=True)

# ---------- 常量 ----------
SEARCH_SORTS: Dict[str, tuple] = {
    "默认": ("mr", "a", "0", "默认"),
    "相关": ("mr", "a", "0", "相关度"),
    "最新": ("mp", "a", "0", "最新发布"),
    "总排行": ("mv", "a", "0", "总排行"),
    "观看": ("mv", "a", "0", "观看最多"),
    "浏览": ("mv", "a", "0", "观看最多"),
    "点赞": ("tf", "a", "0", "点赞最多"),
    "喜欢": ("tf", "a", "0", "点赞最多"),
    "评论": ("mv", "a", "0", "热门"),
}

SEARCH_PAGE_SIZE = 80
SEARCH_SESSIONS: Dict[str, Dict[str, Any]] = {}
