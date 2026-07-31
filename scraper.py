import asyncio
from playwright.async_api import async_playwright
import json
import time

LEAGUES =   [
    {"id": "ekstraklasa", "name": "Ekstraklasa", "flag": "🇵🇱",
     "fixtures_url": "https://www.flashscore.pl/pilka-nozna/polska/ekstraklasa/terminarz/",
     "standings_url": "https://www.flashscore.pl/pilka-nozna/polska/ekstraklasa/tabela/"},
    {"id": "betclic-1-liga", "name": "Betclic 1 Liga", "flag": "🇵🇱",
     "fixtures_url": "https://www.flashscore.pl/pilka-nozna/polska/betclic-1-liga/terminarz/",
     "standings_url": "https://www.flashscore.pl/pilka-nozna/polska/betclic-1-liga/tabela/"},
    {"id": "premier-league", "name": "Premier League", "flag": "🇬🇧",
     "fixtures_url": "https://www.flashscore.pl/pilka-nozna/anglia/premier-league/terminarz/",
     "standings_url": "https://www.flashscore.pl/pilka-nozna/anglia/premier-league/tabela/"},
    {"id": "la-liga", "name": "La Liga", "flag": "🇪🇸",
     "fixtures_url": "https://www.flashscore.pl/pilka-nozna/hiszpania/laliga/terminarz/",
     "standings_url": "https://www.flashscore.pl/pilka-nozna/hiszpania/laliga/tabela/"},
    {"id": "serie-a", "name": "Serie A", "flag": "🇮🇹",
     "fixtures_url": "https://www.flashscore.pl/pilka-nozna/wlochy/serie-a/terminarz/",
     "standings_url": "https://www.flashscore.pl/pilka-nozna/wlochy/serie-a/tabela/"},
    {"id": "bundesliga", "name": "Bundesliga", "flag": "🇩🇪",
     "fixtures_url": "https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga/terminarz/",
     "standings_url": "https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga/tabela/"},
    {"id": "ligue-1", "name": "Ligue 1", "flag": "🇫🇷",
     "fixtures_url": "https://www.flashscore.pl/pilka-nozna/francja/ligue-1/terminarz/",
     "standings_url": "https://www.flashscore.pl/pilka-nozna/francja/ligue-1/tabela/"}
    ATP_URLS = [
    {"id": "atp", "name": "ATP", "flag": "🎾",
     "url": "https://www.flashscore.pl/tenis/atp-singiel/montreal/"},
    {"id": "wta", "name": "WTA", "flag": "🎾",
     "url": "https://www.flashscore.pl/tenis/wta-singiel/toronto/"},
]
     "standings_url": ""
]

CONCURRENT_TEAMS = 3

