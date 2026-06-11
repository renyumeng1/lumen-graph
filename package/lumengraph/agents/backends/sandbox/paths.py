"""
沙盒文件系统路径管理模块。

本模块提供沙盒环境下虚拟路径与真实文件系统路径之间的转换功能。
虚拟路径以固定前缀（如 /sandbox）开头，后跟特定命名空间目录：

    - workspace/ : 全局工作空间，在同一用户的所有线程间共享
    - uploads/   : 用户上传的文件目录（每个线程独立）
    - outputs/   : 生成的输出文件目录（每个线程独立）
    - 无前缀     : 存到用户数据目录

安全特性：
    - 所有路径必须以配置的虚拟前缀开头
    - 禁止路径遍历攻击（../ 等）
    - 线程 ID 和用户 ID 仅允许字母、数字、下划线、连字符

目录结构：
    save_dir/
    └── threads/
        ├── shared/              # 用户级共享数据
        │   └── {uid}/
        │       └── workspace/   # 全局工作空间
        └── {thread_id}/         # 线程级独立数据
            └── user-data/
                ├── uploads/     # 上传文件
                └── outputs/     # 输出文件

Example:
    >>> resolve_virtual_path("thread-123", "/sandbox/workspace/readme.md", uid="user-abc")
    PosixPath('/save_dir/threads/shared/user-abc/workspace/readme.md')

    >>> virtual_path_for_thread_file("thread-123", "/save_dir/threads/shared/user-abc/workspace/readme.md", uid="user-abc")
    '/sandbox/workspace/readme.md'
"""

from __future__ import annotations
import re
from pathlib import Path

from lumengraph import config as conf
from lumengraph.utils.logging_config import logger
from lumengraph.utils.paths import (
    OUTPUTS_DIR_NAME,
    UPLOADS_DIR_NAME,
    VIRTUAL_PATH_PREFIX,
    WORKSPACE_AGENTS_DIR_NAME,
    WORKSPACE_AGENTS_PROMPT_FILE_NAME,
    WORKSPACE_DIR_NAME
)


_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

def get_virtual_path_prefix() -> str:
    """
    获取虚拟路径前缀。

    Returns:
        以斜杠开头的虚拟路径前缀，如 "/sandbox"
    """
    return "/" + VIRTUAL_PATH_PREFIX.strip("/")


def validate_thread_id(thread_id: str) -> str:
    """
    验证线程 ID 的有效性。

    Args:
        thread_id: 要验证的线程 ID

    Returns:
        验证通过的线程 ID（去除首尾空格）

    Raises:
        ValueError: 线程 ID 为空或包含非法字符（仅允许字母、数字、下划线、连字符）
    """
    value = str(thread_id or "").strip()
    if not value:
        raise ValueError("thread_id is required")
    if not _SAFE_ID_RE.match(value):
        raise ValueError("thread_id contains invalid characters")
    return value


def _thread_root_dir(thread_id: str) -> Path:
    """
    获取线程的用户数据根目录。

    Args:
        thread_id: 线程 ID

    Returns:
        线程用户数据根目录路径
    """
    safe_thread_id = validate_thread_id(thread_id)
    return Path(conf.save_dir) / "threads" / safe_thread_id / "user-data"


def _validate_uid(uid: str) -> str:
    """
    验证用户 ID 的有效性。

    Args:
        uid: 要验证的用户 ID

    Returns:
        验证通过的用户 ID（去除首尾空格）

    Raises:
        ValueError: 用户 ID 为空或包含非法字符
    """
    value = str(uid or "").strip()
    if not value:
        raise ValueError("uid is required")
    if not _SAFE_ID_RE.match(value):
        raise ValueError("uid contains invalid characters")
    return value


def _global_user_data_dir(uid: str) -> Path:
    """
    获取用户的全局数据目录（跨线程共享）。

    Args:
        uid: 用户 ID

    Returns:
        用户全局数据目录路径
    """
    safe_uid = _validate_uid(uid)
    return Path(conf.save_dir) / "threads" / "shared" / safe_uid


def sandbox_user_data_dir(thread_id: str) -> Path:
    """
    获取线程的用户数据目录（线程独立）。

    Args:
        thread_id: 线程 ID

    Returns:
        线程用户数据目录路径
    """
    return _thread_root_dir(thread_id)


def sandbox_workspace_dir(thread_id: str, uid: str) -> Path:
    """
    获取用户的工作空间目录。

    工作空间在同一个用户的所有线程间共享。

    Args:
        thread_id: 线程 ID
        uid: 用户 ID

    Returns:
        工作空间目录路径
    """
    validate_thread_id(thread_id)
    return _global_user_data_dir(uid) / WORKSPACE_DIR_NAME


