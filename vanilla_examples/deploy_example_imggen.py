import uuid
import random
from io import BytesIO
from loguru import logger
from PIL import Image
from enum import Enum
from chutes.chute import Chute
from chutes.chute import NodeSelector
from chutes.image import Image as ChuteImage
from fastapi import Response, status, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
import os

# speed up hf download
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

image = (
    ChuteImage(username="chutes", name="hidream", tag="0.1.0", readme="HiDream-I1")
    .from_base("parachutes/python:3.12")
    .run_command(
        "git clone https://github.com/HiDream-ai/HiDream-I1"
    )
    .run_command("pip install -r HiDream-I1/requirements.txt 'torch<2.7' transformers==4.47.1 accelerate safetensors xformers protobuf sentencepiece")
    .run_command("pip install flash-attn==2.7.4.post1 --no-build-isolation")
    .with_env("PYTHONPATH", "/app/HiDream-I1")
)

chute = Chute(
    username="chutes",
    name="hidream",
    readme="HiDream-I1",
    image=image,
    node_selector=NodeSelector(
        gpu_count=1,
        min_vram_gb_per_gpu=80,
        include=["h100", "h800", "h100_sxm", "h200"],
    ),
    concurrency=1,
)

MODELS = {
    "text": {
        "model": "unsloth/Meta-Llama-3.1-8B-Instruct",
        "revision": "a2856192dd7c25b842431f39c179a6c2c2f627d1",
    },
    "image": {
        "model": "HiDream-ai/HiDream-I1-Full",
        "revision": "61848b939643432548f1a59d4e581af54f04356e",
    },
}


class GenerationInput(BaseModel):
    prompt: str
    resolution: Optional[Literal[
        "1024x1024",
        "768x1360",
        "1360x768",
        "880x1168",
        "1168x880",
        "1248x832",
        "832x1248",
    ]] = "1024x1024"
    seed: Optional[int] = Field(None, ge=0, le=100000000)
    guidance_scale: Optional[float] = Field(5.0, ge=0.0, le=10.0)
    num_inference_steps: Optional[int] = Field(50, ge=5, le=75)


@chute.on_startup()
async def initialize_pipeline(self):
    from hi_diffusers import HiDreamImagePipeline
    from hi_diffusers import HiDreamImageTransformer2DModel
    from hi_diffusers.schedulers.fm_solvers_unipc import FlowUniPCMultistepScheduler
    from hi_diffusers.schedulers.flash_flow_match import FlashFlowMatchEulerDiscreteScheduler
    from transformers import LlamaForCausalLM, PreTrainedTokenizerFast
    from huggingface_hub import snapshot_download
    import torch

    for key, model_info in MODELS.items():
        logger.info(f"Ensuring {model_info['model']} revision {model_info['revision']} is downloaded...")
        snapshot_download(model_info["model"], revision=model_info["revision"])

    # Text encoder 4 aka llama 8b.
    logger.info(f"Loading text model...")
    tokenizer_4 = PreTrainedTokenizerFast.from_pretrained(MODELS["text"]["model"], revision=MODELS["text"]["revision"])
    text_encoder_4 = LlamaForCausalLM.from_pretrained(
        MODELS["text"]["model"],
        revision=MODELS["text"]["revision"],
        output_hidden_states=True,
        output_attentions=True,
        attn_implementation="flash_attention_2",
        torch_dtype=torch.bfloat16
    ).to("cuda")

    # Image model.
    scheduler = FlowUniPCMultistepScheduler(num_train_timesteps=1000, shift=3.0, use_dynamic_shifting=False)
    transformer = HiDreamImageTransformer2DModel.from_pretrained(
        MODELS["image"]["model"],
        revision=MODELS["image"]["revision"],
        subfolder="transformer",
        torch_dtype=torch.bfloat16
    ).to("cuda")
    pipe = HiDreamImagePipeline.from_pretrained(
        MODELS["image"]["model"],
        scheduler=scheduler,
        tokenizer_4=tokenizer_4,
        text_encoder_4=text_encoder_4,
        torch_dtype=torch.bfloat16
    ).to("cuda", torch.bfloat16)
    pipe.transformer = transformer
    self.pipe = pipe
    self.torch = torch


@chute.cord(
    public_api_path="/generate",
    method="POST",
    input_schema=GenerationInput,
)
async def generate(self, args: GenerationInput):
    """
    Generate an image.
    """
    with self.torch.no_grad():
        height, width = map(int, args.resolution.split("x"))
        if not args.seed:
            args.seed = random.randint(0, 1000000)
        generator = self.torch.Generator("cuda").manual_seed(args.seed)
    image = self.pipe(
        args.prompt,
        height=height,
        width=width,
        guidance_scale=args.guidance_scale,
        num_inference_steps=args.num_inference_steps,
        num_images_per_prompt=1,
        generator=generator
    ).images[0]
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="image/jpeg",
        headers={"Content-Disposition": f'attachment; filename="{uuid.uuid4()}.jpg"'},
    )
