"""Keyword → SF Symbol catalog for list-icon auto-suggestion.

A curated, offline lookup mapping common list-title keywords to SF Symbol
names. It powers `suggest_list_icon` and the auto-icon behaviour of
`create_calendar` / `create_smart_list` (see `icon_suggest`). The hybrid
suggester tries this table first (deterministic, zero-latency); only on a miss
does it escalate to MCP Sampling, constrained to the symbols defined here.

Every value is a real SF Symbol that renders as a Reminders list badge. Keys
are lowercase base-form keywords; the matcher also matches simple plurals. When
no keyword matches confidently, the suggester falls back to
``AGENT_FALLBACK_SYMBOL`` — the glyph representing an agent-created / automated
list.
"""

from __future__ import annotations

# Fallback icon for an agent-created / automated list when nothing matches
# confidently. `sparkles` is Apple's canonical "generated automatically" glyph,
# so it reads as "an assistant made this list". Tunable here in one place.
AGENT_FALLBACK_SYMBOL = "sparkles"

# SF Symbol -> trigger keywords (lowercase, base form; simple plurals matched
# too). ~100 groups covering the most common Reminders list themes. Ordering
# matters only for score ties: earlier entries win, so more general/common
# mappings are listed before nichier ones within each theme.
ICON_KEYWORDS: dict[str, list[str]] = {
    # Shopping & deliveries
    "cart.fill": ["grocery", "groceries", "shopping", "store", "supermarket", "market"],
    "bag.fill": ["shop", "mall", "retail", "purchase", "outlet"],
    "shippingbox.fill": ["package", "delivery", "shipping", "order", "moving", "move"],
    # Food, cooking & dining
    "fork.knife": [
        "food",
        "meal",
        "meals",
        "dinner",
        "lunch",
        "breakfast",
        "restaurant",
        "recipe",
        "recipes",
        "cooking",
        "menu",
        "eat",
    ],
    "cup.and.saucer.fill": ["coffee", "cafe", "tea"],
    "wineglass.fill": ["wine", "bar", "cocktail", "drinks", "alcohol"],
    "birthday.cake.fill": ["cake", "dessert", "baking", "bakery", "birthday"],
    "flame.fill": ["bbq", "grill", "barbecue"],
    # Work, office & productivity
    "briefcase.fill": ["work", "job", "office", "business", "career"],
    "building.2.fill": ["company", "corporate", "client", "clients"],
    "doc.text.fill": ["document", "documents", "doc", "paperwork", "report", "reports", "paper"],
    "folder.fill": ["files", "folder", "archive", "project", "projects"],
    "person.2.fill": ["team", "people", "meeting", "meetings", "staff"],
    "chart.bar.fill": ["stats", "metrics", "analytics", "kpi", "dashboard"],
    "megaphone.fill": ["marketing", "promotion", "campaign", "announcement"],
    # Tasks & general lists
    "checklist": ["task", "tasks", "todo", "todos", "chore", "chores", "errand", "errands", "checklist"],
    "list.bullet": ["general", "misc", "stuff", "random"],
    "flag.fill": ["goal", "goals", "milestone", "milestones", "priority", "important"],
    "tag.fill": ["label", "labels", "category", "categories"],
    "bookmark.fill": ["bookmark", "bookmarks", "saved", "readlater"],
    "tray.full.fill": ["inbox", "intake", "incoming"],
    "lightbulb.fill": ["idea", "ideas", "brainstorm", "inspiration"],
    "clock.fill": ["routine", "daily", "timer", "habit", "habits"],
    "calendar": ["calendar", "schedule", "agenda", "event", "events", "appointment", "appointments"],
    "calendar.badge.clock": ["deadline", "deadlines", "due"],
    "bell.fill": ["alert", "alerts", "notification", "notifications"],
    # Money & finance
    "dollarsign.circle.fill": [
        "money",
        "finance",
        "finances",
        "financial",
        "budget",
        "expense",
        "expenses",
        "savings",
        "cash",
    ],
    "creditcard.fill": ["bill", "bills", "payment", "payments", "subscription", "subscriptions"],
    "banknote.fill": ["invoice", "invoices", "salary", "income", "paycheck"],
    "building.columns.fill": ["bank", "banking", "tax", "taxes", "legal", "government", "court"],
    # Health, medical & fitness
    "heart.fill": ["health", "wellness"],
    "cross.case.fill": ["medical", "clinic", "firstaid"],
    "stethoscope": ["doctor", "checkup", "physician", "appointment"],
    "pills.fill": ["medication", "meds", "pills", "prescription", "pharmacy", "medicine", "vitamins"],
    "dumbbell.fill": ["gym", "workout", "workouts", "fitness", "lifting", "training", "exercise"],
    "figure.run": ["run", "running", "jog", "jogging", "cardio"],
    "figure.yoga": ["yoga", "stretch", "pilates", "meditation"],
    "figure.pool.swim": ["swim", "swimming", "pool"],
    "bed.double.fill": ["sleep", "rest", "bedtime", "nap"],
    "drop.fill": ["water", "hydration", "hydrate"],
    # Travel & transport
    "airplane": ["travel", "trip", "trips", "flight", "flights", "fly", "vacation", "airport", "holiday"],
    "suitcase.fill": ["packing", "pack", "luggage", "baggage"],
    "car.fill": ["car", "drive", "driving", "auto", "vehicle", "commute", "road"],
    "fuelpump.fill": ["gas", "fuel", "petrol"],
    "map.fill": ["map", "directions", "route", "navigation"],
    "mappin.and.ellipse": ["location", "place", "places", "destination", "address"],
    "bus.fill": ["bus", "transit", "transport"],
    "tram.fill": ["train", "subway", "metro", "rail"],
    "bicycle": ["bike", "bicycle", "cycling"],
    "sailboat.fill": ["boat", "sailing", "cruise"],
    "mountain.2.fill": ["adventure", "outdoor", "outdoors"],
    "figure.hiking": ["hike", "hiking", "trek", "trekking"],
    "tent.fill": ["camping", "camp", "campsite"],
    # Home, chores & DIY
    "house.fill": ["home", "house", "household", "apartment"],
    "washer.fill": ["laundry", "washing", "wash"],
    "trash.fill": ["trash", "garbage", "waste", "recycling"],
    "leaf.fill": ["garden", "gardening", "plant", "plants", "yard", "lawn", "nature"],
    "hammer.fill": ["repair", "fix", "diy", "build", "renovation"],
    "wrench.and.screwdriver.fill": ["tools", "maintenance", "handyman"],
    "paintbrush.fill": ["paint", "painting", "decorate", "decorating"],
    "key.fill": ["keys", "rental", "lease"],
    "lock.fill": ["security", "password", "passwords", "secure"],
    # Family, kids & pets
    "figure.and.child.holdinghands": ["kids", "children", "child", "family", "parenting", "baby"],
    "pawprint.fill": ["pet", "pets", "dog", "dogs", "cat", "cats", "animal", "vet"],
    "gift.fill": ["gift", "gifts", "present", "presents", "registry", "wishlist", "christmas"],
    "heart.circle.fill": ["relationship", "anniversary", "date", "valentine", "wedding"],
    # Education & learning
    "book.fill": ["book", "books", "reading", "read", "library", "novel"],
    "graduationcap.fill": [
        "school",
        "study",
        "studying",
        "class",
        "classes",
        "course",
        "courses",
        "homework",
        "education",
        "college",
        "university",
        "exam",
        "exams",
        "student",
    ],
    "pencil": ["writing", "write", "draft", "journal", "note", "notes"],
    "backpack.fill": ["supplies"],
    # Entertainment & hobbies
    "music.note": ["music", "song", "songs", "playlist", "concert", "concerts"],
    "headphones": ["podcast", "podcasts", "audio", "audiobook"],
    "film.fill": ["movie", "movies", "film", "films", "cinema"],
    "tv.fill": ["tv", "show", "shows", "series", "streaming", "watchlist"],
    "gamecontroller.fill": ["game", "games", "gaming", "videogame"],
    "puzzlepiece.fill": ["puzzle", "hobby", "hobbies"],
    "camera.fill": ["photo", "photos", "photography", "picture", "pictures"],
    "paintpalette.fill": ["art", "craft", "crafts", "drawing", "creative"],
    "guitars.fill": ["guitar", "band", "instrument"],
    "theatermasks.fill": ["theater", "play", "drama"],
    # Tech & computing
    "laptopcomputer": ["computer", "laptop", "coding", "code", "dev", "programming", "software", "tech"],
    "desktopcomputer": ["pc", "desktop", "workstation"],
    "terminal.fill": ["terminal", "scripts", "devops", "server", "servers", "infra"],
    "gearshape.fill": ["settings", "config", "setup", "automation", "system"],
    "wifi": ["network", "internet", "wifi"],
    "iphone": ["phone", "mobile", "app", "apps"],
    "externaldrive.fill": ["backup", "backups", "storage"],
    # Communication & social
    "envelope.fill": ["email", "mail", "message", "messages"],
    "phone.fill": ["call", "calls", "contacts"],
    "bubble.left.and.bubble.right.fill": ["chat", "conversation", "social", "discussion"],
    # Sports
    "sportscourt.fill": ["sport", "sports"],
    "soccerball": ["soccer", "football"],
    "basketball.fill": ["basketball"],
    "baseball.fill": ["baseball"],
    "tennis.racket": ["tennis"],
    "trophy.fill": ["competition", "tournament", "award", "win", "league"],
    # Weather & seasons
    "sun.max.fill": ["summer", "weather", "sunny", "beach"],
    "snowflake": ["winter", "snow", "ski", "skiing"],
    "cloud.rain.fill": ["rain", "rainy"],
    # Personal care & self
    "scissors": ["haircut", "salon", "barber", "grooming"],
    "eyeglasses": ["glasses", "optometry", "eyecare"],
    "moon.stars.fill": ["prayer", "spiritual", "mindfulness"],
    "star.fill": ["favorite", "favorites", "bucketlist"],
    "checkmark.seal.fill": ["license", "certification", "verification", "renewal"],
    "signature": ["contract", "signing", "agreement"],
}
