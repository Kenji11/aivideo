# Phase 2 Storyboard Image Generation Models

This document outlines the models used for storyboard image generation in Phase 2, their schemas, parameters, and usage.

## Models Used

Phase 2 uses two models depending on whether reference assets are available:

1. **black-forest-labs/flux-dev** - Standard image generation (no reference assets)
2. **xlabs-ai/flux-dev-controlnet** - ControlNet-guided generation (with product reference assets)

---

## Model 1: FLUX Dev (Standard)

**Replicate Model:** `black-forest-labs/flux-dev`

**Usage:** Used when no product reference assets are available for a beat.

**Cost:** $0.025 per image

### Schema

```python
{
    "prompt": str,                    # Required
    "seed": int,                      # Optional
    "image": uri,                     # Optional
    "go_fast": boolean,               # Optional
    "guidance": number,               # Optional
    "megapixels": string,             # Optional
    "num_outputs": integer,           # Optional
    "aspect_ratio": str,              # Optional
    "output_format": str,             # Optional
    "output_quality": integer,        # Optional
    "prompt_strength": number,        # Optional
    "num_inference_steps": integer,   # Optional
    "disable_safety_checker": boolean # Optional
}
```

### Parameters

| Parameter | Type | Required | Default | Range | Description |
|----------|------|----------|---------|-------|-------------|
| `prompt` | string | ✅ Yes | - | - | Prompt for generated image. Includes beat template, style information, color palette, lighting, aesthetic, and shot type. |
| `seed` | integer | ❌ No | Random | - | Random seed. Set for reproducible generation. |
| `image` | uri | ❌ No | - | - | Input image for image to image mode. The aspect ratio of your output will match this image. **Not currently used in implementation.** |
| `go_fast` | boolean | ❌ No | `true` | - | Run faster predictions with additional optimizations. |
| `guidance` | number | ❌ No | `3.5` | 0.0 - 10.0 | Guidance for generated image. Lower values can give more realistic images. Good values to try are 2, 2.5, 3 and 3.5. |
| `megapixels` | string | ❌ No | `"1"` | - | Approximate number of megapixels for generated image. |
| `num_outputs` | integer | ❌ No | `1` | 1 - 4 | Number of outputs to generate. |
| `aspect_ratio` | string | ❌ No | `"1:1"` | - | Aspect ratio for the generated image. Currently set to `"16:9"` for 1280x720 storyboard images. |
| `output_format` | string | ❌ No | `"webp"` | - | Format of the output images. Currently set to `"png"` for storyboard images. |
| `output_quality` | integer | ❌ No | `80` | 0 - 100 | Quality when saving the output images, from 0 to 100. 100 is best quality, 0 is lowest quality. Not relevant for .png outputs. Currently set to `90` for storyboards. |
| `prompt_strength` | number | ❌ No | `0.8` | 0.0 - 1.0 | Prompt strength when using img2img. 1.0 corresponds to full destruction of information in image. Only used when `image` parameter is provided. |
| `num_inference_steps` | integer | ❌ No | `28` | 1 - 50 | Number of denoising steps. Recommended range is 28-50, and lower number of steps produce lower quality outputs, faster. |
| `disable_safety_checker` | boolean | ❌ No | `false` | - | Disable safety checker for generated images. |

### Example Usage

```python
output = replicate_client.run(
    "black-forest-labs/flux-dev",
    input={
        "prompt": "Cinematic close-up of energy drink, dramatic lighting, professional product photography, modern aesthetic, red and black color palette, cinematic composition, high quality professional photography, 1280x720 aspect ratio, close_up shot framing",
        "aspect_ratio": "16:9",  # Override default "1:1"
        "output_format": "png",  # Override default "webp"
        "output_quality": 90,  # Override default 80
        # Note: go_fast defaults to true, guidance defaults to 3.5, num_inference_steps defaults to 28
    },
    timeout=60
)
```

