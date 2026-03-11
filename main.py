from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import math
import os
import random
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_simulation(days=100, promo_active=False, seed=42):
    rng = random.Random(seed)
    PRODUCTS = ["Pretzel", "Bread", "Cake"]
    PROB_NORM = [0.50, 0.30, 0.20]
    PROB_PRMO = [0.70, 0.20, 0.10]
    PRICES = {"Pretzel": 60, "Bread": 180, "Cake": 220}
    daily_revenues = []
    daily_customers = []
    product_totals = {"Pretzel": 0, "Bread": 0, "Cake": 0}

    for day in range(days):
        probs = PROB_PRMO if promo_active else PROB_NORM
        day_rev = 0
        day_cust = 0
        for h in range(12):
            actual_hour = 8 + h
            is_peak = 12 <= actual_hour < 14
            lam = 15 * 1.4 if is_peak else 15
            count = max(int(round(rng.gauss(lam, math.sqrt(lam)))), 0)
            for _ in range(count):
                r = rng.random()
                cumulative = 0
                purchase = PRODUCTS[-1]
                for p, prob in zip(PRODUCTS, probs):
                    cumulative += prob
                    if r < cumulative:
                        purchase = p
                        break
                day_rev += PRICES[purchase]
                product_totals[purchase] += 1
            day_cust += count
        daily_revenues.append(day_rev)
        daily_customers.append(day_cust)

    avg_rev = round(sum(daily_revenues) / len(daily_revenues))
    std_rev = round(math.sqrt(sum((r - avg_rev)**2 for r in daily_revenues) / len(daily_revenues)))
    avg_cust = round(sum(daily_customers) / len(daily_customers))
    cv = round(std_rev / avg_rev * 100, 1) if avg_rev > 0 else 0
    top_prod = max(product_totals, key=product_totals.get)

    return {
        "days": days,
        "avg_daily_revenue": avg_rev,
        "std_deviation": std_rev,
        "min_revenue": min(daily_revenues),
        "max_revenue": max(daily_revenues),
        "coefficient_of_variation": cv,
        "avg_customers_per_day": avg_cust,
        "most_popular_product": top_prod,
        "product_totals": product_totals,
        "daily_revenues": daily_revenues,
    }

@app.get("/")
def home():
    return {"status": "BrotHaus Bakery AI is running! 🥨"}

@app.get("/simulate")
def get_simulation(days: int = 100, promo_active: bool = False):
    return run_simulation(days=days, promo_active=promo_active)

@app.get("/simulate/compare")
def compare():
    normal = run_simulation(100, False)
    promo  = run_simulation(100, True)
    uplift = round((promo["avg_daily_revenue"] - normal["avg_daily_revenue"])
                   / normal["avg_daily_revenue"] * 100, 1)
    return {"normal": normal, "promo": promo, "uplift_pct": uplift}

@app.get("/forecast")
def get_forecast(
    yesterday_units: float = 100,
    today_day: int = 1,
    weather: int = 1,
    temperature: float = 18,
    rainfall: int = 0,
    public_holiday: int = 0,
    school_holiday: int = 0,
    promotion: int = 0,
    local_event: int = 0,
    morning_rush: int = 0,
    new_product: int = 0,
    staff_full: int = 1,
    seasonal: int = 0,
    bulk_order: int = 0,
    week_of_month: int = 1,
    customer_mood: int = 2,
    arrival_rate: int = 2,
    peak_hour: int = 0,
    pretzel_festival: int = 0,
    product_mix: int = 2,
    volatility: int = 2,
    demand_percentile: int = 2
):
    base = yesterday_units
    day_w = {1:0.85,2:0.90,3:0.92,4:0.95,5:1.10,6:1.35,7:1.20}
    predicted = max(int(round(
        base
        + round(base * (day_w.get(today_day, 1.0) - 1.0))
        + (12 if weather==1 else -10)
        + (-8 if temperature<0 else -3 if temperature<10 else 5 if temperature<20 else 8)
        + (-18 if rainfall else 0)
        + (18 if public_holiday else 0)
        + (14 if school_holiday else 0)
        + (20 if promotion else 0)
        + (22 if local_event else 0)
        + (25 if morning_rush and today_day<=5 else 15 if morning_rush else 0)
        + (30 if new_product else 0)
        + (0 if staff_full else -25)
        + (45 if seasonal else 0)
        + (35 if bulk_order else 0)
        + {1:12,2:5,3:-3,4:-10}.get(week_of_month, 0)
        + {3:20,2:0,1:-15}.get(customer_mood, 0)
        + {1:-18,2:0,3:22}.get(arrival_rate, 0)
        + (16 if peak_hour else 0)
        + (18 if pretzel_festival else 0)
        + {1:14,2:0,3:-10}.get(product_mix, 0)
        + {1:8,2:0,3:-12}.get(volatility, 0)
        + {1:-20,2:0,3:25}.get(demand_percentile, 0)
    )), 0)
    margin  = max(int(round(predicted * 0.08)), 1)
    revenue = round(predicted * 122)
    staff   = max(math.ceil(predicted/40) + (1 if today_day>=6 else 0), 2)
    grade   = "A" if predicted-base>80 else "B" if predicted-base>30 else "C" if predicted-base>-20 else "D"
    return {
        "predicted_units": predicted,
        "conservative": predicted - margin,
        "optimistic":   predicted + margin,
        "vs_yesterday": predicted - int(base),
        "expected_revenue": revenue,
        "staff_recommended": staff,
        "demand_grade": grade,
        "flour_kg": round(predicted * 0.15, 1),
        "eggs": round(predicted * 0.3),
    }

