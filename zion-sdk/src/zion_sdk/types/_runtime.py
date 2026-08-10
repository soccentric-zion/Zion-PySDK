"""Runtime helpers for generated typed dataclasses.

Provides the universal freebies (`to_dict`, `to_json`) and a single
descriptor-driven ``from_proto`` / ``to_proto`` pair that works for every
generated dataclass. Kept here so generated files stay short and consistent.
"""
from __future__ import annotations

import base64
import enum
import json
from dataclasses import dataclass, asdict, fields, is_dataclass
from datetime import datetime, timezone
from typing import Any, ClassVar

# ---------------------------------------------------------------------------
# Well-known wrappers (kept tiny and JSON-friendly).
# ---------------------------------------------------------------------------


@dataclass
class Timestamp:
    """Mirrors ``google.protobuf.Timestamp``."""

    seconds: int = 0
    nanos: int = 0

    def to_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.seconds + self.nanos / 1e9, tz=timezone.utc)

    @classmethod
    def from_datetime(cls, dt: datetime) -> "Timestamp":
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ts = dt.timestamp()
        return cls(seconds=int(ts), nanos=int((ts - int(ts)) * 1e9))


@dataclass
class Duration:
    """Mirrors ``google.protobuf.Duration``."""

    seconds: int = 0
    nanos: int = 0

    def total_seconds(self) -> float:
        return self.seconds + self.nanos / 1e9


@dataclass
class AnyMessage:
    """Mirrors ``google.protobuf.Any``.

    Stores the raw type URL and value bytes. Decode with :func:`unpack`.
    """

    type_url: str = ""
    value: bytes = b""

    def unpack(self) -> Any:
        """Decode ``value`` into the registered dataclass for ``type_url``."""
        if not self.type_url:
            return None
        full_name = self.type_url.split("/")[-1]
        pb_cls = _resolve_pb(full_name)
        msg = pb_cls()
        msg.ParseFromString(self.value)
        dc_cls = _BY_NAME.get(full_name)
        if dc_cls is None:
            return msg
        return _from_proto(dc_cls, msg)


# ---------------------------------------------------------------------------
# Universal dataclass base — provides to_dict / to_json on every generated cls.
# ---------------------------------------------------------------------------


class _DataclassBase:
    """Base mixin for every generated dataclass."""

    PROTO_FULL_NAME: ClassVar[str] = ""

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(self)

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=_json_default)


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_jsonable(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, enum.Enum):
        return obj.name
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode("ascii")
    return obj


def _json_default(obj: Any) -> Any:
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode("ascii")
    if isinstance(obj, enum.Enum):
        return obj.name
    raise TypeError(f"not JSON-serialisable: {type(obj).__name__}")


# ---------------------------------------------------------------------------
# Dataclass <-> protobuf marshalling.
# ---------------------------------------------------------------------------

_BY_NAME: dict[str, type] = {}


def _register(full_name: str, cls: type) -> None:
    _BY_NAME[full_name] = cls


_WELL_KNOWN = {
    "google.protobuf.Timestamp": Timestamp,
    "google.protobuf.Duration": Duration,
    "google.protobuf.Any": AnyMessage,
}
for _n, _c in _WELL_KNOWN.items():
    _BY_NAME[_n] = _c


def _resolve_pb(full_name: str) -> Any:
    """Look up the *generated protobuf class* for ``full_name`` via the symbol DB."""
    from google.protobuf import symbol_database

    return symbol_database.Default().GetSymbol(full_name)


def _from_proto(cls: type, msg: Any) -> Any:
    """Materialise a dataclass instance from a protobuf message."""
    from google.protobuf.descriptor import FieldDescriptor as FD

    if msg is None:
        return cls()
    kwargs: dict[str, Any] = {}
    for fd in msg.DESCRIPTOR.fields:
        name = fd.name
        py_name = name + "_" if _is_pykw(name) else name
        is_map = fd.message_type is not None and fd.message_type.GetOptions().map_entry
        val = getattr(msg, name)
        if is_map:
            val_fd = fd.message_type.fields_by_name["value"]
            kwargs[py_name] = {k: _convert_scalar(val_fd, v) for k, v in val.items()}
        elif fd.is_repeated:
            kwargs[py_name] = [_convert_scalar(fd, v) for v in val]
        else:
            kwargs[py_name] = _convert_scalar(fd, val)
    inst = cls(**kwargs)
    oneofs = getattr(msg.DESCRIPTOR, "oneofs", ())
    if oneofs:
        inst._oneofs = {o.name: msg.WhichOneof(o.name) for o in oneofs}
    return inst


