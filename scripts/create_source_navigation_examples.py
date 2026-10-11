"""Create a larger, repeatable cold-parse batch under the ignored build directory."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    destination = root / "build/source-navigation-batch"
    destination.mkdir(parents=True, exist_ok=True)
    template = (root / "examples/source_navigation/calculator.cc").read_text()
    for index in range(24):
        functions = []
        for number in range(64):
            functions.append(f"""
int sample_{index}_{number}(int count) {{
    std::vector<int> values;
    for (int item = 0; item < count; ++item) {{
        values.push_back(7 + navigation_demo::scale(item, 3) * 2);
    }}
    std::sort(values.begin(), values.end());
    return values.empty() ? 0 : values.back();
}}
""")
        (destination / f"input_{index:02}.cc").write_text(
            "#include <algorithm>\n#include <vector>\n" + template + "".join(functions)
        )
    print(f"Created 24 C++ inputs in {destination}")


if __name__ == "__main__":
    main()
