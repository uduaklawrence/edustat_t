# geo_config.py

ZONES = {
    "North-Central": [
        "Benue", "Kogi", "Kwara",
        "Nasarawa", "Nassarawa",   # keep alias if old data uses this spelling
        "Niger", "Plateau",
        "Abuja", "FCT", "Federal Capital Territory",
    ],
    "North-East": [
        "Adamawa", "Bauchi", "Borno",
        "Gombe", "Taraba", "Yobe",
    ],
    "North-West": [
        "Jigawa", "Kaduna", "Kano",
        "Katsina", "Kebbi", "Sokoto", "Zamfara",
    ],
    "South-East": [
        "Abia", "Anambra", "Ebonyi",
        "Enugu", "Imo",
    ],
    "South-South": [
        "Akwa Ibom", "Bayelsa", "Cross River",
        "Delta", "Edo", "Rivers",
    ],
    "South-West": [
        "Ekiti", "Lagos", "Ogun",
        "Ondo", "Osun", "Oyo",
    ],
}


def state_to_zone(state: str) -> str:
    state = str(state).strip()

    for zone, states in ZONES.items():
        if state in states:
            return zone

    return "Other"


def states_for_regions(regions) -> list:
    result = set()

    for region in regions or []:
        result.update(ZONES.get(region, []))

    return sorted(result)