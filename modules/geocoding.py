from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Any

import requests

from .config import CONFIG


@dataclass(frozen=True)
class Location:
    query: str
    display_name: str
    lat: float
    lon: float
    source: str = "unknown"


class GeocodingError(RuntimeError):
    pass


_last_request_ts = 0.0


# Proje demosunun adres çözümleme servislerine takılmadan çalışabilmesi için
# Türkiye'deki sık kullanılan il/ilçe merkezlerinden oluşan küçük bir yerel taban.
# Koordinatlar yaklaşık merkez noktalarıdır; navigasyon hassasiyeti değil, karar destek
# demosu amaçlanmıştır.
LOCAL_PLACES: dict[str, tuple[str, float, float]] = {
    # Marmara / kullanıcı demosunda sık kullanılan yerler
    "gebze": ("Gebze, Kocaeli, Türkiye", 40.8028, 29.4307),
    "darica": ("Darıca, Kocaeli, Türkiye", 40.7593, 29.3851),
    "darıca": ("Darıca, Kocaeli, Türkiye", 40.7593, 29.3851),
    "kocaeli": ("Kocaeli / İzmit, Türkiye", 40.7667, 29.9167),
    "izmit": ("İzmit, Kocaeli, Türkiye", 40.7667, 29.9167),
    "istanbul": ("İstanbul, Türkiye", 41.0082, 28.9784),
    "i̇stanbul": ("İstanbul, Türkiye", 41.0082, 28.9784),
    "bahcesehir": ("Bahçeşehir, İstanbul, Türkiye", 41.0608, 28.6747),
    "bahçeşehir": ("Bahçeşehir, İstanbul, Türkiye", 41.0608, 28.6747),
    "basaksehir": ("Başakşehir, İstanbul, Türkiye", 41.0931, 28.8021),
    "başakşehir": ("Başakşehir, İstanbul, Türkiye", 41.0931, 28.8021),
    "tuzla": ("Tuzla, İstanbul, Türkiye", 40.8161, 29.3006),
    "pendik": ("Pendik, İstanbul, Türkiye", 40.8747, 29.2350),
    "kadikoy": ("Kadıköy, İstanbul, Türkiye", 40.9919, 29.0252),
    "kadıköy": ("Kadıköy, İstanbul, Türkiye", 40.9919, 29.0252),
    "uskudar": ("Üsküdar, İstanbul, Türkiye", 41.0255, 29.0150),
    "üsküdar": ("Üsküdar, İstanbul, Türkiye", 41.0255, 29.0150),
    "sile": ("Şile, İstanbul, Türkiye", 41.1754, 29.6133),
    "şile": ("Şile, İstanbul, Türkiye", 41.1754, 29.6133),
    "agva": ("Ağva, İstanbul, Türkiye", 41.1382, 29.8567),
    "ağva": ("Ağva, İstanbul, Türkiye", 41.1382, 29.8567),
    # Büyükşehirler ve il merkezleri
    "adana": ("Adana, Türkiye", 37.0000, 35.3213),
    "adiyaman": ("Adıyaman, Türkiye", 37.7648, 38.2786),
    "adıyaman": ("Adıyaman, Türkiye", 37.7648, 38.2786),
    "afyon": ("Afyonkarahisar, Türkiye", 38.7569, 30.5387),
    "afyonkarahisar": ("Afyonkarahisar, Türkiye", 38.7569, 30.5387),
    "agri": ("Ağrı, Türkiye", 39.7191, 43.0503),
    "ağrı": ("Ağrı, Türkiye", 39.7191, 43.0503),
    "agri merkez": ("Ağrı Merkez, Türkiye", 39.7191, 43.0503),
    "ağrı merkez": ("Ağrı Merkez, Türkiye", 39.7191, 43.0503),
    "amasya": ("Amasya, Türkiye", 40.6533, 35.8331),
    "ankara": ("Ankara, Türkiye", 39.9208, 32.8541),
    "antalya": ("Antalya, Türkiye", 36.8969, 30.7133),
    "artvin": ("Artvin, Türkiye", 41.1828, 41.8183),
    "aydin": ("Aydın, Türkiye", 37.8450, 27.8396),
    "aydın": ("Aydın, Türkiye", 37.8450, 27.8396),
    "balikesir": ("Balıkesir, Türkiye", 39.6484, 27.8826),
    "balıkesir": ("Balıkesir, Türkiye", 39.6484, 27.8826),
    "bilecik": ("Bilecik, Türkiye", 40.1506, 29.9792),
    "bingol": ("Bingöl, Türkiye", 38.8847, 40.4939),
    "bingöl": ("Bingöl, Türkiye", 38.8847, 40.4939),
    "bitlis": ("Bitlis, Türkiye", 38.4006, 42.1095),
    "bolu": ("Bolu, Türkiye", 40.7395, 31.6116),
    "burdur": ("Burdur, Türkiye", 37.7203, 30.2908),
    "bursa": ("Bursa, Türkiye", 40.1828, 29.0664),
    "canakkale": ("Çanakkale, Türkiye", 40.1553, 26.4142),
    "çanakkale": ("Çanakkale, Türkiye", 40.1553, 26.4142),
    "cankiri": ("Çankırı, Türkiye", 40.6013, 33.6134),
    "çankırı": ("Çankırı, Türkiye", 40.6013, 33.6134),
    "corum": ("Çorum, Türkiye", 40.5499, 34.9537),
    "çorum": ("Çorum, Türkiye", 40.5499, 34.9537),
    "denizli": ("Denizli, Türkiye", 37.7765, 29.0864),
    "diyarbakir": ("Diyarbakır, Türkiye", 37.9144, 40.2306),
    "diyarbakır": ("Diyarbakır, Türkiye", 37.9144, 40.2306),
    "edirne": ("Edirne, Türkiye", 41.6771, 26.5557),
    "elazig": ("Elazığ, Türkiye", 38.6810, 39.2264),
    "elazığ": ("Elazığ, Türkiye", 38.6810, 39.2264),
    "erzincan": ("Erzincan, Türkiye", 39.7500, 39.5000),
    "erzurum": ("Erzurum, Türkiye", 39.9043, 41.2679),
    "eskisehir": ("Eskişehir, Türkiye", 39.7767, 30.5206),
    "eskişehir": ("Eskişehir, Türkiye", 39.7767, 30.5206),
    "gaziantep": ("Gaziantep, Türkiye", 37.0662, 37.3833),
    "giresun": ("Giresun, Türkiye", 40.9128, 38.3895),
    "gumushane": ("Gümüşhane, Türkiye", 40.4603, 39.4814),
    "gümüşhane": ("Gümüşhane, Türkiye", 40.4603, 39.4814),
    "hakkari": ("Hakkari, Türkiye", 37.5744, 43.7408),
    "hatay": ("Hatay / Antakya, Türkiye", 36.2023, 36.1613),
    "antakya": ("Antakya, Hatay, Türkiye", 36.2023, 36.1613),
    "isparta": ("Isparta, Türkiye", 37.7648, 30.5566),
    "mersin": ("Mersin, Türkiye", 36.8121, 34.6415),
    "izmir": ("İzmir, Türkiye", 38.4237, 27.1428),
    "i̇zmir": ("İzmir, Türkiye", 38.4237, 27.1428),
    "kars": ("Kars, Türkiye", 40.6013, 43.0975),
    "kastamonu": ("Kastamonu, Türkiye", 41.3887, 33.7827),
    "kayseri": ("Kayseri, Türkiye", 38.7205, 35.4826),
    "kirklareli": ("Kırklareli, Türkiye", 41.7351, 27.2252),
    "kırklareli": ("Kırklareli, Türkiye", 41.7351, 27.2252),
    "kirsehir": ("Kırşehir, Türkiye", 39.1425, 34.1709),
    "kırşehir": ("Kırşehir, Türkiye", 39.1425, 34.1709),
    "konya": ("Konya, Türkiye", 37.8714, 32.4846),
    "kutahya": ("Kütahya, Türkiye", 39.4192, 29.9857),
    "kütahya": ("Kütahya, Türkiye", 39.4192, 29.9857),
    "malatya": ("Malatya, Türkiye", 38.3552, 38.3095),
    "manisa": ("Manisa, Türkiye", 38.6140, 27.4296),
    "kahramanmaras": ("Kahramanmaraş, Türkiye", 37.5753, 36.9228),
    "kahramanmaraş": ("Kahramanmaraş, Türkiye", 37.5753, 36.9228),
    "mardin": ("Mardin, Türkiye", 37.3122, 40.7350),
    "mugla": ("Muğla, Türkiye", 37.2153, 28.3636),
    "muğla": ("Muğla, Türkiye", 37.2153, 28.3636),
    "bodrum": ("Bodrum, Muğla, Türkiye", 37.0344, 27.4305),
    "marmaris": ("Marmaris, Muğla, Türkiye", 36.8550, 28.2742),
    "mus": ("Muş, Türkiye", 38.9462, 41.7539),
    "muş": ("Muş, Türkiye", 38.9462, 41.7539),
    "nevsehir": ("Nevşehir, Türkiye", 38.6244, 34.7239),
    "nevşehir": ("Nevşehir, Türkiye", 38.6244, 34.7239),
    "nigde": ("Niğde, Türkiye", 37.9698, 34.6766),
    "niğde": ("Niğde, Türkiye", 37.9698, 34.6766),
    "ordu": ("Ordu, Türkiye", 40.9862, 37.8797),
    "rize": ("Rize, Türkiye", 41.0255, 40.5177),
    "sakarya": ("Sakarya / Adapazarı, Türkiye", 40.7731, 30.3948),
    "adapazari": ("Adapazarı, Sakarya, Türkiye", 40.7731, 30.3948),
    "adapazarı": ("Adapazarı, Sakarya, Türkiye", 40.7731, 30.3948),
    "samsun": ("Samsun, Türkiye", 41.2867, 36.3300),
    "siirt": ("Siirt, Türkiye", 37.9333, 41.9500),
    "sinop": ("Sinop, Türkiye", 42.0264, 35.1551),
    "sivas": ("Sivas, Türkiye", 39.7477, 37.0179),
    "tekirdag": ("Tekirdağ, Türkiye", 40.9781, 27.5117),
    "tekirdağ": ("Tekirdağ, Türkiye", 40.9781, 27.5117),
    "tokat": ("Tokat, Türkiye", 40.3167, 36.5500),
    "trabzon": ("Trabzon, Türkiye", 41.0027, 39.7168),
    "tunceli": ("Tunceli, Türkiye", 39.1081, 39.5483),
    "sanliurfa": ("Şanlıurfa, Türkiye", 37.1674, 38.7955),
    "şanlıurfa": ("Şanlıurfa, Türkiye", 37.1674, 38.7955),
    "urfa": ("Şanlıurfa, Türkiye", 37.1674, 38.7955),
    "usak": ("Uşak, Türkiye", 38.6823, 29.4082),
    "uşak": ("Uşak, Türkiye", 38.6823, 29.4082),
    "van": ("Van, Türkiye", 38.5012, 43.3729),
    "yozgat": ("Yozgat, Türkiye", 39.8181, 34.8147),
    "zonguldak": ("Zonguldak, Türkiye", 41.4564, 31.7987),
    "aksaray": ("Aksaray, Türkiye", 38.3687, 34.0370),
    "bayburt": ("Bayburt, Türkiye", 40.2552, 40.2249),
    "karaman": ("Karaman, Türkiye", 37.1811, 33.2150),
    "kirikkale": ("Kırıkkale, Türkiye", 39.8468, 33.5153),
    "kırıkkale": ("Kırıkkale, Türkiye", 39.8468, 33.5153),
    "batman": ("Batman, Türkiye", 37.8874, 41.1322),
    "sirnak": ("Şırnak, Türkiye", 37.4187, 42.4918),
    "şırnak": ("Şırnak, Türkiye", 37.4187, 42.4918),
    "bartin": ("Bartın, Türkiye", 41.5811, 32.4610),
    "bartın": ("Bartın, Türkiye", 41.5811, 32.4610),
    "ardahan": ("Ardahan, Türkiye", 41.1105, 42.7022),
    "igdir": ("Iğdır, Türkiye", 39.9201, 44.0436),
    "ığdır": ("Iğdır, Türkiye", 39.9201, 44.0436),
    "yalova": ("Yalova, Türkiye", 40.6500, 29.2667),
    "karabuk": ("Karabük, Türkiye", 41.2061, 32.6204),
    "karabük": ("Karabük, Türkiye", 41.2061, 32.6204),
    "kilis": ("Kilis, Türkiye", 36.7184, 37.1212),
    "osmaniye": ("Osmaniye, Türkiye", 37.0746, 36.2464),
    "duzce": ("Düzce, Türkiye", 40.8438, 31.1565),
    "düzce": ("Düzce, Türkiye", 40.8438, 31.1565),
}


