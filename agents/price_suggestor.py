# agents/price_suggestor.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import statistics

# comparables module
from utils.comparables import get_comparables


class ProductInput(BaseModel):
    id: Optional[int] = None
    title: str
    category: str
    brand: Optional[str] = None
    condition: str
    age_months: int
    asking_price: Optional[float] = None
    location: Optional[str] = None
    use_llm: Optional[bool] = True
    use_comparables: Optional[bool] = False


class PriceSuggestorAgent:
    CATEGORY_RULES = {
        "mobile": {"monthly_rate": 0.015, "cap_floor": 0.20, "fast_decay_months": 24},
        "laptop": {"monthly_rate": 0.012, "cap_floor": 0.20, "fast_decay_months": 36},
        "electronics": {"monthly_rate": 0.010, "cap_floor": 0.20, "fast_decay_months": 36},
        "camera": {"monthly_rate": 0.011, "cap_floor": 0.25, "fast_decay_months": 36},
        "furniture": {"monthly_rate": 0.006, "cap_floor": 0.30, "fast_decay_months": 60},
        "fashion": {"monthly_rate": 0.005, "cap_floor": 0.35, "fast_decay_months": 24},
        "other": {"monthly_rate": 0.008, "cap_floor": 0.25, "fast_decay_months": 36}
    }

    BRAND_PREMIUM = {
        "apple": 0.15,
        "sony": 0.08,
        "canon": 0.10,
        "nike": 0.10,
        "adidas": 0.08,
        "oneplus": 0.05,
        "dell": 0.04,
        "hp": 0.03,
        "samsung": 0.03
    }

    METRO_CITIES = {"mumbai", "delhi", "bangalore", "chennai", "hyderabad", "pune", "kolkata"}

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def _get_category_rule(self, category: str):
        key = category.strip().lower()
        if key in self.CATEGORY_RULES:
            return self.CATEGORY_RULES[key]
        if "mobile" in key or "phone" in key:
            return self.CATEGORY_RULES["mobile"]
        if "laptop" in key:
            return self.CATEGORY_RULES["laptop"]
        if "furn" in key:
            return self.CATEGORY_RULES["furniture"]
        if "camera" in key:
            return self.CATEGORY_RULES["camera"]
        if "shoe" in key or "fashion" in key:
            return self.CATEGORY_RULES["fashion"]
        return self.CATEGORY_RULES["other"]

    def _depreciate(self, base_price: float, months: int, rule: dict):
        if months <= 0:
            return base_price
        first_n = rule["fast_decay_months"]
        monthly = rule["monthly_rate"]
        cap_floor = rule["cap_floor"]
        if months <= first_n:
            factor = (1 - monthly) ** months
        else:
            factor_first = (1 - monthly) ** first_n
            remainder = months - first_n
            factor_after = (1 - monthly * 0.6) ** remainder
            factor = factor_first * factor_after
        depreciated = base_price * factor
        floor_price = base_price * cap_floor
        return max(depreciated, floor_price)

    def _condition_range(self, condition: str):
        cond = condition.strip().lower()
        if cond == "like new":
            return (0.95, 1.05)
        if cond == "good":
            return (0.75, 0.90)
        if cond == "fair":
            return (0.50, 0.75)
        return (0.7, 0.9)

    def _brand_adj(self, brand: Optional[str]):
        if not brand:
            return 0.0
        b = brand.strip().lower()
        for k, v in self.BRAND_PREMIUM.items():
            if k in b:
                return v
        return 0.0

    def suggest(self, data: ProductInput) -> Dict[str, Any]:
        if data.asking_price is None:
            raise ValueError("asking_price required for heuristic suggestion.")

        base = float(data.asking_price)
        cat_rule = self._get_category_rule(data.category)
        depreciated = self._depreciate(base, data.age_months, cat_rule)
        cond_min, cond_max = self._condition_range(data.condition)
        brand_adj = self._brand_adj(data.brand)

        if data.location and data.location.strip().lower() in self.METRO_CITIES:
            loc_adj_min, loc_adj_max = 0.0, 0.05
        else:
            loc_adj_min, loc_adj_max = -0.05, 0.0

        raw_min = depreciated * cond_min * (1 + loc_adj_min)
        raw_max = depreciated * cond_max * (1 + brand_adj + loc_adj_max)

        def round_price(x):
            return int(round(x / 100.0) * 100) if x >= 20000 else int(round(x / 50.0) * 50)

        min_price = max(50, round_price(raw_min))
        max_price = max(min_price + 50, round_price(raw_max))

        reasoning = (
            f"Started with asking price ₹{base}. "
            f"Applied depreciation ({cat_rule['monthly_rate']}/month, fast decay {cat_rule['fast_decay_months']}m). "
            f"After {data.age_months} months → base value ₹{round(depreciated,2)}. "
            f"Condition factor {cond_min}-{cond_max}, brand adj {brand_adj:.2f}, location adj {loc_adj_min}-{loc_adj_max}."
        )

        fair_price_range = {
            "min": min_price,
            "max": max_price,
            "currency": "INR",
            "display": f"₹{min_price:,} - ₹{max_price:,}"
        }

        comparables = []
        if data.use_comparables:
            try:
                comps = get_comparables(data.title, location=data.location, max_results=8)
                comparables = comps
                prices = [c["price"] for c in comps if c.get("price")]
                if prices:
                    median_price = int(statistics.median(prices))
                    comp_min, comp_max = int(median_price * 0.95), int(median_price * 1.05)
                    new_min = round_price(min_price * 0.4 + comp_min * 0.6)
                    new_max = round_price(max_price * 0.4 + comp_max * 0.6)
                    fair_price_range = {
                        "min": new_min,
                        "max": max(new_min + 50, new_max),
                        "currency": "INR",
                        "display": f"₹{new_min:,} - ₹{max(new_min+50, new_max):,}"
                    }
            except Exception:
                pass

        if data.use_llm and self.llm:
            try:
                prompt = (
                    "You are a pricing assistant for used products. "
                    f"Product: {data.title} ({data.category}, brand={data.brand}), "
                    f"age={data.age_months} months, condition={data.condition}, "
                    f"asking_price={data.asking_price}. "
                    f"Heuristic fair price: {fair_price_range}. "
                    f"Comparables: {comparables if comparables else 'none'}. "
                    "Give a short natural language reasoning and optionally suggest a refined range. "
                    "Answer in 3-4 sentences."
                )
                llm_text = self.llm(prompt)
                reasoning = llm_text
            except Exception:
                pass

        return {
            "fair_price_range": fair_price_range,
            "reasoning": reasoning,
            "comparables": comparables
        }
