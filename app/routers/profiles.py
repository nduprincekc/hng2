from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from typing import Optional
from app.database import get_db
from app.models import Profile

router = APIRouter()

VALID_SORT_FIELDS = {"age", "created_at", "gender_probability"}
VALID_ORDERS = {"asc", "desc"}
VALID_AGE_GROUPS = {"child", "teenager", "adult", "senior"}
VALID_GENDERS = {"male", "female"}

# Country name -> ISO code mapping for NLP parser
COUNTRY_MAP = {
    "nigeria": "NG", "ghana": "GH", "kenya": "KE", "ethiopia": "ET",
    "tanzania": "TZ", "uganda": "UG", "senegal": "SN", "mali": "ML",
    "niger": "NE", "burkina faso": "BF", "guinea": "GN", "benin": "BJ",
    "togo": "TG", "sierra leone": "SL", "liberia": "LR", "ivory coast": "CI",
    "cote d'ivoire": "CI", "cameroon": "CM", "angola": "AO", "mozambique": "MZ",
    "zambia": "ZM", "zimbabwe": "ZW", "malawi": "MW", "rwanda": "RW",
    "burundi": "BI", "somalia": "SO", "sudan": "SD", "south sudan": "SS",
    "chad": "TD", "central african republic": "CF", "democratic republic of congo": "CD",
    "congo": "CG", "gabon": "GA", "equatorial guinea": "GQ", "namibia": "NA",
    "botswana": "BW", "lesotho": "LS", "swaziland": "SZ", "eswatini": "SZ",
    "madagascar": "MG", "mauritius": "MU", "seychelles": "SC", "comoros": "KM",
    "djibouti": "DJ", "eritrea": "ER", "egypt": "EG", "libya": "LY",
    "tunisia": "TN", "algeria": "DZ", "morocco": "MA", "mauritania": "MR",
    "gambia": "GM", "guinea-bissau": "GW", "cape verde": "CV", "sao tome": "ST",
    "south africa": "ZA", "namibia": "NA", "haiti": "HT", "jamaica": "JM",
    "trinidad": "TT", "barbados": "BB", "usa": "US", "united states": "US",
    "uk": "GB", "united kingdom": "GB", "canada": "CA", "australia": "AU",
    "france": "FR", "germany": "DE", "italy": "IT", "spain": "ES",
    "brazil": "BR", "india": "IN", "china": "CN", "japan": "JP",
}


def format_profile(p: Profile) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "gender": p.gender,
        "gender_probability": p.gender_probability,
        "age": p.age,
        "age_group": p.age_group,
        "country_id": p.country_id,
        "country_name": p.country_name,
        "country_probability": p.country_probability,
        "created_at": p.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if p.created_at else None,
    }


def apply_filters(query, gender, age_group, country_id, min_age, max_age,
                  min_gender_probability, min_country_probability):
    if gender:
        query = query.filter(Profile.gender == gender)
    if age_group:
        query = query.filter(Profile.age_group == age_group)
    if country_id:
        query = query.filter(Profile.country_id == country_id.upper())
    if min_age is not None:
        query = query.filter(Profile.age >= min_age)
    if max_age is not None:
        query = query.filter(Profile.age <= max_age)
    if min_gender_probability is not None:
        query = query.filter(Profile.gender_probability >= min_gender_probability)
    if min_country_probability is not None:
        query = query.filter(Profile.country_probability >= min_country_probability)
    return query


