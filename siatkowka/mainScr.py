import asyncio
from playwright.async_api import async_playwright
import json
import time
import os
import shutil

LEAGUES = [
    {
        "id": "tauron-liga-m",
        "name": "Tauron Liga",
        "flag": "🇵🇱",
        "fixtures_url": "https://www.flashscore.pl/siatkowka/polska/tauron-liga/terminarz/",
        "results_url": "https://www.flashscore.pl/siatkowka/polska/tauron-liga/wyniki/",
        "standings_url": "https://www.flashscore.pl/siatkowka/polska/tauron-liga/tabela/"
    },
    {
        "id": "tauron-1-liga-m",
        "name": "Tauron 1. Liga",
        "flag": "🇵🇱",
        "fixtures_url": "https://www.flashscore.pl/siatkowka/polska/tauron-i-liga/terminarz/",
        "results_url": "https://www.flashscore.pl/siatkowka/polska/tauron-i-liga/wyniki/",
        "standings_url": "https://www.flashscore.pl/siatkowka/polska/tauron-i-liga/tabela/"
    },
    {
        "id": "tauron-liga-k",
        "name": "Tauron Liga Kobiet",
        "flag": "🇵🇱",
        "fixtures_url": "https://www.flashscore.pl/siatkowka/polska/i-liga-kobiet/terminarz/",
        "results_url": "https://www.flashscore.pl/siatkowka/polska/i-liga-kobiet/wyniki/",
        "standings_url": "https://www.flashscore.pl/siatkowka/polska/i-liga-kobiet/tabela/"
    }
]