async def get_match_stats(page, match_url):
    try:
        base = match_url.split('?')[0]
        mid_part = ''
        if '?mid=' in match_url:
            mid_part = '?' + match_url.split('?')[1]
        if not base.endswith('/'):
            base += '/'
        stats_url = base + "szczegoly/statystyki/ogolnie/" + mid_part
        
        await page.goto(stats_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        stats = await page.evaluate("""
            () => {
                const result = {
                    corners: {home: null, away: null}, yellow: {home: null, away: null},
                    red: {home: null, away: null}, shots: {home: null, away: null},
                    shots_on_target: {home: null, away: null}, xg: {home: null, away: null},
                    possession: {home: null, away: null}, fouls: {home: null, away: null},
                    offsides: {home: null, away: null}
                };
                document.querySelectorAll('[data-testid="wcl-statistics"]').forEach(row => {
                    try {
                        const category = row.querySelector('[data-testid="wcl-statistics-category"]');
                        const values = row.querySelectorAll('[data-testid="wcl-statistics-value"]');
                        if (!category || values.length < 2) return;
                        const catText = category.innerText.toLowerCase();
                        const homeVal = values[0].innerText.trim().replace('%', '').split('\\n')[0];
                        const awayVal = values[1].innerText.trim().replace('%', '').split('\\n')[0];
                        const parseNum = (v) => { const n = parseFloat(v); return isNaN(n) ? null : n; };
                        if (catText.includes('rzuty rożne')) { result.corners.home = parseNum(homeVal); result.corners.away = parseNum(awayVal); }
                        else if (catText.includes('żółte kartki')) { result.yellow.home = parseNum(homeVal); result.yellow.away = parseNum(awayVal); }
                        else if (catText.includes('czerwone kartki')) { result.red.home = parseNum(homeVal); result.red.away = parseNum(awayVal); }
                        else if (catText.includes('strzały łącznie') || catText === 'strzały') { result.shots.home = parseNum(homeVal); result.shots.away = parseNum(awayVal); }
                        else if (catText.includes('strzały na bramkę')) { result.shots_on_target.home = parseNum(homeVal); result.shots_on_target.away = parseNum(awayVal); }
                        else if (catText.includes('oczekiwane gole') || catText === 'xg') { result.xg.home = parseNum(homeVal); result.xg.away = parseNum(awayVal); }
                        else if (catText.includes('posiadanie')) { result.possession.home = parseNum(homeVal); result.possession.away = parseNum(awayVal); }
                        else if (catText.includes('faule')) { result.fouls.home = parseNum(homeVal); result.fouls.away = parseNum(awayVal); }
                        else if (catText.includes('spalone')) { result.offsides.home = parseNum(homeVal); result.offsides.away = parseNum(awayVal); }
                    } catch(e) {}
                });
                return result;
            }
        """)
        return stats
    except:
        return None

async def get_match_h2h_and_odds(page, match_url):
    """Pobiera H2H i kursy 1X2 dla konkretnego meczu"""
    result = {"h2h": [], "odds": {"home": None, "draw": None, "away": None}}
    try:
        # Base URL bez query
        base = match_url.split('?')[0]
        mid_part = ''
        if '?mid=' in match_url:
            mid_part = '?' + match_url.split('?')[1]
        if not base.endswith('/'):
            base += '/'
        
        # H2H
        h2h_url = base + "szczegoly/h2h/" + mid_part
        try:
            await page.goto(h2h_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2.5)
            
            h2h = await page.evaluate("""
                () => {
                    const results = [];
                    // Szukamy sekcji H2H (bezposrednie)
                    const sections = document.querySelectorAll('.h2h__section');
                    let directSection = null;
                    sections.forEach(s => {
                        const title = s.querySelector('.section__title');
                        if (title && title.innerText.toLowerCase().includes('bezpo')) {
                            directSection = s;
                        }
                    });
                    // Jesli nie ma - bierzemy 3 sekcje (home/away/direct)
                    const target = directSection || sections[2] || sections[0];
                    if (target) {
                        target.querySelectorAll('.h2h__row').forEach(r => {
                            const date = r.querySelector('.h2h__date');
                            const home = r.querySelector('.h2h__homeParticipant, .h2h__participant--home');
                            const away = r.querySelector('.h2h__awayParticipant, .h2h__participant--away');
                            const resultEl = r.querySelector('.h2h__result');
                            
                            let score = '';
                            if (resultEl) {
                                const scores = resultEl.querySelectorAll('span');
                                if (scores.length >= 2) score = scores[0].innerText.trim() + ':' + scores[1].innerText.trim();
                                else score = resultEl.innerText.trim().replace(/\\s+/g, '');
                            }
                            
                            if (home && away && score) {
                                results.push({
                                    date: date ? date.innerText.trim() : '',
                                    home: home.innerText.trim(),
                                    away: away.innerText.trim(),
                                    result: score
                                });
                            }
                        });
                    }
                    return results.slice(0, 5);
                }
            """)
            result["h2h"] = h2h
        except:
            pass
        
        # KURSY 1X2
        try:
            odds_url = base + "porownanie-kursow/koncowy/pelny-czas/" + mid_part
            await page.goto(odds_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            odds = await page.evaluate("""
                () => {
                    const result = { home: null, draw: null, away: null };
                    // Szukamy wierszy z kursami (biorzemy pierwszy)
                    const rows = document.querySelectorAll('.oddsCell__odd, [class*="oddsCell"]');
                    if (rows.length >= 3) {
                        result.home = parseFloat(rows[0].innerText.trim());
                        result.draw = parseFloat(rows[1].innerText.trim());
                        result.away = parseFloat(rows[2].innerText.trim());
                    }
                    // Alternatywnie
                    if (!result.home) {
                        const table = document.querySelector('.ui-table__body');
                        if (table) {
                            const firstRow = table.querySelector('.ui-table__row');
                            if (firstRow) {
                                const cells = firstRow.querySelectorAll('.oddsCell__odd, span');
                                const nums = [];
                                cells.forEach(c => {
                                    const n = parseFloat(c.innerText.trim());
                                    if (!isNaN(n) && n > 1) nums.push(n);
                                });
                                if (nums.length >= 3) {
                                    result.home = nums[0];
                                    result.draw = nums[1];
                                    result.away = nums[2];
                                }
                            }
                        }
                    }
                    return result;
                }
            """)
            if odds and odds.get("home"):
                result["odds"] = odds
        except:
            pass
            
    except:
        pass
    
    return result

def calculate_team_stats(matches, team_name, match_details):
    btts = over15 = over25 = over35 = count = 0
    totals = {'corners': 0, 'yellow': 0, 'red': 0, 'shots': 0, 'shots_ot': 0, 'xg': 0, 'fouls': 0, 'offsides': 0}
    counts = {'corners': 0, 'yellow': 0, 'red': 0, 'shots': 0, 'shots_ot': 0, 'xg': 0, 'fouls': 0, 'offsides': 0}
    goals_scored = goals_conceded = 0
    form = []
    per_match = {'corners': [], 'yellow': [], 'red': [], 'shots': [], 'shots_ot': [], 'xg': [], 'fouls': [], 'offsides': []}
    
    for m in matches:
        try:
            hg = int(m['home_score'])
            ag = int(m['away_score'])
            count += 1
            is_home = team_name.lower()[:5] in m['home'].lower()
            
            if is_home:
                goals_scored += hg
                goals_conceded += ag
                if hg > ag: form.append('W')
                elif ag > hg: form.append('L')
                else: form.append('D')
            else:
                goals_scored += ag
                goals_conceded += hg
                if ag > hg: form.append('W')
                elif hg > ag: form.append('L')
                else: form.append('D')
            
            if hg > 0 and ag > 0: btts += 1
            if hg + ag > 1: over15 += 1
            if hg + ag > 2: over25 += 1
            if hg + ag > 3: over35 += 1
            
            if m.get('match_id') and m['match_id'] in match_details:
                d = match_details[m['match_id']]
                mapping = {'corners': 'corners', 'yellow': 'yellow', 'red': 'red', 'shots': 'shots',
                          'shots_ot': 'shots_on_target', 'xg': 'xg', 'fouls': 'fouls', 'offsides': 'offsides'}
                for key, dkey in mapping.items():
                    if d[dkey]['home'] is not None:
                        val = d[dkey]['home'] if is_home else d[dkey]['away']
                        totals[key] += val
                        counts[key] += 1
                        per_match[key].append(val)
        except:
            continue
    
    if count == 0:
        return {}
    
    def avg(key, decimals=1):
        return round(totals[key] / counts[key], decimals) if counts[key] > 0 else 0
    
    return {
        "total_matches": count,
        "btts_pct": round(btts/count*100),
        "over15_pct": round(over15/count*100),
        "over25_pct": round(over25/count*100),
        "over35_pct": round(over35/count*100),
        "avg_goals_scored": round(goals_scored/count, 2),
        "avg_goals_conceded": round(goals_conceded/count, 2),
        "avg_corners": avg('corners'),
        "avg_yellow": avg('yellow'),
        "avg_red": avg('red', 2),
        "avg_shots": avg('shots'),
        "avg_shots_on_target": avg('shots_ot'),
        "avg_xg": avg('xg', 2),
        "avg_fouls": avg('fouls'),
        "avg_offsides": avg('offsides'),
        "form": form[:5],
        "corners_per_match": per_match['corners'],
        "yellow_per_match": per_match['yellow'],
        "shots_per_match": per_match['shots'],
        "xg_per_match": per_match['xg']
    }

async def scrape_team_in_page(page, team_name, team_url):
    # Retry 2 razy jeśli timeout
    for attempt in range(2):
        try:
            await page.goto(team_url + "wyniki/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            break
        except Exception as e:
            if attempt == 1:
                print(f"   ✗ {team_name}: {str(e)[:60]}")
                return team_name, {}
            await asyncio.sleep(5)  # poczekaj przed retry
    
    try:
        matches_data = await page.evaluate("""
            () => {
                const matches = [];
                document.querySelectorAll('.event__match').forEach(el => {
                    const homeEl = el.querySelector('.event__homeParticipant, .event__participant--home');
                    const awayEl = el.querySelector('.event__awayParticipant, .event__participant--away');
                    const homeScoreEl = el.querySelector('.event__score--home');
                    const awayScoreEl = el.querySelector('.event__score--away');
                    const link = el.querySelector('a[href*="/mecz/"]');
                    if (homeEl && awayEl && homeScoreEl && awayScoreEl) {
                        matches.push({
                            home: homeEl.innerText.trim(),
                            away: awayEl.innerText.trim(),
                            home_score: homeScoreEl.innerText.trim(),
                            away_score: awayScoreEl.innerText.trim(),
                            match_id: el.id ? el.id.split('_').pop() : '',
                            url: link ? link.href : ''
                        });
                    }
                });
                return matches;
            }
        """)
        
        matches = matches_data[:15]
        match_details = {}
        successful = 0
        
        for tm in matches[:12]:
            if successful >= 5:
                break
            if tm.get('url'):
                stats = await get_match_stats(page, tm['url'])
                if stats:
                    has_data = any(v['home'] is not None for v in stats.values())
                    if has_data:
                        match_details[tm['match_id']] = stats
                        successful += 1
        
        team_stats = calculate_team_stats(matches, team_name, match_details)
        print(f"   ✓ {team_name}: {successful}m")
        return team_name, team_stats
    except Exception as e:
        print(f"   ✗ {team_name}: {str(e)[:60]}")
        return team_name, {}
        await asyncio.sleep(3)
        
        matches_data = await page.evaluate("""
            () => {
                const matches = [];
                document.querySelectorAll('.event__match').forEach(el => {
                    const homeEl = el.querySelector('.event__homeParticipant, .event__participant--home');
                    const awayEl = el.querySelector('.event__awayParticipant, .event__participant--away');
                    const homeScoreEl = el.querySelector('.event__score--home');
                    const awayScoreEl = el.querySelector('.event__score--away');
                    const link = el.querySelector('a[href*="/mecz/"]');
                    if (homeEl && awayEl && homeScoreEl && awayScoreEl) {
                        matches.push({
                            home: homeEl.innerText.trim(),
                            away: awayEl.innerText.trim(),
                            home_score: homeScoreEl.innerText.trim(),
                            away_score: awayScoreEl.innerText.trim(),
                            match_id: el.id ? el.id.split('_').pop() : '',
                            url: link ? link.href : ''
                        });
                    }
                });
                return matches;
            }
        """)
        
        matches = matches_data[:15]
        match_details = {}
        successful = 0
        
        for tm in matches[:12]:
            if successful >= 5:
                break
            if tm.get('url'):
                stats = await get_match_stats(page, tm['url'])
                if stats:
                    has_data = any(v['home'] is not None for v in stats.values())
                    if has_data:
                        match_details[tm['match_id']] = stats
                        successful += 1
        
        team_stats = calculate_team_stats(matches, team_name, match_details)
        print(f"   ✓ {team_name}: {successful}m")
        return team_name, team_stats
    except Exception as e:
        print(f"   ✗ {team_name}: {str(e)[:60]}")
        return team_name, {}

async def scrape_team_worker(browser, team_batch):
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080}
    )
    page = await context.new_page()
    results = []
    for team_name, team_url in team_batch:
        result = await scrape_team_in_page(page, team_name, team_url)
        results.append(result)
    await context.close()
    return results

async def get_upcoming_match_url(page, match_id, home, away):
    """Buduje URL nadchodzacego meczu (potrzebne do H2H i kursow)"""
    # Flashscore używa formatu: /mecz/pilka-nozna/{home-slug}/{away-slug}/?mid={match_id}
    # Ale my mamy tylko match_id. Musimy znaleźć URL z terminarza.
    # Prosciej - używamy shortcut ?mid=
    return f"https://www.flashscore.pl/mecz/pilka-nozna/?mid={match_id}"

async def scrape_league(browser, league):
    print(f"\n{'='*60}")
    print(f"🏆 {league['flag']} {league['name']}")
    print(f"{'='*60}")
    
    matches = []
    standings = []
    
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080}
    )
    page = await context.new_page()
    
    try:
        print(f"[1] Terminarz...")
        await page.goto(league['fixtures_url'], wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2)
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(1)
        
        matches_data = await page.evaluate("""
            () => {
                const matches = [];
                document.querySelectorAll('.event__match').forEach(el => {
                    const homeEl = el.querySelector('.event__homeParticipant, .event__participant--home');
                    const awayEl = el.querySelector('.event__awayParticipant, .event__participant--away');
                    const timeEl = el.querySelector('.event__stageTime, .event__time');
                    const link = el.querySelector('a[href*="/mecz/"]');
                    let dateHeader = '';
                    let node = el;
                    while (node) {
                        node = node.previousElementSibling;
                        if (!node) break;
                        if (node.className && (node.className.includes('event__header') || node.className.includes('date'))) {
                            dateHeader = node.innerText.trim().split('\\n')[0];
                            break;
                        }
                    }
                    if (homeEl && awayEl) {
                        const timeStr = timeEl ? timeEl.innerText.trim() : '';
                        matches.push({
                            home: homeEl.innerText.trim(),
                            away: awayEl.innerText.trim(),
                            datetime: dateHeader ? (dateHeader + ' ' + timeStr) : timeStr || 'TBA',
                            id: el.id,
                            url: link ? link.href : ''
                        });
                    }
                });
                return matches;
            }
        """)
        
        selected = matches_data[:10]
        print(f"    {len(selected)} meczow")
        
        for m in selected:
            mid = m['id'].split('_')[-1] if m.get('id') else ''
            matches.append({
                "home": m['home'], "away": m['away'], "datetime": m['datetime'],
                "match_id": mid, "match_url": m.get('url', ''),
                "league_id": league['id'], "league_name": league['name'],
                "league_flag": league['flag'], "home_stats": {}, "away_stats": {},
                "h2h": [], "odds": {"home": None, "draw": None, "away": None}
            })
        
        print(f"[2] Tabela...")
        await page.goto(league['standings_url'], wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2)
        
        standings = await page.evaluate("""
            () => {
                const rows = document.querySelectorAll('.ui-table__row');
                const results = [];
                rows.forEach((row, i) => {
                    const name = row.querySelector('.tableCellParticipant__name');
                    const pts = row.querySelector('.table__cell--points');
                    const link = row.querySelector('a');
                    if (name) {
                        results.push({
                            team: name.innerText.trim(),
                            points: pts ? pts.innerText.trim() : '0',
                            rank: i + 1,
                            url: link ? link.href : ''
                        });
                    }
                });
                return results;
            }
        """)
        for s in standings:
            s['league_id'] = league['id']
        
        # H2H + KURSY dla każdego meczu
        print(f"[3] H2H i kursy dla {len(matches)} meczów...")
        for i, m in enumerate(matches):
            if m.get('match_url'):
                print(f"    [{i+1}/{len(matches)}] {m['home']} vs {m['away']}")
                data = await get_match_h2h_and_odds(page, m['match_url'])
                m['h2h'] = data['h2h']
                m['odds'] = data['odds']
        
        await context.close()
        
        # STATYSTYKI DRUŻYN
        teams_in_matches = set()
        for m in matches:
            teams_in_matches.add(m['home'].lower())
            teams_in_matches.add(m['away'].lower())
        
        team_urls = []
        for t in standings:
            if t['url']:
                t_lower = t['team'].lower()
                for tm in teams_in_matches:
                    if t_lower[:6] in tm or tm[:6] in t_lower:
                        team_urls.append((t['team'], t['url']))
                        break
        
        print(f"[4] Statystyki {len(team_urls)} drużyn w {CONCURRENT_TEAMS} workerach...")
        
        chunks = [[] for _ in range(CONCURRENT_TEAMS)]
        for i, tu in enumerate(team_urls):
            chunks[i % CONCURRENT_TEAMS].append(tu)
        
        tasks = [scrape_team_worker(browser, chunk) for chunk in chunks if chunk]
        results_batches = await asyncio.gather(*tasks, return_exceptions=True)
        
        team_stats_cache = {}
        for batch in results_batches:
            if isinstance(batch, list):
                for result in batch:
                    if isinstance(result, tuple):
                        name, stats = result
                        team_stats_cache[name] = stats
        
        print(f"[5] Łączenie...")
        for m in matches:
            for team_name, stats in team_stats_cache.items():
                if team_name.lower()[:6] in m['home'].lower() or m['home'].lower()[:6] in team_name.lower():
                    m['home_stats'] = stats
                if team_name.lower()[:6] in m['away'].lower() or m['away'].lower()[:6] in team_name.lower():
                    m['away_stats'] = stats
        
        return matches, standings
        
    except Exception as e:
        print(f"❌ BLAD: {e}")
        try:
            await context.close()
        except:
            pass
        return matches, standings

