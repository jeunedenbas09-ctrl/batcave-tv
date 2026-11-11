"""Mise à jour Batcave dans le cloud (GitHub Actions) : génère donnees.json et briefing.mp3.
Pas de PC requis. Ne contient aucun secret. Les données lues sont publiques (météo, mosquée, FFF)."""
import asyncio, datetime as dt, json, re, urllib.parse, urllib.request
from html import unescape

PARIS = dt.timezone(dt.timedelta(hours=1))
MAINTENANT = dt.datetime.now(PARIS)
JOURS = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
MOIS = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode("utf-8", "replace")

def meteo():
    g = json.loads(get("https://geocoding-api.open-meteo.com/v1/search?name=Choisy-le-Roi&count=1&language=fr"))["results"][0]
    d = json.loads(get("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
        "latitude": g["latitude"], "longitude": g["longitude"], "timezone": "auto", "forecast_days": 1,
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset"})))
    c, j = d["current"], d["daily"]
    return {"ville": "Choisy-le-Roi", "temp": round(c["temperature_2m"]), "ressenti": round(c["apparent_temperature"]),
            "min": round(j["temperature_2m_min"][0]), "max": round(j["temperature_2m_max"][0]),
            "pluie": j["precipitation_probability_max"][0], "vent": round(c["wind_speed_10m"]),
            "lever": j["sunrise"][0][-5:], "coucher": j["sunset"][0][-5:], "releve": c["time"]}

def tableau(html, cle):
    i = html.find('"' + cle + '":[')
    d, debut = 0, html.index("[", i)
    for p in range(debut, len(html)):
        d += (html[p] == "[") - (html[p] == "]")
        if d == 0:
            return json.loads(html[debut:p + 1])

def prieres():
    html = get("https://mawaqit.net/fr/mosquee-de-choisy-le-roi-choisy-le-roi")
    cal = tableau(html, "calendar")[MAINTENANT.month - 1][str(MAINTENANT.day)]
    iq = tableau(html, "iqamaCalendar")[MAINTENANT.month - 1][str(MAINTENANT.day)]
    noms = ["Fajr", "Shuruq", "Dhuhr", "Asr", "Maghrib", "Isha"]
    adhan = dict(zip(noms, cal))
    out = []
    for nom, dec in zip(["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"], iq):
        a = adhan[nom]; h, m = map(int, a.split(":")); t = (h*60 + m + int(dec.replace("+", ""))) % 1440
        out.append({"nom": nom, "adhan": a, "iqama": f"{t//60:02d}:{t%60:02d}"})
    out.insert(1, {"nom": "Shuruq", "adhan": adhan["Shuruq"], "iqama": None})
    return {"mosquee": "AMC Mosquée de Choisy-Le-Roi", "prieres": out, "jumua": ["12:45", "13:45"]}

def classement_et_match():
    """Lit le classement et le prochain match sur le site de la FFF (page publique)."""
    base = "https://epreuves.fff.fr/competition/club/500031-choisy-le-roi-as-2/equipe/2026_180_SEM_2/"
    cl = unescape(re.sub(r"<[^>]+>", " ", get(base + "classement")))
    cal = unescape(re.sub(r"<[^>]+>", " ", get(base + "resultat-calendrier")))
    return {"source": base, "classement_brut": " ".join(cl.split())[:4000], "calendrier_brut": " ".join(cal.split())[:4000]}

async def voix(texte, fichier):
    import edge_tts
    await edge_tts.Communicate(texte, voice="fr-FR-HenriNeural", rate="+0%", pitch="-6Hz").save(fichier)

if __name__ == "__main__":
    prio = json.loads(open("priorites.json", encoding="utf-8").read())
    donnees = {"date": f"{JOURS[MAINTENANT.weekday()]} {MAINTENANT.day} {MOIS[MAINTENANT.month-1]} {MAINTENANT.year}",
               "genere": MAINTENANT.strftime("%Y-%m-%d %H:%M"), "meteo": meteo(), "prieres": prieres(),
               "priorites": prio, "match": classement_et_match()}
    texte = (f"Bonjour, Monsieur Amine. Il est {MAINTENANT.hour} heures {MAINTENANT.minute:02d}. "
             f"À Choisy-le-Roi, {donnees['meteo']['temp']} degrés. "
             "Vos priorités du jour : " + " ; ".join(prio) + ". La Batcave est prête. Force et honneur, Monsieur.")
    donnees["texte"] = texte
    json.dump(donnees, open("donnees.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    asyncio.run(voix(texte, "briefing.mp3"))
    print("donnees.json et briefing.mp3 prêts")