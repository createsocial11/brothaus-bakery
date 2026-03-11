"""
=============================================================
  BROTHAUS BAKERY — FASTAPI BACKEND
  Run: uvicorn main:app --reload
  Docs: http://localhost:8000/docs
=============================================================
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import math
import os

try:
    import google.generativeai as genai
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction="""You are Klaus, a friendly expert German baker at BrotHaus bakery
            in a busy business district. You specialize in traditional German breads, pastries, and baked goods.
            You know recipes for Brezel, Schwarzbrot, Stollen, Broetchen, Streuselkuchen, and more.
            You also understand bakery sales forecasting, customer patterns, and operations.
            Always respond warmly, use occasional German words like 'Wunderbar!' or 'Guten Morgen!',
            and give helpful practical baking and business tips. Keep responses concise and useful.
            When asked about sales or forecasting, relate it to the bakery context."""
        )
        AI_AVAILABLE = True
    else:
        AI_AVAILABLE = False
except ImportError:
    AI_AVAILABLE = False

app = FastAPI(
    title="BrotHaus Bakery API",
    description="AI-powered German Bakery Sales Forecasting System",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
#  REQUEST MODELS
# ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    text: str

class ForecastRequest(BaseModel):
    yesterday_units: float
    today_day: int           # 1=Mon ... 7=Sun
    weather: int             # 1=Good, 0=Bad
    temperature: float       # degrees C
    rainfall: int            # 1=Yes, 0=No
    public_holiday: int
    school_holiday: int
    promotion: int
    local_event: int
    morning_rush: int
    new_product: int
    staff_full: int          # 1=Full, 0=Short
    seasonal: int
    bulk_order: int
    week_of_month: int       # 1-4
    customer_mood: int       # 3=Happy, 2=Neutral, 1=Unhappy
    # Simulation factors
    arrival_rate: int        # 1=Low, 2=Normal, 3=High
    peak_hour: int           # 1=Active, 0=No
    pretzel_festival: int    # 1=Yes, 0=No
    product_mix: int         # 1=Pretzel-Heavy, 2=Balanced, 3=Cake-Heavy
    volatility: int          # 1=Stable, 2=Moderate, 3=Volatile
    demand_percentile: int   # 1=Bottom25, 2=Mid50, 3=Top25

class SimulationRequest(BaseModel):
    days: Optional[int] = 100
    promo_active: Optional[bool] = False


# ─────────────────────────────────────────────────────────────
#  SIMULATION ENGINE
# ─────────────────────────────────────────────────────────────

import random

def poisson_approx(lam, rng=None):
    """Approximate Poisson using normal distribution for speed."""
    r = rng or random
    val = r.gauss(lam, math.sqrt(lam))
    return max(int(round(val)), 0)

def run_simulation(days=100, promo_active=False, seed=42):
    """Run the professor's 6-step bakery simulation."""
    rng = random.Random(seed)

    PRODUCTS  = ["Pretzel", "Bread", "Cake"]
    PROB_NORM = [0.50, 0.30, 0.20]
    PROB_PRMO = [0.70, 0.20, 0.10]
    PRICES    = {"Pretzel": 60, "Bread": 180, "Cake": 220}

    daily_revenues  = []
    daily_customers = []
    product_totals  = {"Pretzel": 0, "Bread": 0, "Cake": 0}
    hourly_avg      = [0.0] * 12

    for day in range(days):
        probs = PROB_PRMO if promo_active else PROB_NORM
        day_rev  = 0
        day_cust = 0
        hour_counts = []

        for h in range(12):
            actual_hour = 8 + h
            is_peak = 12 <= actual_hour < 14
            lam = 15 * 1.4 if is_peak else 15        # Step 4: +40% peak boost
            count = poisson_approx(lam, rng)          # Step 1: Poisson arrivals
            hour_counts.append(count)

            for _ in range(count):
                # Step 2: Product purchase probability
                r = rng.random()
                cumulative = 0
                purchase = PRODUCTS[-1]
                for p, prob in zip(PRODUCTS, probs):
                    cumulative += prob
                    if r < cumulative:
                        purchase = p
                        break
                # Step 3: Revenue calculation
                day_rev += PRICES[purchase]
                product_totals[purchase] += 1

            day_cust += count

        daily_revenues.append(day_rev)
        daily_customers.append(day_cust)
        for i, c in enumerate(hour_counts):
            hourly_avg[i] += c / days

    avg_rev  = round(sum(daily_revenues) / len(daily_revenues))
    std_rev  = round(math.sqrt(sum((r - avg_rev)**2 for r in daily_revenues) / len(daily_revenues)))
    avg_cust = round(sum(daily_customers) / len(daily_customers))
    cv       = round(std_rev / avg_rev * 100, 1) if avg_rev > 0 else 0
    top_prod = max(product_totals, key=product_totals.get)

    return {
        "days": days,
        "promo_active": promo_active,
        "avg_daily_revenue": avg_rev,
        "std_deviation": std_rev,
        "min_revenue": min(daily_revenues),
        "max_revenue": max(daily_revenues),
        "median_revenue": sorted(daily_revenues)[len(daily_revenues)//2],
        "coefficient_of_variation": cv,
        "avg_customers_per_day": avg_cust,
        "most_popular_product": top_prod,
        "product_totals": product_totals,
        "daily_revenues": daily_revenues,
        "hourly_averages": [round(x, 1) for x in hourly_avg],
    }


# ─────────────────────────────────────────────────────────────
#  FORECAST ENGINE — 22 FACTORS
# ─────────────────────────────────────────────────────────────

def run_forecast(r: ForecastRequest):
    base = r.yesterday_units

    # Section B — Case Study
    day_w = {1:0.85,2:0.90,3:0.92,4:0.95,5:1.10,6:1.35,7:1.20}
    day_effect     = round(base * (day_w.get(r.today_day, 1.0) - 1.0))
    weather_effect = 12 if r.weather == 1 else -10
    temp_effect    = (-8 if r.temperature < 0 else -3 if r.temperature < 10
                      else 5 if r.temperature < 20 else 8 if r.temperature < 30 else 2)
    rain_effect    = -18 if r.rainfall     == 1 else 0
    holiday_effect = 18  if r.public_holiday == 1 else 0
    school_effect  = 14  if r.school_holiday == 1 else 0
    promo_effect   = 20  if r.promotion    == 1 else 0
    event_effect   = 22  if r.local_event  == 1 else 0

    # Section C — Bakery-Specific
    rush_effect     = (25 if r.morning_rush==1 and r.today_day<=5 else
                       15 if r.morning_rush==1 else 0)
    launch_effect   = 30  if r.new_product  == 1 else 0
    staff_effect    = 0   if r.staff_full   == 1 else -25
    seasonal_effect = 45  if r.seasonal     == 1 else 0
    bulk_effect     = 35  if r.bulk_order   == 1 else 0
    week_effect     = {1:12,2:5,3:-3,4:-10}.get(r.week_of_month, 0)
    mood_effect     = {3:20,2:0,1:-15}.get(r.customer_mood, 0)

    # Section D — Simulation Factors
    arrival_effect   = {1:-18,2:0,3:22}.get(r.arrival_rate, 0)
    peak_effect      = 16 if r.peak_hour          == 1 else 0
    festival_effect  = 18 if r.pretzel_festival   == 1 else 0
    mix_effect       = {1:14,2:0,3:-10}.get(r.product_mix, 0)
    vol_effect       = {1:8,2:0,3:-12}.get(r.volatility, 0)
    pct_effect       = {1:-20,2:0,3:25}.get(r.demand_percentile, 0)

    predicted = max(int(round(
        base + day_effect + weather_effect + temp_effect + rain_effect
        + holiday_effect + school_effect + promo_effect + event_effect
        + rush_effect + launch_effect + staff_effect + seasonal_effect
        + bulk_effect + week_effect + mood_effect
        + arrival_effect + peak_effect + festival_effect
        + mix_effect + vol_effect + pct_effect
    )), 0)

    margin     = max(int(round(predicted * 0.08)), 1)
    avg_price  = 60*0.5 + 180*0.3 + 220*0.2
    revenue    = round(predicted * avg_price)
    staff_rec  = max(math.ceil(predicted / 40) + (1 if r.today_day >= 6 else 0), 2)
    net        = predicted - int(r.yesterday_units)
    total_adj  = predicted - int(base)

    grade = ("A" if total_adj > 80 else "B" if total_adj > 30
             else "C" if total_adj > -20 else "D")

    factors = {
        "day_of_week": day_effect, "weather": weather_effect,
        "temperature": temp_effect, "rainfall": rain_effect,
        "public_holiday": holiday_effect, "school_holiday": school_effect,
        "promotion": promo_effect, "local_event": event_effect,
        "morning_rush": rush_effect, "new_product": launch_effect,
        "staff": staff_effect, "seasonal": seasonal_effect,
        "bulk_order": bulk_effect, "week_of_month": week_effect,
        "customer_mood": mood_effect,
        "sim_arrival_rate": arrival_effect, "sim_peak_hour": peak_effect,
        "sim_pretzel_festival": festival_effect, "sim_product_mix": mix_effect,
        "sim_volatility": vol_effect, "sim_demand_percentile": pct_effect,
    }

    return {
        "predicted_units": predicted,
        "conservative": predicted - margin,
        "optimistic": predicted + margin,
        "vs_yesterday": net,
        "expected_revenue": revenue,
        "staff_recommended": staff_rec,
        "demand_grade": grade,
        "flour_kg": round(predicted * 0.150, 1),
        "eggs": round(predicted * 0.3),
        "factors": factors,
    }


# ─────────────────────────────────────────────────────────────
#  API ROUTES
# ─────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {
        "status": "BrotHaus Bakery AI is running! 🥨",
        "version": "2.0",
        "ai_available": AI_AVAILABLE,
        "endpoints": ["/forecast", "/simulate", "/chat", "/recipe/{name}", "/docs"]
    }