**Parameters NOT currently used:**
- `seed` - Not set (uses random)
- `image` - Not used (not using image-to-image mode)
- `go_fast` - Uses default `true`
- `guidance` - Uses default `3.5`
- `megapixels` - Uses default `"1"`
- `num_outputs` - Uses default `1`
- `prompt_strength` - Not used (only for img2img mode)
- `num_inference_steps` - Uses default `28`
- `disable_safety_checker` - Uses default `false`

---

## Model 2: FLUX Dev ControlNet

**Replicate Model:** `xlabs-ai/flux-dev-controlnet`

**Usage:** Used when a product reference asset is available for a beat. The reference image is preprocessed using Canny edge detection, and the edges are used to guide generation while maintaining product consistency.

**Cost:** $0.058 per image

**Preprocessing:** The original product image is converted to Canny edges using OpenCV before being passed to the model.

### Schema

```python
{
    "prompt": str,                           # Required
    "control_image": uri,                   # Required
    "control_type": str,                    # Required
    "control_strength": float,              # Required
    "aspect_ratio": str,                    # Optional (used in implementation)
    "seed": int,                            # Optional
    "steps": int,                           # Optional
    "lora_url": str,                        # Optional
    "lora_strength": number,                # Optional
    "output_format": str,                   # Optional
    "guidance_scale": number,               # Optional
    "output_quality": integer,              # Optional
    "negative_prompt": str,                 # Optional
    "depth_preprocessor": str,              # Optional
    "soft_edge_preprocessor": str,          # Optional
    "image_to_image_strength": number,      # Optional
    "return_preprocessed_image": boolean    # Optional
}
```

### Parameters

| Parameter | Type | Required | Default | Range | Description |
|----------|------|----------|---------|-------|-------------|
| `prompt` | string | ✅ Yes | - | - | Text prompt describing the image to generate. Same format as FLUX Dev, but ControlNet uses the control image structure to guide generation. |
| `control_image` | uri | ✅ Yes | - | - | Image to use with control net. Preprocessed edge image (Canny edges) from the product reference. Generated by preprocessing the original product image. |
| `control_type` | string | ✅ Yes | `"depth"` | - | Type of control net. Options: `"canny"`, `"depth"`, `"soft_edge"`. Currently using `"canny"` for edge-based control. |
| `control_strength` | number | ✅ Yes | `0.5` | 0.0 - 3.0 | Strength of control net. Different controls work better with different strengths. Canny works best with 0.5, soft edge works best with 0.4, and depth works best between 0.5 and 0.75. If images are low quality, try reducing the strength and try reducing the guidance scale. Currently set to `0.15` for subtle structure hints. |
| `aspect_ratio` | string | ❌ No | - | - | Aspect ratio for the generated image. Currently set to `"16:9"` for 1280x720 storyboard images. |
| `seed` | integer | ❌ No | Random | - | Set a seed for reproducibility. Random by default. |
| `steps` | integer | ❌ No | `28` | 1 - 50 | Number of inference steps. Higher values produce better quality but take longer. Currently set to `40` for storyboards. |
| `lora_url` | string | ❌ No | - | - | Optional LoRA model to use. Give a URL to a HuggingFace .safetensors file, a Replicate .tar file or a CivitAI download link. |
| `lora_strength` | number | ❌ No | `1` | -1.0 - 3.0 | Strength of LoRA model. |
| `output_format` | string | ❌ No | `"webp"` | - | Format of the output images. Currently set to `"png"` for storyboards. |
| `guidance_scale` | number | ❌ No | `3.5` | 0.0 - 5.0 | Guidance scale for prompt adherence. Higher values make the model follow the prompt more closely. Currently set to `4.0` for better prompt adherence. |
| `output_quality` | integer | ❌ No | `80` | 0 - 100 | Quality of the output images, from 0 to 100. 100 is best quality, 0 is lowest quality. Currently set to `100` (maximum) for ControlNet generations. |
| `negative_prompt` | string | ❌ No | - | - | Things you do not want to see in your image. Default includes: "blurry, low quality, distorted, deformed, ugly, amateur, watermark, text, signature, letters, words, multiple subjects, cluttered, busy, messy, chaotic" |
| `depth_preprocessor` | string | ❌ No | `"DepthAnything"` | - | Preprocessor to use with depth control net. Only used when `control_type` is `"depth"`. |
| `soft_edge_preprocessor` | string | ❌ No | `"HED"` | - | Preprocessor to use with soft edge control net. Only used when `control_type` is `"soft_edge"`. |
| `image_to_image_strength` | number | ❌ No | - | 0.0 - 1.0 | Strength of image to image control. 0 means none of the control image is used. 1 means the control image is returned used as is. Try values between 0 and 0.25 for best results. **Not currently used in implementation.** |
| `return_preprocessed_image` | boolean | ❌ No | `false` | - | Return the preprocessed image used to control the generation process. Useful for debugging. |

