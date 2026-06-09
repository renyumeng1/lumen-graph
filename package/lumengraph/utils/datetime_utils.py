"""日期时间工具模块。

提供 UTC 和上海时区的日期时间处理函数，包括：
- 时间获取：获取当前时间（UTC/上海时区）
- 时区转换：确保 datetime 转换为指定时区
- 格式转换：datetime 与 ISO 格式字符串互转
- 类型强制转换：支持 int、float、str 等多种输入格式

Example:
    >>> from lumengraph.agents.utils.datetime_utils import utc_now, utc_isoformat
    >>> utc_now()
    datetime.datetime(2026, 6, 9, 10, 30, 0, tzinfo=datetime.timezone.utc)
    >>> utc_isoformat(utc_now())
    '2026-06-09T10:30:00Z'
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from zoneinfo import ZoneInfo

UTC = dt.UTC
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
_ISO_Z_SUFFIX = "+00:00"


def utc_now() -> dt.datetime:
    """获取当前 UTC 时间。

    Returns:
        dt.datetime: 当前 UTC 时区的 datetime 对象。

    Example:
        >>> utc_now()  # doctest: +ELLIPSIS
        datetime.datetime(..., tzinfo=datetime.timezone.utc)
    """
    return dt.datetime.now(UTC)


def utc_now_naive() -> dt.datetime:
    """获取当前 UTC 时间（不含时区信息）。

    注意：返回的是 UTC 时间，但没有 tzinfo 属性。

    Returns:
        dt.datetime: 当前 UTC 时间（无时区）的 datetime 对象。

    Example:
        >>> utc_now_naive()  # doctest: +ELLIPSIS
        datetime.datetime(...)
    """
    return dt.datetime.now(UTC).replace(tzinfo=None)


def shanghai_now() -> dt.datetime:
    """获取当前上海时区时间。

    Returns:
        dt.datetime: 当前上海时区的 datetime 对象。

    Example:
        >>> shanghai_now()  # doctest: +ELLIPSIS
        datetime.datetime(..., tzinfo=ZoneInfo('Asia/Shanghai'))
    """
    return utc_now().astimezone(SHANGHAI_TZ)


def ensure_utc(value: dt.datetime) -> dt.datetime:
    """确保 datetime 对象为 UTC 时区。

    如果输入没有时区信息，则假定为上海时区后转换为 UTC。
    如果输入已是 UTC 时区，则直接返回。

    Args:
        value: 待转换的 datetime 对象。

    Returns:
        dt.datetime: UTC 时区的 datetime 对象。

    Example:
        >>> from datetime import datetime
        >>> ensure_utc(datetime(2026, 6, 9, 10, 30, 0))  # 无时区 -> 假定上海后转UTC
        datetime.datetime(2026, 6, 9, 2, 30, tzinfo=datetime.timezone.utc)
        >>> ensure_utc(datetime(2026, 6, 9, 10, 30, 0, tzinfo=UTC))  # 已是UTC
        datetime.datetime(2026, 6, 9, 10, 30, tzinfo=datetime.timezone.utc)
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=SHANGHAI_TZ)

    return value.astimezone(UTC)


def ensure_shanghai(value: dt.datetime) -> dt.datetime:
    """确保 datetime 对象为上海时区。

    如果输入没有时区信息，则假定为上海时区。
    如果输入已是其他时区，则转换到上海时区。

    Args:
        value: 待转换的 datetime 对象。

    Returns:
        dt.datetime: 上海时区的 datetime 对象。

    Example:
        >>> from datetime import datetime
        >>> ensure_shanghai(datetime(2026, 6, 9, 10, 30, 0))
        datetime.datetime(2026, 6, 9, 10, 30, tzinfo=ZoneInfo('Asia/Shanghai'))
    """
    if value.tzinfo is None:
        value.replace(tzinfo=SHANGHAI_TZ)
    return value.astimezone(SHANGHAI_TZ)


def utc_isoformat(value: dt.datetime | None = None) -> str:
    """将 datetime 转换为 UTC ISO 格式字符串。

    生成的字符串使用 'Z' 后缀表示 UTC 时区，而非 '+00:00'。

    Args:
        value: 待转换的 datetime 对象。如果为 None，则使用当前 UTC 时间。

    Returns:
        str: UTC ISO 格式字符串，格式为 "YYYY-MM-DDTHH:MM:SSZ"。

    Example:
        >>> utc_isoformat()  # doctest: +ELLIPSIS
        '20...-...-...T...:...:...Z'
        >>> from datetime import datetime
        >>> utc_isoformat(datetime(2026, 6, 9, 10, 30, 0, tzinfo=UTC))
        '2026-06-09T10:30:00Z'
    """
    value = ensure_utc(value or utc_now())

    iso_string = value.isoformat()
    if iso_string.endswith(_ISO_Z_SUFFIX):
        return iso_string.replace(_ISO_Z_SUFFIX, "Z")
    return iso_string


