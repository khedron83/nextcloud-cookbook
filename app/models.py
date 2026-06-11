from dataclasses import dataclass, field
from typing import Optional
import re


def parse_duration(iso: str) -> int:
    """ISO 8601 duration (e.g. PT1H30M) → total minutes."""
    if not iso:
        return 0
    total = 0
    h = re.search(r'(\d+)H', iso)
    m = re.search(r'(\d+)M', iso)
    s = re.search(r'(\d+)S', iso)
    if h:
        total += int(h.group(1)) * 60
    if m:
        total += int(m.group(1))
    if s:
        total += int(s.group(1)) // 60
    return total


def minutes_to_duration(minutes: int) -> str:
    """Total minutes → ISO 8601 duration."""
    if not minutes:
        return ""
    h, m = divmod(minutes, 60)
    result = "PT"
    if h:
        result += f"{h}H"
    if m:
        result += f"{m}M"
    return result


@dataclass
class RecipeSummary:
    recipe_id: int
    name: str
    keywords: str = ""
    date_modified: str = ""
    category: str = ""


@dataclass
class Nutrition:
    calories: str = ""
    carbohydrate_content: str = ""
    cholesterol_content: str = ""
    fat_content: str = ""
    fiber_content: str = ""
    protein_content: str = ""
    saturated_fat_content: str = ""
    serving_size: str = ""
    sodium_content: str = ""
    sugar_content: str = ""
    trans_fat_content: str = ""
    unsaturated_fat_content: str = ""

    @classmethod
    def from_api(cls, data: dict) -> "Nutrition":
        return cls(
            calories=data.get("calories", ""),
            carbohydrate_content=data.get("carbohydrateContent", ""),
            cholesterol_content=data.get("cholesterolContent", ""),
            fat_content=data.get("fatContent", ""),
            fiber_content=data.get("fiberContent", ""),
            protein_content=data.get("proteinContent", ""),
            saturated_fat_content=data.get("saturatedFatContent", ""),
            serving_size=data.get("servingSize", ""),
            sodium_content=data.get("sodiumContent", ""),
            sugar_content=data.get("sugarContent", ""),
            trans_fat_content=data.get("transFatContent", ""),
            unsaturated_fat_content=data.get("unsaturatedFatContent", ""),
        )

    def to_api(self) -> dict:
        return {
            "@type": "NutritionInformation",
            "calories": self.calories,
            "carbohydrateContent": self.carbohydrate_content,
            "cholesterolContent": self.cholesterol_content,
            "fatContent": self.fat_content,
            "fiberContent": self.fiber_content,
            "proteinContent": self.protein_content,
            "saturatedFatContent": self.saturated_fat_content,
            "servingSize": self.serving_size,
            "sodiumContent": self.sodium_content,
            "sugarContent": self.sugar_content,
            "transFatContent": self.trans_fat_content,
            "unsaturatedFatContent": self.unsaturated_fat_content,
        }


@dataclass
class Recipe:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    url: str = ""
    image: str = ""
    recipe_yield: str = ""
    prep_time: str = ""
    cook_time: str = ""
    total_time: str = ""
    recipe_category: str = ""
    keywords: str = ""
    recipe_ingredient: list[str] = field(default_factory=list)
    recipe_instructions: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    nutrition: Optional[Nutrition] = None
    date_created: str = ""
    date_modified: str = ""
    rating: int = 0

    @classmethod
    def from_api(cls, data: dict) -> "Recipe":
        instructions = []
        for item in data.get("recipeInstructions", []):
            if isinstance(item, str):
                instructions.append(item)
            elif isinstance(item, dict):
                instructions.append(item.get("text", ""))

        tools = data.get("tool", [])
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",") if t.strip()]

        nutrition = None
        if data.get("nutrition"):
            nutrition = Nutrition.from_api(data["nutrition"])

        rating = 0
        agg = data.get("aggregateRating")
        if agg and isinstance(agg, dict):
            try:
                rating = max(0, min(5, round(float(agg.get("ratingValue") or 0))))
            except (ValueError, TypeError):
                pass

        return cls(
            id=data.get("id"),
            name=str(data.get("name", "") or ""),
            description=str(data.get("description", "") or ""),
            url=str(data.get("url", "") or ""),
            image=str(data.get("image", "") or ""),
            recipe_yield=str(data.get("recipeYield", "") or ""),
            prep_time=str(data.get("prepTime", "") or ""),
            cook_time=str(data.get("cookTime", "") or ""),
            total_time=str(data.get("totalTime", "") or ""),
            recipe_category=str(data.get("recipeCategory", "") or ""),
            keywords=str(data.get("keywords", "") or ""),
            recipe_ingredient=data.get("recipeIngredient", []),
            recipe_instructions=instructions,
            tools=tools,
            nutrition=nutrition,
            date_created=data.get("dateCreated", ""),
            date_modified=data.get("dateModified", ""),
            rating=rating,
        )

    def to_api(self) -> dict:
        data: dict = {
            "@context": "http://schema.org",
            "@type": "Recipe",
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "image": self.image or "",
            "recipeYield": self.recipe_yield,
            "prepTime": self.prep_time,
            "cookTime": self.cook_time,
            "totalTime": self.total_time,
            "recipeCategory": self.recipe_category,
            "keywords": self.keywords,
            "recipeIngredient": self.recipe_ingredient,
            "recipeInstructions": [
                {"@type": "HowToStep", "text": step}
                for step in self.recipe_instructions
            ],
            "tool": self.tools,
        }
        if self.id is not None:
            data["id"] = self.id
        if self.nutrition:
            data["nutrition"] = self.nutrition.to_api()
        if self.rating > 0:
            data["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": str(self.rating),
                "ratingCount": "1",
            }
        return data
