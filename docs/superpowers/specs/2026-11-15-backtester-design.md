# Trading-lab voor Claude: ontwerp (versie 2)

Status: ter goedkeuring. Er is nog niets gebouwd.
Dit vervangt versie 1 (een Python-programma met een eigen webpagina en eigen AI-sleutel).

## Waarom

Veel beginnende traders backtesten een strategie met veel winst, maar halen die winst live niet. Ze slaan setups over of traden buiten hun regels. Dit project laat hen eerst zien wat hun strategie echt doet, en controleert daarna of ze hun regels live volgen en legt uit waarom een trade won of verloor.

Het is een publieke GitHub-repo voor andere mensen. De maker leert er zelf ook mee bouwen, want het is zijn eerste grote project.

## Wat het wordt

Een Claude-plugin op GitHub, met vier onderdelen:

1. **Dataopslag en MCP-server (Python).** Downloadt historische koersdata voor 4 markten en bewaart die op de computer van de gebruiker. Berekent de indicatoren zelf, draait backtests en haalt recente data op.
2. **Drie skills** (instructies voor Claude): een backtest, het heropenen van een bewaarde strategie, en het verwerken van nieuwe trades.
3. **Schermwatcher (apart programma).** Draait op de achtergrond bij TradingView en bewaart een screenshot per trade in een map.
4. **Rapportpagina (artefact).** Toont grote grafieken, 3 voorbeeldtrades en later het dagboek met statistieken.

Er is geen eigen AI in het programma. Claude doet het lezen, uitleggen en schrijven met het abonnement van de gebruiker.

## Fases

- **Fase 1: de backtester.** Hier wordt eerst gebouwd en getest. Dit document beschrijft het volledig.
- **Fase 2: het trading-dagboek met schermwatcher.** Staat hier in grote lijnen. Het wordt na fase 1 verder uitgewerkt en opnieuw goedgekeurd.

## Fase 1: de backtester

Markten: S&P 500, Nasdaq 100, goud en zilver. Crypto en forex komen later.

Stappen voor de gebruiker:
1. De gebruiker beschrijft zijn strategie in gewone tekst, of plakt Pine Script.
   Voorbeeld van de maker: "Als de eerste 1-uurscandle van de dag bij XAUUSD daalt met meer dan 0,5% en de volgende candle sluit terug naar boven maar onder de helft van de eerste candle, met RSI < 30, dan short met TP 4R en SL 1R."
2. Claude zet dit om naar regels in een vast formaat. De gebruiker ziet de vertaling in gewone taal en bevestigt of corrigeert die. Daarna geeft de gebruiker de strategie een naam.
3. De backtest draait op de lokaal opgeslagen data.
4. Claude maakt het rapport: een paar grote grafieken met alle cijfers (aantal trades, winstpercentage, resultaat in R, grootste daling, gemiddelde duur) en 3 voorbeeldtrades.
5. De 3 voorbeeldtrades zijn een verliezer, een winnaar en een trade die lang duurde voor TP of SL werd geraakt. Op elke grafiek staan de setup, de entry, TP en SL, wat de indicatoren van de strategie zeiden, en de bekendste indicatoren. Het moet eruitzien als een echte trade, zodat de gebruiker kan zien of de strategie doet wat hij zei.
6. Later opent de gebruiker de strategie opnieuw met de naam, in dezelfde of een andere sessie, en bouwt Claude daarop voort.

**Timeframes (beslissing van de maker):** 1 minuut, 5 minuten, 15 minuten, 30 minuten, 1 uur, 4 uur en dag.

**Twee soorten data, één MCP-server:** de server leest de lokaal opgeslagen historische data voor backtests, en haalt daarnaast op aanvraag recente candles op bij de databron voor het reviewen van trades van vandaag of deze week (fase 2).

**Data:** alleen koersen (open, hoog, laag, slot, volume) worden gedownload. Indicatoren zoals RSI of MACD worden altijd uit die koersen berekend, dus elke indicator kan gebruikt worden zonder extra download.

