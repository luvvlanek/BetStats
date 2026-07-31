import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        # Znajdz Bruk-Bet w tabeli 1 ligi
        await page.goto("https://www.flashscore.pl/pilka-nozna/polska/betclic-1-liga/tabela/", 
                        wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        
        # Znajdz URL Bruk-Bet
        brukbet_url = await page.evaluate("""
            () => {
                const rows = document.querySelectorAll('.ui-table__row');
                for (const row of rows) {
                    const name = row.querySelector('.tableCellParticipant__name');
                    if (name && name.innerText.toLowerCase().includes('bruk')) {
                        const link = row.querySelector('a');
                        return link ? link.href : null;
                    }
                }
                return null;
            }
        """)
        
        print(f"URL Bruk-Bet: {brukbet_url}")
        
        if brukbet_url:
            # Wejdz na wyniki
            await page.goto(brukbet_url + "wyniki/", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            
            matches = await page.evaluate("""
                () => {
                    const out = [];
                    document.querySelectorAll('.event__match').forEach(el => {
                        const homeEl = el.querySelector('.event__homeParticipant, .event__participant--home');
                        const awayEl = el.querySelector('.event__awayParticipant, .event__participant--away');
                        const homeScoreEl = el.querySelector('.event__score--home');
                        const awayScoreEl = el.querySelector('.event__score--away');
                        const link = el.querySelector('a[href*="/mecz/"]');
                        
                        if (homeEl && awayEl && homeScoreEl && awayScoreEl) {
                            out.push({
                                home: homeEl.innerText.trim(),
                                away: awayEl.innerText.trim(),
                                score: homeScoreEl.innerText.trim() + ':' + awayScoreEl.innerText.trim(),
                                url: link ? link.href : ''
                            });
                        }
                    });
                    return out.slice(0, 15);
                }
            """)
            
            print(f"\nZnaleziono {len(matches)} meczow Bruk-Bet:")
            
            for i, m in enumerate(matches, 1):
                print(f"\n[{i}] {m['home']} vs {m['away']} ({m['score']})")
                
                # Sprawdz statystyki
                if m['url']:
                    base = m['url'].split('?')[0]
                    mid_part = '?' + m['url'].split('?')[1] if '?mid=' in m['url'] else ''
                    if not base.endswith('/'):
                        base += '/'
                    stats_url = base + "szczegoly/statystyki/ogolnie/" + mid_part
                    
                    try:
                        await page.goto(stats_url, wait_until="domcontentloaded", timeout=15000)
                        await asyncio.sleep(3)
                        count = await page.evaluate("document.querySelectorAll('[data-testid=\"wcl-statistics\"]').length")
                        print(f"    Statystyki: {count}")
                    except:
                        print(f"    BLAD ladowania")
        
        await browser.close()

asyncio.run(main())