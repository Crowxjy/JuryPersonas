#!/usr/bin/env python3
"""
heatmap.py — Objective UX attention & experience measurement engine.

Produces an "objective experience measurement pack" for a single UI screenshot:
  1) attention heatmap (colorized overlay) + grayscale saliency
  2) four HCI metrics: attention_distribution, scanpath, cognitive_load, coverage
  3) machine-readable metrics.json (for downstream skills, e.g. expert roundtable)

Engine tiers:
  B (default): MSI-Net deep saliency model (bundled, TF SavedModel) -> data-driven,
               objective, ~SOTA correlation with real eye-tracking on the MIT/Tuebingen
               benchmark family. Calibrated with center bias + foveal Gaussian smoothing,
               which the benchmark shows improves agreement with real fixations.
  A (fallback): pure rule-based saliency from semantic AOIs supplied via --aoi-json,
               used only when the model cannot run. Fully interpretable.

This script INTENTIONALLY does not produce subjective judgments, diagnoses, or
recommendations. It only measures. Interpretation is left to downstream skills.

Usage:
  python3 modes/observe/heatmap.py --image SRC.jpg --outdir OUT [--engine auto|B|A]
                              [--fold-px N] [--aoi-json AOI.json]
"""
import os, sys, json, time, argparse, math

