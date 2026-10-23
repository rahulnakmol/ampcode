"""Reader themes for distilling-videos publications.

Single source of truth for `assets/themes.css` and `assets/THEMES.md`, generated at render time.
Each variant maps seven tokens to named entries of the family's official palette. Text tokens must
reach WCAG AA (4.5:1) on the background, the surface, and the tinted note/target backgrounds; an
official value that fails is mixed toward black (light themes) or white (dark themes) in 4 % steps
until it passes, and the adaptation is recorded and labeled. Images are never recolored.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

TOKENS = ("bg", "surface", "fg", "muted", "rule", "accent", "warm")
TEXT_TOKENS = ("fg", "muted", "accent", "warm")
CSS_NAMES = {"bg": "--paper", "surface": "--surface", "fg": "--ink", "muted": "--graphite", "rule": "--rule",
             "accent": "--cobalt", "warm": "--sodium"}
AA = 4.5
DEFAULT = "house-light"
DEFAULT_DARK = "house-dark"

FAMILIES: Dict[str, Dict[str, str]] = {
    "house": {"name": "House", "source": "distilling-videos house style (this repository)",
              "license": "Same as this repository", "author": "distilling-videos"},
    "tokyo-night": {"name": "Tokyo Night", "author": "enkia (original VS Code theme); folke (Night/Storm/Moon/Day palettes)",
                    "source": "https://github.com/tokyo-night/tokyo-night-vscode-theme; "
                              "https://github.com/folke/tokyonight.nvim (lua/tokyonight/colors, extras/lua)",
                    "license": "MIT (VS Code theme); Apache-2.0 (tokyonight.nvim)"},
    "github": {"name": "GitHub", "author": "GitHub (Primer)",
               "source": "https://github.com/primer/primitives (npm @primer/primitives 11.10.0, "
                         "dist/css/functional/themes); https://github.com/primer/github-vscode-theme",
               "license": "MIT"},
    "catppuccin": {"name": "Catppuccin", "author": "Catppuccin",
                   "source": "https://github.com/catppuccin/palette (npm @catppuccin/palette 1.8.0)",
                   "license": "MIT"},
    "gruvbox": {"name": "Gruvbox", "author": "Pavel Pertsev (morhetz)",
                "source": "https://github.com/morhetz/gruvbox (colors/gruvbox.vim)", "license": "MIT/X11"},
    "nord": {"name": "Nord", "author": "Arctic Ice Studio / Sven Greb",
             "source": "https://github.com/nordtheme/nord (src/nord.css)", "license": "MIT"},
    "dracula": {"name": "Dracula", "author": "Zeno Rocha and Dracula Theme contributors",
                "source": "https://draculatheme.com/spec (Dracula Classic and Alucard Classic palettes); "
                          "https://github.com/dracula/dracula-theme",
                "license": "MIT"},
    "solarized": {"name": "Solarized", "author": "Ethan Schoonover",
                  "source": "https://github.com/altercation/solarized (README palette)", "license": "MIT"},
    "one": {"name": "One", "author": "GitHub (Atom One Dark / One Light syntax themes)",
            "source": "https://github.com/atom/atom (packages/one-dark-syntax and one-light-syntax, "
                      "styles/colors.less; HSL values converted to hex)",
            "license": "MIT"},
    "rose-pine": {"name": "Rosé Pine", "author": "Rosé Pine",
                  "source": "https://github.com/rose-pine/rose-pine-palette (palette.json)", "license": "MIT"},
    "kanagawa": {"name": "Kanagawa", "author": "Tommaso Laurenzi (rebelot)",
                 "source": "https://github.com/rebelot/kanagawa.nvim (lua/kanagawa/colors.lua, themes.lua)",
                 "license": "MIT"},
    "everforest": {"name": "Everforest", "author": "Sainnhe Park",
                   "source": "https://github.com/sainnhe/everforest (autoload/everforest.vim, medium contrast)",
                   "license": "MIT"},
    "ayu": {"name": "Ayu", "author": "Ike Ku and ayu contributors",
            "source": "https://github.com/ayu-theme/ayu-colors (npm ayu 9.1.0, dist/generated)",
            "license": "MIT"},
    "material": {"name": "Material", "author": "Mattia Astorino (Material Theme)",
                 "source": "Material Theme color palette documentation, archived at "
                           "https://web.archive.org/web/2022/https://material-theme.com/docs/reference/color-palette/ "
                           "(the original repository and npm package were withdrawn)",
                 "license": "Palette values only; the withdrawn project was Apache-2.0. No theme code is copied."},
    "night-owl": {"name": "Night Owl", "author": "Sarah Drasner",
                  "source": "https://github.com/sdras/night-owl-vscode-theme (themes/*.json)", "license": "MIT"},
    "monokai": {"name": "Monokai", "author": "Wimer Hazenberg",
                "source": "Classic Monokai palette (https://monokai.nl); values as published in the Material Theme "
                          "palette archive and the original TextMate theme",
                "license": "Palette values only; the original theme has no explicit license. No theme code is copied. "
                           "Monokai Pro is a separate commercial product and is not used."},
    "synthwave-84": {"name": "SynthWave '84", "author": "Robb Owen",
                     "source": "https://github.com/robb0wen/synthwave-vscode (themes/synthwave-color-theme.json)",
                     "license": "MIT"},
    "cobalt2": {"name": "Cobalt2", "author": "Wes Bos",
                "source": "https://github.com/wesbos/cobalt2-vscode (theme/cobalt2.json)", "license": "MIT"},
    "palenight": {"name": "Palenight", "author": "Olaolu Olawuyi (whizkydee)",
                  "source": "https://github.com/whizkydee/vscode-palenight-theme (themes/palenight.json)",
                  "license": "MIT"},
    "tomorrow": {"name": "Tomorrow", "author": "Chris Kempson",
                 "source": "https://github.com/chriskempson/tomorrow-theme (vim/colors/*.vim)", "license": "MIT"},
    "zenburn": {"name": "Zenburn", "author": "Jani Nurminen",
                "source": "https://github.com/jnurmine/Zenburn (colors/zenburn.vim)",
                "license": "Palette values only; the Vim script is GPL. No theme code is copied."},
}


def _v(id_: str, family: str, variant: str, mode: str, **tokens: Tuple[str, str]) -> Dict[str, Any]:
    missing = set(TOKENS) - set(tokens)
    if missing:
        raise ValueError(f"theme {id_} is missing {sorted(missing)}")
    return {"id": id_, "family": family, "variant": variant, "mode": mode, "tokens": tokens}


# Each token is (hex, palette entry it comes from).
VARIANTS: List[Dict[str, Any]] = [
    _v("house-light", "house", "Light", "light", bg=("#f4f5f7", "paper"), surface=("#e6e8ec", "code ground"),
       fg=("#15171c", "ink"), muted=("#565b66", "graphite"), rule=("#d5d8de", "rule"),
       accent=("#1f45c8", "cobalt"), warm=("#9a5400", "sodium")),
    _v("house-dark", "house", "Dark", "dark", bg=("#0e1015", "darkroom"), surface=("#1b1e26", "darkroom raised"),
       fg=("#e9ebef", "paper ink"), muted=("#a2a8b4", "graphite light"), rule=("#2c313c", "rule dark"),
       accent=("#9fb0f5", "cobalt light"), warm=("#e3a857", "sodium light")),
    _v("tokyo-night-night", "tokyo-night", "Night", "dark", bg=("#1a1b26", "bg"), surface=("#16161e", "bg_dark"),
       fg=("#c0caf5", "fg"), muted=("#a9b1d6", "fg_dark"), rule=("#414868", "terminal_black"),
       accent=("#7aa2f7", "blue"), warm=("#e0af68", "yellow")),
    _v("tokyo-night-storm", "tokyo-night", "Storm", "dark", bg=("#24283b", "bg"), surface=("#1f2335", "bg_dark"),
       fg=("#c0caf5", "fg"), muted=("#a9b1d6", "fg_dark"), rule=("#414868", "terminal_black"),
       accent=("#7aa2f7", "blue"), warm=("#e0af68", "yellow")),
    _v("tokyo-night-moon", "tokyo-night", "Moon", "dark", bg=("#222436", "bg"), surface=("#1e2030", "bg_dark"),
       fg=("#c8d3f5", "fg"), muted=("#828bb8", "fg_dark"), rule=("#444a73", "terminal_black"),
       accent=("#82aaff", "blue"), warm=("#ffc777", "yellow")),
    _v("tokyo-night-day", "tokyo-night", "Day", "light", bg=("#e1e2e7", "bg"), surface=("#d0d5e3", "bg_dark"),
       fg=("#3760bf", "fg"), muted=("#6172b0", "fg_dark"), rule=("#a8aecb", "fg_gutter"),
       accent=("#2e7de9", "blue"), warm=("#b15c00", "orange")),
    _v("github-light", "github", "Light", "light", bg=("#ffffff", "bgColor-default"),
       surface=("#f6f8fa", "bgColor-muted"), fg=("#1f2328", "fgColor-default"), muted=("#59636e", "fgColor-muted"),
       rule=("#d1d9e0", "borderColor-default"), accent=("#0969da", "fgColor-accent"),
       warm=("#9a6700", "fgColor-attention")),
    _v("github-dark", "github", "Dark", "dark", bg=("#0d1117", "bgColor-default"), surface=("#151b23", "bgColor-muted"),
       fg=("#f0f6fc", "fgColor-default"), muted=("#9198a1", "fgColor-muted"), rule=("#3d444d", "borderColor-default"),
       accent=("#4493f8", "fgColor-accent"), warm=("#d29922", "fgColor-attention")),
    _v("github-dark-dimmed", "github", "Dark Dimmed", "dark", bg=("#212830", "bgColor-default"),
       surface=("#262c36", "bgColor-muted"), fg=("#d1d7e0", "fgColor-default"), muted=("#9198a1", "fgColor-muted"),
       rule=("#3d444d", "borderColor-default"), accent=("#478be6", "fgColor-accent"),
       warm=("#c69026", "fgColor-attention")),
    _v("catppuccin-latte", "catppuccin", "Latte", "light", bg=("#eff1f5", "base"), surface=("#e6e9ef", "mantle"),
       fg=("#4c4f69", "text"), muted=("#6c6f85", "subtext0"), rule=("#ccd0da", "surface0"),
       accent=("#1e66f5", "blue"), warm=("#fe640b", "peach")),
    _v("catppuccin-frappe", "catppuccin", "Frappé", "dark", bg=("#303446", "base"), surface=("#292c3c", "mantle"),
       fg=("#c6d0f5", "text"), muted=("#a5adce", "subtext0"), rule=("#414559", "surface0"),
       accent=("#8caaee", "blue"), warm=("#ef9f76", "peach")),
    _v("catppuccin-macchiato", "catppuccin", "Macchiato", "dark", bg=("#24273a", "base"),
       surface=("#1e2030", "mantle"), fg=("#cad3f5", "text"), muted=("#a5adcb", "subtext0"),
       rule=("#363a4f", "surface0"), accent=("#8aadf4", "blue"), warm=("#f5a97f", "peach")),
    _v("catppuccin-mocha", "catppuccin", "Mocha", "dark", bg=("#1e1e2e", "base"), surface=("#181825", "mantle"),
       fg=("#cdd6f4", "text"), muted=("#a6adc8", "subtext0"), rule=("#313244", "surface0"),
       accent=("#89b4fa", "blue"), warm=("#fab387", "peach")),
    _v("gruvbox-dark", "gruvbox", "Dark", "dark", bg=("#282828", "dark0"), surface=("#3c3836", "dark1"),
       fg=("#ebdbb2", "light1"), muted=("#a89984", "light4"), rule=("#504945", "dark2"),
       accent=("#83a598", "bright_blue"), warm=("#fe8019", "bright_orange")),
    _v("gruvbox-light", "gruvbox", "Light", "light", bg=("#fbf1c7", "light0"), surface=("#ebdbb2", "light1"),
       fg=("#3c3836", "dark1"), muted=("#7c6f64", "dark4"), rule=("#d5c4a1", "light2"),
       accent=("#076678", "faded_blue"), warm=("#af3a03", "faded_orange")),
    _v("nord", "nord", "Nord", "dark", bg=("#2e3440", "nord0"), surface=("#3b4252", "nord1"), fg=("#eceff4", "nord6"),
       muted=("#d8dee9", "nord4"), rule=("#434c5e", "nord2"), accent=("#88c0d0", "nord8"),
       warm=("#d08770", "nord12")),
    _v("dracula", "dracula", "Dracula", "dark", bg=("#282a36", "Background"), surface=("#44475a", "Selection"),
       fg=("#f8f8f2", "Foreground"), muted=("#6272a4", "Comment"), rule=("#44475a", "Selection"),
       accent=("#8be9fd", "Cyan"), warm=("#ffb86c", "Orange")),
    _v("dracula-alucard", "dracula", "Alucard", "light", bg=("#fffbeb", "Background"), surface=("#cfcfde", "Selection"),
       fg=("#1f1f1f", "Foreground"), muted=("#6c664b", "Comment"), rule=("#cfcfde", "Selection"),
       accent=("#036a96", "Cyan"), warm=("#a34d14", "Orange")),
    _v("solarized-light", "solarized", "Light", "light", bg=("#fdf6e3", "base3"), surface=("#eee8d5", "base2"),
       fg=("#657b83", "base00"), muted=("#93a1a1", "base1"), rule=("#eee8d5", "base2"),
       accent=("#268bd2", "blue"), warm=("#cb4b16", "orange")),
    _v("solarized-dark", "solarized", "Dark", "dark", bg=("#002b36", "base03"), surface=("#073642", "base02"),
       fg=("#839496", "base0"), muted=("#586e75", "base01"), rule=("#073642", "base02"),
       accent=("#268bd2", "blue"), warm=("#cb4b16", "orange")),
    _v("one-dark", "one", "One Dark", "dark", bg=("#282c34", "syntax-bg"), surface=("#3e4451", "syntax-selection"),
       fg=("#abb2bf", "mono-1"), muted=("#828997", "mono-2"), rule=("#3e4451", "syntax-selection"),
       accent=("#61afef", "hue-2"), warm=("#e5c07b", "hue-6-2")),
    _v("one-light", "one", "One Light", "light", bg=("#fafafa", "syntax-bg"), surface=("#e5e5e6", "syntax-selection"),
       fg=("#383a42", "mono-1"), muted=("#696c77", "mono-2"), rule=("#e5e5e6", "syntax-selection"),
       accent=("#4078f2", "hue-2"), warm=("#b76b01", "hue-6")),
    _v("rose-pine", "rose-pine", "Rosé Pine", "dark", bg=("#191724", "base"), surface=("#1f1d2e", "surface"),
       fg=("#e0def4", "text"), muted=("#908caa", "subtle"), rule=("#26233a", "overlay"),
       accent=("#9ccfd8", "foam"), warm=("#f6c177", "gold")),
    _v("rose-pine-moon", "rose-pine", "Moon", "dark", bg=("#232136", "base"), surface=("#2a273f", "surface"),
       fg=("#e0def4", "text"), muted=("#908caa", "subtle"), rule=("#393552", "overlay"),
       accent=("#9ccfd8", "foam"), warm=("#f6c177", "gold")),
    _v("rose-pine-dawn", "rose-pine", "Dawn", "light", bg=("#faf4ed", "base"), surface=("#fffaf3", "surface"),
       fg=("#464261", "text"), muted=("#797593", "subtle"), rule=("#f2e9e1", "overlay"),
       accent=("#286983", "pine"), warm=("#ea9d34", "gold")),
    _v("kanagawa-wave", "kanagawa", "Wave", "dark", bg=("#1f1f28", "sumiInk3"), surface=("#16161d", "sumiInk0"),
       fg=("#dcd7ba", "fujiWhite"), muted=("#c8c093", "oldWhite"), rule=("#363646", "sumiInk5"),
       accent=("#7e9cd8", "crystalBlue"), warm=("#ffa066", "surimiOrange")),
    _v("kanagawa-dragon", "kanagawa", "Dragon", "dark", bg=("#181616", "dragonBlack3"),
       surface=("#12120f", "dragonBlack1"), fg=("#c5c9c5", "dragonWhite"), muted=("#a6a69c", "dragonGray"),
       rule=("#393836", "dragonBlack5"), accent=("#8ba4b0", "dragonBlue2"), warm=("#b6927b", "dragonOrange")),
    _v("kanagawa-lotus", "kanagawa", "Lotus", "light", bg=("#f2ecbc", "lotusWhite3"), surface=("#e5ddb0", "lotusWhite2"),
       fg=("#545464", "lotusInk1"), muted=("#716e61", "lotusGray2"), rule=("#dcd5ac", "lotusWhite1"),
       accent=("#4d699b", "lotusBlue4"), warm=("#cc6d00", "lotusOrange")),
    _v("everforest-dark", "everforest", "Dark", "dark", bg=("#2d353b", "bg0"), surface=("#343f44", "bg1"),
       fg=("#d3c6aa", "fg"), muted=("#9da9a0", "grey2"), rule=("#475258", "bg3"),
       accent=("#7fbbb3", "blue"), warm=("#e69875", "orange")),
    _v("everforest-light", "everforest", "Light", "light", bg=("#fdf6e3", "bg0"), surface=("#f4f0d9", "bg1"),
       fg=("#5c6a72", "fg"), muted=("#829181", "grey2"), rule=("#e6e2cc", "bg3"),
       accent=("#3a94c5", "blue"), warm=("#f57d26", "orange")),
    _v("ayu-light", "ayu", "Light", "light", bg=("#fcfcfc", "editor.bg"), surface=("#f8f9fa", "ui.bg"),
       fg=("#5c6166", "editor.fg"), muted=("#828e9f", "ui.fg"), rule=("#e7eaed", "ui.line over bg"),
       accent=("#22a4e6", "syntax.entity"), warm=("#f29718", "common.accent")),
    _v("ayu-mirage", "ayu", "Mirage", "dark", bg=("#242936", "editor.bg"), surface=("#1f2430", "ui.bg"),
       fg=("#cccac2", "editor.fg"), muted=("#707a8c", "ui.fg"), rule=("#171b24", "ui.line"),
       accent=("#73d0ff", "syntax.entity"), warm=("#ffcc66", "common.accent")),
    _v("ayu-dark", "ayu", "Dark", "dark", bg=("#10141c", "editor.bg"), surface=("#0d1017", "ui.bg"),
       fg=("#bfbdb6", "editor.fg"), muted=("#5a6378", "ui.fg"), rule=("#1b1f29", "ui.line"),
       accent=("#59c2ff", "syntax.entity"), warm=("#e6b450", "common.accent")),
    _v("material-oceanic", "material", "Oceanic", "dark", bg=("#263238", "Background"),
       surface=("#32424a", "Second Background"), fg=("#b0bec5", "Foreground"), muted=("#607d8b", "Text"),
       rule=("#2a373e", "Border"), accent=("#80cbc4", "Links"), warm=("#ffcb6b", "Yellow")),
    _v("material-darker", "material", "Darker", "dark", bg=("#212121", "Background"),
       surface=("#292929", "Second Background"), fg=("#b0bec5", "Foreground"), muted=("#727272", "Text"),
       rule=("#3f3f3f", "Highlight"), accent=("#80cbc4", "Links"), warm=("#ffcb6b", "Yellow")),
    _v("material-deep-ocean", "material", "Deep Ocean", "dark", bg=("#0f111a", "Background"),
       surface=("#181a1f", "Second Background"), fg=("#8f93a2", "Foreground"), muted=("#717cb4", "Comments"),
       rule=("#1f2233", "Highlight"), accent=("#80cbc4", "Links"), warm=("#ffcb6b", "Yellow")),
    _v("material-lighter", "material", "Lighter", "light", bg=("#fafafa", "Background"),
       surface=("#ffffff", "Second Background"), fg=("#546e7a", "Foreground"), muted=("#94a7b0", "Text"),
       rule=("#d3e1e8", "Border"), accent=("#00bcd4", "Accent"), warm=("#f78c6c", "Orange")),
    _v("night-owl", "night-owl", "Night Owl", "dark", bg=("#011627", "editor.background"),
       surface=("#0b2942", "Second Background"), fg=("#d6deeb", "editor.foreground"),
       muted=("#5f7e97", "panel.border"), rule=("#122d42", "Border"), accent=("#82aaff", "function blue"),
       warm=("#ecc48d", "string")),
    _v("night-owl-light", "night-owl", "Light Owl", "light", bg=("#fbfbfb", "editor.background"),
       surface=("#f0f0f0", "sideBar.background"), fg=("#403f53", "editor.foreground"),
       muted=("#90a7b2", "editorLineNumber.foreground"), rule=("#d9d9d9", "panel.border"),
       accent=("#4876d6", "function blue"), warm=("#c96765", "string")),
    _v("monokai", "monokai", "Classic", "dark", bg=("#272822", "background"), surface=("#3e3d32", "line highlight"),
       fg=("#f8f8f2", "foreground"), muted=("#75715e", "comment"), rule=("#49483e", "selection"),
       accent=("#66d9ef", "blue"), warm=("#e6db74", "yellow")),
    _v("synthwave-84", "synthwave-84", "SynthWave '84", "dark", bg=("#262335", "editor.background"),
       surface=("#241b2f", "sideBar.background"), fg=("#ffffff", "foreground"), muted=("#848bbd", "comment"),
       rule=("#34294f", "Border"), accent=("#36f9f6", "cyan"), warm=("#fede5d", "yellow")),
    _v("cobalt2", "cobalt2", "Cobalt2", "dark", bg=("#193549", "editor.background"),
       surface=("#15232d", "sideBar.background"), fg=("#ffffff", "editor.foreground"),
       muted=("#aaaaaa", "descriptionForeground"), rule=("#0d3a58", "focusBorder"), accent=("#ffc600", "yellow"),
       warm=("#ff9d00", "orange")),
    _v("palenight", "palenight", "Palenight", "dark", bg=("#292d3e", "editor.background"),
       surface=("#31364a", "editorWidget.background"), fg=("#bfc7d5", "editor.foreground"),
       muted=("#697098", "comment"), rule=("#4c5374", "editorLineNumber.foreground"), accent=("#82aaff", "blue"),
       warm=("#ffcb6b", "yellow")),
    _v("tomorrow", "tomorrow", "Tomorrow", "light", bg=("#ffffff", "background"), surface=("#efefef", "line"),
       fg=("#4d4d4c", "foreground"), muted=("#8e908c", "comment"), rule=("#d6d6d6", "selection"),
       accent=("#4271ae", "blue"), warm=("#f5871f", "orange")),
    _v("tomorrow-night", "tomorrow", "Night", "dark", bg=("#1d1f21", "background"), surface=("#282a2e", "line"),
       fg=("#c5c8c6", "foreground"), muted=("#969896", "comment"), rule=("#373b41", "selection"),
       accent=("#81a2be", "blue"), warm=("#f0c674", "yellow")),
    _v("tomorrow-night-eighties", "tomorrow", "Night Eighties", "dark", bg=("#2d2d2d", "background"),
       surface=("#393939", "line"), fg=("#cccccc", "foreground"), muted=("#999999", "comment"),
       rule=("#515151", "selection"), accent=("#6699cc", "blue"), warm=("#ffcc66", "yellow")),
    _v("tomorrow-night-blue", "tomorrow", "Night Blue", "dark", bg=("#002451", "background"),
       surface=("#00346e", "line"), fg=("#ffffff", "foreground"), muted=("#7285b7", "comment"),
       rule=("#003f8e", "selection"), accent=("#bbdaff", "blue"), warm=("#ffeead", "yellow")),
    _v("tomorrow-night-bright", "tomorrow", "Night Bright", "dark", bg=("#000000", "background"),
       surface=("#2a2a2a", "line"), fg=("#eaeaea", "foreground"), muted=("#969896", "comment"),
       rule=("#424242", "selection"), accent=("#7aa6da", "blue"), warm=("#e7c547", "yellow")),
    _v("zenburn", "zenburn", "Zenburn", "dark", bg=("#3f3f3f", "Normal bg"), surface=("#353535", "LineNr bg"),
       fg=("#dcdccc", "Normal fg"), muted=("#9fafaf", "Directory"), rule=("#5d6262", "LineNr fg"),
       accent=("#8cd0d3", "Number"), warm=("#f0dfaf", "Keyword")),
]


def _rgb(hex_: str) -> Tuple[float, float, float]:
    value = hex_.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _hex(rgb: Tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb)


def mix(a: str, b: str, amount: float) -> str:
    """sRGB mix: `amount` of b into a (matches CSS color-mix(in srgb, b amount, a))."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(x + (y - x) * amount for x, y in zip(ra, rb)))  # type: ignore[arg-type]


