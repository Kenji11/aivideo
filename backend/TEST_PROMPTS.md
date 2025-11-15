# Test Prompts for Video Generation

## Quick Test Prompts (Simple)

### 1. Product Showcase - Luxury Watch
```
Create a luxury product showcase video for premium sunglasses with modern style, vibrant colors, and bright lighting
```

### 2. Lifestyle Ad - Athletic Shoes
```
Create a lifestyle advertisement video for running shoes featuring active people, energetic mood, and dynamic camera movements
```

### 3. Announcement - Product Launch
```
Create an announcement video for a new tech product launch with minimalist design, clean aesthetics, and professional tone
```

## Detailed Test Prompts (Complex)

### 4. Luxury Product - Premium Watch
```
Create a luxury product showcase video for a premium Swiss watch. The video should have an elegant, sophisticated aesthetic with gold and black color palette. Show the watch in various settings - close-up details, on a wrist, in a luxury setting. Use dramatic soft lighting and smooth camera movements. The mood should be refined and timeless.
```

### 5. Lifestyle Ad - Fitness Equipment
```
Create a lifestyle advertisement video for premium fitness equipment. Show people using the equipment in a modern gym setting. Use vibrant colors like blue, green, and orange. The mood should be energetic and motivating. Include dynamic shots with camera movements like tracking and panning. Use bright natural lighting to create an inspiring atmosphere.
```

### 6. Tech Product - Smartphone
```
Create a product showcase video for a new smartphone. Use a modern, sleek aesthetic with minimalist design. Color palette should be neutral - grays, whites, and subtle blues. Show the phone from multiple angles with smooth transitions. Use soft diffused lighting. The mood should be calm and professional, highlighting the phone's premium features.
```

### 7. Fashion - Clothing Brand
```
Create a lifestyle advertisement video for a sustainable fashion brand. Show models wearing the clothing in natural outdoor settings. Use earthy tones and organic colors. The aesthetic should be modern and eco-conscious. Include shots of nature, people walking, and lifestyle moments. Use bright natural lighting with a peaceful, inspiring mood.
```

### 8. Food & Beverage - Coffee Brand
```
Create a product showcase video for a premium coffee brand. Show the coffee beans, brewing process, and final cup. Use warm, inviting colors like browns, creams, and golds. The aesthetic should be artisanal and cozy. Include close-up shots of coffee preparation. Use warm, soft lighting. The mood should be comforting and sophisticated.
```

### 9. Beauty Product - Skincare
```
Create a luxury product showcase video for high-end skincare products. Show the products in an elegant bathroom or spa setting. Use clean, fresh colors - whites, soft pinks, and light blues. The aesthetic should be minimalist and luxurious. Include smooth, slow camera movements. Use soft, diffused lighting. The mood should be calm, rejuvenating, and premium.
```

### 10. Automotive - Electric Vehicle
```
Create a lifestyle advertisement video for an electric vehicle. Show the car in urban and natural settings. Use modern, futuristic colors - silver, blue, and white. The aesthetic should be sleek and innovative. Include dynamic driving shots and close-ups of features. Use bright, natural lighting. The mood should be forward-thinking and exciting.
```

## Edge Cases & Stress Tests

### 11. Very Short Prompt
```
Luxury watch video
```

### 12. Very Long Prompt
```
Create a comprehensive product showcase video for a premium luxury timepiece that combines traditional Swiss craftsmanship with modern design innovation. The video should feature an elegant and sophisticated aesthetic with a refined color palette consisting of deep gold, rich black, and pristine white tones. Showcase the watch in multiple luxurious settings including a high-end jewelry store, a formal event, and an executive office. The mood should be timeless, refined, and prestigious. Use dramatic soft lighting with subtle shadows to highlight the intricate details of the watch face, the precision of the movement, and the quality of the leather strap. Include various camera angles such as extreme close-ups of the watch mechanism, medium shots of the watch on a wrist, and wide establishing shots of the luxury environments. The camera movements should be smooth and deliberate, using slow tracking shots and gentle pans to create a sense of elegance and sophistication. The overall atmosphere should convey exclusivity, craftsmanship, and timeless luxury.
```