@app.get("/chat")
def chat(text: str = "hello"):
    text_lower = text.lower()
    if "brezel" in text_lower or "pretzel" in text_lower:
        reply = "Wunderbar! Brezel: 500g flour, 7g yeast, 300ml warm water, 10g salt, 30g butter. Knead 10min, rest 1hr, dip in baking soda solution, bake 220C for 15min! 🥨"
    elif "schwarzbrot" in text_lower:
        reply = "Schwarzbrot: 400g rye flour, 100g wheat flour, 15g salt, 7g yeast, 350ml water, caraway seeds. Ferment 2hrs, bake 180C for 60min. 🍞"
    elif "stollen" in text_lower:
        reply = "Christmas Stollen: 500g flour, 200g butter, 200g dried fruit, 100g marzipan, spices. Bake 180C 45min, dust with icing sugar! 🎄"
    elif "peak" in text_lower or "hour" in text_lower:
        reply = "Our peak hours are 12PM-2PM! Customer arrivals increase by 40% - from lambda=15 to lambda=21 per hour! 📈"
    elif "simulation" in text_lower:
        reply = "The simulation uses Poisson distribution with lambda=15 customers/hour for 12 hours. After 100 days the average revenue is around Rs 27,000! 📊"
    elif "saturday" in text_lower or "weekend" in text_lower:
        reply = "Saturday is our BEST day! 35% more sales than average. We recommend all staff on deck from opening time! 💪"
    else:
        reply = f"Guten Tag! You said: '{text}'. I am Klaus your BrotHaus baker! Ask me about Brezel, Schwarzbrot, Stollen, peak hours or the simulation! 🥨"
    return {"reply": reply}

@app.get("/recipe/{bread_name}")
def get_recipe(bread_name: str):
    recipes = {
        "Brezel": "Classic Soft Pretzel: 500g flour, 7g yeast, 300ml warm water, 10g salt, 30g butter. Knead 10min, rest 1hr, shape, dip in 4% baking soda solution, bake 220C for 15min until deep brown! 🥨",
        "Schwarzbrot": "Dark Rye Bread: 400g rye flour, 100g wheat flour, 15g salt, 7g yeast, 350ml water, 2 tbsp caraway seeds. Mix, ferment 2hrs, bake 180C for 60min. 🍞",
        "Stollen": "Christmas Stollen: 500g flour, 200g butter, 200g dried fruit, 100g marzipan, cardamom, nutmeg. Mix, shape, bake 180C 45min, dust with icing sugar. 🎄",
        "Brötchen": "German Rolls: 500g flour, 7g yeast, 300ml water, 10g salt, 1 tsp sugar. Knead, rest 1hr, shape rolls, bake 220C for 20min until golden. 🫓",
        "Streuselkuchen": "Crumb Cake: Base: 300g flour, 100g butter, 100g sugar, 2 eggs. Topping: 200g flour, 100g butter, 80g sugar. Layer and bake 180C for 35min. 🍰",
    }
    recipe = recipes.get(bread_name, f"Traditional German {bread_name}: flour, water, salt, yeast. Mix, knead, rest, bake at 200C until golden! 🥐")
    return {"recipe": recipe}

@app.get("/products")
def get_products():
    return {
        "products": [
            {"name": "Pretzel", "emoji": "🥨", "price": 60,  "prob_normal": 0.50, "prob_promo": 0.70},
            {"name": "Bread",   "emoji": "🍞", "price": 180, "prob_normal": 0.30, "prob_promo": 0.20},
            {"name": "Cake",    "emoji": "🎂", "price": 220, "prob_normal": 0.20, "prob_promo": 0.10},
        ],
        "avg_ticket": 122,
        "peak_hours": "12:00 - 14:00",
    }
