from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import math
import os
import random

try:
    import google.generativeai as genai
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction="""You are Klaus, a friendly expert German baker at BrotHaus bakery.
            You know recipes for Brezel, Schwarzbrot, Stollen, Broetchen and more.
            Always respond warmly, use occasional German words like Wunderbar or Guten Morgen,
            and give helpful practical baking tips. Keep responses concise."""
        )
        AI_AVAILABLE = True
    else:
        AI_AVAILABLE = False
except Exception:
    AI_AVAILABLE = False

app = FastAPI(title="BrotHaus Bakery API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    text: str

class ForecastRequest(BaseModel):
    yesterday_units: float
    today_day: int
    weather: int
    temperature: float
    rainfall: int
    public_holiday: int
    school_holiday: int
    promotion: int
    local_event: int
    morning_rush: int
    new_product: int
    staff_full: int
    seasonal: int
    bulk_order: int
    week_of_month: int
    customer_mood: int
    arrival_rate: int
    peak_hour: int
    pretzel_festival: int
    product_mix: int
    volatility: int
    demand_percentile: int

class SimulationRequest(BaseModel):
    days: Optional[int] = 100
    promo_active: Optional[bool] = False

def poisson_approx(lam, rng):
    val = rng.gauss(lam, math.sqrt(lam))
    return max(int(round(val)), 0)

def run_simulation(days=100, promo_active=False, seed=42):
    rng = random.Random(seed)
    PRODUCTS = ["Pretzel", "Bread", "Cake"]
    PROB_NORM = [0.50, 0.30, 0.20]
    PROB_PRMO = [0.70, 0.20, 0.10]
    PRICES = {"Pretzel": 60, "Bread": 180, "Cake": 220}
    daily_revenues = []
    daily_customers = []
    product_totals = {"Pretzel": 0, "Bread": 0, "Cake": 0}
    hourly_avg = [0.0] * 12

    for day in range(days):
        probs = PROB_PRMO if promo_active else PROB_NORM
        day_rev = 0
        day_cust = 0
        hour_counts = []
        for h in range(12):
            actual_hour = 8 + h
            is_peak = 12 <= actual_hour < 14
            lam = 15 * 1.4 if is_peak else 15
            count = poisson_approx(lam, rng)
            hour_counts.append(count)
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
        for i, c in enumerate(hour_counts):
            hourly_avg[i] += c / days

    avg_rev = round(sum(daily_revenues) / len(daily_revenues))
    std_rev = round(math.sqrt(sum((r - avg_rev)**2 for r in daily_revenues) / len(daily_revenues)))
    avg_cust = round(sum(daily_customers) / len(daily_customers))
    cv = round(std_rev / avg_rev * 100, 1) if avg_rev > 0 else 0
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

def run_forecast(r):
    base = r.yesterday_units
    day_w = {1:0.85,2:0.90,3:0.92,4:0.95,5:1.10,6:1.35,7:1.20}
    day_effect     = round(base * (day_w.get(r.today_day, 1.0) - 1.0))
    weather_effect = 12 if r.weather == 1 else -10
    temp_effect    = (-8 if r.temperature < 0 else -3 if r.temperature < 10
                      else 5 if r.temperature < 20 else 8 if r.temperature < 30 else 2)
    rain_effect    = -18 if r.rainfall == 1 else 0
    holiday_effect = 18  if r.public_holiday == 1 else 0
    school_effect  = 14  if r.school_holiday == 1 else 0
    promo_effect   = 20  if r.promotion == 1 else 0
    event_effect   = 22  if r.local_event == 1 else 0
    rush_effect    = (25 if r.morning_rush==1 and r.today_day<=5 else 15 if r.morning_rush==1 else 0)
    launch_effect  = 30  if r.new_product == 1 else 0
    staff_effect   = 0   if r.staff_full == 1 else -25
    seasonal_effect= 45  if r.seasonal == 1 else 0
    bulk_effect    = 35  if r.bulk_order == 1 else 0
    week_effect    = {1:12,2:5,3:-3,4:-10}.get(r.week_of_month, 0)
    mood_effect    = {3:20,2:0,1:-15}.get(r.customer_mood, 0)
    arrival_effect = {1:-18,2:0,3:22}.get(r.arrival_rate, 0)
    peak_effect    = 16 if r.peak_hour == 1 else 0
    festival_effect= 18 if r.pretzel_festival == 1 else 0
    mix_effect     = {1:14,2:0,3:-10}.get(r.product_mix, 0)
    vol_effect     = {1:8,2:0,3:-12}.get(r.volatility, 0)
    pct_effect     = {1:-20,2:0,3:25}.get(r.demand_percentile, 0)

    predicted = max(int(round(
        base + day_effect + weather_effect + temp_effect + rain_effect
        + holiday_effect + school_effect + promo_effect + event_effect
        + rush_effect + launch_effect + staff_effect + seasonal_effect
        + bulk_effect + week_effect + mood_effect
        + arrival_effect + peak_effect + festival_effect
        + mix_effect + vol_effect + pct_effect
    )), 0)

    margin    = max(int(round(predicted * 0.08)), 1)
    avg_price = 60*0.5 + 180*0.3 + 220*0.2
    revenue   = round(predicted * avg_price)
    staff_rec = max(math.ceil(predicted / 40) + (1 if r.today_day >= 6 else 0), 2)
    net       = predicted - int(r.yesterday_units)
    total_adj = predicted - int(base)
    grade = ("A" if total_adj > 80 else "B" if total_adj > 30 else "C" if total_adj > -20 else "D")

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
    }

@app.get("/")
def home():
    return {"status": "BrotHaus Bakery AI is running! 🥨", "ai_available": AI_AVAILABLE}

@app.post("/forecast")
def get_forecast(request: ForecastRequest):
    return run_forecast(request)

@app.post("/simulate")
def get_simulation(request: SimulationRequest):
    days = max(10, min(request.days or 100, 1000))
    return run_simulation(days=days, promo_active=request.promo_active or False)

@app.get("/simulate/compare")
def compare_simulations():
    normal = run_simulation(days=100, promo_active=False)
    promo  = run_simulation(days=100, promo_active=True)
    uplift = round((promo["avg_daily_revenue"] - normal["avg_daily_revenue"])
                   / normal["avg_daily_revenue"] * 100, 1)
    return {"normal": normal, "promo": promo, "revenue_uplift_pct": uplift}

@app.post("/chat")
async def chat(message: ChatMessage):
    if not AI_AVAILABLE:
        return {"reply": "Guten Morgen! I am Klaus 🥨 AI chat needs a Gemini API key. Add GEMINI_API_KEY in Render environment variables!", "ai_mode": False}
    try:
        response = gemini_model.generate_content(message.text)
        return {"reply": response.text, "ai_mode": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recipe/{bread_name}")
async def get_recipe(bread_name: str):
    if not AI_AVAILABLE:
        return {"recipe": f"Traditional German {bread_name}: flour, water, salt, yeast. Mix, knead, rest 1 hour, bake at 200C until golden!", "ai_mode": False}
    try:
        response = gemini_model.generate_content(f"Give a traditional German recipe for {bread_name} with ingredients and steps.")
        return {"recipe": response.text, "ai_mode": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products")
def get_products():
    return {
        "products": [
            {"name": "Pretzel", "price": 60,  "prob_normal": 0.50, "prob_promo": 0.70},
            {"name": "Bread",   "price": 180, "prob_normal": 0.30, "prob_promo": 0.20},
            {"name": "Cake",    "price": 220, "prob_normal": 0.20, "prob_promo": 0.10},
        ]
    }
