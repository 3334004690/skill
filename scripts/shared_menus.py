"""Plain-language Markdown menus shared by media generation CLIs."""


def render_menu(title, rows, closing="", columns=("想设置什么", "可以怎么选")):
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [f"**{title}**", "", f"| {cell(columns[0])} | {cell(columns[1])} |", "| :--- | :--- |"]
    lines.extend(f"| {cell(label)} | {cell(value)} |" for label, value in rows)
    if closing:
        lines.extend(("", closing))
    return "\n".join(lines)


def ratio_choices(ratios):
    names = {"1:1": "方形", "16:9": "横屏", "9:16": "竖屏", "21:9": "电影宽屏",
             "4:3": "横幅", "3:4": "竖幅", "adaptive": "跟随参考图"}
    return "、".join(f"{names[ratio]} {ratio}" if ratio in names and ratio != "adaptive"
                    else names.get(ratio, ratio) for ratio in ratios)