def luminance(hex_: str) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in _rgb(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def grounds(tokens: Dict[str, str]) -> Dict[str, str]:
    """Every background text is drawn on: page, surface, and the tinted note and target grounds."""
    return {"bg": tokens["bg"], "surface": tokens["surface"], "note": mix(tokens["bg"], tokens["warm"], 0.08),
            "target": mix(tokens["bg"], tokens["accent"], 0.10)}


def resolve(variant: Dict[str, Any]) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """Return final token values and the list of adaptations needed for AA contrast."""
    tokens = {name: value[0].lower() for name, value in variant["tokens"].items()}
    extreme = "#000000" if variant["mode"] == "light" else "#ffffff"
    adaptations = []
    for _ in range(3):  # tinted grounds depend on accent and warm, so settle iteratively
        changed = False
        for name in TEXT_TOKENS:
            worst = min(contrast(tokens[name], g) for g in grounds(tokens).values())
            if worst >= AA:
                continue
            original, step = tokens[name], 0
            while min(contrast(tokens[name], g) for g in grounds(tokens).values()) < AA and step < 25:
                step += 1
                tokens[name] = mix(original, extreme, step * 0.04)
            record = next((a for a in adaptations if a["token"] == name), None)
            if record:
                record["value"] = tokens[name]
            else:
                adaptations.append({"token": name, "official": variant["tokens"][name][0].lower(),
                                    "palette": variant["tokens"][name][1], "value": tokens[name]})
            changed = True
        if not changed:
            break
    return tokens, adaptations


def resolved() -> List[Dict[str, Any]]:
    out = []
    for variant in VARIANTS:
        tokens, adaptations = resolve(variant)
        family = FAMILIES[variant["family"]]
        label = family["name"] if variant["variant"] == family["name"] else f"{family['name']} {variant['variant']}"
        out.append({**variant, "values": tokens, "adaptations": adaptations, "label": label,
                    "family_name": family["name"]})
    return out


def _declarations(item: Dict[str, Any]) -> str:
    values = item["values"]
    parts = [f"{CSS_NAMES[t]}: {values[t]};" for t in TOKENS] + [f"color-scheme: {item['mode']};"]
    return " ".join(parts)


def css() -> str:
    items = {i["id"]: i for i in resolved()}
    lines = ["/* Generated by scripts/themes.py. Sources, licenses, and adaptations: THEMES.md. */",
             f":root {{ {_declarations(items[DEFAULT])} }}",
             f"@media screen and (prefers-color-scheme: dark) {{ html:not([data-theme]) {{ "
             f"{_declarations(items[DEFAULT_DARK])} }} }}"]
    for item in items.values():
        lines.append(f'html[data-theme="{item["id"]}"] {{ {_declarations(item)} }}')
    lines.append(f"@media print {{ html[data-theme], html:not([data-theme]) {{ {_declarations(items[DEFAULT])} }} }}")
    return "\n".join(lines) + "\n"


def options() -> List[Tuple[str, List[Tuple[str, str]]]]:
    """Picker groups: [(family name, [(theme id, label)])]. Adapted variants say so."""
    groups: Dict[str, List[Tuple[str, str]]] = {}
    for item in resolved():
        label = item["label"] + (" (adapted)" if item["adaptations"] else "")
        groups.setdefault(item["family_name"], []).append((item["id"], label))
    return list(groups.items())


def provenance_md() -> str:
    lines = ["# Reader themes", "",
             "Generated by `scripts/themes.py`. The default follows the reader's system color scheme "
             "(House light or House dark). Print and PDF always use House light. Theme choice is stored only "
             "in this browser's `localStorage` when available. Source screenshots are never recolored.", "",
             "Each variant maps seven tokens (background, surface, text, muted text, rule, accent, warm accent) "
             "to named entries of the official palette. Text tokens must reach WCAG AA (4.5:1) on the "
             "background, the surface, and the tinted note and target grounds. When an official value fails, it "
             "is mixed toward black (light) or white (dark) in 4 % steps until it passes; the variant is labeled "
             "\"(adapted)\" and the table below lists the official value and the value used.", ""]
    by_family: Dict[str, List[Dict[str, Any]]] = {}
    for item in resolved():
        by_family.setdefault(item["family"], []).append(item)
    for key, items in by_family.items():
        family = FAMILIES[key]
        lines += [f"## {family['name']}", "", f"- Author: {family['author']}", f"- Source: {family['source']}",
                  f"- License: {family['license']}", ""]
        for item in items:
            mapping = ", ".join(f"{t} {item['tokens'][t][0].lower()} ({item['tokens'][t][1]})" for t in TOKENS)
            lines.append(f"- **{item['variant']}** (`{item['id']}`, {item['mode']}): {mapping}.")
            for a in item["adaptations"]:
                lines.append(f"  - Adapted {a['token']}: official {a['official']} ({a['palette']}) → {a['value']} "
                             "for AA contrast.")
        lines.append("")
    return "\n".join(lines)