### 13. Multiple Products
```
Create a lifestyle video showcasing a complete home fitness setup including dumbbells, yoga mat, and resistance bands. Show people using all the equipment in a modern home gym. Use vibrant, energetic colors and dynamic camera movements.
```

### 14. Abstract/Conceptual
```
Create an inspirational video about sustainable living. Show nature scenes, renewable energy, and eco-friendly practices. Use organic, earthy colors with a peaceful, hopeful mood.
```

### 15. Event/Announcement
```
Create an announcement video for a music festival launch. Use bold, vibrant colors and energetic mood. Include dynamic shots of crowds, stages, and performers. Make it exciting and engaging.
```

## Template-Specific Prompts

### Product Showcase Template
```
Create a product showcase video for premium wireless headphones. Show the headphones from all angles with smooth transitions. Use modern, sleek design with black and silver colors. Professional lighting and elegant mood.
```

### Lifestyle Ad Template
```
Create a lifestyle advertisement for organic tea products. Show people enjoying tea in cozy, natural settings. Use warm, earthy colors. Peaceful mood with soft natural lighting.
```

### Announcement Template
```
Create an announcement video for a new mobile app launch. Use minimalist design with blue and white colors. Clean, modern aesthetic. Professional and exciting mood.
```

## Performance Test Prompts

### 16. Minimal Details
```
Product video for sunglasses
```

### 17. Maximum Details
```
Create an ultra-detailed luxury product showcase video for a handcrafted leather briefcase. The video must feature a sophisticated, artisanal aesthetic with rich browns, deep blacks, and warm gold accents. Show the briefcase in multiple professional settings: a luxury office, a business meeting, and an executive travel scene. The mood should be prestigious, professional, and timeless. Use dramatic, cinematic lighting with soft shadows to highlight the texture of the leather, the precision of the stitching, and the quality of the hardware. Include extreme close-ups of the leather grain, medium shots of the briefcase being used, and wide establishing shots of the luxury environments. Camera movements should be slow and deliberate: smooth tracking shots following the briefcase, gentle pans across details, and steady close-ups. Include shots of the interior compartments, the lock mechanism, and the handle. The overall atmosphere must convey craftsmanship, luxury, and professional excellence. The color grading should enhance the warm tones of the leather and create depth. Transitions between shots should be smooth and elegant. The pacing should be deliberate and sophisticated, allowing viewers to appreciate every detail of this premium product.
```

## Recommended Test Sequence

1. **Start Simple**: Use prompt #1 or #2 for initial testing
2. **Test Templates**: Try prompts #16, #17, #18 to test different templates
3. **Test Complexity**: Use prompts #4-10 for detailed scenarios
4. **Edge Cases**: Test prompts #11-15 for robustness
5. **Performance**: Use prompt #17 for stress testing

## Expected Results

- **Phase 1**: Should extract template, style, product info, beats, transitions
- **Phase 2**: Should generate animatic frames (one per beat)
- **Phase 3**: Should generate style guide and product reference images
- **Phase 4**: Should generate video chunks and stitch them together

## Quick Copy-Paste Prompts

```bash
# Simple
"Create a luxury product showcase video for premium sunglasses with modern style, vibrant colors, and bright lighting"

# Medium
"Create a lifestyle advertisement video for running shoes featuring active people, energetic mood, and dynamic camera movements"

# Complex
"Create a luxury product showcase video for a premium Swiss watch. The video should have an elegant, sophisticated aesthetic with gold and black color palette. Show the watch in various settings - close-up details, on a wrist, in a luxury setting. Use dramatic soft lighting and smooth camera movements. The mood should be refined and timeless."
```

