import asyncio
from playwright.async_api import async_playwright
import json
import time

# ZMIEŃ TUTAJ TURNIEJE NA AKTUALNE:
TOURNAMENTS = [
    {"id": "atp-montreal", "name": "ATP Montreal", "flag": "🎾",
     "url": "https://www.flashscore.pl/tenis/atp-singiel/montreal/"},
    {"id": "wta-toronto", "name": "WTA Toronto", "flag": "🎾",
     "url": "https://www.flashscore.pl/tenis/wta-singiel/toronto/"},
]

async def scrape_tennis():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        try:
            await page.goto("https://www.flashscore.pl/", wait_until="domcontentloaded", timeout=15000)
            await page.click("#onetrust-accept-btn-handler", timeout=5000)
        except:
            pass
        
        all_matches = []
        
        for tour in TOURNAMENTS:
            print(f"🎾 {tour['name']}...")
            try:
                await page.goto(tour['url'], wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(3)
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(2)
                
                matches = await page.evaluate("""
                    () => {
                        const out = [];
                        document.querySelectorAll('.event__match').forEach(el => {
                            const homeEl = el.querySelector('.event__homeParticipant, .event__participant--home');
                            const awayEl = el.querySelector('.event__awayParticipant, .event__participant--away');
                            const timeEl = el.querySelector('.event__stageTime, .event__time');
                            const link = el.querySelector('a[href*="/mecz/"]');
                            
                            if (homeEl && awayEl) {
                                const timeStr = timeEl ? timeEl.innerText.trim() : '';
                                out.push({
                                    home: homeEl.innerText.trim(),
                                    away: awayEl.innerText.trim(),
                                    datetime: timeStr || 'TBA',
                                    id: el.id,
                                    url: link ? link.href : ''
                                });
                            }
                        });
                        return out;
                    }
                """)
                
                selected = matches[:20]
                print(f"   Znaleziono {len(selected)} meczy")
                
                for m in selected:
                    mid = m['id'].split('_')[-1] if m.get('id') else ''
                    all_matches.append({
                        "home": m['home'],
                        "away": m['away'],
                        "datetime": m['datetime'],
                        "match_id": mid,
                        "match_url": m.get('url', ''),
                        "league_id": tour['id'],
                        "league_name": tour['name'],
                        "league_flag": tour['flag'],
                        "sport": "tennis",
                        "home_stats": {},
                        "away_stats": {}
                    })
                
            except Exception as e:
                print(f"   Błąd: {e}")
        
        await browser.close()
        
        # Dołącz do data.json
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = {"matches": [], "standings": [], "leagues": []}
        
        # Usuń stare mecze tenisowe
        data["matches"] = [m for m in data["matches"] if m.get("sport") != "tennis"]
        data["matches"].extend(all_matches)
        
        # Dodaj turnieje do lig
        existing_ids = [l["id"] for l in data.get("leagues", [])]
        for t in TOURNAMENTS:
            if t["id"] not in existing_ids:
                data["leagues"].append({"id": t["id"], "name": t["name"], "flag": t["flag"]})
        
        data["updated"] = time.strftime("%Y-%m-%d %H:%M")
        
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        print(f"\n✅ Tenis: {len(all_matches)} meczy dodanych do data.json")

if __name__ == "__main__":
    asyncio.run(scrape_tennis())