@app.post("/forecast")
def get_forecast(request: ForecastRequest):
    """Run the 22-factor AI morning forecast."""
    return run_forecast(request)

@app.post("/simulate")
def get_simulation(request: SimulationRequest):
    """Run professor's 6-step 100-day simulation."""
    days = max(10, min(request.days or 100, 1000))
    return run_simulation(days=days, promo_active=request.promo_active or False)

@app.get("/simulate/compare")
def compare_simulations():
    """Compare normal vs Pretzel Festival simulation."""
    normal = run_simulation(days=100, promo_active=False)
    promo  = run_simulation(days=100, promo_active=True)
    uplift = round((promo["avg_daily_revenue"] - normal["avg_daily_revenue"])
                   / normal["avg_daily_revenue"] * 100, 1)
    return {
        "normal": normal,
        "promo": promo,
        "revenue_uplift_pct": uplift,
        "revenue_uplift_abs": promo["avg_daily_revenue"] - normal["avg_daily_revenue"],
    }

@app.post("/chat")
async def chat(message: ChatMessage):
    """Chat with Klaus the AI baker (requires GEMINI_API_KEY)."""
    if not AI_AVAILABLE:
        return {
            "reply": (
                "Guten Morgen! I'm Klaus, your BrotHaus baker! "
                "AI chat requires a Gemini API key — get one free at aistudio.google.com "
                "and add it to your .env file as GEMINI_API_KEY. "
                "In the meantime, try the /forecast or /simulate endpoints! 🥨"
            ),
            "ai_mode": False
        }
    try:
        response = gemini_model.generate_content(message.text)
        return {"reply": response.text, "ai_mode": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recipe/{bread_name}")
async def get_recipe(bread_name: str):
    """Get a traditional German recipe (requires GEMINI_API_KEY)."""
    if not AI_AVAILABLE:
        recipes = {
            "Brezel": "Classic Soft Pretzel: 500g flour, 7g yeast, 300ml warm water, 10g salt, 30g butter. Knead 10 min, rest 1hr, shape, dip in 4% baking soda solution, bake 220C for 12-15 min until deep brown.",
            "Schwarzbrot": "Dark Rye Bread: 400g rye flour, 100g wheat flour, 15g salt, 7g yeast, 350ml water, 2 tbsp caraway seeds. Mix, ferment 2hrs, bake 180C for 60 min.",
            "Stollen": "Christmas Stollen: 500g flour, 200g butter, 200g dried fruit, 100g marzipan, spices (cardamom, nutmeg). Mix, shape, bake 180C 45 min, dust with icing sugar.",
        }
        recipe = recipes.get(bread_name, f"Traditional German recipe for {bread_name}: flour, water, salt, yeast — bake at 200C until golden!")
        return {"recipe": recipe, "ai_mode": False}
    try:
        prompt = f"Give me a traditional German bakery recipe for {bread_name} with exact ingredients and clear steps. Make it practical and authentic."
        response = gemini_model.generate_content(prompt)
        return {"recipe": response.text, "ai_mode": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products")
def get_products():
    """Get BrotHaus product catalog with prices and probabilities."""
    return {
        "products": [
            {"name": "Pretzel", "emoji": "🥨", "price": 60,  "prob_normal": 0.50, "prob_promo": 0.70, "category": "savory"},
            {"name": "Bread",   "emoji": "🍞", "price": 180, "prob_normal": 0.30, "prob_promo": 0.20, "category": "staple"},
            {"name": "Cake",    "emoji": "🎂", "price": 220, "prob_normal": 0.20, "prob_promo": 0.10, "category": "sweet"},
        ],
        "avg_ticket": round(60*0.5 + 180*0.3 + 220*0.2, 2),
        "peak_hours": "12:00 - 14:00",
        "peak_boost": "+40%",
    }