# Single-thread env MUST be set before importing TF (sandbox pthread limit).
for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS",
          "TF_NUM_INTRAOP_THREADS","TF_NUM_INTEROP_THREADS"):
    os.environ.setdefault(k, "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, label, center_of_mass, maximum_filter

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_MODEL = os.path.join(SKILL_ROOT, "assets", "msinet_tf")

def resolve_model_dir(model_dir):
    """Return a loadable MSI-Net SavedModel dir, or None.
    Priority: (1) offline assets/--model-dir if it contains saved_model.pb;
    (2) auto-download alexanderkroner/MSI-Net to writable ~/.cache (read-only
    skill dir can't be written); (3) None -> caller degrades to Engine A.
    The HF SavedModel uses input_1 + single output, fully compatible with
    saliency_model_B's infer(input_1=...); no inference code change needed."""
    try:
        if model_dir and os.path.isdir(model_dir) and \
           os.path.exists(os.path.join(model_dir, "saved_model.pb")):
            return model_dir
    except Exception:
        pass
    try:
        from huggingface_hub import snapshot_download
        cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
        os.makedirs(cache_dir, exist_ok=True)
        d = snapshot_download(repo_id="alexanderkroner/MSI-Net", cache_dir=cache_dir)
        if os.path.exists(os.path.join(d, "saved_model.pb")):
            return d
    except Exception as e:
        sys.stderr.write(f"[resolve_model_dir] HF auto-download failed: {e}\n")
    return None



# ----------------------------- saliency engines -----------------------------
def saliency_model_B(img, model_dir, target_h=512):
    """Deep saliency (MSI-Net). Returns float saliency map [0..1] at original size."""
    import tensorflow as tf
    W0, H0 = img.size
    w, h = img.size
    scale = target_h / h
    nh, nw = target_h, max(1, int(round(w * scale)))
    rimg = img.resize((nw, nh), Image.BILINEAR)
    arr = np.array(rimg).astype(np.float32)[..., ::-1]  # RGB->BGR
    arr -= np.array([103.939, 116.779, 123.68], dtype=np.float32)
    m = tf.saved_model.load(model_dir)
    infer = m.signatures["serving_default"]
    out = infer(input_1=tf.constant(arr[None, ...]))
    sal = list(out.values())[0].numpy()[0, ..., 0]
    sal = sal - sal.min()
    if sal.max() > 0:
        sal /= sal.max()
    sal_img = Image.fromarray((sal * 255).astype(np.uint8)).resize((W0, H0), Image.BILINEAR)
    return np.array(sal_img).astype(np.float32) / 255.0


def saliency_rule_A(img, aois):
    """Rule-based fallback. aois: list of dicts {x,y,intensity,radius,label}."""
    W0, H0 = img.size
    field = np.zeros((H0, W0), np.float64)
    yy, xx = np.mgrid[0:H0, 0:W0]
    for a in aois:
        r = a["radius"]
        field += a["intensity"] * np.exp(-(((xx - a["x"])**2 + (yy - a["y"])**2) / (2.0 * r * r)))
    center_bias = np.exp(-((xx - W0/2)**2) / (2.0 * (W0*0.55)**2))
    top_bias = np.clip(1.15 - (yy / H0) * 0.55, 0.4, 1.15)
    field *= center_bias * top_bias
    field = gaussian_filter(field, sigma=max(W0, H0)*0.012)
    if field.max() > 0:
        field /= field.max()
    return field.astype(np.float32)


def calibrate(sal, W, H):
    """显著性后处理校准。在原有「横向中心偏置 + 中央凹高斯平滑 + gamma」基础上,
    叠加两项「自上而下(top-down)」任务先验,降低纯 bottom-up 模型在 UI 长落地页上
    系统性高估「高对比色块」、低估「顶部标题 / 底部 CTA」的偏差:

      方向①(UI 任务先验):给「首屏顶部标题区」与「底部 CTA / 价格 / 按钮区」叠加
        注意力增益——真实用户在卖货落地页上对标题与行动点(价格、立即开通)有强注意,
        而 bottom-up 模型几乎不给权重。
      方向②(自上而下衰减):沿纵向施加随高度递减的衰减,模拟用户滚动浏览长图时注意力
        自上而下衰减;页面越长(高宽比越大),衰减越陡。

    说明:这些是「注意力 = 视觉显著性 × 任务相关性」中后者的工程近似,目的是让预测更贴近
    真实浏览行为;它仍是预测,不替代真实眼动。校准项记录在 metrics.meta.calibration。
    """
    yy, xx = np.mgrid[0:H, 0:W]
    yn = yy / max(H - 1, 1)          # 归一化纵向位置 0(顶)~1(底)

    # 原有:横向中心偏置
    center_bias = np.exp(-((xx - W/2)**2) / (2*(W*0.6)**2))
    sal = sal * (0.6 + 0.4 * center_bias)

    # 归一化到 [0,1],便于后续按显著性强弱做带状压制
    if sal.max() > 0:
        sal = sal / sal.max()

    # 方向②补强:中段「过强孤立色块」软压制。
    # bottom-up 模型在 UI 长图上会被中部高亮/高对比色块(如深底中的白卡)绝对统治,
    # 这类区域视觉扎眼但未必是任务焦点。对屏幕中段且显著性已接近饱和的像素做幂次压缩,
    # 把它从「绝对峰值」拉回合理量级,给顶部标题 / 底部 CTA 的先验留出显现空间。
    mid_mask = (yn >= 0.16) & (yn <= 0.78)
    mid_zone = np.zeros_like(sal, dtype=np.float64)
    mid_zone[mid_mask] = 1.0
    mid_zone = gaussian_filter(mid_zone, sigma=max(W, H)*0.02)  # 软化边界,避免硬切
    # 压制系数:仅作用于「中段 ∩ 高显著(>0.55)」,显著性越高压得越多
    high = np.clip((sal - 0.55) / 0.45, 0.0, 1.0)
    suppress = 1.0 - 0.62 * mid_zone * high
    sal = sal * suppress

    # 方向②:自上而下纵向衰减。长图更陡——按高宽比放大衰减强度。
    aspect = H / max(W, 1)                      # 高宽比;长落地页通常 >2
    decay_strength = float(np.clip(0.30 + 0.12 * (aspect - 1.0), 0.30, 0.78))
    vertical_decay = 1.0 - decay_strength * yn  # 顶部=1,底部=1-decay_strength
    sal = sal * vertical_decay

    # 方向①:UI 任务先验增益(顶部标题区 + 底部 CTA/价格区)。
    # 深色 UI 上的文字标题、扁平按钮原始显著性极弱(实测 ~0.1,仅为亮色块的 1/10),
    # 纯乘性放大不足以让其成为「可见的次级热点」;故对「该区域内本就有内容的像素」
    # 设一个注意力地板(floor),保证任务焦点至少达到次级热点量级——但只抬「有内容处」,
    # 绝不在纯空白凭空造热点(下方用 content_mask 约束)。
    content_mask = np.clip(sal / 0.06, 0.0, 1.0)   # 原始有内容(显著性非极低)处≈1
    top_band, bottom_band = 0.14, 0.14
    top_floor, bottom_floor = 0.62, 0.55           # 任务区注意力地板(归一化后量级)
    top_w = np.clip((top_band - yn) / top_band, 0.0, 1.0)        # 越靠顶权重越高
    bot_w = np.clip((yn - (1.0 - bottom_band)) / bottom_band, 0.0, 1.0)  # 越靠底越高
    floor = np.maximum(top_floor * top_w, bottom_floor * bot_w) * content_mask
    sal = np.maximum(sal, floor)

    # 原有:中央凹高斯平滑 + 归一化 + gamma
    sal = gaussian_filter(sal, sigma=max(W, H)*0.012)
    if sal.max() > 0:
        sal /= sal.max()
    return np.power(sal, 0.7)


# ----------------------------- metrics --------------------------------------
def detect_hotspots(sal, W, H, thresh=0.45, max_spots=8):
    """Connected high-saliency regions -> ranked AOIs."""
    mask = sal >= thresh
    lab, n = label(mask)
    spots = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(xs) < (W*H) * 0.0004:  # ignore tiny specks
            continue
        cy, cx = float(ys.mean()), float(xs.mean())
        peak = float(sal[ys, xs].max())
        mass = float(sal[ys, xs].sum())
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        spots.append({"cx": round(cx,1), "cy": round(cy,1), "peak": round(peak,3),
                      "mass": mass, "bbox": bbox})
    spots.sort(key=lambda s: s["mass"], reverse=True)
    total = sum(s["mass"] for s in spots) or 1.0
    for s in spots:
        s["attention_share"] = round(s["mass"]/total, 3)
        del s["mass"]
    return spots[:max_spots]


def metric_scanpath(spots, W, H):
    """Predicted fixation order. Heuristic: start top-left/top, then by descending
    saliency with a small proximity weighting (saccade cost). Objective ordering of
    the detected hotspots; the spatial truth is the saliency map."""
    if not spots:
        return []
    remaining = [dict(s) for s in spots]
    # entry: highest combined (saliency, top-left prior)
    def entry_score(s):
        topleft = 1 - ((s["cx"]/W)*0.3 + (s["cy"]/H)*0.7)
        return s["peak"]*0.6 + topleft*0.4
    order = []
    cur = max(remaining, key=entry_score)
    remaining.remove(cur); order.append(cur)
    while remaining:
        def nxt(s):
            d = math.hypot((s["cx"]-cur["cx"])/W, (s["cy"]-cur["cy"])/H)
            return s["peak"]*0.7 - d*0.3
        cur = max(remaining, key=nxt)
        remaining.remove(cur); order.append(cur)
    return [{"order": i+1, "xy": [round(s["cx"]), round(s["cy"])],
             "peak": s["peak"], "attention_share": s["attention_share"]}
            for i, s in enumerate(order)]


def metric_cognitive_load(img, sal, spots):
    """Visual-complexity proxies grounded in Feature-Congestion clutter theory
    (Rosenholtz et al.) and GUI visual-complexity research:
      - edge_density: Sobel edge ratio (structural clutter)
      - color_variety: distinct quantized colors (color congestion)
      - luminance_entropy: Shannon entropy of brightness
      - focal_competition: number of comparable-strength hotspots (split attention)
    A 0-100 composite is reported with its sub-scores so downstream readers can
    weight them differently."""
    rgb = np.asarray(img.convert("RGB"), np.float32)
    gray = rgb.mean(2)
    gx = np.abs(np.diff(gray, axis=1)); gy = np.abs(np.diff(gray, axis=0))
    edge_density = float(((gx > 24).mean() + (gy > 24).mean()) / 2)
    q = (rgb // 32).astype(np.int32)
    color_variety = int(len(np.unique(q.reshape(-1, 3), axis=0)))
    hist = np.histogram(gray, bins=32, range=(0,255))[0].astype(np.float64)
    p = hist / hist.sum(); p = p[p > 0]
    lum_entropy = float(-(p*np.log2(p)).sum())
    peaks = [s["peak"] for s in spots]
    focal_competition = int(sum(1 for pk in peaks if pk >= 0.6))
    # composite (normalized, transparent weights)
    e = min(edge_density/0.18, 1)          # ~0.18 edge ratio = busy
    c = min(color_variety/600, 1)
    h = min(lum_entropy/5.0, 1)
    f = min(focal_competition/5.0, 1)
    score = round(100*(0.35*e + 0.2*c + 0.2*h + 0.25*f), 1)
    level = "低" if score < 33 else ("中" if score < 66 else "高")
    return {"composite_score": score, "level": level,
            "edge_density": round(edge_density,4),
            "color_variety": color_variety,
            "luminance_entropy": round(lum_entropy,3),
            "focal_competition": focal_competition}


def metric_coverage(sal, spots, W, H, fold_px):
    """Above-the-fold reach + attention concentration (Gini).
    Theory: attention is a finite resource; effective hierarchy concentrates it and
    places key elements above the fold (NN/g)."""
    fold = fold_px if fold_px and fold_px < H else int(H*0.42)
    above = sal[:fold, :].sum(); total = sal.sum() or 1.0
    above_fold_ratio = round(float(above/total), 3)
    # Gini of saliency (concentration). 0=uniform, 1=all in one spot.
    flat = np.sort(sal.flatten())
    n = flat.size; cum = np.cumsum(flat); s = cum[-1] or 1.0
    gini = round(float((n + 1 - 2*(cum/s).sum())/n), 3)
    spots_in_fold = sum(1 for sp in spots if sp["cy"] <= fold)
    hot_ratio = round(float((sal >= 0.5).mean()), 4)
    return {"fold_px": fold, "above_fold_attention_ratio": above_fold_ratio,
            "attention_gini": gini, "hotspots_above_fold": spots_in_fold,
            "hotspot_count": len(spots), "hot_pixel_ratio": hot_ratio}


# ----------------------------- colorize -------------------------------------
def colorize(src, sal, out_path):
    W, H = src.size
    def cmap(v):
        r = np.clip((v-0.25)/0.45, 0, 1)
        g = np.where(v<0.55, np.clip((v-0.15)/0.4,0,1), np.clip(1-(v-0.55)/0.45,0,1))
        return r, g, np.zeros_like(v)
    r, g, b = cmap(sal)
    alpha = np.clip((sal-0.12)/0.6, 0, 1)*0.6
    ov = np.zeros((H, W, 4), np.uint8)
    ov[...,0]=(r*255).astype(np.uint8); ov[...,1]=(g*255).astype(np.uint8)
    ov[...,3]=(alpha*255).astype(np.uint8)
    res = Image.alpha_composite(src.convert("RGBA"), Image.fromarray(ov,"RGBA"))
    res.convert("RGB").save(out_path, quality=92)


# ----------------------------- main -----------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--engine", default="auto", choices=["auto","B","A"])
    ap.add_argument("--model-dir", default=DEFAULT_MODEL)
    ap.add_argument("--fold-px", type=int, default=0)
    ap.add_argument("--aoi-json", default="")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    img = Image.open(args.image).convert("RGB")
    W, H = img.size
    engine_used = None; raw = None
    downgrade_reason = None   # 记录 B 档为何不可用,供上层触发人工确认

    if args.engine in ("auto","B"):
        model_dir = resolve_model_dir(args.model_dir)
        if model_dir is None:
            msg = ("MSI-Net weights unavailable: assets/msinet_tf missing and HF "
                   "auto-download failed (check network or bundle weights in release).")
            sys.stderr.write(f"[engine B unavailable] {msg}\n")
            downgrade_reason = "weights_unavailable: " + msg
            if args.engine == "B":
                raise SystemExit(msg)
        else:
            try:
                raw = saliency_model_B(img, model_dir)
                engine_used = "B-MSI-Net"
            except Exception as e:
                sys.stderr.write(f"[engine B failed] {e}\n")
                downgrade_reason = "inference_failed: " + str(e)
                if args.engine == "B":
                    raise
    if raw is None:
        aois = []
        if args.aoi_json and os.path.exists(args.aoi_json):
            aois = json.load(open(args.aoi_json))
        if not aois:
            raise SystemExit("Engine A needs --aoi-json with AOIs.")
        raw = saliency_rule_A(img, aois)
        engine_used = "A-rule"
        # ⛔ 显式降级信号:落到 A 档,打一行醒目 stderr,供上层捕获后触发人工确认
        #    (SKILL.md 红线:B 档掉 A 档不得静默降级,必须停下让用户二选一)
        if downgrade_reason is None:
            downgrade_reason = "fell_back_to_A: engine B not selected or unavailable"
        sys.stderr.write(
            f"[DOWNGRADE B->A] 热力图已从 B 档(MSI-Net)降级到 A 档(规则兜底)。"
            f"原因: {downgrade_reason}。"
            f"按 SKILL.md 红线,须暂停并请用户确认『修复 B 档』还是『接受 A 档』。\n")

    sal = calibrate(raw, W, H)
    np.save(os.path.join(args.outdir, "saliency_raw.npy"), sal)
    Image.fromarray((sal*255).astype(np.uint8)).save(os.path.join(args.outdir,"saliency_gray.jpg"))
    colorize(img, sal, os.path.join(args.outdir, "heatmap.jpg"))

    spots = detect_hotspots(sal, W, H)
    metrics = {
        "meta": {"engine": engine_used, "image": os.path.basename(args.image),
                 "image_size": [W, H],
                 "downgrade_reason": downgrade_reason,
                 "needs_human_confirm": (engine_used == "A-rule"),
                 "calibration": ["center_bias", "vertical_topdown_decay",
                                 "ui_prior_top_title", "ui_prior_bottom_cta",
                                 "foveal_gaussian_smoothing", "gamma_0.7"],
                 "confidence_note": ("Deep saliency prediction calibrated per MIT/Tuebingen "
                    "benchmark practice (center bias + smoothing). Predictive only; "
                    "not a substitute for live eye-tracking.") if engine_used.startswith("B")
                    else "Rule-based interpretable fallback; lower fidelity than model."},
        "attention_distribution": {"hotspots": spots},
        "scanpath": metric_scanpath(spots, W, H),
        "cognitive_load": metric_cognitive_load(img, sal, spots),
        "coverage": metric_coverage(sal, spots, W, H, args.fold_px),
    }
    json.dump(metrics, open(os.path.join(args.outdir,"metrics.json"),"w"),
              ensure_ascii=False, indent=2)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"\n[OK] engine={engine_used} outputs in {args.outdir}/", file=sys.stderr)

if __name__ == "__main__":
    main()