def sandbox_workspace_agents_prompt_file(thread_id: str, uid: str) -> Path:
    """
    获取工作空间的 agents 提示文件路径。

    Args:
        thread_id: 线程 ID
        uid: 用户 ID

    Returns:
        agents 提示文件路径
    """
    return sandbox_workspace_dir(thread_id, uid) / WORKSPACE_AGENTS_DIR_NAME / WORKSPACE_AGENTS_PROMPT_FILE_NAME


def _threads_root_dir() -> Path:
    """
    获取所有线程的根目录。

    Returns:
        线程根目录路径
    """
    return (Path(conf.save_dir) / "threads").resolve(strict=False)


def _resolve_threads_child_path(path: Path) -> Path:
    """
    解析路径并验证其是否在线程根目录下。

    防止路径遍历攻击，确保文件操作限制在允许的目录内。

    Args:
        path: 要验证的路径

    Returns:
        解析后的安全路径

    Raises:
        ValueError: 路径解析后超出线程根目录
    """
    root = _threads_root_dir()
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ValueError("path resolved outside threads root")
    return resolved


def _chmod_writable(path: Path, *, dir: bool = False) -> None:
    """
    设置文件或目录为可写权限。

    Args:
        path: 要设置权限的路径
        dir: 是否为目录（目录需要执行位）
    """
    safe_path = _resolve_threads_child_path(path)
    mode = 0o777 if dir else 0o666
    try:
        safe_path.chmod(mode)
    except OSError:
        pass


def ensure_workspace_default_files(workspace_dir: Path) -> None:
    """
    确保工作空间的默认文件和目录存在。

    创建 agents 目录和 AGENTS.md 提示文件。

    Args:
        workspace_dir: 工作空间目录路径
    """
    workspace_dir = _resolve_threads_child_path(workspace_dir)
    agents_dir = workspace_dir / WORKSPACE_AGENTS_DIR_NAME
    agents_file = agents_dir / WORKSPACE_AGENTS_PROMPT_FILE_NAME


    try:
        agents_dir.mkdir(parents=True,exist_ok=True)
        _chmod_writable(agents_dir,dir=True)
    except FileExistsError:
        logger.warning("工作区默认 Agents 目录创建失败：路径已被文件占用")
    except OSError as exc:
        logger.warning(f"工作区默认 Agents 目录初始化失败：{exc}")
        return
    

    try:
        with agents_file.open("xb"):
            pass
        _chmod_writable(agents_file)
    
    except FileExistsError:
        if agents_file.is_dir():
            logger.warning("工作区默认 AGENTS.md 创建失败：路径已被目录占用")
    except OSError as exc:
        logger.warning(f"工作区默认 Agents 文件初始化失败：{exc}")


def sandbox_outputs_dir(thread_id: str) -> Path:
    """
    获取线程的输出文件目录。

    Args:
        thread_id: 线程 ID

    Returns:
        输出文件目录路径
    """
    return _thread_root_dir(thread_id) / OUTPUTS_DIR_NAME


def sandbox_uploads_dir(thread_id: str) -> Path:
    """
    获取线程的上传文件目录。

    Args:
        thread_id: 线程 ID

    Returns:
        上传文件目录路径
    """
    return _thread_root_dir(thread_id) / UPLOADS_DIR_NAME

def ensure_thread_dirs(thread_id: str, uid: str) -> None:
    """
    确保线程所需的所有目录存在。

    包括用户全局目录、工作空间、上传目录、输出目录。
    工作空间会同时初始化默认的 agents 目录和提示文件。

    Args:
        thread_id: 线程 ID
        uid: 用户 ID
    """
    _resolve_threads_child_path(_global_user_data_dir(uid)).mkdir(parents=True, exist_ok=True)
    workspace_dir = _resolve_threads_child_path(sandbox_workspace_dir(thread_id, uid))
    workspace_dir.mkdir(parents=True, exist_ok=True)
    ensure_workspace_default_files(workspace_dir)
    _resolve_threads_child_path(sandbox_uploads_dir(thread_id)).mkdir(parents=True, exist_ok=True)
    _resolve_threads_child_path(sandbox_outputs_dir(thread_id)).mkdir(parents=True, exist_ok=True)