@router.get("/profiles")
def get_profiles(
    gender: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    min_gender_probability: Optional[float] = Query(None),
    min_country_probability: Optional[float] = Query(None),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    # Validate gender
    if gender and gender not in VALID_GENDERS:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid query parameters"})

    # Validate age_group
    if age_group and age_group not in VALID_AGE_GROUPS:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid query parameters"})

    # Validate sort_by
    if sort_by and sort_by not in VALID_SORT_FIELDS:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid query parameters"})

    # Validate order
    if order and order not in VALID_ORDERS:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid query parameters"})

    # Validate age range
    if min_age is not None and min_age < 0:
        return JSONResponse(status_code=422, content={"status": "error", "message": "Invalid query parameters"})
    if max_age is not None and max_age < 0:
        return JSONResponse(status_code=422, content={"status": "error", "message": "Invalid query parameters"})
    if min_age is not None and max_age is not None and min_age > max_age:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid query parameters"})

    query = db.query(Profile)
    query = apply_filters(query, gender, age_group, country_id, min_age, max_age,
                          min_gender_probability, min_country_probability)

    # Sorting
    if sort_by:
        sort_col = getattr(Profile, sort_by)
        query = query.order_by(asc(sort_col) if order == "asc" else desc(sort_col))

    total = query.count()
    offset = (page - 1) * limit
    profiles = query.offset(offset).limit(limit).all()

    return JSONResponse(status_code=200, content={
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [format_profile(p) for p in profiles],
    })


def parse_natural_language(q: str) -> Optional[dict]:
    """
    Rule-based NLP parser. Converts plain English into filter dict.
    Returns None if query cannot be interpreted.
    """
    q_lower = q.lower().strip()

    if not q_lower:
        return None

    filters = {}
    matched_something = False

    # --- Gender ---
    if "male and female" in q_lower or "female and male" in q_lower:
        pass  # no gender filter = both
        matched_something = True
    elif "female" in q_lower or "woman" in q_lower or "women" in q_lower or "girls" in q_lower:
        filters["gender"] = "female"
        matched_something = True
    elif "male" in q_lower or "man" in q_lower or "men" in q_lower or "boys" in q_lower:
        filters["gender"] = "male"
        matched_something = True

    # --- Age group keywords ---
    if "teenager" in q_lower or "teenagers" in q_lower or "teen" in q_lower or "teens" in q_lower:
        filters["age_group"] = "teenager"
        matched_something = True
    elif "child" in q_lower or "children" in q_lower or "kids" in q_lower:
        filters["age_group"] = "child"
        matched_something = True
    elif "senior" in q_lower or "seniors" in q_lower or "elderly" in q_lower or "old people" in q_lower:
        filters["age_group"] = "senior"
        matched_something = True
    elif "adult" in q_lower or "adults" in q_lower:
        filters["age_group"] = "adult"
        matched_something = True
    elif "young" in q_lower or "youth" in q_lower:
        # "young" maps to 16-24 (not a stored age_group)
        filters["min_age"] = 16
        filters["max_age"] = 24
        matched_something = True

    # --- Explicit age expressions ---
    import re

    # "above X" or "over X"
    above_match = re.search(r"(?:above|over|older than)\s+(\d+)", q_lower)
    if above_match:
        filters["min_age"] = int(above_match.group(1))
        matched_something = True

    # "below X" or "under X"
    below_match = re.search(r"(?:below|under|younger than)\s+(\d+)", q_lower)
    if below_match:
        filters["max_age"] = int(below_match.group(1))
        matched_something = True

    # "between X and Y"
    between_match = re.search(r"between\s+(\d+)\s+and\s+(\d+)", q_lower)
    if between_match:
        filters["min_age"] = int(between_match.group(1))
        filters["max_age"] = int(between_match.group(2))
        matched_something = True

    # --- Country ---
    # Check "from <country>" or "in <country>"
    country_match = re.search(r"(?:from|in)\s+([a-z\s\-']+?)(?:\s+(?:above|below|over|under|between|aged|who|with|and)|$)", q_lower)
    if country_match:
        country_str = country_match.group(1).strip()
        if country_str in COUNTRY_MAP:
            filters["country_id"] = COUNTRY_MAP[country_str]
            matched_something = True
        else:
            # Try partial match
            for country_name, code in COUNTRY_MAP.items():
                if country_name in country_str or country_str in country_name:
                    filters["country_id"] = code
                    matched_something = True
                    break

    if not matched_something:
        return None

    return filters


@router.get("/profiles/search")
def search_profiles(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if not q or not q.strip():
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing or empty query"})

    filters = parse_natural_language(q)

    if filters is None:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Unable to interpret query"})

    query = db.query(Profile)
    query = apply_filters(
        query,
        gender=filters.get("gender"),
        age_group=filters.get("age_group"),
        country_id=filters.get("country_id"),
        min_age=filters.get("min_age"),
        max_age=filters.get("max_age"),
        min_gender_probability=None,
        min_country_probability=None,
    )

    total = query.count()
    offset = (page - 1) * limit
    profiles = query.offset(offset).limit(limit).all()

    return JSONResponse(status_code=200, content={
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [format_profile(p) for p in profiles],
    })