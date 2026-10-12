"""极简 PPM（P3 文本格式）位图：零依赖的确定性"截图"基础设施。

预览截图管线（源文档 3.2 路线 2）的最小实现：配置 → 渲染 → PPM 文件，
供提案预览与像素 diff 使用。图像 = 二维数组 of (r, g, b)。
"""


def blank(w: int, h: int, rgb=(250, 250, 250)) -> list:
    return [[rgb for _ in range(w)] for _ in range(h)]


def size(img: list) -> tuple:
    return len(img[0]), len(img)


def draw_rect(img: list, x: int, y: int, w: int, h: int, rgb: tuple):
    """绘制实心矩形；越界自动裁剪（组件超画布不报错，渲染层容错）。"""
    W, H = size(img)
    for row in range(max(0, y), min(H, y + h)):
        for col in range(max(0, x), min(W, x + w)):
            img[row][col] = rgb


def write_ppm(path, img: list):
    W, H = size(img)
    lines = ["P3", f"{W} {H}", "255"]
    for row in img:
        lines.append(" ".join(f"{c} {g} {b}" for c, g, b in row))
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(lines) + "\n")


def read_ppm(path) -> list:
    with open(path, encoding="ascii") as f:
        tokens = f.read().split()
    assert tokens[0] == "P3", "仅支持 P3 文本 PPM"
    w, h = int(tokens[1]), int(tokens[2])
    assert int(tokens[3]) == 255
    vals = [int(t) for t in tokens[4:]]
    px = [tuple(vals[i:i + 3]) for i in range(0, len(vals), 3)]
    return [px[r * w:(r + 1) * w] for r in range(h)]