def _resolve_user_data_base_dir(
    thread_id: str, uid: str, relative_path: str
) -> tuple[Path, Path]:
    """
    根据相对路径解析基础目录和目标路径。

    根据路径的第一层命名空间（目录）路由到不同的基础目录：
        - "workspace" -> 工作空间目录（跨线程共享）
        - "uploads"   -> 上传目录（线程独立）
        - "outputs"   -> 输出目录（线程独立）
        - 其他        -> 用户数据目录（线程独立）

    Args:
        thread_id: 线程 ID
        uid: 用户 ID
        relative_path: 相对路径（如 "workspace/foo.txt" 或 "uploads/img.png"）

    Returns:
        元组 (base_dir, target_path)：
            - base_dir: 用于权限检查的基础目录
            - target_path: 实际的文件操作目标路径
    """
    parts = Path(relative_path).parts
    if not parts:
        base_dir = sandbox_user_data_dir(thread_id)
        return base_dir.resolve(), base_dir.resolve()

    namespace = parts[0]
    if namespace == WORKSPACE_DIR_NAME:
        base_dir = sandbox_workspace_dir(thread_id, uid)
        target_path = base_dir.joinpath(*parts[1:]) if len(parts) > 1 else base_dir
        return base_dir.resolve(), target_path.resolve()

    if namespace == UPLOADS_DIR_NAME:
        base_dir = sandbox_uploads_dir(thread_id)
        target_path = base_dir.joinpath(*parts[1:]) if len(parts) > 1 else base_dir
        return base_dir.resolve(), target_path.resolve()

    if namespace == OUTPUTS_DIR_NAME:
        base_dir = sandbox_outputs_dir(thread_id)
        target_path = base_dir.joinpath(*parts[1:]) if len(parts) > 1 else base_dir
        return base_dir.resolve(), target_path.resolve()

    base_dir = sandbox_user_data_dir(thread_id)
    return base_dir.resolve(), (base_dir / relative_path).resolve()


def resolve_virtual_path(thread_id: str, virtual_path: str, *, uid: str) -> Path:
    """
    将虚拟路径转换为真实文件系统路径。

    安全检查：
        - 路径必须以配置的虚拟前缀开头
        - 不允许路径遍历（防止 ../ 攻击）

    Args:
        thread_id: 线程 ID
        virtual_path: 虚拟路径（如 "/sandbox/workspace/readme.md"）
        uid: 用户 ID（关键字参数）

    Returns:
        对应的真实文件系统路径

    Raises:
        ValueError: 路径不以虚拟前缀开头，或检测到路径遍历攻击
    """
    clean_virtual_path = "/" + str(virtual_path or "").strip().lstrip("/")
    virtual_prefix = get_virtual_path_prefix()

    if clean_virtual_path != virtual_prefix and not clean_virtual_path.startswith(f"{virtual_prefix}/"):
        raise ValueError(f"path must start with {virtual_prefix}")

    relative_path = clean_virtual_path[len(virtual_prefix):].lstrip("/")
    base_dir, target_path = _resolve_user_data_base_dir(thread_id, uid, relative_path)

    try:
        target_path.relative_to(base_dir)
    except ValueError as exc:
        raise ValueError("path traversal detected") from exc

    return target_path
    

def virtual_path_for_thread_file(thread_id: str, path: str | Path, *, uid: str) -> str:
    """
    将真实文件系统路径转换为虚拟路径。

    是 resolve_virtual_path 的逆操作。

    Args:
        thread_id: 线程 ID
        path: 真实文件系统路径
        uid: 用户 ID（关键字参数）

    Returns:
        对应的虚拟路径（如 "/sandbox/workspace/readme.md"）

    Raises:
        ValueError: 文件路径不在允许的目录内
    """
    target_path = Path(path).resolve()
    thread_root = sandbox_user_data_dir(thread_id).resolve()
    global_workspace_root = sandbox_workspace_dir(thread_id, uid).resolve()

    try:
        relative_path = target_path.relative_to(global_workspace_root)

    except ValueError:
        try:
            relative_path = target_path.relative_to(thread_root)

        except ValueError as exc:
            raise ValueError("file is outside allowed user-data directories") from exc
        relative_path_str = relative_path.as_posix()

    else:
        workspace_relative = relative_path.as_posix()
        relative_path_str = (
            WORKSPACE_DIR_NAME
            if workspace_relative in {"", "."}
            else f"{WORKSPACE_DIR_NAME}/{workspace_relative}"
        )

    prefix = get_virtual_path_prefix().rstrip("/")
    if not relative_path_str:
        return prefix
    return f"{prefix}/{relative_path_str}"


