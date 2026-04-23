##### **HNG Project : Stage 2 — Intelligence API Query Engine**

##### 

This is my Stage 2 submission for the HNG Internship backend track. The task here was to upgrade a basic profile storage API into something actually useful — that is an API that clients can filter, sort, paginate through, and even query in plain English.

The stack I used is FastAPI + PostgreSQL, deployed on Railway. 



The database is seeded with 2026 demographic profiles. The seed is gotten from HNG task <https://drive.google.com/file/d/1Up06dcS9OfUEnDj\_u6OV\_xTRntupFhPH/view>



**Live API:** `https://hng2-production-f7d9.up.railway.app`

**GitHub:** `https://github.com/nduprincekc/hng2`

\---

## Endpoints for this project

### GET /api/profiles

This is the main endpoint. It supports filtering, sorting, and pagination all in one request.

**Filters you can use:**

* `gender` — male or female
* `age\_group` — child, teenager, adult, senior
* `country\_id` — ISO code like NG, KE, GH
* `min\_age` and `max\_age` — age range
* `min\_gender\_probability` — minimum confidence score for gender
* `min\_country\_probability` — minimum confidence score for country

**Sorting:**

* `sort\_by` — age, created\_at, or gender\_probability
* `order` — asc or desc

**Pagination:**

* `page` — defaults to 1
* `limit` — defaults to 10, maximum is 50

**Example request:**

```
GET /api/profiles?gender=male\&country\_id=NG\&min\_age=25\&sort\_by=age\&order=desc\&page=1\&limit=10
```

**Example response:**

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 412,
  "data": \[...]
}
```

\---

### GET /api/profiles/search

This is the natural language search endpoint. Instead of passing structured filters, you just type what you're looking for in plain English.

```
GET /api/profiles/search?q=young males from nigeria
GET /api/profiles/search?q=females above 30
GET /api/profiles/search?q=adult males from kenya
```

Pagination works here too — you can pass `page` and `limit` alongside `q`.

\---

## How the Natural Language Parser Works

I built this with pure rule-based logic — no AI, no external libraries, just Python string matching and regex.

When a query comes in, I lowercase it and scan it for known keywords in a specific order: gender first, then age group, then explicit age numbers, then country.

**Gender keywords:**

If the query contains "female", "woman", "women", or "girls" — it sets `gender=female`. If it contains "male", "man", "men", or "boys" — it sets `gender=male`. If it contains "male and female" — no gender filter is applied, meaning both are returned.

I check for female before male on purpose because the word "female" contains "male" in it — if I checked male first, "female" would incorrectly match.

**Age group keywords:**

* "teenager", "teen", "teens" → `age\_group=teenager`
* "child", "children", "kids" → `age\_group=child`
* "senior", "elderly" → `age\_group=senior`
* "adult", "adults" → `age\_group=adult`
* "young", "youth" → `min\_age=16` + `max\_age=24` (this is not a stored age group, just a range)

**Explicit age expressions (handled with regex):**

* "above 30" / "over 30" / "older than 30" → `min\_age=30`
* "below 25" / "under 25" / "younger than 25" → `max\_age=25`
* "between 20 and 40" → `min\_age=20`, `max\_age=40`

**Country detection:**

I look for "from <country>" or "in <country>" patterns, then look up the country name in a dictionary of 50+ countries mapped to their ISO codes. So "from nigeria" becomes `country\_id=NG`, "from kenya" becomes `country\_id=KE`, and so on.

**Example mappings:**

```
"young males"                        → gender=male, min\_age=16, max\_age=24
"females above 30"                   → gender=female, min\_age=30
"people from angola"                 → country\_id=AO
"adult males from kenya"             → gender=male, age\_group=adult, country\_id=KE
"male and female teenagers above 17" → age\_group=teenager, min\_age=17
```

If the parser finds nothing it recognises, it returns:

```json
{ "status": "error", "message": "Unable to interpret query" }
```

\---

## Limitations

There are some things the parser doesn't handle and I want to be upfront about them:

* **Typos** — "nigerria" won't match Nigeria. There's no fuzzy matching.
* **Negation** — "not from Nigeria" or "everyone except males" won't work.
* **Multiple countries** — "from Nigeria or Ghana" will only pick up one country.
* **Direct ISO codes** — typing "NG" instead of "Nigeria" in a natural language query won't work.
* **Complex phrasing** — "people in their 30s" won't parse. Use "between 30 and 39" instead.
* **Ambiguous words** — "senior developer" would incorrectly match `age\_group=senior` because the parser sees the word "senior".
* **Non-English queries** — only English is supported.

\---

## Running Locally

```bash
git clone https://github.com/nduprincekc/hng2
cd hng2
pip install -r requirements.txt
cp .env.example .env
# Add your DATABASE\_URL to .env
uvicorn app.main:app --reload
```

Place `seed\_profiles.json` in the project root, then seed the database:

```bash
python seed.py
```

API will be live at `http://localhost:8000`
Swagger docs at `http://localhost:8000/docs`

