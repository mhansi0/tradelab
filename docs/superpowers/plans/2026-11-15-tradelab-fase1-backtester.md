# Tradelab fase 1 (backtester) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een publieke Claude-plugin op GitHub waarmee iemand in Claude een strategie in gewone tekst uitlegt, die laat backtesten op lokaal opgeslagen data, en een rapport krijgt met grote grafieken en 3 voorbeeldtrades.

**Architecture:** Een Python-pakket `tradelab` met drie lagen: data (download bij Twelve Data, opslag als parquet, timeframes lokaal samengesteld), rekenmotor (strategie als vaste regels met veilige formules, backtest, statistieken) en uitvoer (Plotly-grafieken in één HTML-rapport). Een MCP-server maakt die lagen aanroepbaar voor Claude. Twee skills vertellen Claude hoe het gesprek loopt. Claude doet het vertalen en het schrijven, het pakket doet het rekenen.

**Tech Stack:** Python 3.12 (via uv), `mcp` (FastMCP), pandas, pyarrow, plotly, httpx, pydantic 2, pytest. Git en GitHub.

**Spec:** `docs/superpowers/specs/2026-11-15-backtester-design.md`

**Naam:** `tradelab` is een werknaam. Wil de maker een andere naam, vervang die dan overal voor Task 1 begint.

## Wat vooraf gecontroleerd is (15 november 2026)

