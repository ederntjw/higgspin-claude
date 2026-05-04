"""Higgsfield model routing — May 2026, middle-cost tier.

Maps logical aesthetic_types and pipeline lanes → live Higgsfield model
slugs. Slugs follow the platform's `{vendor}/{model}[/{variant}]` convention
used at POST https://platform.higgsfield.ai/{model_id}.

Validated against the live model gallery on 2026-05-04.
"""

AESTHETIC_TO_MODEL = {
    "fashion":        "google/nano-banana-pro",
    "portrait":       "google/nano-banana-pro",
    "lifestyle":      "google/nano-banana-pro",
    "product":        "google/nano-banana-pro",
    "cinematic":      "black-forest-labs/flux-2",
    "architectural":  "black-forest-labs/flux-2",
    "atmospheric":    "black-forest-labs/flux-2",
    "typography":     "openai/gpt-image",
    "poster":         "openai/gpt-image",
    "illustration":   "bytedance/seedream/v5/lite",
    "stylized":       "bytedance/seedream/v5/lite",
    "brand_palette":  "higgsfield-ai/soul/hex",
}

LANE_TO_MODEL = {
    "t2i_middle":          "google/nano-banana-pro",
    "i2i_product_middle":  "black-forest-labs/flux/kontext",
    "i2i_product_cheap":   "higgsfield-ai/soul/inpaint",
    "i2v_middle":          "bytedance/seedance/v2/fast",
    "i2v_alt_middle":      "higgsfield-ai/dop/turbo",
    "t2v_premium":         "openai/sora-2",
    "t2v_premium_alt":     "google/veo-3.1",
}

# Cascade: when the primary lane model fails, try these in order.
# Both i2v lanes lead with Seedance v2/fast — best product/label consistency in
# 2026 video models. Override by editing this map directly.
LANE_CASCADE = {
    "i2i_product_middle": ["black-forest-labs/flux/kontext", "google/nano-banana-pro", "higgsfield-ai/soul/inpaint"],
    "t2i_middle":         ["google/nano-banana-pro", "black-forest-labs/flux-2"],
    "i2v_middle":         ["bytedance/seedance/v2/fast", "kling-video/v2.1/pro/image-to-video", "higgsfield-ai/dop/turbo"],
    "i2v_product_lock":   ["bytedance/seedance/v2/fast", "kling-video/v2.1/pro/image-to-video", "higgsfield-ai/dop/turbo"],
}


def resolve(lane: str, *, fallback: int = 0) -> str:
    """Resolve a lane name to a model slug. fallback=0 returns primary,
    fallback=1 returns first cascade alternative, etc."""
    cascade = LANE_CASCADE.get(lane, [LANE_TO_MODEL.get(lane)])
    if fallback < 0 or fallback >= len(cascade) or cascade[fallback] is None:
        raise KeyError(f"No fallback {fallback} for lane {lane}")
    return cascade[fallback]
