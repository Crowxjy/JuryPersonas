#!/usr/bin/env python3
"""
annotate_issues.py — 单页可理解性走查「页面问题标注」红框图生成器（模块级）。

输入：
  --image SRC.png        原始界面截图（与 Phase A 生成热力图用的同一张原图）
  --semantic SEM.json    Phase A 产出的 semantic.json（含 blocks[].bbox 模块像素包围框）
  --issues ISSUES.json   Phase B 产品专家走查的问题清单（哪些模块有问题）
  --out OUT.png          输出红框标注图路径

职责边界：
  - 坐标（bbox）= Phase A 客观事实；
  - “哪个模块有问题”= Phase B 产品专家判断；
  - 本脚本只把 B 的判断标注到 A 的坐标上，不做任何判断。

颗粒度：模块级（框住 semantic.json 中出问题模块的整框 bbox）。

issues.json 结构（任一形式均可）：
  {"problem_block_ids": [2, 5, 7]}                         # 出问题的模块序号列表
  或
  {"problems": [{"block_id": 2, "label": "①"},            # 可选角标编号
                {"block_id": 5, "label": "②"}]}

semantic.json 需含：
  {"blocks": [{"id": 1, "text": "...", "type": "...", "bbox": [x0,y0,x1,y1]}, ...]}

红框样式：纯红描边、线宽随图自适应（约对角线 0.5%，最小 3px）、可选左上角问题编号角标。
"""
import os, sys, json, argparse


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_problem_map(issues):
    """返回 {block_id(int): label(str|None)}。"""
    pm = {}
    if isinstance(issues, dict):
        if "problems" in issues and isinstance(issues["problems"], list):
            for it in issues["problems"]:
                bid = it.get("block_id")
                if bid is None:
                    continue
                pm[int(bid)] = it.get("label")
        if "problem_block_ids" in issues and isinstance(issues["problem_block_ids"], list):
            for bid in issues["problem_block_ids"]:
                pm.setdefault(int(bid), None)
    elif isinstance(issues, list):
        for bid in issues:
            pm.setdefault(int(bid), None)
    return pm


def find_bbox(blocks, bid):
    for b in blocks:
        try:
            if int(b.get("id")) == int(bid):
                return b.get("bbox")
        except (TypeError, ValueError):
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--semantic", required=True)
    ap.add_argument("--issues", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--color", default="#FF1A1A", help="红框颜色")
    args = ap.parse_args()

    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(args.image).convert("RGB")
    W, H = img.size
    draw = ImageDraw.Draw(img)

    blocks = load_json(args.semantic).get("blocks", [])
    problem_map = build_problem_map(load_json(args.issues))

    if not problem_map:
        # 无问题：原图直出（调用方应据此选择留空/填「—」而非嵌图）
        img.save(args.out)
        print(json.dumps({"ok": True, "drawn": 0, "note": "no problems; passthrough"}, ensure_ascii=False))
        return

    diag = (W ** 2 + H ** 2) ** 0.5
    lw = max(3, int(diag * 0.005))
    pad = max(2, lw)  # 红框略放大，避免压住模块边缘
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", max(14, int(diag * 0.018)))
    except Exception:
        font = ImageFont.load_default()

    drawn, missing = 0, []
    for bid, label in problem_map.items():
        bbox = find_bbox(blocks, bid)
        if not bbox or len(bbox) != 4:
            missing.append(bid)
            continue
        x0, y0, x1, y1 = [int(v) for v in bbox]
        x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
        x1 = min(W, x1 + pad); y1 = min(H, y1 + pad)
        for i in range(lw):
            draw.rectangle([x0 - i, y0 - i, x1 + i, y1 + i], outline=args.color)
        if label:
            tag = str(label)
            tb = draw.textbbox((0, 0), tag, font=font)
            tw, th = tb[2] - tb[0], tb[3] - tb[1]
            bx0, by0 = x0, max(0, y0 - th - 6)
            draw.rectangle([bx0, by0, bx0 + tw + 8, by0 + th + 6], fill=args.color)
            draw.text((bx0 + 4, by0 + 2), tag, fill="#FFFFFF", font=font)
        drawn += 1

    img.save(args.out)
    print(json.dumps({"ok": True, "drawn": drawn, "missing_block_ids": missing,
                      "out": args.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