- Het gratis Twelve Data-plan geeft 800 aanroepen per dag.
- Intraday data (1 en 5 minuten) gaat terug tot begin 2020 voor `XAU/USD`, `SPY`, `QQQ` en `SLV`.
- `XAG/USD` (zilver) is niet beschikbaar op het gratis plan. Het vraagt het Grow- of Venture-plan (https://twelvedata.com/pricing). Daarom gebruikt fase 1 het zilverfonds `SLV` als vervanger, met een duidelijke melding.
- Op de computer van de maker staan Python 3.15.2, git 2.56 en Node 26. `uv` en `gh` staan er niet.
- Niet gecontroleerd: het exacte antwoordformaat van de Twelve Data-API, het huidige plugin-formaat van Claude Code, en de huidige FastMCP-API. Elke taak die ervan afhangt begint met een controlestap.

## Voor je begint (door de maker, ongeveer 20 minuten)

- [ ] **Kies een projectmap.** De huidige map wordt verwijderd met deze sessie. Zeg in het gesprek waar het project moet staan, dan verhuist Claude de sessie.
- [ ] **Installeer uv** (beheert Python en de pakketten). In PowerShell: `winget install --id=astral-sh.uv -e`. Controle: `uv --version` toont een versie.
- [ ] **Maak een gratis Twelve Data-account** op https://twelvedata.com en kopieer je API-sleutel. Zet hem zelf in het bestand `%USERPROFILE%\.tradelab\twelvedata.key` (alleen de sleutel, één regel). Deel de sleutel niet in het gesprek.
- [ ] **Maak een GitHub-account** op https://github.com als je er nog geen hebt. De repo zelf maak je pas in Task 14.

## Global Constraints

- Markten: `SP500` → `SPY`, `NAS100` → `QQQ`, `GOLD` → `XAU/USD`, `SILVER` → `SLV` (vervanger). Geen andere markten.
- Timeframes: `1min`, `5min`, `15min`, `30min`, `1h`, `4h`, `1day`.
- Alleen koersen worden opgeslagen (open, high, low, close, volume). Indicatoren worden altijd berekend.
- Alle tijden in opslag en uitvoer zijn UTC.
- Tekst van een model wordt nooit uitgevoerd met `eval`, `exec` of `compile`. Formules gaan door de whitelist in `expr.py`.
- Geen vooruitkijken: een signaal op candle N geeft een instap op de open van candle N+1.
- Eén positie tegelijk. Raken SL en TP in dezelfde candle, dan telt de SL. Resultaten in R, zonder kosten.
- De API-sleutel komt nooit in een log, foutmelding, testbestand of commit.
- Python: `requires-python = ">=3.11,<3.14"`, vastgezet op 3.12 met `.python-version`. Python 3.15 van de maker wordt niet gebruikt, omdat pakketten daar mogelijk nog niet voor bestaan.
- Code, foutmeldingen, README en rapport in het Engels (publieke repo). Claude vertaalt in het gesprek.
- Vaste tekst in README en rapport: `Not financial advice. This tool explains backtests and past trades for learning purposes. It does not tell you what to buy or sell.`
- Opslagmap: omgevingsvariabele `TRADELAB_HOME`, anders `~/.tradelab`.
- Alle opdrachten draaien met `uv run`. Elke taak eindigt met een commit.

## Review Focus

1. **Een strategie zonder enkele trade.** Verwacht: cijfers op nul, een rapport dat dit zegt, geen deling door nul. Tests in Task 9, 10 en 11.
2. **Gaten in de data** (weekend, ontbrekende candles, een dag waarvan de eerste candle mist). Verwacht: geen crash, `first.*` gebruikt de eerste candle die er wel is. Tests in Task 4 en 7.
3. **Een formule met een onbekende naam of een aanvalspoging** (`__import__('os')`). Verwacht: een foutmelding die de formule noemt, en er wordt niets uitgevoerd. Tests in Task 6 en 7.
4. **Een download die afbreekt, een limietmelding (429) of een ontbrekende sleutel.** Verwacht: opnieuw starten gaat verder zonder dubbele rijen, de melding zegt wat te doen en toont de sleutel niet. Tests in Task 5.
5. **Een strategienaam met vreemde tekens of een naam die al bestaat.** Verwacht: een veilige mapnaam, geen pad buiten de opslagmap, niet stil overschrijven. Tests in Task 2 en 7.

## Bestanden

```
.claude-plugin/plugin.json        plugin-beschrijving
.claude-plugin/marketplace.json   zodat anderen de plugin kunnen installeren
.mcp.json                         start de MCP-server
skills/backtest/SKILL.md          skill 1: nieuwe strategie backtesten
skills/strategy/SKILL.md          skill 2: bewaarde strategie heropenen
pyproject.toml  .python-version  .gitignore  LICENSE  README.md
src/tradelab/__init__.py          versie
src/tradelab/paths.py             opslagmap, veilige namen
src/tradelab/markets.py           de 4 markten, timeframes, handelsdag
src/tradelab/indicators.py        sma, ema, rsi, macd, atr, bollinger
src/tradelab/store.py             parquet lezen en schrijven, timeframes samenstellen
src/tradelab/twelvedata.py        ophalen bij Twelve Data, limiet respecteren
src/tradelab/download.py          opdracht `tradelab download`, hervatbaar
src/tradelab/expr.py              veilige formules
src/tradelab/strategy.py          regels valideren, bewaren, uitleggen
src/tradelab/engine.py            backtest
src/tradelab/stats.py             cijfers en keuze van 3 voorbeelden
src/tradelab/charts.py            Plotly-grafieken
src/tradelab/report.py            HTML-rapport
src/tradelab/server.py            MCP-tools
tests/                            één testbestand per module
docs/strategy-format.md           het regelformaat, voor mensen en voor Claude
docs/data-sources.md              wat de databron wel en niet geeft
```

**Dataconventie (geldt overal):** een candle-tabel is een `pd.DataFrame` met een `DatetimeIndex` in UTC met de naam `time`, en de kolommen `open`, `high`, `low`, `close`, `volume` als float. Volume is `0.0` als de bron er geen heeft.

---

### Task 1: Projectskelet en git

**Files:**
- Create: `pyproject.toml`, `.python-version`, `.gitignore`, `LICENSE`, `README.md`, `src/tradelab/__init__.py`
- Test: `tests/test_smoke.py`

**Interfaces:**
- Produces: importeerbaar pakket `tradelab` met `tradelab.__version__ == "0.1.0"`, en de opdrachten `tradelab` en `tradelab-mcp` (die pas in Task 5 en 11 werken).

- [ ] **Step 1:** `git init -b main` in de projectmap. Kopieer `docs/superpowers/` (ontwerp en dit plan) mee.
- [ ] **Step 2: Schrijf de falende test**

```python
def test_version():
    import tradelab
    assert tradelab.__version__ == "0.1.0"
```

- [ ] **Step 3:** Maak `pyproject.toml` met deze vaste waarden:

```toml
[project]
name = "tradelab"
version = "0.1.0"
requires-python = ">=3.11,<3.14"
dependencies = ["mcp", "pandas", "pyarrow", "plotly", "httpx", "pydantic>=2"]

[project.scripts]
tradelab = "tradelab.download:main"
tradelab-mcp = "tradelab.server:main"

[dependency-groups]
dev = ["pytest"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/tradelab"]
```

`.python-version` bevat `3.12`. `.gitignore` bevat `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.key`, `.env`, `data/`. `LICENSE` is MIT. `README.md` is voorlopig de titel plus de vaste tekst uit Global Constraints.
- [ ] **Step 4:** Run `uv sync` en daarna `uv run pytest -v`. Verwacht: 1 passed.
- [ ] **Step 5:** Commit: `chore: project skeleton`.

---

### Task 2: Opslagmap, markten en handelsdag

**Files:**
- Create: `src/tradelab/paths.py`, `src/tradelab/markets.py`
- Test: `tests/test_paths.py`, `tests/test_markets.py`

**Interfaces:**
- Produces:
  - `paths.home() -> Path`
  - `paths.data_file(market: str, base: str) -> Path` geeft `home()/data/<MARKET>/<base>.parquet`
  - `paths.slugify(name: str) -> str` (kleine letters, alleen `a-z0-9-`, `ValueError` als er niets overblijft)
  - `paths.strategy_dir(name: str) -> Path` geeft `home()/strategies/<slug>`
  - `markets.Market` (frozen dataclass: `key, symbol, label, timezone, session_start, note`)
  - `markets.MARKETS: dict[str, Market]`, `markets.TIMEFRAMES: dict[str, int]` (minuten), `markets.get_market(key) -> Market` (`ValueError` met de geldige sleutels)
  - `markets.session_keys(index: pd.DatetimeIndex, timezone: str, session_start: str) -> pd.DataFrame` met kolommen `session` (datum van de handelsdag) en `minute` (minuten sinds de start van die handelsdag), zelfde index.

Vaste waarden: `SP500`, `NAS100` en `SILVER` gebruiken `America/New_York` en `09:30`. `GOLD` gebruikt `UTC` en `00:00`. De `note` van `SILVER` is `Proxy: SLV silver fund, US market hours only. Spot silver needs a paid data plan.`

- [ ] **Step 1: Schrijf de falende tests**

```python
def test_home_uses_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADELAB_HOME", str(tmp_path))
    assert paths.home() == tmp_path

def test_slugify():
    assert paths.slugify("Goud Eerste Candle!") == "goud-eerste-candle"

def test_slugify_rejects_traversal():
    with pytest.raises(ValueError):
        paths.slugify("../..")

def test_strategy_dir_stays_inside_home(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADELAB_HOME", str(tmp_path))
    assert paths.strategy_dir("a/../../b").parent == tmp_path / "strategies"

def test_market_symbols():
    assert {k: m.symbol for k, m in MARKETS.items()} == {
        "SP500": "SPY", "NAS100": "QQQ", "GOLD": "XAU/USD", "SILVER": "SLV"}

def test_timeframes():
    assert TIMEFRAMES == {"1min": 1, "5min": 5, "15min": 15, "30min": 30,
                          "1h": 60, "4h": 240, "1day": 1440}

def test_session_keys_new_york():
    idx = pd.DatetimeIndex(["2025-01-02 14:30", "2025-01-02 14:35", "2025-01-03 14:30"], tz="UTC")
    k = session_keys(idx, "America/New_York", "09:30")
    assert list(k["minute"]) == [0, 5, 0]
    assert k["session"].nunique() == 2

def test_bar_before_session_start_belongs_to_previous_session():
    idx = pd.DatetimeIndex(["2025-01-02 23:55", "2025-01-03 00:00"], tz="UTC")
    k = session_keys(idx, "UTC", "00:00")
    assert k["session"].iloc[0] != k["session"].iloc[1]
    assert list(k["minute"]) == [1435, 0]
```

- [ ] **Step 2:** Run `uv run pytest tests/test_paths.py tests/test_markets.py -v`. Verwacht: FAIL (modules bestaan niet).
- [ ] **Step 3:** Implementeer beide modules. Aanpak voor `session_keys`: zet de index om naar de tijdzone, trek de starttijd eraf, en neem daarvan de datum (`session`) en de minuten sinds middernacht (`minute`).
- [ ] **Step 4:** Run dezelfde tests. Verwacht: PASS.
- [ ] **Step 5:** Commit: `feat: paths, markets and session keys`.

---

### Task 3: Indicatoren

**Files:**
- Create: `src/tradelab/indicators.py`
- Test: `tests/test_indicators.py`

**Interfaces:**
- Produces:
  - `sma(s: pd.Series, length: int) -> pd.Series`
  - `ema(s: pd.Series, length: int) -> pd.Series` (gelijk aan `s.ewm(span=length, adjust=False).mean()`)
  - `rsi(close: pd.Series, length: int = 14) -> pd.Series` (Wilder: eerste waarde op positie `length` uit het gewone gemiddelde van de eerste `length` veranderingen, daarna `avg = (avg * (length - 1) + nieuw) / length`; `100` als het gemiddelde verlies nul is)
  - `macd(close, fast=12, slow=26, signal=9) -> pd.DataFrame` met kolommen `line`, `signal`, `hist`
  - `atr(df: pd.DataFrame, length: int = 14) -> pd.Series` (Wilder-gemiddelde van de true range)
  - `bollinger(close, length=20, mult=2.0) -> pd.DataFrame` met kolommen `upper`, `mid`, `lower`

- [ ] **Step 1: Schrijf de falende tests**

```python
def test_sma():
    out = sma(pd.Series([1, 2, 3, 4, 5.0]), 3)
    assert out.tolist()[2:] == [2.0, 3.0, 4.0] and out[:2].isna().all()

def test_rsi_balanced_is_50():
    closes = [100.0]
    for i in range(14):
        closes.append(closes[-1] + (1 if i % 2 == 0 else -1))
    assert rsi(pd.Series(closes), 14).iloc[14] == pytest.approx(50.0)

def test_rsi_wilder_step():
    closes = [100.0]
    for i in range(14):
        closes.append(closes[-1] + (1 if i % 2 == 0 else -1))
    closes.append(closes[-1] + 1)
    assert rsi(pd.Series(closes), 14).iloc[15] == pytest.approx(53.5714, abs=1e-3)

def test_rsi_only_gains_is_100():
    assert rsi(pd.Series(range(1, 30), dtype=float), 14).iloc[-1] == 100.0

def test_rsi_first_values_are_nan():
    assert rsi(pd.Series(range(1, 30), dtype=float), 14).iloc[:14].isna().all()

def test_macd_hist_is_line_minus_signal():
    m = macd(pd.Series(range(1, 80), dtype=float))
    assert ((m["line"] - m["signal"]) - m["hist"]).abs().max() < 1e-9

def test_bollinger_flat_series_has_zero_width():
    b = bollinger(pd.Series([5.0] * 30))
    assert b["upper"].iloc[-1] == b["lower"].iloc[-1] == 5.0

def test_atr_constant_range():
    df = pd.DataFrame({"high": [11.0] * 30, "low": [9.0] * 30, "close": [10.0] * 30})
    assert atr(df, 14).iloc[-1] == pytest.approx(2.0)
```

- [ ] **Step 2:** Run `uv run pytest tests/test_indicators.py -v`. Verwacht: FAIL.
- [ ] **Step 3:** Implementeer met pandas. Geen extra pakket.
- [ ] **Step 4:** Run dezelfde tests. Verwacht: PASS.
- [ ] **Step 5:** Commit: `feat: indicators`.

---

### Task 4: Opslag en timeframes samenstellen

**Files:**
- Create: `src/tradelab/store.py`
- Test: `tests/test_store.py`, `tests/conftest.py`

**Interfaces:**
- Consumes: `paths.data_file`, `markets.get_market`, `markets.TIMEFRAMES`, `markets.session_keys`
- Produces:
  - `class DataMissingError(Exception)`
  - `save_candles(market: str, base: str, df: pd.DataFrame) -> None` (voegt samen met wat er staat, bij dubbele tijden wint de nieuwe rij, gesorteerd)
  - `load_base(market: str, base: str) -> pd.DataFrame` (lege tabel met de juiste kolommen als het bestand niet bestaat)
  - `resample(df: pd.DataFrame, minutes: int, timezone: str, session_start: str) -> pd.DataFrame`
  - `load_candles(market: str, timeframe: str, start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame`
  - `status() -> list[dict]` met per markt en basis: `market`, `base`, `rows`, `first`, `last`
  - `tests/conftest.py`: fixture `home` (zet `TRADELAB_HOME` op `tmp_path`) en helper `make_candles(start: str, periods: int, freq: str, price: float = 100.0) -> pd.DataFrame`

Vaste regels: basisbestanden zijn `1min` en `5min`. `load_candles(..., "1min")` leest het 1-minuutbestand. Elk ander timeframe wordt samengesteld uit het 5-minuutbestand. Blokken beginnen op de start van de handelsdag van de markt. Een blok aan het einde van de dag mag korter zijn. Is er geen data, dan `DataMissingError` met de tekst `No data for <MARKET>. Run: uv run tradelab download`.

- [ ] **Step 1: Schrijf de falende tests**

```python
def test_save_merges_without_duplicates(home):
    a = make_candles("2025-01-02 00:00", 10, "5min")
    b = make_candles("2025-01-02 00:25", 10, "5min", price=200.0)
    save_candles("GOLD", "5min", a); save_candles("GOLD", "5min", b)
    out = load_base("GOLD", "5min")
    assert len(out) == 15 and out.index.is_monotonic_increasing
    assert out.loc["2025-01-02 00:25", "close"] == 200.0

def test_load_base_missing_is_empty(home):
    out = load_base("GOLD", "5min")
    assert out.empty and list(out.columns) == ["open", "high", "low", "close", "volume"]

def test_resample_aggregates_ohlcv():
    df = make_candles("2025-01-02 00:00", 3, "5min")
    df["open"] = [1, 2, 3.0]; df["high"] = [5, 9, 4.0]; df["low"] = [0.5, 1, 2.0]
    df["close"] = [2, 3, 3.5]; df["volume"] = [10, 20, 30.0]
    out = resample(df, 15, "UTC", "00:00")
    assert out.iloc[0].tolist() == [1.0, 9.0, 0.5, 3.5, 60.0]

def test_4h_on_us_session_gives_two_bars():
    df = make_candles("2025-01-02 14:30", 78, "5min")   # 09:30 to 16:00 New York
    out = resample(df, 240, "America/New_York", "09:30")
    assert [t.strftime("%H:%M") for t in out.index] == ["14:30", "18:30"]

def test_1day_gives_one_bar_per_session():
    df = make_candles("2025-01-02 14:30", 78, "5min")
    assert len(resample(df, 1440, "America/New_York", "09:30")) == 1

def test_resample_survives_missing_first_bars():
    df = make_candles("2025-01-02 14:30", 78, "5min").iloc[7:]
    out = resample(df, 60, "America/New_York", "09:30")
    assert out.index[0].strftime("%H:%M") == "14:30" and not out.isna().any().any()

def test_load_candles_resamples_from_5min(home):
    save_candles("GOLD", "5min", make_candles("2025-01-02 00:00", 24, "5min"))
    assert len(load_candles("GOLD", "1h")) == 2

def test_load_candles_missing_data(home):
    with pytest.raises(DataMissingError, match="tradelab download"):
        load_candles("GOLD", "1h")
```

- [ ] **Step 2:** Run `uv run pytest tests/test_store.py -v`. Verwacht: FAIL.
- [ ] **Step 3:** Implementeer. Aanpak voor `resample`: groepeer op `session` en `minute // minutes` uit `session_keys`. De tijd van een blok is de start van het blok (dus ook als de eerste candles ontbreken), terug naar UTC.
- [ ] **Step 4:** Run dezelfde tests. Verwacht: PASS.
- [ ] **Step 5:** Commit: `feat: candle store and resampling`.

---

### Task 5: Twelve Data ophalen en `tradelab download`

**Files:**
- Create: `src/tradelab/twelvedata.py`, `src/tradelab/download.py`, `docs/data-sources.md`
- Test: `tests/test_twelvedata.py`, `tests/test_download.py`

**Interfaces:**
- Consumes: `store.save_candles`, `store.load_base`, `markets.MARKETS`, `paths.home`
- Produces:
  - `class DataSourceError(Exception)`
  - `twelvedata.api_key() -> str` (eerst `TWELVEDATA_API_KEY`, dan `home()/twelvedata.key`)
  - `twelvedata.fetch_page(symbol: str, interval: str, end: datetime | None, client: httpx.Client) -> pd.DataFrame` (hoogstens 5000 candles, de laatste voor `end`)
  - `twelvedata.fetch_range(symbol, interval, start: datetime, end: datetime, client: httpx.Client | None = None, sleep=time.sleep) -> Iterator[pd.DataFrame]` (van nieuw naar oud, één pagina per stap)
  - `download.plan_ranges(first, last, want_start, now) -> list[tuple[datetime, datetime]]`
  - `download.download(markets: list[str], years_5min: float = 5, years_1min: float = 1, fetch=twelvedata.fetch_range, now: datetime | None = None, log=print) -> None`
  - `download.main() -> None` met de opties `--markets`, `--years-5min`, `--years-1min`

Vaste waarden: `SECONDS_BETWEEN_CALLS = 8` (gratis plan: 8 per minuut), `PAGE_SIZE = 5000`, bij code 429 wacht 60 seconden en probeer hoogstens 5 keer. Een volledige download voor 4 markten is ongeveer 270 aanroepen, dus ongeveer 35 minuten.

- [ ] **Step 1: Controleer de API.** Lees de actuele documentatie van het `time_series`-eindpunt (https://twelvedata.com/docs). Leg in `docs/data-sources.md` vast: de parameternamen voor symbool, interval, einddatum, aantal rijen en tijdzone, de vorm van een goed antwoord en van een foutantwoord, en de bevindingen uit "Wat vooraf gecontroleerd is". Wijkt iets af van dit plan, dan wint de documentatie.
- [ ] **Step 2: Schrijf de falende tests** (met `httpx.MockTransport`, zonder internet)

```python
def test_fetch_page_parses_to_utc_floats(client_returning):
    client = client_returning({"status": "ok", "values": [
        {"datetime": "2025-01-02 00:05:00", "open": "2", "high": "3", "low": "1", "close": "2.5"},
        {"datetime": "2025-01-02 00:00:00", "open": "1", "high": "2", "low": "0.5", "close": "2"}]})
    df = fetch_page("XAU/USD", "5min", None, client)
    assert str(df.index.tz) == "UTC" and df.index.is_monotonic_increasing
    assert df["close"].tolist() == [2.0, 2.5] and df["volume"].tolist() == [0.0, 0.0]

def test_fetch_range_pages_back_until_start(paged_client):
    client, calls, slept = paged_client(pages=3)
    frames = list(fetch_range("SPY", "5min", START, END, client=client, sleep=slept.append))
    assert len(frames) == 3 and len(calls) == 3
    assert slept == [8, 8]
    assert pd.concat(frames).index.is_unique

def test_rate_limit_retries_then_fails(client_returning):
    client = client_returning({"status": "error", "code": 429, "message": "limit"})
    slept = []
    with pytest.raises(DataSourceError):
        list(fetch_range("SPY", "5min", START, END, client=client, sleep=slept.append))
    assert slept.count(60) == 5

def test_api_error_message_hides_key(client_returning, monkeypatch):
    monkeypatch.setenv("TWELVEDATA_API_KEY", "SECRET123")
    client = client_returning({"status": "error", "code": 403, "message": "plan"})
    with pytest.raises(DataSourceError) as e:
        fetch_page("XAG/USD", "5min", None, client)
    assert "plan" in str(e.value) and "SECRET123" not in str(e.value)

def test_missing_key_explains(home, monkeypatch):
    monkeypatch.delenv("TWELVEDATA_API_KEY", raising=False)
    with pytest.raises(DataSourceError, match="TWELVEDATA_API_KEY"):
        api_key()

def test_plan_ranges():
    assert plan_ranges(None, None, WANT, NOW) == [(WANT, NOW)]
    assert plan_ranges(FIRST, LAST, WANT, NOW) == [(LAST, NOW), (WANT, FIRST)]
    assert plan_ranges(WANT, LAST, WANT, NOW) == [(LAST, NOW)]

def test_download_resumes_without_duplicates(home):
    def flaky(symbol, interval, start, end, **_):
        yield make_candles("2025-01-02 00:00", 10, "5min")
        raise DataSourceError("network")
    with pytest.raises(DataSourceError):
        download(["GOLD"], fetch=flaky, now=NOW, log=lambda *_: None)
    assert len(load_base("GOLD", "5min")) == 10          # first page was saved
    download(["GOLD"], fetch=fake_full_fetch, now=NOW, log=lambda *_: None)
    assert load_base("GOLD", "5min").index.is_unique
```

- [ ] **Step 3:** Run `uv run pytest tests/test_twelvedata.py tests/test_download.py -v`. Verwacht: FAIL.
- [ ] **Step 4:** Implementeer. `download` bewaart elke pagina meteen met `save_candles` en schrijft per pagina één regel voortgang, bijvoorbeeld `GOLD 5min: 2024-03-01 (12 pages)`. De sleutel gaat alleen in de aanvraag mee, nooit in `log`.
- [ ] **Step 5:** Run dezelfde tests. Verwacht: PASS.
- [ ] **Step 6: Echte controle (met de sleutel van de maker).** Run `uv run tradelab download --markets GOLD --years-5min 0.02 --years-1min 0.01`. Verwacht: regels voortgang en daarna toont `uv run python -c "from tradelab import store; print(store.status())"` rijen voor `GOLD`. Controleer met `git status` dat er geen data of sleutel klaarstaat voor een commit.
- [ ] **Step 7:** Commit: `feat: twelve data client and resumable download`.

---

### Task 6: Veilige formules

**Files:**
- Create: `src/tradelab/expr.py`
- Test: `tests/test_expr.py`

**Interfaces:**
- Produces:
  - `class ExprError(ValueError)`
  - `class Namespace(dict)` (een groep reeksen, bereikbaar met een punt: `first.high`, `macd.hist`)
  - `names_in(expr: str) -> set[str]` (de hoofdnamen die een formule gebruikt, zonder functienamen)
  - `evaluate(expr: str, env: Mapping[str, Any]) -> pd.Series | float`
  - `FUNCTIONS`: `prev(x, n=1)`, `highest(x, n)`, `lowest(x, n)` (inclusief de huidige candle), `crossover(a, b)`, `crossunder(a, b)`, `abs`, `min`, `max`

Toegestaan: getallen, namen uit `env`, `+ - * /`, vergelijkingen (ook ketens zoals `1 < x < 3`), `and`, `or`, `not`, min-teken, een punt op een `Namespace`, en aanroepen van `FUNCTIONS`. Al het andere geeft `ExprError` met de formule erin. Een vergelijking met een ontbrekende waarde (NaN) is onwaar.

- [ ] **Step 1: Schrijf de falende tests**

```python
ENV = {"close": pd.Series([1.0, 3.0, 2.0]), "open": pd.Series([2.0, 2.0, 2.0]),
       "rsi": pd.Series([float("nan"), 25.0, 40.0]),
       "first": Namespace(high=pd.Series([5.0, 5.0, 5.0]))}

def test_and_comparison():
    assert evaluate("close > open and rsi < 30", ENV).tolist() == [False, True, False]

def test_arithmetic_and_namespace():
    assert evaluate("(first.high - close) / 2", ENV).tolist() == [2.0, 1.0, 1.5]

def test_prev_and_crossover():
    assert evaluate("prev(close)", ENV).tolist()[1:] == [1.0, 3.0]
    assert evaluate("crossover(close, open)", ENV).tolist() == [False, True, False]

def test_nan_comparison_is_false():
    assert evaluate("rsi < 30", ENV).iloc[0] == False

def test_names_in():
    assert names_in("prev(close) > first.high and rsi < 30") == {"close", "first", "rsi"}

@pytest.mark.parametrize("bad", [
    "__import__('os').system('x')", "close.__class__", "open('f')",
    "[c for c in close]", "lambda: 1", "close if rsi else open", "foo > 1", "close ** 2"])
def test_rejects_everything_else(bad):
    with pytest.raises(ExprError) as e:
        evaluate(bad, ENV)
    assert bad in str(e.value)
```

- [ ] **Step 2:** Run `uv run pytest tests/test_expr.py -v`. Verwacht: FAIL.
- [ ] **Step 3:** Implementeer met `ast.parse(expr, mode="eval")` en een eigen wandeling over de boom die alleen de toegestane knopen kent. Gebruik geen `eval`.
- [ ] **Step 4:** Run dezelfde tests. Verwacht: PASS.
- [ ] **Step 5:** Commit: `feat: safe expression evaluator`.

---

### Task 7: Strategieregels

**Files:**
- Create: `src/tradelab/strategy.py`, `docs/strategy-format.md`, `tests/fixtures/gold_first_candle.json`
- Test: `tests/test_strategy.py`

**Interfaces:**
- Consumes: `expr.evaluate`, `expr.names_in`, `expr.Namespace`, `expr.FUNCTIONS`, `indicators.*`, `markets.get_market`, `markets.session_keys`, `paths.strategy_dir`
- Produces:
  - `IndicatorSpec` (pydantic): `type` (`sma|ema|rsi|macd|atr|bollinger`), `length: int | None`, `source: str = "close"`, `fast`, `slow`, `signal`, `mult` (alle optioneel)
  - `Setup` (pydantic): `name`, `direction` (`long|short`), `entry_when: list[str]` (minstens 1), `stop: str`, `take_profit_r: float | None`, `take_profit: str | None` (precies één van de twee), `exit_when: list[str] = []`
  - `Strategy` (pydantic): `name`, `description` (de originele tekst van de gebruiker), `market`, `timeframe`, `timezone: str | None`, `session_start: str | None` (leeg betekent: die van de markt), `indicators: dict[str, IndicatorSpec]`, `setups: list[Setup]` (minstens 1)
  - `build_env(strategy: Strategy, candles: pd.DataFrame) -> dict[str, Any]`
  - `validate(raw: dict) -> tuple[Strategy | None, list[str]]`
  - `explain(setup: Setup, env: dict, at: pd.Timestamp) -> list[dict]` met per formule `{"expr", "passed", "values"}`, waarbij `values` de waarde van elke gebruikte naam op dat moment is
  - `save(strategy: Strategy, overwrite: bool = False) -> Path` (schrijft `strategy.json`), `load(name: str) -> Strategy`, `list_names() -> list[str]`

Namen in `env`: `open`, `high`, `low`, `close`, `volume`, elke indicatornaam, `bar_of_day` (1 voor de eerste candle van de handelsdag), `first` (`open/high/low/close` van de eerste candle van de handelsdag die er is) en `prev_day` (`open/high/low/close` van de vorige handelsdag, leeg op de eerste dag). `macd` en `bollinger` zijn een `Namespace`. De naam `entry` (de instapprijs) bestaat alleen in `stop` en `take_profit`.

`tests/fixtures/gold_first_candle.json` is het voorbeeld van de maker:

```json
{
  "name": "goud-eerste-candle-short",
  "description": "Als de eerste 1-uurscandle van de dag bij XAUUSD daalt met meer dan 0,5% en de volgende candle sluit terug naar boven maar onder de helft van de eerste candle, met RSI < 30, dan short met TP 4R en SL boven de eerste candle.",
  "market": "GOLD",
  "timeframe": "1h",
  "indicators": {"rsi": {"type": "rsi", "length": 14}},
  "setups": [{
    "name": "short-na-daling",
    "direction": "short",
    "entry_when": [
      "bar_of_day == 2",
      "(first.close - first.open) / first.open < -0.005",
      "close > open",
      "close < (first.high + first.low) / 2",
      "rsi < 30"
    ],
    "stop": "first.high",
    "take_profit_r": 4
  }]
}
```

- [ ] **Step 1: Schrijf de falende tests**

```python
def test_example_is_valid(example):
    s, errors = validate(example)
    assert errors == [] and s.setups[0].take_profit_r == 4

def test_unknown_name_is_reported(example):
    example["setups"][0]["entry_when"].append("foo > 1")
    _, errors = validate(example)
    assert any("foo > 1" in e for e in errors)

def test_attack_is_reported_not_run(example):
    example["setups"][0]["stop"] = "__import__('os').system('x')"
    _, errors = validate(example)
    assert len(errors) == 1

def test_needs_exactly_one_take_profit(example):
    example["setups"][0]["take_profit"] = "prev_day.low"
    assert validate(example)[1]

def test_indicator_may_not_shadow_reserved_name(example):
    example["indicators"]["close"] = {"type": "sma", "length": 5}
    assert validate(example)[1]

def test_entry_name_only_in_stop_and_take_profit(example):
    example["setups"][0]["entry_when"].append("entry > 0")
    assert validate(example)[1]
    example["setups"][0]["entry_when"].pop()
    example["setups"][0]["stop"] = "entry * 1.003"
    assert validate(example)[1] == []

def test_env_session_names(example):
    s, _ = validate(example)
    env = build_env(s, make_candles("2025-01-02 00:00", 48, "1h"))
    assert env["bar_of_day"].tolist()[:3] == [1, 2, 3] and env["bar_of_day"].iloc[24] == 1
    assert env["first"]["high"].iloc[:24].nunique() == 1
    assert env["prev_day"]["close"].iloc[:24].isna().all()
    assert env["prev_day"]["close"].iloc[24:].notna().all()

def test_first_uses_first_available_bar(example):
    s, _ = validate(example)
    candles = make_candles("2025-01-02 00:00", 24, "1h").iloc[3:]
    env = build_env(s, candles)
    assert env["first"]["open"].iloc[0] == candles["open"].iloc[0]

def test_explain_lists_each_condition(example):
    s, _ = validate(example)
    env = build_env(s, make_candles("2025-01-02 00:00", 48, "1h"))
    rows = explain(s.setups[0], env, env["close"].index[25])
    assert [r["expr"] for r in rows] == s.setups[0].entry_when
    assert rows[0] == {"expr": "bar_of_day == 2", "passed": True, "values": {"bar_of_day": 2}}

def test_save_load_and_no_silent_overwrite(home, example):
    s, _ = validate(example)
    save(s)
    assert load("goud-eerste-candle-short") == s
    assert list_names() == ["goud-eerste-candle-short"]
    with pytest.raises(FileExistsError):
        save(s)
    save(s, overwrite=True)
```

- [ ] **Step 2:** Run `uv run pytest tests/test_strategy.py -v`. Verwacht: FAIL.
- [ ] **Step 3:** Implementeer. `validate` controleert eerst de vorm met pydantic en rekent daarna elke formule uit op 60 nepcandles, zodat onbekende namen en verboden constructies een melding geven. Schrijf `docs/strategy-format.md`: elk veld, elke naam in `env`, elke functie, en het voorbeeld hierboven.
- [ ] **Step 4:** Run dezelfde tests. Verwacht: PASS.
- [ ] **Step 5:** Commit: `feat: strategy rules, validation and explain`.

---

### Task 8: Backtestmotor

**Files:**
- Create: `src/tradelab/engine.py`
- Test: `tests/test_engine.py`, `tests/test_paper_example.py`

**Interfaces:**
- Consumes: `strategy.Strategy`, `strategy.build_env`, `expr.evaluate`
- Produces:
  - `Trade` (dataclass): `setup, direction, signal_time, entry_time, entry, stop, take_profit, exit_time, exit, outcome` (`tp|sl|exit|open`), `r: float | None`, `bars_held: int`
  - `Skipped` (dataclass): `setup, signal_time, reason`
  - `BacktestResult` (dataclass): `trades: list[Trade]`, `skipped: list[Skipped]`, `start`, `end`, `bars: int`
  - `run(strategy: Strategy, candles: pd.DataFrame, env: dict | None = None) -> BacktestResult`

Vaste regels:
1. Een signaal is een candle waarop alle formules in `entry_when` waar zijn. Instap op de open van de volgende candle. Een signaal op de laatste candle telt niet.
2. `stop` en `take_profit` worden uitgerekend op de signaalcandle, met `entry` gelijk aan de instapprijs. `take_profit_r` betekent: instap plus of min `take_profit_r` keer de afstand tussen instap en stop.
3. Overslaan met reden `entry beyond stop` als de instap op of voorbij de stop ligt, en met reden `stop not computable` als de stop leeg is.
4. Per candle vanaf de instapcandle, in deze volgorde: opent de candle voorbij de stop, dan uit op de open (`sl`). Opent hij voorbij de TP, dan uit op de open (`tp`). Raakt hij de stop, dan uit op de stop (`sl`), ook als de TP in dezelfde candle geraakt is. Raakt hij de TP, dan uit op de TP (`tp`).
5. Is een formule in `exit_when` waar op de slot van een candle, dan uit op de open van de volgende candle (`exit`).
6. Signalen tot en met de candle waarop een trade sluit tellen niet (één positie tegelijk).
7. `r` is de winst gedeeld door de afstand tussen instap en stop, positief bij winst. `bars_held` telt de instapcandle tot en met de uitstapcandle.
8. Loopt een trade nog aan het einde van de data, dan `outcome="open"` en `r=None`.

- [ ] **Step 1: Schrijf de falende tests.** `tests/test_engine.py` gebruikt een helper `strat(direction, entry_when, stop, tp_r)` en met de hand gemaakte candles:

```python
def test_tp_gives_plus_r():            # long, entry 100, stop 99, tp_r 2, later high 102
    assert (t.outcome, t.r, t.exit) == ("tp", 2.0, 102.0)

def test_sl_wins_when_both_hit_in_one_bar():
    assert (t.outcome, t.r) == ("sl", -1.0)

def test_gap_through_stop_exits_at_open():   # long, stop 99, next bar opens 97
    assert t.outcome == "sl" and t.exit == 97.0 and t.r == -3.0

def test_entry_is_next_bar_open_no_lookahead():
    a = run(s, candles)
    changed = candles.copy(); changed.iloc[SIGNAL + 2:] *= 1.5
    assert run(s, changed).trades[0].entry == a.trades[0].entry

def test_signal_during_open_trade_is_ignored():
    assert len(result.trades) == 1

def test_entry_beyond_stop_is_skipped():
    assert result.trades == [] and result.skipped[0].reason == "entry beyond stop"

def test_signal_on_last_bar_is_ignored():
    assert result.trades == [] and result.skipped == []

def test_trade_open_at_end():
    assert (t.outcome, t.r) == ("open", None)

def test_exit_when_closes_at_next_open():
    assert t.outcome == "exit" and t.exit == candles["open"].iloc[EXIT_SIGNAL + 1]

def test_short_mirrors_long():
    assert (t.outcome, t.r) == ("tp", 2.0)
```

`tests/test_paper_example.py` is het rekenvoorbeeld op papier. Het gebruikt de fixture uit Task 7 met `rsi` lengte 2, en deze 1-uurscandles van goud (UTC, open, high, low, close):

```python
ROWS = [("2025-01-02 22:00", 2010, 2011, 2004, 2005),
        ("2025-01-02 23:00", 2005, 2006, 1999, 2000),
        ("2025-01-03 00:00", 2000, 2001, 1986, 1988),   # first candle: -0.6%
        ("2025-01-03 01:00", 1988, 1992, 1987, 1991),   # signal: rsi(2) = 26.09
        ("2025-01-03 02:00", 1991, 1992, 1985, 1986),   # entry at open 1991
        ("2025-01-03 03:00", 1986, 1987, 1960, 1962),
        ("2025-01-03 04:00", 1962, 1963, 1950, 1952)]   # tp 1951 hit

def test_paper_example():
    t, = run(strategy, candles).trades
    assert t.signal_time == pd.Timestamp("2025-01-03 01:00", tz="UTC")
    assert (t.entry, t.stop, t.take_profit) == (1991.0, 2001.0, 1951.0)
    assert (t.outcome, t.exit, t.r, t.bars_held) == ("tp", 1951.0, 4.0, 3)
```

- [ ] **Step 2:** Run `uv run pytest tests/test_engine.py tests/test_paper_example.py -v`. Verwacht: FAIL.
- [ ] **Step 3:** Implementeer. Reken de signalen in één keer uit met pandas. Loop daarna alleen binnen een open trade candle voor candle, over numpy-rijen.
- [ ] **Step 4:** Run dezelfde tests. Verwacht: PASS.
- [ ] **Step 5:** Commit: `feat: backtest engine`.

---

### Task 9: Cijfers en de 3 voorbeelden

**Files:**
- Create: `src/tradelab/stats.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- Consumes: `engine.BacktestResult`, `engine.Trade`
- Produces:
  - `summarize(result: BacktestResult) -> dict` met de sleutels `trades`, `wins`, `losses`, `win_rate`, `total_r`, `avg_r`, `profit_factor`, `max_drawdown_r`, `avg_bars_held`, `open_trades`, `skipped`, `equity` (lijst van `{"time", "r_cum"}`) en `monthly` (lijst van `{"month", "r"}`)
  - `pick_examples(trades: list[Trade], seed: int = 0) -> dict[str, Trade | None]` met de sleutels `loss`, `win`, `long`

Vaste regels: alleen gesloten trades tellen mee. `long` is de gesloten trade met de meeste `bars_held`. Daarna worden `loss` (r < 0) en `win` (r > 0) willekeurig gekozen uit de rest, met `random.Random(seed)`. Bestaat een soort niet, dan `None`. `profit_factor` is `None` als er geen verlies is.

- [ ] **Step 1: Schrijf de falende tests**

```python
def test_summarize_known_trades():      # r values: +2, -1, -1, +4
    s = summarize(result)
    assert (s["trades"], s["wins"], s["win_rate"], s["total_r"]) == (4, 2, 0.5, 4.0)
    assert s["profit_factor"] == 3.0 and s["max_drawdown_r"] == 2.0
    assert [p["r_cum"] for p in s["equity"]] == [2.0, 1.0, 0.0, 4.0]

def test_summarize_zero_trades():
    s = summarize(BacktestResult([], [], START, END, 100))
    assert (s["trades"], s["win_rate"], s["total_r"], s["profit_factor"]) == (0, 0.0, 0.0, None)
    assert s["equity"] == [] and s["monthly"] == []

def test_open_trades_do_not_count():
    assert summarize(result_with_one_open)["trades"] == 1

def test_pick_examples_three_different_trades():
    ex = pick_examples(trades, seed=1)
    assert ex["loss"].r < 0 and ex["win"].r > 0
    assert ex["long"].bars_held == max(t.bars_held for t in trades)
    assert len({id(t) for t in ex.values()}) == 3

def test_pick_examples_seed_is_repeatable():
    assert pick_examples(trades, 5) == pick_examples(trades, 5)

def test_pick_examples_empty():
    assert pick_examples([], 0) == {"loss": None, "win": None, "long": None}
```

- [ ] **Step 2:** Run `uv run pytest tests/test_stats.py -v`. Verwacht: FAIL.
- [ ] **Step 3:** Implementeer.
- [ ] **Step 4:** Run dezelfde tests. Verwacht: PASS.
- [ ] **Step 5:** Commit: `feat: stats and example picker`.

---

### Task 10: Grafieken en rapport

**Files:**
- Create: `src/tradelab/charts.py`, `src/tradelab/report.py`
- Test: `tests/test_charts.py`, `tests/test_report.py`

**Interfaces:**
- Consumes: `engine.Trade`, `strategy.Strategy`, `strategy.explain`, `indicators.*`, `stats.summarize`, `paths.strategy_dir`
- Produces:
  - `charts.equity_figure(summary: dict) -> go.Figure` (opgetelde R in de tijd)
  - `charts.monthly_figure(summary: dict) -> go.Figure` (R per maand, staven)
  - `charts.distribution_figure(trades: list[Trade]) -> go.Figure` (verdeling van R)
  - `charts.trade_figure(strategy: Strategy, candles: pd.DataFrame, env: dict, trade: Trade, bars_before: int = 60, bars_after: int = 20) -> go.Figure`
  - `report.build(strategy: Strategy, summary: dict, examples: list[dict], figures: dict[str, go.Figure], commentary: str, data_range: tuple[str, str]) -> str` (HTML). Elk voorbeeld is `{"kind", "trade", "conditions", "figure"}`.
  - `report.write(name: str, html: str) -> Path` (schrijft `report.html` in de map van de strategie)

`trade_figure` heeft drie rijen: koers (candles, EMA 50, EMA 200, en indicatoren van de strategie die op de koers horen: `sma`, `ema`, `bollinger`), RSI 14 en MACD. Indicatoren van de strategie met andere instellingen dan deze standaard staan erbij met hun eigen naam. Op de koers: een aantekening `Setup` op de signaalcandle, een markering `Entry`, een rode zone van instap tot stop en een groene zone van instap tot TP (beide van de instaptijd tot de uitstaptijd), en een markering `Exit`.

Het rapport bevat in deze volgorde: de naam, de vaste tekst uit Global Constraints, de originele beschrijving en de regels, de gebruikte periode, de cijfers, de drie grote grafieken, de drie voorbeelden (elk met grafiek, feiten van de trade en een tabel met elke formule, of die klopte en met welke waarden), en de uitleg van Claude. Plotly wordt één keer geladen vanaf `cdnjs.cloudflare.com`, in de versie die bij het geïnstalleerde `plotly` hoort. Controleer dat die URL bestaat.

- [ ] **Step 1: Schrijf de falende tests**

```python
def test_trade_figure_marks_setup_entry_and_zones(strategy, candles, env, trade):
    fig = trade_figure(strategy, candles, env, trade)
    assert any(isinstance(t, go.Candlestick) for t in fig.data)
    texts = [a.text for a in fig.layout.annotations]
    assert "Setup" in texts and "Entry" in texts and "Exit" in texts
    assert len(fig.layout.shapes) >= 2
    names = {t.name for t in fig.data}
    assert {"EMA 50", "EMA 200", "RSI 14", "MACD"} <= names

def test_trade_figure_window(strategy, candles, env, trade):
    fig = trade_figure(strategy, candles, env, trade, bars_before=10, bars_after=5)
    assert len(fig.data[0].x) <= 10 + trade.bars_held + 1 + 5

def test_summary_figures_handle_zero_trades():
    s = summarize(BacktestResult([], [], START, END, 100))
    equity_figure(s); monthly_figure(s); distribution_figure([])

def test_report_contains_everything(strategy, summary, examples, figures):
    html = build(strategy, summary, examples, figures, "Why it lost.\n\nWhy it won.", ("2021-01-01", "2025-12-31"))
    assert "Not financial advice." in html
    assert html.count("cdnjs.cloudflare.com/ajax/libs/plotly.js") == 1
    assert "bar_of_day == 2" in html and "<p>Why it won.</p>" in html

def test_report_escapes_commentary(strategy, summary, examples, figures):
    html = build(strategy, summary, examples, figures, "<script>alert(1)</script>", RANGE)
    assert "<script>alert(1)</script>" not in html

def test_report_without_trades(strategy):
    html = build(strategy, summarize(EMPTY), [], empty_figures, "", RANGE)
    assert "No trades" in html

def test_write_puts_report_in_strategy_dir(home):
    assert write("goud-eerste-candle-short", "<html></html>").name == "report.html"
```

- [ ] **Step 2:** Run `uv run pytest tests/test_charts.py tests/test_report.py -v`. Verwacht: FAIL.
- [ ] **Step 3:** Implementeer. De uitleg van Claude is platte tekst: `html.escape`, daarna één `<p>` per alinea.
- [ ] **Step 4:** Run dezelfde tests. Verwacht: PASS.
- [ ] **Step 5: Bekijk het zelf.** Bouw met het rekenvoorbeeld uit Task 8 een rapport en open het in de browser. Verwacht: de candles, de rode en groene zone en de drie rijen zijn zichtbaar, en de pagina past op een telefoonbreedte zonder zijwaarts scrollen.
- [ ] **Step 6:** Commit: `feat: charts and html report`.

---

### Task 11: MCP-server

**Files:**
- Create: `src/tradelab/server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: alles uit Task 4 en Task 7 tot en met 10
- Produces: een FastMCP-server met de naam `tradelab` en deze tools (gewone functies, dus direct te testen), plus `main()` die de server over stdio start:
  - `data_status() -> list[dict]` (per markt: label, note, beschikbare periode per basis)
  - `validate_strategy(strategy: dict) -> dict` geeft `{"ok", "errors", "strategy"}`
  - `save_strategy(strategy: dict, overwrite: bool = False) -> dict` geeft `{"name", "path"}` (valideert eerst)
  - `list_strategies() -> list[dict]` met `name`, `market`, `timeframe`, `has_backtest`
  - `get_strategy(name: str) -> dict` geeft `{"strategy", "summary", "report_path"}` (de laatste twee `None` zonder backtest)
  - `run_backtest(name: str, start: str | None = None, end: str | None = None, seed: int = 0) -> dict` geeft `{"summary", "examples", "data_range", "warnings"}` en schrijft `backtest.json` (cijfers, alle trades, seed, periode). Elk voorbeeld is `{"kind", "trade", "conditions"}`.
  - `build_report(name: str, commentary: str) -> dict` geeft `{"path"}` (gebruikt de seed en periode uit `backtest.json`)

Fouten komen terug als een leesbare melding: ontbrekende data (met de downloadopdracht), onbekende strategie (met de bestaande namen), ongeldige regels (met de lijst fouten). `warnings` meldt het als de gevraagde periode langer is dan de beschikbare data, en bij `SILVER` de `note` van de markt.

- [ ] **Step 1: Controleer de API.** Lees de actuele documentatie van de Python `mcp` SDK (FastMCP: server maken, tool registreren, starten over stdio) en gebruik die vorm.
- [ ] **Step 2: Schrijf de falende tests** (met de fixture `home` en nepdata in de opslag)

```python
def test_full_flow(home, example, gold_data):
    assert server.validate_strategy(example)["ok"] is True
    assert server.save_strategy(example)["name"] == "goud-eerste-candle-short"
    out = server.run_backtest("goud-eerste-candle-short")
    assert out["summary"]["trades"] >= 1
    assert {e["kind"] for e in out["examples"]} <= {"loss", "win", "long"}
    assert out["examples"][0]["conditions"][0]["expr"] == "bar_of_day == 2"
    path = server.build_report("goud-eerste-candle-short", "Looks fine.")["path"]
    assert Path(path).read_text(encoding="utf-8").count("Not financial advice.") == 1
    got = server.get_strategy("goud-eerste-candle-short")
    assert got["summary"]["trades"] == out["summary"]["trades"] and got["report_path"] == path

def test_invalid_strategy_is_not_saved(home, example):
    example["setups"][0]["entry_when"] = ["foo > 1"]
    with pytest.raises(ValueError, match="foo > 1"):
        server.save_strategy(example)
    assert server.list_strategies() == []

def test_backtest_without_data_says_how_to_download(home, example):
    server.save_strategy(example)
    with pytest.raises(Exception, match="tradelab download"):
        server.run_backtest("goud-eerste-candle-short")

def test_unknown_strategy_lists_names(home):
    with pytest.raises(ValueError, match="No strategy named"):
        server.get_strategy("nope")

def test_zero_trades_flow(home, never_triggers, gold_data):
    server.save_strategy(never_triggers)
    out = server.run_backtest(never_triggers["name"])
    assert out["summary"]["trades"] == 0 and out["examples"] == []
    assert "No trades" in Path(server.build_report(never_triggers["name"], "")["path"]).read_text(encoding="utf-8")

def test_period_longer_than_data_warns(home, example, gold_data):
    server.save_strategy(example)
    out = server.run_backtest("goud-eerste-candle-short", start="2000-01-01")
    assert out["warnings"] and out["data_range"][0] > "2000-01-01"

def test_seed_changes_examples_but_not_summary(home, example, gold_data): ...
```

- [ ] **Step 3:** Run `uv run pytest tests/test_server.py -v`. Verwacht: FAIL.
- [ ] **Step 4:** Implementeer. De tools zijn dunne lagen: ze roepen de modules aan en zetten het resultaat om naar gewone JSON (tijden als ISO-tekst).
- [ ] **Step 5:** Run `uv run pytest -v` (alles). Verwacht: PASS.
- [ ] **Step 6: Echte controle.** Run `uv run tradelab-mcp` en stuur niets. Verwacht: het proces blijft wachten zonder foutmelding. Stop het met Ctrl+C.
- [ ] **Step 7:** Commit: `feat: mcp server`.

---

### Task 12: Plugin en skills

**Files:**
- Create: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.mcp.json`, `skills/backtest/SKILL.md`, `skills/strategy/SKILL.md`

**Interfaces:**
- Consumes: de tools uit Task 11 en `docs/strategy-format.md`
- Produces: de plugin `tradelab` met de skills `backtest` en `strategy`. De MCP-server start met `uv run --directory ${CLAUDE_PLUGIN_ROOT} tradelab-mcp`.

- [ ] **Step 1: Controleer het formaat.** Lees de actuele documentatie van Claude Code over plugins, skills in plugins, `.mcp.json` in een plugin en marketplaces. Gebruik de veldnamen en mappen van die documentatie. Wijkt iets af van dit plan, dan wint de documentatie.
- [ ] **Step 2:** Schrijf `skills/backtest/SKILL.md`. De beschrijving zegt wanneer de skill start: de gebruiker wil een tradingstrategie testen of uitleggen. De skill laat Claude deze stappen volgen:
  1. Roep `data_status` aan. Ontbreekt data, leg dan uit hoe de gebruiker `uv run tradelab download` start (ongeveer 35 minuten voor alles) en stop.
  2. Vraag de strategie in gewone woorden of als Pine Script, en voor welke markt en welk timeframe.
  3. Lees `docs/strategy-format.md` en vertaal naar het regelformaat. Wat niet uit te drukken is, meld je als niet ondersteund. Je verzint geen regels.
  4. Roep `validate_strategy` aan en los fouten op.
  5. Laat de vertaling zien in gewone taal, formule voor formule, en noem elke aanname (bijvoorbeeld wat "de helft van de candle" betekent, en waar de stop staat). Wacht op bevestiging.
  6. Vraag een naam, roep `save_strategy` en daarna `run_backtest` aan.
  7. Schrijf de uitleg: wat de cijfers betekenen, en per voorbeeldtrade wat de setup was en waarom hij won, verloor of lang duurde, op basis van `conditions`. Geen advies over wat te kopen of te verkopen.
  8. Roep `build_report` aan met die uitleg. Toon het rapport: als artefact waar dat kan, anders met het pad naar `report.html`.
  9. Wil de gebruiker andere voorbeelden, roep dan `run_backtest` aan met een andere `seed` en bouw het rapport opnieuw.
- [ ] **Step 3:** Schrijf `skills/strategy/SKILL.md`. De skill krijgt een naam mee. Claude roept `get_strategy` aan, vat de regels en de laatste cijfers samen, en vraagt wat de gebruiker wil: opnieuw testen, de regels aanpassen (bewaren met `overwrite` na bevestiging) of het rapport tonen. Zonder naam, of bij een onbekende naam, toont Claude `list_strategies`.
- [ ] **Step 4:** Schrijf `plugin.json`, `marketplace.json` en `.mcp.json`.
- [ ] **Step 5: Echte controle.** Start Claude Code met de plugin uit deze map (de manier staat in de documentatie uit Step 1). Verwacht: de tools van `tradelab` staan in de lijst, en de skill `backtest` start als je typt dat je een strategie wilt testen.
- [ ] **Step 6:** Commit: `feat: claude plugin with backtest and strategy skills`.

---

### Task 13: Proef op echte data

**Files:**
- Modify: wat de proef aan fouten oplevert, steeds met eerst een falende test in het testbestand van die module

**Interfaces:**
- Consumes: alles

- [ ] **Step 1:** Run `uv run tradelab download` (alle markten, ongeveer 35 minuten, in een eigen terminal). Verwacht: `data_status` toont voor elke markt 5 jaar aan `5min` en 1 jaar aan `1min`.
- [ ] **Step 2:** Start de skill `backtest` in Claude en voer het voorbeeld van de maker in, woord voor woord uit het ontwerp. Verwacht: Claude toont een vertaling die gelijk is aan `tests/fixtures/gold_first_candle.json`, of legt uit waarom het afwijkt.
- [ ] **Step 3:** Controleer één voorbeeldtrade met de hand tegen TradingView: de tijd van de eerste candle, de daling in procent, de instap, de stop en de TP. Verwacht: gelijk, op kleine prijsverschillen tussen databronnen na. Schrijf de uitkomst in `docs/data-sources.md`.
- [ ] **Step 4:** Test een tweede strategie op een andere markt en een ander timeframe (bijvoorbeeld een EMA-kruising op `SP500`, `15min`) en een strategie die nooit een trade geeft. Verwacht: beide geven een rapport zonder foutmelding.
- [ ] **Step 5:** Heropen in een nieuwe sessie de eerste strategie met de skill `strategy` en de naam. Verwacht: Claude toont de regels en de cijfers van de laatste backtest.
- [ ] **Step 6:** Commit de oplossingen: `fix: findings from real-data trial`.

---

### Task 14: README en GitHub

**Files:**
- Modify: `README.md`
- Create: `docs/screenshot-report.png` (een schermafbeelding van een echt rapport)

- [ ] **Step 1:** Schrijf `README.md` in het Engels: wat het is in drie zinnen, de vaste tekst uit Global Constraints, de schermafbeelding, wat je nodig hebt (Claude Code of de Claude-desktopapp, uv, een gratis Twelve Data-sleutel), installeren in genummerde stappen, de eerste backtest, de 4 markten met de melding over zilver, de beperkingen (geen kosten, R, gratis data vanaf 2020, minuutdata 1 jaar), en wat er nog komt (fase 2).
- [ ] **Step 2: Volg de README zelf** op een schone map (`git clone` van de lokale repo naar een tijdelijke map, daarna de installatiestappen). Verwacht: de tests slagen en de skill werkt. Pas de README aan waar een stap ontbrak.
- [ ] **Step 3: Controleer dat er niets geheims in de repo zit.** Run `git ls-files` en `git grep -i -n "apikey\|api_key=" -- . ":!docs" ":!src/tradelab/twelvedata.py" ":!tests"`. Verwacht: geen `.key`, geen `data/`, geen echte sleutel.
- [ ] **Step 4: De maker maakt de repo.** Op https://github.com/new: naam `tradelab`, zichtbaarheid Public, zonder README, licentie of .gitignore (die bestaan al). Dit doet de maker zelf.
- [ ] **Step 5: Publiceer, na een duidelijk ja van de maker.** Run `git remote add origin https://github.com/<gebruikersnaam>/tradelab.git` en `git push -u origin main`. Git opent een venster om in te loggen bij GitHub. Verwacht: de bestanden staan op de pagina van de repo.
- [ ] **Step 6:** Zet op GitHub een korte beschrijving en de onderwerpen `claude`, `mcp`, `trading`, `backtesting`. Installeer de plugin vanaf GitHub in een schone Claude-sessie, op de manier uit de documentatie van Task 12. Verwacht: de skill `backtest` werkt.
- [ ] **Step 7:** Maak de eerste release: `git tag v0.1.0` en `git push origin v0.1.0`.

---

## Fase 2: routekaart (geen taken, eerst een eigen ontwerp)

Fase 2 krijgt een eigen ontwerp en een eigen plan zodra fase 1 op GitHub staat. Het hergebruikt `strategy.explain`, `charts.trade_figure`, de opslag en het rapport. Wat erbij komt:

1. **Schermwatcher** (`tradelab watch`): de gebruiker markeert eenmalig het deel van het scherm met posities en orders. Een screenshot wordt bewaard als dat deel verandert, in `~/.tradelab/strategies/<naam>/inbox/`.
2. **Recente data** (MCP-tool `fetch_recent`): haalt de candles rond een trade direct bij Twelve Data op, omdat de lokale data niet tot vandaag loopt.
3. **Trade controleren** (MCP-tool `check_trade`): rekent de regels van de strategie uit op het moment van de echte trade en geeft per formule terug of die klopte.
4. **Skill 3** (`journal`): Claude leest de nieuwe screenshots, haalt de gegevens van elke trade eruit, roept `check_trade` aan, schrijft de uitleg en werkt het dagboek in het rapport bij.
5. **Dagboek-statistieken:** hoeveel trades volgden de regels, het resultaat van trades binnen en buiten de regels, en overgeslagen setups (signalen uit de backtest zonder echte trade).

Open vragen voor dat ontwerp: hoe betrouwbaar Claude een trade uit een screenshot leest, hoe de watcher op Windows en macOS schermdelen vastlegt, en of de limiet van het gratis dataplan genoeg is voor dagelijks gebruik.