ALIASES: dict[str, str] = {
    "istanbul": "istanbul",
    "i̇stanbul": "istanbul",
    "izmir": "izmir",
    "i̇zmir": "izmir",
    "agri merkez": "agri merkez",
    "ağrı merkez": "ağrı merkez",
    "bahcesehir 2 kisim": "bahcesehir",
    "bahcesehir 2. kisim": "bahcesehir",
    "bahçeşehir 2 kısım": "bahçeşehir",
    "bahçeşehir 2. kısım": "bahçeşehir",
}


def _headers() -> dict[str, str]:
    return {
        "User-Agent": CONFIG.nominatim_user_agent,
        "Accept": "application/json",
        "Accept-Language": "tr,en;q=0.8",
    }


def _normalize_text(text: str) -> str:
    text = text.strip().lower().replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_coordinate_pair(query: str) -> Location | None:
    """Kullanıcı 40.8028, 29.4307 gibi koordinat girerse doğrudan kullanır."""
    cleaned = query.strip().replace(";", ",")
    match = re.fullmatch(r"\s*(-?\d+(?:[\.,]\d+)?)\s*,\s*(-?\d+(?:[\.,]\d+)?)\s*", cleaned)
    if not match:
        return None
    lat = float(match.group(1).replace(",", "."))
    lon = float(match.group(2).replace(",", "."))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise GeocodingError("Girilen koordinatlar geçerli aralıkta değil.")
    return Location(query=query.strip(), display_name=f"Koordinat: {lat:.5f}, {lon:.5f}", lat=lat, lon=lon, source="Manuel koordinat")


