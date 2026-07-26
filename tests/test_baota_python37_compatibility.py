from pathlib import Path


PLUGIN_ROOT = Path("cf_tunnel")


def test_plugin_source_avoids_python38_plus_runtime_typing_features() -> None:
    unsupported_markers = (
        "from typing import Protocol",
        "from typing import TypeAlias",
        "from typing import final",
        "@final",
        "slots=True",
        "JsonScalar: TypeAlias",
        "Callable[[list[",
        "Callable[[PluginConfig], tuple[",
    )
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(PLUGIN_ROOT.glob("*.py"))
    )

    assert not any(marker in source for marker in unsupported_markers)
