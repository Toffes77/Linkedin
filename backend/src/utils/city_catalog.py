import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

import geonamescache
from babel import Locale


CITY_FORMAT = re.compile(r"^[^,]+, \S.*$")

# GeoNames conserva el nombre geográfico original. Solo se adaptan exónimos
# españoles inequívocos que forman parte de la presentación actual de Atanes.
CITY_NAME_ES_OVERRIDES = {
    2950159: "Berlín",
    2988507: "París",
    3169070: "Roma",
    3173435: "Milán",
    2867714: "Múnich",
}


def normalize_city_search(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return " ".join(without_accents.casefold().split())


@dataclass(frozen=True, slots=True)
class CityRecord:
    pais: str
    ciudad: str
    nombre: str
    population: int
    normalized_city: str
    normalized_name: str


class CityCatalog:
    def __init__(self):
        geonames = geonamescache.GeonamesCache()
        territory_names = Locale.parse("es").territories
        records_by_name: dict[str, CityRecord] = {}

        for raw_city in geonames.get_cities().values():
            country_code = raw_city["countrycode"]
            country_name = territory_names.get(country_code)
            if not country_name:
                continue

            city_name = CITY_NAME_ES_OVERRIDES.get(
                raw_city["geonameid"],
                raw_city["name"],
            ).strip()
            if not city_name:
                continue

            display_name = f"{country_name}, {city_name}"
            normalized_name = normalize_city_search(display_name)
            record = CityRecord(
                pais=country_name,
                ciudad=city_name,
                nombre=display_name,
                population=int(raw_city.get("population") or 0),
                normalized_city=normalize_city_search(city_name),
                normalized_name=normalized_name,
            )
            current = records_by_name.get(normalized_name)
            if current is None or record.population > current.population:
                records_by_name[normalized_name] = record

        self.records = tuple(records_by_name.values())
        self.by_normalized_name = {
            record.normalized_name: record for record in self.records
        }

    def search(self, query: str, limit: int) -> list[CityRecord]:
        normalized_query = normalize_city_search(query)
        matches: list[tuple[int, int, str, CityRecord]] = []
        for record in self.records:
            if record.normalized_city.startswith(normalized_query):
                relevance = 0
            elif record.normalized_name.startswith(normalized_query):
                relevance = 1
            elif normalized_query in record.normalized_city:
                relevance = 2
            elif normalized_query in record.normalized_name:
                relevance = 3
            else:
                continue
            matches.append(
                (relevance, -record.population, record.normalized_name, record)
            )

        matches.sort(key=lambda item: item[:3])
        return [item[3] for item in matches[:limit]]

    def canonicalize(self, value: str) -> CityRecord | None:
        if not CITY_FORMAT.fullmatch(value):
            return None
        return self.by_normalized_name.get(normalize_city_search(value))


@lru_cache(maxsize=1)
def get_city_catalog() -> CityCatalog:
    return CityCatalog()