**Stop loss en R:** bij een short staat de SL boven het hoogste punt van de eerste candle van de dag. R is de afstand tussen de instap en die SL. TP is een veelvoud van R (in het voorbeeld 4R). Bij een long staat de SL gespiegeld onder het laagste punt. De strategietekst mag zelf zeggen waar de SL staat. Dit is de standaardlezing.

## Fase 2: het trading-dagboek (grote lijnen)

1. De gebruiker start de schermwatcher en trade op TradingView (gratis account kan, demo of echt).
2. De watcher bewaart per trade een screenshot in een map die Claude kan lezen.
3. De gebruiker voert de derde skill uit. Claude leest de nieuwe screenshots, haalt de gegevens van elke trade eruit en werkt de rapportpagina bij.
4. Omdat de lokaal opgeslagen data niet tot die periode loopt, haalt de MCP-server de recente data en de belangrijkste indicatoren op voor het moment van de trade.
5. Claude vergelijkt de trade met de bewaarde strategie. Bij een verloren trade toont Claude wat niet klopte met de regels. Bij een gewonnen trade zegt Claude ook waarom het lukte.
6. De pagina toont statistieken over alle trades.

## Doelen

- Een niet-technische trader kan zonder code zijn idee testen.
- De gebruiker begrijpt waarom een trade won of verloor, door de grafiek.
- De vertaling van tekst naar regels is zichtbaar en controleerbaar. Claude beslist niets onzichtbaar.
- Het project werkt zonder eigen AI-sleutel en zonder betaalde dataprovider.

## Geen doelen (fase 1)

- Geen crypto en forex, geen aandelen buiten de 4 markten.
- Geen live handelen, geen koop- of verkoopadvies.
- Geen schermwatcher en geen dagboek (fase 2).
- Geen optimalisatie van parameters.
- Geen eigen Pine Script-interpreter.

## Wat het niet mag worden

- Een tool die zegt wat je moet kopen.
- Een backtest die er te mooi uitziet door vooruitkijken, dus door informatie te gebruiken die op dat moment nog niet bekend was.
- Een programma dat door een AI geschreven code uitvoert op de computer van de gebruiker.

## Beperkingen

- Publiek, dus een duidelijke melding "geen financieel advies" in de README en in het rapport.
- Pine Script draait alleen binnen TradingView. Claude vertaalt het naar het vaste formaat. Wat niet te vertalen is, wordt gemeld als "niet ondersteund".
- Gratis databronnen hebben limieten en veranderen. Het ontwerp daarom: eenmaal downloaden en lokaal bewaren.
- Wat Claude's apps ondersteunen (skills, MCP-servers, artefacten, lokale bestanden) is niet voor alle varianten gecontroleerd.

## Aanpakken die we overwogen

- **A. Website.** Makkelijk te delen, maar kan niet op de achtergrond meekijken voor het dagboek.
- **B. Python-programma met eigen webpagina en eigen AI-sleutel (versie 1).** Werkt, maar de gebruiker heeft een eigen AI-sleutel en een eigen scherm naast Claude nodig.
- **C. Desktop-app.** Veel werk voor een eerste resultaat.
- **D. Claude-plugin: skills, MCP-server en schermwatcher.** Gekozen door de maker. Claude is het scherm, het lezen en het schrijven. Er is geen eigen AI-sleutel nodig.

## Beslissingen van de maker

- Claude-plugin op GitHub, geschreven in Python voor de MCP-server en de watcher.
- Strategie in gewone tekst of Pine Script, in Claude uitgelegd.
- De 4 markten hierboven.
- Fase 1 eerst: de backtester met grote grafieken en 3 voorbeeldtrades.
- Skills voor backtesten, een strategie heropenen met de naam, en nieuwe trades verwerken.
- Schermwatcher bewaart screenshots die Claude leest.
- Indicatoren van het moment van de trade komen via een MCP-server.
- Stop loss boven de eerste candle, R als afstand.

## Mijn keuzes (nog niet door de maker bevestigd)

