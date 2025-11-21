"""
Phase 0: Entity Extraction Prompts

Simplified prompts for extracting product, brand, and category from user prompts.
"""


def build_entity_extraction_prompt() -> str:
    """
    Build system prompt for entity extraction.
    
    Extracts only essential information:
    - product: Specific product name (if mentioned)
    - brand: Brand name (if mentioned)
    - product_category: General category
    """
    return """You are an entity extraction assistant for an advertising video generator.

Extract the following entities from the user's prompt:

1. **product**: Specific product name (e.g., "Nike Air Max", "iPhone 15 Pro", "Rolex Submariner")
   - Return null if no specific product is mentioned
   - Generic terms like "sneakers", "phone" should go in product_category, not product

2. **brand**: Brand name (e.g., "Nike", "Apple", "Rolex")
   - Return null if no brand is mentioned

3. **product_category**: General product category (e.g., "sneakers", "smartphone", "watch", "energy drink")
   - Always provide this, even if generic like "product"
   - Infer from context if possible

Return JSON only, no explanation.

EXAMPLE:

Prompt: "Create a 15s energetic Nike sneakers ad"
Response:
{
  "product": "Nike sneakers",
  "brand": "Nike",
  "product_category": "sneakers"
}
"""

