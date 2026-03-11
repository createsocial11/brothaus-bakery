import json
import math
import random
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

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

def calc_forecast(p):
    base = float(p.get("yesterday_units", [100])[0])
    today_day = int(p.get("today_day", [1])[0])
    weather = int(p.get("weather", [1])[0])
    temperature = float(p.get("temperature", [18])[0])
    rainfall = int(p.get("rainfall", [0])[0])
    public_holiday = int(p.get("public_holiday", [0])[0])
    school_holiday = int(p.get("school_holiday", [0])[0])
    promotion = int(p.get("promotion", [0])[0])
    local_event = int(p.get("local_event", [0])[0])
    morning_rush = int(p.get("morning_rush", [0])[0])
    new_product = int(p.get("new_product", [0])[0])
    staff_full = int(p.get("staff_full", [1])[0])
    seasonal = int(p.get("seasonal", [0])[0])
    bulk_order = int(p.get("bulk_order", [0])[0])
    week_of_month = int(p.get("week_of_month", [1])[0])
    customer_mood = int(p.get("customer_mood", [2])[0])
    arrival_rate = int(p.get("arrival_rate", [2])[0])
    peak_hour = int(p.get("peak_hour", [0])[0])
    pretzel_festival = int(p.get("pretzel_festival", [0])[0])
    product_mix = int(p.get("product_mix", [2])[0])
    volatility = int(p.get("volatility", [2])[0])
    demand_percentile = int(p.get("demand_percentile", [2])[0])

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
        "optimistic": predicted + margin,
        "vs_yesterday": predicted - int(base),
        "expected_revenue": revenue,
        "staff_recommended": staff,
        "demand_grade": grade,
        "flour_kg": round(predicted * 0.15, 1),
        "eggs": round(predicted * 0.3),
    }

RECIPES = {
    "Brezel": "Classic Soft Pretzel: 500g flour, 7g yeast, 300ml warm water, 10g salt, 30g butter. Knead 10min, rest 1hr, shape, dip in baking soda solution, bake 220C for 15min! 🥨",
    "Schwarzbrot": "Dark Rye Bread: 400g rye flour, 100g wheat flour, 15g salt, 7g yeast, 350ml water, caraway seeds. Ferment 2hrs, bake 180C for 60min. 🍞",
    "Stollen": "Christmas Stollen: 500g flour, 200g butter, 200g dried fruit, 100g marzipan, spices. Bake 180C 45min, dust with icing sugar! 🎄",
    "Brötchen": "German Rolls: 500g flour, 7g yeast, 300ml water, 10g salt. Knead, rest 1hr, shape, bake 220C for 20min! 🫓",
    "Streuselkuchen": "Crumb Cake: 300g flour, 100g butter, 100g sugar, 2 eggs. Topping: 200g flour, 100g butter, 80g sugar. Bake 180C 35min! 🍰",
}

class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        if path == "" or path == "/":
            self.send_json({"status": "BrotHaus Bakery AI is running! 🥨", "version": "2.0"})

        elif path == "/simulate":
            days = int(params.get("days", [100])[0])
            promo = params.get("promo_active", ["false"])[0].lower() == "true"
            self.send_json(run_simulation(days=days, promo_active=promo))

        elif path == "/simulate/compare":
            normal = run_simulation(100, False)
            promo  = run_simulation(100, True)
            uplift = round((promo["avg_daily_revenue"] - normal["avg_daily_revenue"])
                           / normal["avg_daily_revenue"] * 100, 1)
            self.send_json({"normal": normal, "promo": promo, "uplift_pct": uplift})

        elif path == "/forecast":
            self.send_json(calc_forecast(params))

        elif path == "/chat":
            text = params.get("text", ["hello"])[0].lower()
            if "brezel" in text or "pretzel" in text:
                reply = "Wunderbar! Brezel: 500g flour, 7g yeast, 300ml warm water, 10g salt. Knead, rest 1hr, dip in baking soda solution, bake 220C for 15min! 🥨"
            elif "peak" in text or "hour" in text:
                reply = "Peak hours are 12PM-2PM! Arrivals increase 40% — lambda goes from 15 to 21 per hour! 📈"
            elif "simulation" in text:
                reply = "Poisson simulation: lambda=15 customers/hour, 12 hours, 100 days. Avg revenue around Rs 27,000! 📊"
            elif "schwarzbrot" in text:
                reply = "Schwarzbrot: dark rye bread with caraway seeds. 400g rye flour, ferment 2hrs, bake 180C for 60min! 🍞"
            else:
                reply = f"Guten Tag! I am Klaus your BrotHaus baker! Ask me about Brezel, peak hours, or the simulation! 🥨"
            self.send_json({"reply": reply})

        elif path.startswith("/recipe/"):
            name = path.split("/recipe/")[-1]
            recipe = RECIPES.get(name, f"Traditional German {name}: flour, water, salt, yeast. Bake at 200C until golden! 🥐")
            self.send_json({"recipe": recipe})

        elif path == "/products":
            self.send_json({"products": [
                {"name": "Pretzel", "price": 60,  "prob_normal": 0.50, "prob_promo": 0.70},
                {"name": "Bread",   "price": 180, "prob_normal": 0.30, "prob_promo": 0.20},
                {"name": "Cake",    "price": 220, "prob_normal": 0.20, "prob_promo": 0.10},
            ]})
        else:
            self.send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"BrotHaus API starting on port {port}")
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()