async def main():
    start_time = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto("https://www.flashscore.pl/", wait_until="domcontentloaded", timeout=15000)
            await page.click("#onetrust-accept-btn-handler", timeout=5000)
        except:
            pass
        await context.close()
        
        all_matches = []
        all_standings = []
        
        for i, league in enumerate(LEAGUES):
            try:
                matches, standings = await scrape_league(browser, league)
                all_matches.extend(matches)
                all_standings.extend(standings)
                # Pauza między ligami żeby Flashscore ochłonął
                if i < len(LEAGUES) - 1:
                    print(f"\n⏸️  Pauza 15 sekund przed następną ligą...")
                    await asyncio.sleep(15)
            except Exception as e:
                print(f"❌ Pomijam {league['name']}: {e}")
                continue        
        await browser.close()
        
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump({
                "matches": all_matches, "standings": all_standings,
                "leagues": [{"id": l["id"], "name": l["name"], "flag": l["flag"]} for l in LEAGUES],
                "updated": time.strftime("%Y-%m-%d %H:%M")
            }, f, indent=4, ensure_ascii=False)
        
        elapsed = int(time.time() - start_time)
        print(f"\n{'='*60}")
        print(f"✅ ZAKONCZONO w {elapsed//60}m {elapsed%60}s")
        print(f"   Meczow: {len(all_matches)} | Druzyn: {len(all_standings)}")
        print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())