from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    url = "https://www.flashscore.pl/mecz/pilka-nozna/gks-katowice-K4AgRmS1/wisla-krakow-rob20Q2Q/szczegoly/statystyki/ogolnie/?mid=21B0E0Q9"
    
    print("Wchodze...")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    
    try:
        page.click("#onetrust-accept-btn-handler", timeout=5000)
    except:
        pass
    
    print("Czekam 10 sekund...")
    time.sleep(10)
    
    page.evaluate("window.scrollBy(0, 500)")
    time.sleep(3)
    
    html = page.content()
    with open("debug_stats.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Zapisano debug_stats.html\n")
    
    print("=== WSZYSTKIE TEKSTY ZE STATYSTYKAMI ===\n")
    
    all_stats = page.evaluate("""
        () => {
            const results = [];
            const keywords = ['rożn', 'żółt', 'strza', 'posiadan', 'faul', 'ofsajd', 'obron', 'atak', 'kartk', 'czerw', 'corner'];
            document.querySelectorAll('div, span').forEach(el => {
                try {
                    if (el.children.length <= 3) {
                        const t = (el.innerText || '').trim();
                        if (t && t.length < 100) {
                            for (const kw of keywords) {
                                if (t.toLowerCase().includes(kw)) {
                                    results.push(t);
                                    break;
                                }
                            }
                        }
                    }
                } catch(e) {}
            });
            return [...new Set(results)];
        }
    """)
    
    for s in all_stats:
        print(f"  '{s}'")
    
    print(f"\nZnaleziono {len(all_stats)} statystyk")
    
    # Znajdz kontener statystyk
    print("\n=== SZUKAM STRUKTURY WIERSZY ===\n")
    
    rows_html = page.evaluate("""
        () => {
            // Znajdz element z tekstem "Rzuty rożne" i pokaz jego kontener
            let found = null;
            document.querySelectorAll('*').forEach(el => {
                try {
                    const t = (el.innerText || '').trim();
                    if (t === 'Rzuty rożne' && !found) {
                        found = el.closest('[class]');
                        for (let i = 0; i < 5 && found; i++) {
                            if (found.parentElement) found = found.parentElement;
                        }
                    }
                } catch(e) {}
            });
            return found ? found.outerHTML.substring(0, 3000) : 'NIE ZNALEZIONO';
        }
    """)
    
    print(rows_html)
    
    input("\nNacisnij ENTER...")
    browser.close()