### ControlNet Preprocessing

Before calling the model, the product reference image is preprocessed:

1. **Load image** using OpenCV
2. **Convert to grayscale**
3. **Apply Canny edge detection** (thresholds: 100, 200)
4. **Convert to 3-channel** (required by ControlNet)
5. **Save as temporary file** for API call

### Example Usage

```python
# Preprocess product image
control_image_path = controlnet_service.preprocess_for_controlnet(
    product_image_path,
    method="canny"
)

# Generate with ControlNet
with open(control_image_path, 'rb') as control_file:
    output = replicate_client.run(
        "xlabs-ai/flux-dev-controlnet",
        input={
            "prompt": "Cinematic close-up of energy drink, dramatic lighting, professional product photography, modern aesthetic, red and black color palette, cinematic composition, high quality professional photography, 1280x720 aspect ratio, close_up shot framing",
            "control_image": control_file,
            "control_type": "canny",
            "control_strength": 0.15,  # Lower than default 0.5 for more creativity
            "aspect_ratio": "16:9",  # 1280x720 aspect ratio
            "output_format": "png",  # Override default "webp"
            "output_quality": 100,  # Override default 80
            "steps": 40,  # Override default 28
            "guidance_scale": 4.0,  # Override default 3.5
            "negative_prompt": "blurry, low quality, distorted, deformed, ugly, amateur, watermark, text, signature, letters, words, multiple subjects, cluttered, busy, messy, chaotic"
            # Note: image_to_image_strength is NOT used (could be added to reduce reference dominance)
        },
        timeout=120
    )
```

**Parameters NOT currently used:**
- `seed` - Not set (uses random)
- `lora_url` - Not used
- `lora_strength` - Not used
- `depth_preprocessor` - Not used (using canny, not depth)
- `soft_edge_preprocessor` - Not used (using canny, not soft_edge)
- `image_to_image_strength` - **Not used** (could help reduce reference image dominance)
- `return_preprocessed_image` - Not used (set to false)

---

## Decision Logic

ControlNet is used when:
- `reference_mapping` contains the beat_id
- `usage_type == 'product'`
- Asset IDs are available in the mapping
- Product asset exists in database with valid S3 URL

Otherwise, standard FLUX Dev is used.

---

## Notes

- **ControlNet strength** (`control_strength`) is currently set to `0.15` to allow more prompt-driven creativity while maintaining subtle structural consistency. The default is `0.5` (recommended for Canny), but lower values give more creative freedom.
- **Image-to-image strength** (`image_to_image_strength`) is **not currently used**. This parameter allows passing the original reference image (not just edges) with strength 0-1. Recommended values are 0-0.25 for best results. This could be used to further reduce the dominance of the reference image.
- **Control type** is set to `"canny"` for edge-based control. The model also supports `"depth"` and `"soft_edge"` control types with different optimal strength values.
- Both models return a URL to the generated image, which is then downloaded and uploaded to S3.
- Timeout for FLUX Dev: 60 seconds
- Timeout for FLUX Dev ControlNet: 120 seconds (longer due to preprocessing)

