import subprocess
import time
from datetime import datetime

INTERVAL_MINUTES = 60  # co ile minut uruchamiać

def run_scraper():
    print(f"\n{'='*60}")
    print(f"🚀 START scrapera: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(['python', 'scraper.py'], capture_output=False, timeout=3600)
        print(f"\n✅ Scraper zakończony (exit code: {result.returncode})")
    except subprocess.TimeoutExpired:
        print("\n⚠️ Scraper przekroczył 20 minut - anulowany")
    except Exception as e:
        print(f"\n❌ Błąd: {e}")

def main():
    print(f"🤖 AUTO SCRAPER uruchomiony")
    print(f"⏰ Odpala scraper co {INTERVAL_MINUTES} minut")
    print(f"❗ Aby zatrzymać: naciśnij Ctrl+C\n")
    
    while True:
        run_scraper()
        
        next_run = datetime.now().timestamp() + (INTERVAL_MINUTES * 60)
        next_time = datetime.fromtimestamp(next_run).strftime('%H:%M:%S')
        
        print(f"\n💤 Następne uruchomienie o: {next_time}")
        print(f"⏳ Czekam {INTERVAL_MINUTES} minut...")
        
        try:
            time.sleep(INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            print("\n\n👋 Zatrzymano ręcznie. Do zobaczenia!")
            break

if __name__ == "__main__":
    main()