def _lookup_place_by_exact_or_contained(text: str) -> Location | None:
    """Verilen kısa metinde yerel tabana göre en uygun yer adını arar."""
    normalized = _normalize_text(text)
    if not normalized:
        return None

    for alias, canonical in sorted(ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        n_alias = _normalize_text(alias)
        if re.search(rf"(^|\s){re.escape(n_alias)}(\s|$)", normalized):
            place = LOCAL_PLACES.get(canonical) or LOCAL_PLACES.get(_normalize_text(canonical))
            if place:
                display, lat, lon = place
                return Location(text.strip(), display, lat, lon, "Yerel demo koordinat tabanı")

    normalized_places = [(_normalize_text(key), key) for key in LOCAL_PLACES.keys()]
    normalized_places.sort(key=lambda item: len(item[0]), reverse=True)
    for norm_key, original_key in normalized_places:
        if re.search(rf"(^|\s){re.escape(norm_key)}(\s|$)", normalized):
            display, lat, lon = LOCAL_PLACES[original_key]
            return Location(text.strip(), display, lat, lon, "Yerel demo koordinat tabanı")
    return None


def _geocode_with_local_db(clean_query: str) -> Location | None:
    normalized = _normalize_text(clean_query)
    if not normalized:
        return None

    # Virgüllü adreslerde ilk parça genelde daha özel yerdir: "Gebze, Kocaeli" gibi.
    first_part = re.split(r"[,/;-]", clean_query, maxsplit=1)[0].strip()
    if first_part and first_part != clean_query.strip():
        first_match = _lookup_place_by_exact_or_contained(first_part)
        if first_match:
            return Location(clean_query, first_match.display_name, first_match.lat, first_match.lon, first_match.source)

    # Önce özel aliasları dene.
    for alias, canonical in sorted(ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        n_alias = _normalize_text(alias)
        if re.search(rf"(^|\s){re.escape(n_alias)}(\s|$)", normalized):
            place = LOCAL_PLACES.get(canonical) or LOCAL_PLACES.get(_normalize_text(canonical))
            if place:
                display, lat, lon = place
                return Location(clean_query, display, lat, lon, "Yerel demo koordinat tabanı")

    # Sonra en uzun yer adından başlayarak genel eşleşme yap.
    normalized_places = [(_normalize_text(key), key) for key in LOCAL_PLACES.keys()]
    normalized_places.sort(key=lambda item: len(item[0]), reverse=True)
    for norm_key, original_key in normalized_places:
        if re.search(rf"(^|\s){re.escape(norm_key)}(\s|$)", normalized):
            display, lat, lon = LOCAL_PLACES[original_key]
            return Location(clean_query, display, lat, lon, "Yerel demo koordinat tabanı")
    return None


def _rate_limit() -> None:
    global _last_request_ts
    elapsed = time.time() - _last_request_ts
    if elapsed < 1.2:
        time.sleep(1.2 - elapsed)


def _geocode_with_nominatim(clean_query: str) -> Location:
    global _last_request_ts
    _rate_limit()
    url = "https://nominatim.openstreetmap.org/search"
    query_for_api = clean_query if "türkiye" in clean_query.lower() or "turkey" in clean_query.lower() else f"{clean_query}, Türkiye"
    params: dict[str, Any] = {
        "q": query_for_api,
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 1,
    }
    try:
        response = requests.get(url, params=params, headers=_headers(), timeout=20)
        _last_request_ts = time.time()
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "bilinmiyor"
        raise GeocodingError(f"Nominatim adres çözümleme hatası: HTTP {status_code}") from exc
    except requests.RequestException as exc:
        raise GeocodingError(f"Nominatim bağlantı hatası: {exc}") from exc

    data = response.json()
    if not data:
        raise GeocodingError("Nominatim adres sonucu bulamadı.")

    item = data[0]
    return Location(
        query=clean_query,
        display_name=item.get("display_name", clean_query),
        lat=float(item["lat"]),
        lon=float(item["lon"]),
        source="Nominatim",
    )


def _candidate_place_names(clean_query: str) -> list[str]:
    """Open-Meteo/Photon gibi yer adı arayan servisler için sade adaylar üretir."""
    normalized_original = clean_query.strip()
    candidates = [normalized_original]
    for sep in [",", "-", "/"]:
        if sep in normalized_original:
            candidates.append(normalized_original.split(sep)[0].strip())
    words = _normalize_text(normalized_original).split()
    # Cadde/no gibi kelimeleri temizleyip son 1-2 anlamlı kelimeyi dene.
    stop = {"cd", "cad", "cadde", "caddesi", "sok", "sokak", "mah", "mahalle", "mahallesi", "no", "numara", "kisim", "kısım", "merkez"}
    meaningful = [w for w in words if w not in stop and not w.isdigit()]
    if meaningful:
        candidates.append(" ".join(meaningful[-2:]))
        candidates.append(meaningful[-1])
    # Tekrarları korumadan dön.
    unique: list[str] = []
    for c in candidates:
        c = c.strip()
        if c and c not in unique:
            unique.append(c)
    return unique


def _geocode_with_open_meteo(clean_query: str) -> Location:
    """Ücretsiz ve anahtarsız Open-Meteo Geocoding API ile şehir/ilçe araması yapar."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    errors: list[str] = []
    for candidate in _candidate_place_names(clean_query):
        params = {
            "name": candidate,
            "count": 5,
            "language": "tr",
            "format": "json",
        }
        try:
            response = requests.get(url, params=params, headers=_headers(), timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            errors.append(str(exc))
            continue

        results = response.json().get("results", [])
        if not results:
            continue

        # Türkiye sonucunu tercih et; yoksa ilk sonucu kullan.
        item = next((r for r in results if r.get("country_code") == "TR"), results[0])
        name_parts = [item.get("name"), item.get("admin1"), item.get("country")]
        display_name = ", ".join(str(p) for p in name_parts if p)
        return Location(
            query=clean_query,
            display_name=display_name or clean_query,
            lat=float(item["latitude"]),
            lon=float(item["longitude"]),
            source="Open-Meteo Geocoding",
        )
    raise GeocodingError("Open-Meteo şehir/ilçe sonucu bulamadı." + (" " + " | ".join(errors[:2]) if errors else ""))


def _geocode_with_photon(clean_query: str) -> Location:
    """Nominatim erişilemezse Komoot Photon demo servisiyle yedek arama yapar."""
    url = "https://photon.komoot.io/api"
    errors: list[str] = []
    for candidate in _candidate_place_names(clean_query):
        params: dict[str, Any] = {
            "q": candidate,
            "limit": 1,
            # Photon her dil kodunu desteklemiyor; tr bazı durumlarda 400 döndürebiliyor.
            # Bu yüzden lang parametresini göndermiyoruz.
        }
        try:
            response = requests.get(url, params=params, headers=_headers(), timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            errors.append(str(exc))
            continue

        data = response.json()
        features = data.get("features", [])
        if not features:
            continue

        feature = features[0]
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", None)
        if not coords or len(coords) < 2:
            continue

        lon, lat = coords[0], coords[1]
        parts = [
            props.get("name"),
            props.get("street"),
            props.get("district"),
            props.get("city"),
            props.get("state"),
            props.get("country"),
        ]
        display_name = ", ".join(str(p) for p in parts if p)
        return Location(
            query=clean_query,
            display_name=display_name or clean_query,
            lat=float(lat),
            lon=float(lon),
            source="Photon",
        )
    raise GeocodingError("Photon adres sonucu bulamadı." + (" " + " | ".join(errors[:2]) if errors else ""))


def geocode_address(query: str) -> Location:
    """Adresi koordinata çevirir.

    Sıra özellikle demo dayanıklılığı için böyledir:
    1. Kullanıcı koordinat girdiyse doğrudan kullanılır.
    2. Türkiye şehir/ilçe adları yerel demo tabanından çözülür.
    3. Nominatim denenir.
    4. Open-Meteo Geocoding denenir.
    5. Photon denenir.

    Böylece Nominatim 403 veya Photon 400 verse bile uygulama basit şehir/ilçe
    demolarında durmaz.
    """
    clean_query = query.strip()
    if not clean_query:
        raise GeocodingError("Adres boş bırakılamaz.")

    coordinate_location = _parse_coordinate_pair(clean_query)
    if coordinate_location:
        return coordinate_location

    local_location = _geocode_with_local_db(clean_query)
    if local_location:
        return local_location

    errors: list[str] = []
    for resolver in (_geocode_with_nominatim, _geocode_with_open_meteo, _geocode_with_photon):
        try:
            return resolver(clean_query)
        except GeocodingError as exc:
            errors.append(str(exc))

    raise GeocodingError(
        "Adres çözümlenemedi. Şehir/ilçe adını daha açık yazın veya doğrudan koordinat girin "
        "(örnek: 40.8028, 29.4307). Ayrıntı: " + " | ".join(errors)
    )
