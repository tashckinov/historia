from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorldState:
    territory_owner: dict[str, str] = field(default_factory=dict)
    country_regions: dict[str, list[str]] = field(default_factory=dict)
    active_wars: list[tuple[str, str]] = field(default_factory=list)
    active_truces: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "territory_owner": self.territory_owner,
            "country_regions": self.country_regions,
            "active_wars": [list(pair) for pair in self.active_wars],
            "active_truces": [list(pair) for pair in self.active_truces],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WorldState":
        payload = payload or {}
        territory_owner_raw = payload.get("territory_owner", {})
        country_regions_raw = payload.get("country_regions", {})
        active_wars_raw = payload.get("active_wars", [])
        active_truces_raw = payload.get("active_truces", [])

        territory_owner = {
            str(region).strip(): str(owner).strip()
            for region, owner in territory_owner_raw.items()
            if str(region).strip() and str(owner).strip()
        } if isinstance(territory_owner_raw, dict) else {}

        country_regions = {
            str(country).strip(): [str(region).strip() for region in regions if str(region).strip()]
            for country, regions in country_regions_raw.items()
            if str(country).strip() and isinstance(regions, list)
        } if isinstance(country_regions_raw, dict) else {}

        active_wars = _normalize_pairs(active_wars_raw)
        active_truces = _normalize_pairs(active_truces_raw)
        return cls(
            territory_owner=territory_owner,
            country_regions=country_regions,
            active_wars=active_wars,
            active_truces=active_truces,
        )

    def owner_of(self, region: str) -> str | None:
        return self.territory_owner.get(region.strip())

    def apply_confirmed_updates(self, articles: list[dict[str, Any]]) -> None:
        for article in articles:
            if not isinstance(article, dict):
                continue

            if article.get("confirmed") is False:
                continue

            for change in article.get("territory_changes", []):
                if not isinstance(change, dict):
                    continue
                region = str(change.get("region", "")).strip()
                new_owner = str(change.get("to", "")).strip()
                if not region or not new_owner:
                    continue
                old_owner = self.territory_owner.get(region)
                if old_owner and old_owner in self.country_regions:
                    self.country_regions[old_owner] = [r for r in self.country_regions[old_owner] if r != region]
                self.territory_owner[region] = new_owner
                self.country_regions.setdefault(new_owner, [])
                if region not in self.country_regions[new_owner]:
                    self.country_regions[new_owner].append(region)

            for pair in _normalize_pairs(article.get("wars_started", [])):
                if pair not in self.active_wars:
                    self.active_wars.append(pair)
                if pair in self.active_truces:
                    self.active_truces.remove(pair)

            for pair in _normalize_pairs(article.get("truces_started", [])):
                if pair not in self.active_truces:
                    self.active_truces.append(pair)
                if pair in self.active_wars:
                    self.active_wars.remove(pair)

    def summary_for_country(self, country: str, regions_of_interest: list[str] | None = None) -> str:
        country = (country or "").strip()
        own_regions = self.country_regions.get(country, [])

        related_wars = [pair for pair in self.active_wars if country in pair]
        related_truces = [pair for pair in self.active_truces if country in pair]

        roi = []
        if regions_of_interest:
            for region in regions_of_interest:
                owner = self.owner_of(region)
                if owner:
                    roi.append(f"- {region}: {owner}")

        parts = [
            f"- Регионы игрока ({country}): {', '.join(own_regions) if own_regions else 'нет данных'}",
            f"- Активные войны ({country}): {', '.join(f'{a} vs {b}' for a, b in related_wars) if related_wars else 'нет данных'}",
            f"- Активные перемирия ({country}): {', '.join(f'{a} ↔ {b}' for a, b in related_truces) if related_truces else 'нет данных'}",
            "- Спорные/упомянутые регионы:\n" + ("\n".join(roi) if roi else "нет данных"),
        ]
        return "\n".join(parts)


def _normalize_pairs(raw: Any) -> list[tuple[str, str]]:
    if not isinstance(raw, list):
        return []

    pairs: list[tuple[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            a = str(item.get("a", "")).strip()
            b = str(item.get("b", "")).strip()
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            a = str(item[0]).strip()
            b = str(item[1]).strip()
        else:
            continue
        if not a or not b:
            continue
        pair = tuple(sorted((a, b)))
        if pair not in pairs:
            pairs.append(pair)
    return pairs
