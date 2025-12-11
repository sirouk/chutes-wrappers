# The following is an example chute deployment `zai-org/GLM-4.6` for the GLM-4.6 model from: https://chutes.ai/app/chute/e75f8264-bd20-5a30-a577-29eb8a77e85a?tab=source

import os
from chutes.chute import NodeSelector
from chutes.chute.template.sglang import build_sglang_chute

# speed up hf download
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

chute = build_sglang_chute(
    username="chutes",
    readme="zai-org/GLM-4.6",
    model_name="zai-org/GLM-4.6",
    image="chutes/sglang:nightly-2025112601",
    concurrency=32,
    revision="be72194883d968d7923a07e2f61681ea9a2826d1",
    node_selector=NodeSelector(
        gpu_count=8,
        include=["h200"],
    ),
    engine_args=(
        "--cuda-graph-max-bs 32 "
        "--tool-call-parser glm45 "
        "--reasoning-parser glm45"
    ),
)