async def get_match_sets(page, match_url):
    """Pobiera wyniki setów z konkretnego meczu siatkówki."""
    try:
        base = match_url.split('?')[0]
        mid_part = ''
        if '?mid=' in match_url:
            mid_part = '?' + match_url.split('?')[1]
        if not base.endswith('/'):
            base += '/'
        summary_url = base + "podsumowanie-meczu/" + mid_part

        await page.goto(summary_url, wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(2.5)

        sets_data = await page.evaluate("""
            () => {
                const result = { home_sets: [], away_sets: [] };

                // Struktura Flashscore: 2 wiersze z partscore-strong (wynik ostateczny) + partscore (sety)
                const rows = document.querySelectorAll('.smh__part, .partScore, [class*="partScore"]');

                // Alternatywnie - szukaj tabeli setów
                const homeRow = document.querySelector('.duelParticipant__home');
                const awayRow = document.querySelector('.duelParticipant__away');

                // Bardziej niezawodne - z wcl-scores
                const scoreElements = document.querySelectorAll('[class*="event__part"]');

                // NAJPROSTSZE: bierzemy wszystkie liczby z detailScore
                const detailScores = document.querySelectorAll('.detailScore__matchInfo, .smh__part, [class*="smh__part"]');

                // Zbierzmy wszystkie liczby wyglądające jak wynik seta (od 15 do 40)
                const bodyText = document.body.innerText;

                // Fallback: parsuj header meczu z wynikami setów
                // Format wygląda jak "3 - 0" ogólnie + "25 14, 25 18, 35 33" per set
                return result;
            }
        """)

        # Metoda alternatywna - z parsowania URL/HTML bezpośrednio
        html = await page.content()
        return parse_sets_from_html(html)

    except Exception as e:
        print(f"    ⚠️ Błąd sets {match_url}: {e}")
        return None


def parse_sets_from_html(html):
    """Fallback - parsuj sety z HTML bezpośrednio (regex)."""
    import re
    result = {"home_sets": [], "away_sets": [], "total_points": 0, "sets_count": 0}

    # Szukamy sekcji z wynikami setów - Flashscore używa różnych klas
    # Wzorzec: liczby 15-40 pojawiające się parami
    # Najpewniejsze: HTML zawiera "Wynik" i pod nim liczby dla home/away

    # Szukamy wszystkich elementów z klasą smh__score lub podobną
    smh_pattern = re.compile(r'<div[^>]*class="[^"]*smh__part[^"]*"[^>]*>(\d+)</div>', re.IGNORECASE)
    matches = smh_pattern.findall(html)

    # Jeśli znaleźliśmy - to są liczby setów jeden po drugim
    if len(matches) >= 4 and len(matches) % 2 == 0:
        n_sets = len(matches) // 2
        for i in range(n_sets):
            try:
                home = int(matches[i * 2])
                away = int(matches[i * 2 + 1])
                if 0 <= home <= 50 and 0 <= away <= 50:
                    result["home_sets"].append(home)
                    result["away_sets"].append(away)
            except:
                continue

    # Fallback: szukaj po innej klasie
    if not result["home_sets"]:
        part_pattern = re.compile(r'event__part[^>]*>(\d+)</', re.IGNORECASE)
        parts = part_pattern.findall(html)
        if len(parts) >= 4 and len(parts) % 2 == 0:
            n_sets = len(parts) // 2
            for i in range(n_sets):
                try:
                    home = int(parts[i * 2])
                    away = int(parts[i * 2 + 1])
                    if 0 <= home <= 50 and 0 <= away <= 50:
                        result["home_sets"].append(home)
                        result["away_sets"].append(away)
                except:
                    continue

    # Wylicz totalpunkty i liczbę setów
    result["sets_count"] = len(result["home_sets"])
    result["total_points"] = sum(result["home_sets"]) + sum(result["away_sets"])

    # Wynik meczu (kto wygrał ile setów)
    home_won_sets = sum(1 for i in range(result["sets_count"]) if result["home_sets"][i] > result["away_sets"][i])
    away_won_sets = result["sets_count"] - home_won_sets
    result["home_sets_won"] = home_won_sets
    result["away_sets_won"] = away_won_sets
    result["match_score"] = f"{home_won_sets}:{away_won_sets}"

    return result


def calculate_team_stats(matches, team_name):
    """Wylicza statystyki drużyny z listy meczów (siatkówka)."""
    count = 0
    form = []
    sets_stats = {
        "over_35_sets": 0,
        "over_45_sets": 0,
        "tiebreak_5set": 0,  # czy był 5. set
        "won_first_set": 0,
        "total_sets": 0,
    }
    points_per_match = []
    sets_per_match = []
    sets_won_per_match = []

    for m in matches:
        try:
            if not m.get('sets_data'):
                continue
            sd = m['sets_data']
            if sd['sets_count'] == 0:
                continue

            count += 1
            is_home = team_name.lower()[:5] in m['home'].lower()

            # Forma - kto wygrał
            home_won = sd['home_sets_won']
            away_won = sd['away_sets_won']
            if is_home:
                if home_won > away_won:
                    form.append('W')
                else:
                    form.append('L')
                team_sets_won = home_won
                won_first = sd['home_sets'][0] > sd['away_sets'][0] if sd['home_sets'] else False
            else:
                if away_won > home_won:
                    form.append('W')
                else:
                    form.append('L')
                team_sets_won = away_won
                won_first = sd['away_sets'][0] > sd['home_sets'][0] if sd['home_sets'] else False

            sets_stats["total_sets"] += sd['sets_count']
            if sd['sets_count'] >= 4:
                sets_stats["over_35_sets"] += 1
            if sd['sets_count'] >= 5:
                sets_stats["over_45_sets"] += 1
                sets_stats["tiebreak_5set"] += 1
            if won_first:
                sets_stats["won_first_set"] += 1

            points_per_match.append(sd['total_points'])
            sets_per_match.append(sd['sets_count'])
            sets_won_per_match.append(team_sets_won)
        except Exception as e:
            continue

    if count == 0:
        return {}

    def pct(x):
        return round(x / count * 100)

    def avg(lst, dec=1):
        return round(sum(lst) / len(lst), dec) if lst else 0

    return {
        "total_matches": count,
        "form": form[:5],
        "over_35_sets_pct": pct(sets_stats["over_35_sets"]),
        "over_45_sets_pct": pct(sets_stats["over_45_sets"]),
        "tiebreak_pct": pct(sets_stats["tiebreak_5set"]),
        "won_first_set_pct": pct(sets_stats["won_first_set"]),
        "avg_sets": avg(sets_per_match),
        "avg_points": avg(points_per_match, 0),
        "avg_sets_won": avg(sets_won_per_match),
        "points_per_match": points_per_match,
        "sets_per_match": sets_per_match
    }
async def scrape_team_matches(page, team_name, team_url):
    """Pobiera ostatnie wyniki drużyny (dla statystyk historycznych)."""
    try:
        await page.goto(team_url + "wyniki/", wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(2.5)
    except Exception as e:
        print(f"   ✗ {team_name}: goto error")
        return team_name, {}

    try:
        matches_list = await page.evaluate("""
            () => {
                const matches = [];
                document.querySelectorAll('.event__match').forEach(el => {
                    const homeEl = el.querySelector('.event__homeParticipant, .event__participant--home');
                    const awayEl = el.querySelector('.event__awayParticipant, .event__participant--away');
                    const link = el.querySelector('a[href*="/mecz/"]');
                    if (homeEl && awayEl) {
                        matches.push({
                            home: homeEl.innerText.trim(),
                            away: awayEl.innerText.trim(),
                            match_id: el.id ? el.id.split('_').pop() : '',
                            url: link ? link.href : ''
                        });
                    }
                });
                return matches;
            }
        """)

        # Bierzemy ostatnie 5 meczów i pobieramy sety
        matches_with_sets = []
        for tm in matches_list[:5]:
            if tm.get('url'):
                sets_data = await get_match_sets(page, tm['url'])
                tm['sets_data'] = sets_data
                if sets_data and sets_data.get('sets_count', 0) > 0:
                    matches_with_sets.append(tm)

        team_stats = calculate_team_stats(matches_with_sets, team_name)
        print(f"   ✓ {team_name}: {len(matches_with_sets)}m")
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
        result = await scrape_team_in_page(page, team_name, team_url) if False else await scrape_team_matches(page, team_name, team_url)
        results.append(result)
    await context.close()
    return results


async def scrape_league(browser, league):
    print(f"\n{'='*60}")
    print(f"🏐 {league['flag']} {league['name']}")
    print(f"{'='*60}")

    matches = []
    standings = []
    finished_matches = []
    live_matches = []

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080}
    )
    page = await context.new_page()

    try:
        parse_matches_js = """
            () => {
                const matches = [];
                document.querySelectorAll('.event__match').forEach(el => {
                    const classes = el.className || '';
                    let status = 'scheduled';
                    if (classes.includes('event__match--live')) status = 'live';
                    else if (classes.includes('event__match--scheduled')) status = 'scheduled';
                    else status = 'finished';

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

                    if (!homeEl || !awayEl) return;

                    let homeScore = null;
                    let awayScore = null;
                    const hs = el.querySelector('.event__score--home');
                    const as = el.querySelector('.event__score--away');
                    if (hs && as) {
                        const hv = hs.innerText.trim();
                        const av = as.innerText.trim();
                        if (/^\\d+$/.test(hv) && /^\\d+$/.test(av)) {
                            homeScore = parseInt(hv);
                            awayScore = parseInt(av);
                        }
                    }

                    const timeStr = timeEl ? timeEl.innerText.trim() : '';
                    matches.push({
                        home: homeEl.innerText.trim(),
                        away: awayEl.innerText.trim(),
                        datetime: dateHeader ? (dateHeader + ' ' + timeStr) : (timeStr || 'TBA'),
                        status: status,
                        home_score: homeScore,
                        away_score: awayScore,
                        id: el.id,
                        url: link ? link.href : ''
                    });
                });
                return matches;
            }
        """

        print(f"[1a] Terminarz...")
        await page.goto(league['fixtures_url'], wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(1)
        fixtures_data = await page.evaluate(parse_matches_js)

        print(f"[1b] Wyniki...")
        await page.goto(league['results_url'], wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)
        for _ in range(2):
            try:
                await page.click("a:has-text('Pokaż więcej meczów')", timeout=2000)
                await asyncio.sleep(1.5)
            except:
                break
        results_data = await page.evaluate(parse_matches_js)

        seen_ids = set()
        matches_data = []
        for m in fixtures_data + results_data:
            mid = m.get('id', '')
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                matches_data.append(m)

        scheduled_matches = [m for m in matches_data if m['status'] == 'scheduled']
        live_matches = [m for m in matches_data if m['status'] == 'live']
        finished_matches = [m for m in matches_data if m['status'] == 'finished']

        print(f"    📅 Nadchodzących: {len(scheduled_matches)}")
        print(f"    🔴 LIVE: {len(live_matches)}")
        print(f"    ✅ Zakończonych: {len(finished_matches)}")

        selected = scheduled_matches[:10] + live_matches

        for m in selected:
            mid = m['id'].split('_')[-1] if m.get('id') else ''
            matches.append({
                "home": m['home'],
                "away": m['away'],
                "datetime": m['datetime'],
                "status": m['status'],
                "match_id": mid,
                "match_url": m.get('url', ''),
                "league_id": league['id'],
                "league_name": league['name'],
                "league_flag": league['flag'],
                "sport": "volleyball",
                "home_stats": {},
                "away_stats": {}
            })

        # [2] Pobierz sety zakończonych meczów (dla weryfikacji + statystyk)
        print(f"[2] Pobieranie setów {min(len(finished_matches), 15)} zakończonych meczów...")
        for i, fm in enumerate(finished_matches[:15]):
            if not fm.get('url'):
                continue
            print(f"    [{i+1}/{min(len(finished_matches), 15)}] {fm['home']} vs {fm['away']}")
            sd = await get_match_sets(page, fm['url'])
            fm['sets_data'] = sd

        # [3] Tabela
        print(f"[3] Tabela...")
        try:
            await page.goto(league['standings_url'], wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            standings = await page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('.ui-table__row');
                    const results = [];
                    rows.forEach((row, i) => {
                        const name = row.querySelector('.tableCellParticipant__name');
                        const link = row.querySelector('a');
                        if (name) {
                            results.push({
                                team: name.innerText.trim(),
                                rank: i + 1,
                                url: link ? link.href : ''
                            });
                        }
                    });
                    return results;
                }
            """)
        except:
            standings = []

        await context.close()

        # [4] Statystyki drużyn
        team_urls = []
        for t in standings:
            if t.get('url') and t.get('team'):
                team_urls.append((t['team'], t['url']))

        print(f"[4] Statystyki {len(team_urls)} drużyn...")

        CONCURRENT = 3
        chunks = [[] for _ in range(CONCURRENT)]
        for i, tu in enumerate(team_urls):
            chunks[i % CONCURRENT].append(tu)

        tasks = [scrape_team_worker(browser, chunk) for chunk in chunks if chunk]
        results_batches = await asyncio.gather(*tasks, return_exceptions=True)

        team_stats_cache = {}
        for batch in results_batches:
            if isinstance(batch, list):
                for result in batch:
                    if isinstance(result, tuple):
                        name, stats = result
                        team_stats_cache[name] = stats

        # [5] Łączenie
        print(f"[5] Łączenie...")
        for m in matches:
            for team_name, stats in team_stats_cache.items():
                if team_name.lower()[:6] in m['home'].lower() or m['home'].lower()[:6] in team_name.lower():
                    m['home_stats'] = stats
                if team_name.lower()[:6] in m['away'].lower() or m['away'].lower()[:6] in team_name.lower():
                    m['away_stats'] = stats

        return matches, standings, finished_matches, live_matches

    except Exception as e:
        print(f"❌ BLAD: {e}")
        try:
            await context.close()
        except:
            pass
        return matches, standings, finished_matches, live_matches


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
        all_finished = []
        all_live = {}

        for i, league in enumerate(LEAGUES):
            try:
                matches, standings, finished, live = await scrape_league(browser, league)
                all_matches.extend(matches)
                all_standings.extend(standings)

                for fm in finished:
                    sd = fm.get('sets_data')
                    if not sd or sd.get('sets_count', 0) == 0:
                        continue

                    score = sd['match_score']  # np. "3:0"
                    key = f"{fm['home']}_{fm['away']}"

                    all_finished.append({
                        "home": fm['home'],
                        "away": fm['away'],
                        "score": score,
                        "sets_home": sd['home_sets'],
                        "sets_away": sd['away_sets'],
                        "total_points": sd['total_points'],
                        "sets_count": sd['sets_count'],
                        "datetime": fm.get('datetime', ''),
                        "league_id": league['id'],
                        "league_name": league['name'],
                        "league_flag": league['flag'],
                        "sport": "volleyball",
                        "is_finished": True,
                        "is_live": False,
                        "stage": "Koniec"
                    })

                    all_live[key] = {
                        "home": fm['home'],
                        "away": fm['away'],
                        "is_live": False,
                        "is_finished": True,
                        "score": score,
                        "sets_home": sd['home_sets'],
                        "sets_away": sd['away_sets'],
                        "total_points": sd['total_points'],
                        "sets_count": sd['sets_count'],
                        "stage": "Koniec",
                        "datetime": fm.get('datetime', ''),
                        "league_id": league['id'],
                        "league_name": league['name'],
                        "league_flag": league['flag'],
                        "sport": "volleyball"
                    }

                for lm in live:
                    key = f"{lm['home']}_{lm['away']}"
                    score = "0:0"
                    if lm.get('home_score') is not None and lm.get('away_score') is not None:
                        score = f"{lm['home_score']}:{lm['away_score']}"

                    all_live[key] = {
                        "home": lm['home'],
                        "away": lm['away'],
                        "is_live": True,
                        "is_finished": False,
                        "score": score,
                        "stage": lm.get('datetime', ''),
                        "datetime": lm.get('datetime', ''),
                        "league_id": league['id'],
                        "league_name": league['name'],
                        "league_flag": league['flag'],
                        "sport": "volleyball"
                    }

                if i < len(LEAGUES) - 1:
                    print(f"\n⏸️  Pauza 15s przed następną ligą...")
                    await asyncio.sleep(15)
            except Exception as e:
                print(f"❌ Pomijam {league['name']}: {e}")
                continue

        await browser.close()

        PREFIX = "volley_pl"
        data_file = f"data_{PREFIX}.json"
        live_file = f"live_{PREFIX}.json"
        finished_file = f"finished_{PREFIX}.json"

        with open(data_file, "w", encoding="utf-8") as f:
            json.dump({
                "matches": all_matches,
                "standings": all_standings,
                "leagues": [{"id": l["id"], "name": l["name"], "flag": l["flag"]} for l in LEAGUES],
                "updated": time.strftime("%Y-%m-%d %H:%M")
            }, f, indent=4, ensure_ascii=False)

        with open(live_file, "w", encoding="utf-8") as f:
            json.dump({"matches": all_live, "updated": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=4, ensure_ascii=False)

        with open(finished_file, "w", encoding="utf-8") as f:
            json.dump({"matches": all_finished, "updated": time.strftime("%Y-%m-%d %H:%M")}, f, indent=4, ensure_ascii=False)

        # Kopiowanie do frontendu
        FRONTEND_DIR = os.path.abspath(os.path.join(os.getcwd(), ".."))
        print(f"\n📤 Kopiowanie do {FRONTEND_DIR}:")
        for filename in [data_file, live_file, finished_file]:
            try:
                shutil.copy2(filename, os.path.join(FRONTEND_DIR, filename))
                print(f"   ✅ {filename}")
            except Exception as e:
                print(f"   ❌ {filename}: {e}")

        elapsed = int(time.time() - start_time)
        print(f"\n{'='*60}")
        print(f"✅ ZAKONCZONO w {elapsed//60}m {elapsed%60}s")
        print(f"   📅 Meczów: {len(all_matches)}")
        print(f"   🔴 Live/Finished: {len(all_live)}")
        print(f"   ✅ Zakończonych: {len(all_finished)}")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())