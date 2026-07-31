import asyncio
from playwright.async_api import async_playwright
import json
import time
from datetime import datetime

LEAGUE_URLS = {
    'ekstraklasa': 'https://www.flashscore.pl/pilka-nozna/polska/ekstraklasa/',
    'betclic-1-liga': 'https://www.flashscore.pl/pilka-nozna/polska/betclic-1-liga/',
    'premier-league': 'https://www.flashscore.pl/pilka-nozna/anglia/premier-league/',
    'la-liga': 'https://www.flashscore.pl/pilka-nozna/hiszpania/laliga/',
    'serie-a': 'https://www.flashscore.pl/pilka-nozna/wlochy/serie-a/',
    'bundesliga': 'https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga/',
    'ligue-1': 'https://www.flashscore.pl/pilka-nozna/francja/ligue-1/'
}

INTERVAL_SECONDS = 180  # co 3 minuty

async def scrape_live():
    live_data = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        try:
            await page.goto("https://www.flashscore.pl/", wait_until="domcontentloaded", timeout=15000)
            await page.click("#onetrust-accept-btn-handler", timeout=5000)
        except:
            pass
        
        for league_id, url in LEAGUE_URLS.items():
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)
                
                matches = await page.evaluate("""
                    () => {
                        const out = [];
                        document.querySelectorAll('.event__match').forEach(el => {
                            const homeEl = el.querySelector('.event__homeParticipant, .event__participant--home');
                            const awayEl = el.querySelector('.event__awayParticipant, .event__participant--away');
                            const homeScoreEl = el.querySelector('.event__score--home');
                            const awayScoreEl = el.querySelector('.event__score--away');
                            const stageEl = el.querySelector('.event__stage, [class*="stage"]');
                            const timeEl = el.querySelector('.event__stageTime, .event__time');
                            
                            if (homeEl && awayEl) {
                                const isLive = el.className.includes('live') || el.className.includes('inprogress');
                                const stage = stageEl ? stageEl.innerText.trim() : '';
                                const isFinished = stage.toLowerCase().includes('koniec') || stage.toLowerCase().includes('finished');
                                
                                out.push({
                                    home: homeEl.innerText.trim(),
                                    away: awayEl.innerText.trim(),
                                    home_score: homeScoreEl ? homeScoreEl.innerText.trim() : null,
                                    away_score: awayScoreEl ? awayScoreEl.innerText.trim() : null,
                                    stage: stage,
                                    time: timeEl ? timeEl.innerText.trim() : '',
                                    is_live: isLive,
                                    is_finished: isFinished,
                                    match_id: el.id ? el.id.split('_').pop() : ''
                                });
                            }
                        });
                        return out;
                    }
                """)
                
                # Filtruj tylko live/finished dziś
                for m in matches:
                    if m.get('home_score') is not None and m.get('home_score') != '':
                        key = m['home'] + '_' + m['away']
                        live_data[key] = {
                            'home': m['home'],
                            'away': m['away'],
                            'score': m['home_score'] + ':' + m['away_score'],
                            'stage': m['stage'],
                            'is_live': m['is_live'],
                            'is_finished': m['is_finished'],
                            'league_id': league_id,
                            'match_id': m['match_id']
                        }
                
                print(f"✓ {league_id}: {sum(1 for m in matches if m.get('home_score'))} meczów z wynikiem")
            except Exception as e:
                print(f"✗ {league_id}: {str(e)[:80]}")
        
        await browser.close()
    
    # Zapisz
    with open("live.json", "w", encoding="utf-8") as f:
        json.dump({
            "matches": live_data,
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Zapisano {len(live_data)} live/finished meczy")

async def main():
    print("🔴 LIVE SCRAPER - co 3 minuty")
    while True:
        try:
            print(f"\n{'='*50}")
            print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Pobieram live...")
            await scrape_live()
            print(f"💤 Czekam {INTERVAL_SECONDS}s do następnego skanu...")
        except Exception as e:
            print(f"❌ Błąd: {e}")
        
        try:
            await asyncio.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n👋 Zatrzymano!")
            break

if __name__ == "__main__":
    asyncio.run(main())