def _convert_scalar(fd: Any, val: Any) -> Any:
    from google.protobuf.descriptor import FieldDescriptor as FD

    if fd.type == FD.TYPE_MESSAGE:
        full = fd.message_type.full_name
        if full == "google.protobuf.Timestamp":
            return Timestamp(seconds=val.seconds, nanos=val.nanos)
        if full == "google.protobuf.Duration":
            return Duration(seconds=val.seconds, nanos=val.nanos)
        if full == "google.protobuf.Any":
            return AnyMessage(type_url=val.type_url, value=val.value)
        dc = _BY_NAME.get(full)
        if dc is None:
            return val
        return _from_proto(dc, val)
    if fd.type == FD.TYPE_ENUM:
        full = fd.enum_type.full_name
        dc = _BY_NAME.get(full)
        if dc is not None:
            try:
                return dc(val)
            except ValueError:
                # Unknown enum number — preserve as int.
                return val
        return val
    return val


def _to_proto(dc: Any, pb_cls: type) -> Any:
    """Materialise a protobuf message from a dataclass instance."""
    from google.protobuf.descriptor import FieldDescriptor as FD

    msg = pb_cls()
    for fd in msg.DESCRIPTOR.fields:
        name = fd.name
        py_name = name + "_" if _is_pykw(name) else name
        val = getattr(dc, py_name, None)
        if val is None:
            continue
        # Oneof handling: skip default-valued fields so we do not clobber the
        # active arm. Proto3 oneofs are a single slot — setting any field
        # clears the others, so we set only non-default values.
        if fd.containing_oneof is not None and _is_default(fd, val):
            continue
        is_map = fd.message_type is not None and fd.message_type.GetOptions().map_entry
        if is_map:
            val_fd = fd.message_type.fields_by_name["value"]
            container = getattr(msg, name)
            for k, v in val.items():
                _assign_map_entry(container, k, v, val_fd)
        elif fd.is_repeated:
            container = getattr(msg, name)
            for v in val:
                _append_repeated(container, v, fd)
        else:
            _assign_singular(msg, fd, val)
    return msg


def _is_default(fd: Any, val: Any) -> bool:
    from google.protobuf.descriptor import FieldDescriptor as FD

    if fd.type in (FD.TYPE_STRING,):
        return val == ""
    if fd.type == FD.TYPE_BYTES:
        return val == b""
    if fd.type == FD.TYPE_BOOL:
        return val is False
    if fd.type in (FD.TYPE_FLOAT, FD.TYPE_DOUBLE):
        return val == 0.0
    if fd.type in (FD.TYPE_INT32, FD.TYPE_INT64, FD.TYPE_UINT32, FD.TYPE_UINT64,
                   FD.TYPE_SINT32, FD.TYPE_SINT64, FD.TYPE_FIXED32, FD.TYPE_FIXED64,
                   FD.TYPE_SFIXED32, FD.TYPE_SFIXED64):
        return val == 0
    if fd.type == FD.TYPE_ENUM:
        return int(val) == 0
    # Messages inside a oneof: treat as default only if the dataclass is
    # all-zero (cheap check via repr).
    if fd.type == FD.TYPE_MESSAGE:
        return val is None
    return False


def _assign_singular(msg: Any, fd: Any, val: Any) -> None:
    from google.protobuf.descriptor import FieldDescriptor as FD

    if fd.type == FD.TYPE_MESSAGE:
        sub = getattr(msg, fd.name)
        full = fd.message_type.full_name
        if full == "google.protobuf.Timestamp":
            sub.seconds = val.seconds
            sub.nanos = val.nanos
        elif full == "google.protobuf.Duration":
            sub.seconds = val.seconds
            sub.nanos = val.nanos
        elif full == "google.protobuf.Any":
            sub.type_url = val.type_url
            sub.value = val.value
        else:
            sub.CopyFrom(val.to_proto())
    elif fd.type == FD.TYPE_ENUM:
        setattr(msg, fd.name, int(val))
    else:
        setattr(msg, fd.name, val)


def _append_repeated(container: Any, val: Any, fd: Any) -> None:
    from google.protobuf.descriptor import FieldDescriptor as FD

    if fd.type == FD.TYPE_MESSAGE:
        full = fd.message_type.full_name
        if full == "google.protobuf.Timestamp":
            sub = container.add()
            sub.seconds = val.seconds
            sub.nanos = val.nanos
        elif full == "google.protobuf.Any":
            sub = container.add()
            sub.type_url = val.type_url
            sub.value = val.value
        else:
            container.add().CopyFrom(val.to_proto())
    elif fd.type == FD.TYPE_ENUM:
        container.append(int(val))
    else:
        container.append(val)


def _assign_map_entry(container: Any, key: Any, val: Any, val_fd: Any) -> None:
    from google.protobuf.descriptor import FieldDescriptor as FD

    if val_fd.type == FD.TYPE_MESSAGE:
        container[key].CopyFrom(val.to_proto())
    elif val_fd.type == FD.TYPE_ENUM:
        container[key] = int(val)
    else:
        container[key] = val


def _is_pykw(name: str) -> bool:
    import keyword

    return keyword.iskeyword(name)