- **Doelgroep-app:** Claude Code of de Claude-desktopapp, omdat die lokale bestanden, een lokale MCP-server en een achtergrondprogramma kunnen gebruiken. De webversie van Claude past daar niet bij. De bouwer controleert dit.

- **Bron van waarheid zijn lokale bestanden, het artefact is een weergave.** De strategie (met naam), de trades en de screenshots staan als bestanden op de computer. De rapportpagina wordt daaruit opnieuw gebouwd. Zo blijft alles bewaard, ook als een artefact niet beschikbaar is in een sessie.
- **Eén eigen MCP-server doet het data- en indicatorwerk**, zowel voor de lokale bestanden als voor het ophalen van recente data. De gebruiker hoeft dan geen aparte Twelve Data-koppeling in te stellen.
- **Dataperiode:** standaard 5 jaar voor 1 uur, 4 uur en dag. Voor 1, 5, 15 en 30 minuten zo ver terug als de gratis bron toelaat, want gratis minuutdata gaat meestal minder ver terug. De gebruiker kan dat aanpassen. De bouwer controleert wat de bron toelaat.
- **Grotere timeframes worden lokaal samengesteld uit kleinere** waar dat kan (bijvoorbeeld 5 minuten uit 1 minuut). Dat scheelt downloads en houdt de timeframes onderling gelijk.
- **Databronnen (gecontroleerd op 15 november 2026):** Twelve Data met een gratis account, 800 aanroepen per dag, intraday data vanaf begin 2020. S&P 500 via SPY, Nasdaq 100 via QQQ, goud via XAU/USD. Zilver (XAG/USD) vraagt een betaald plan bij Twelve Data, dus fase 1 gebruikt het zilverfonds SLV als vervanger, met een melding. SLV handelt alleen tijdens Amerikaanse beursuren. Een gratis bron voor de echte zilverkoers (bijvoorbeeld Dukascopy) is niet gecontroleerd en komt later.
- **De AI levert geen code, maar regels in een vast formaat.** Een eigen rekenmotor voert die regels uit.
- **Instap** op de open van de candle na het signaal. **Eén positie tegelijk.** Raken SL en TP in dezelfde candle, dan telt de SL. Resultaten in R, zonder kosten. Is de instap al op of voorbij de SL, of is R nul, dan wordt de trade overgeslagen en gemeld.
- **"Begin van de dag":** de open van de handelsdag per markt. Beurzen: de open van de beurs, 09:30 New York. Goud en zilver: 18:00 New York, als de markt na de dagelijkse pauze weer opent (beslissing van de maker op 15 november 2026, na de proef op echte data: met 00:00 UTC was elke zondagavond een "dag" van één candle). Aanpasbaar per strategie.
- **Welke 3 trades:** per categorie een willekeurige, zodat het niet uitgekozen is. Met een manier om een andere te tonen.
- **Indicatoren op de grafiek:** die van de strategie zelf, plus RSI, MACD en EMA 50/200. Volume alleen als de bron het heeft.
- **Herkenning van een trade door de watcher (fase 2):** de gebruiker markeert eenmalig het deel van het scherm met je posities en orders. De watcher maakt een screenshot als dat deel verandert. Claude beslist later wat een trade is. Dit is een voorstel dat in fase 2 verder wordt ontworpen.

## Aan de bouwer overgelaten

- Welke gratis databronnen precies, en hoe ver terug uurdata beschikbaar is.
- Mapstructuur, naam van de repo, testopzet.
- Hoe de regels er precies uitzien, zolang ze controleerbaar blijven voor de gebruiker.
- Hoe de skills en het artefact aan elkaar gekoppeld worden.
- Foutmeldingen en uiterlijk.

## Hoe we merken dat het werkt (fase 1)

- Het voorbeeld van de maker wordt correct vertaald en getest op goud.
- De gebruiker ziet 3 trades op de grafiek die kloppen met de data.
- Een rekenvoorbeeld op papier komt overeen met de uitkomst van de motor.
- Er zijn tests voor vooruitkijken, SL en TP in dezelfde candle, en ontbrekende data.
- Een bewaarde strategie kan in een nieuwe sessie met de naam heropend worden.