def shanghai_isoformat(value: dt.datetime | None = None) -> str:
    """将 datetime 转换为上海时区 ISO 格式字符串。

    Args:
        value: 待转换的 datetime 对象。如果为 None，则使用当前上海时间。

    Returns:
        str: 上海时区 ISO 格式字符串。

    Example:
        >>> shanghai_isoformat()  # doctest: +ELLIPSIS
        '20...-...-...+...:...'
    """
    value = ensure_shanghai(value or shanghai_now())
    return value.isoformat()


def coerce_datetime(value: dt.datetime | None) -> dt.datetime | None:
    """强制转换 datetime 为 UTC 时区。

    如果输入为 None，则返回 None。
    如果输入是 datetime，则确保其时区为 UTC。

    Args:
        value: 待转换的值。

    Returns:
        dt.datetime | None: UTC 时区的 datetime，或 None（如果输入为 None）。

    Example:
        >>> from datetime import datetime
        >>> coerce_datetime(None)
        >>> coerce_datetime(datetime(2026, 6, 9, 10, 30, 0))
        datetime.datetime(2026, 6, 9, 2, 30, tzinfo=datetime.timezone.utc)
    """
    if value is None:
        return None
    return ensure_utc(value)


def coerce_any_to_utc_datetime(value: dt.datetime | int | float | str | None) -> dt.datetime | None:
    """将任意类型的值转换为 UTC datetime。

    支持的类型：
    - None：返回 None
    - datetime：直接转换为 UTC
    - int/float：作为 Unix 时间戳转换
    - str：尝试解析为 ISO 格式或数字时间戳

    Args:
        value: 待转换的值，支持多种格式。

    Returns:
        dt.datetime | None: UTC 时区的 datetime，或 None（如果输入为 None）。

    Raises:
        ValueError: 字符串格式不支持（既不是有效的 ISO 格式也不是有效的数字）。
        TypeError: 输入类型不支持。

    Example:
        >>> coerce_any_to_utc_datetime(None)
        >>> coerce_any_to_utc_datetime(1717929600)
        datetime.datetime(2026, 6, 9, 0, 0, tzinfo=datetime.timezone.utc)
        >>> coerce_any_to_utc_datetime("2026-06-09T10:30:00Z")
        datetime.datetime(2026, 6, 9, 10, 30, tzinfo=datetime.timezone.utc)
    """
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return ensure_utc(value)

    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(value, tz=UTC)

    if isinstance(value, str):
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", _ISO_Z_SUFFIX))
            return ensure_utc(parsed)

        except ValueError:
            try:
                as_number = float(value)
                return dt.datetime.fromtimestamp(as_number, tz=UTC)
            except ValueError:
                raise ValueError(f"Unsupported datetime string format: {value!r}") from None
    raise TypeError(f"Unsupported datetime value:{value!r}")


def normalize_iterable_to_utc(values: Iterable[dt.datetime | None]) -> list[dt.datetime | None]:
    """将可迭代对象中的所有 datetime 转换为 UTC 时区。

    Args:
        values: 包含 datetime 或 None 的可迭代对象。

    Returns:
        list[dt.datetime | None]: 转换后的列表，非 datetime 元素会被转换为 None。

    Example:
        >>> from datetime import datetime
        >>> dts = [datetime(2026, 6, 9, 10, 30), datetime(2026, 6, 9, 12, 0), None]
        >>> result = normalize_iterable_to_utc(dts)
        >>> len(result)
        3
    """
    return [coerce_datetime(item) if isinstance(item, dt.datetime) else None for item in values]


def format_utc_datetime(value: dt.datetime | None) -> str | None:
    """将 datetime 格式化为 UTC ISO 字符串。

    与 utc_isoformat 的区别：输入为 None 时返回 None，而非使用当前时间。

    Args:
        value: 待格式化的 datetime 对象。

    Returns:
        str | None: UTC ISO 格式字符串，或 None（如果输入为 None）。

    Example:
        >>> from datetime import datetime
        >>> format_utc_datetime(datetime(2026, 6, 9, 10, 30, 0, tzinfo=UTC))
        '2026-06-09T10:30:00Z'
        >>> format_utc_datetime(None)
    """
    if value is None:
        return None
    return utc_isoformat(value)


def utc_isoformat_from_timestamp(timestamp: float | int | None) -> str | None:
    """从 Unix 时间戳生成 UTC ISO 格式字符串。

    Args:
        timestamp: Unix 时间戳（秒）。如果为 None，返回 None。

    Returns:
        str | None: UTC ISO 格式字符串，或 None（如果输入为 None）。

    Example:
        >>> utc_isoformat_from_timestamp(1717929600)
        '2026-06-09T00:00:00+00:00'
        >>> utc_isoformat_from_timestamp(None)
    """
    if timestamp is None:
        return None
    return dt.datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


__all__ = [
    "UTC",
    "SHANGHAI_TZ",
    "utc_now",
    "utc_now_naive",
    "shanghai_now",
    "ensure_utc",
    "ensure_shanghai",
    "utc_isoformat",
    "shanghai_isoformat",
    "coerce_datetime",
    "coerce_any_to_utc_datetime",
    "normalize_iterable_to_utc",
    "format_utc_datetime",
    "utc_isoformat_from_timestamp",
]