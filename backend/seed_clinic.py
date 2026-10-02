"""
Sentinel Clinic Seed — admin + full demo clinic.
Creates:
  • admin / password123            (role: admin — clinic oversight console)
  • Dr. Celeste Raine (cel / 1234) — psychologist
  • Dr. Marcus Vale  (marcus / 4321) — psychologist
  • 30 teen clients (13-19), each with a completely different background,
    presentation, and personality; ~12 months of journals (warm patient-facing
    summaries + structured OAP clinical summaries), daily moods, ring vitals,
    bookings, follow-ups with grades/feedback, clinical notes, psych journal,
    notifications, crisis history, triage entries, audit + event stores.

Journal content is generated from per-client "voice profiles" so every teen
writes in a distinct, realistic register. Run:  python seed_clinic.py
"""

import json
import os
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password, initialize_encryption
from app.models.ai_analysis import AIAnalysis
from app.models.audit import AuditLog
from app.models.booking import Booking
from app.models.clinical_note import ClinicalNote
from app.models.crisis import CrisisLog, CrisisState
from app.models.emotion_result import EmotionResult
from app.models.event_store import EventRecord
from app.models.followup import FollowupTask
from app.models.journal import JournalEntry
from app.models.mood import MoodLog
from app.models.notification import Notification
from app.models.psych_journal import PsychJournalEntry
from app.models.ring import RingSensorLog
from app.models.ring_device import RingDevice
from app.models.sensor_reading import SensorReading
from app.models.session_report import SessionReport
from app.models.triage import TriageEntry
from app.models.user import User

# ── Encryption must be live before any EncryptedText write ──────────
_passphrase = os.environ.get("ENCRYPTION_PASSPHRASE")
if not _passphrase:
    from app.core.config import settings

    _passphrase = settings.encryption_passphrase
if not _passphrase:
    print("ERROR: set ENCRYPTION_PASSPHRASE (see ../.env) before seeding.")
    sys.exit(1)
initialize_encryption(_passphrase)

RNG = random.Random(20260914)
now = datetime.now(UTC)


def days_ago(d, hour=None, minute=None):
    t = now - timedelta(days=d)
    if hour is not None:
        t = t.replace(hour=hour, minute=minute or 0, second=RNG.randint(0, 59), microsecond=0)
    return t.isoformat()


def days_ahead(d, hour="15:00"):
    return (now + timedelta(days=d)).strftime("%Y-%m-%d")


# ════════════════════════════════════════════════════════════════════
# 1. RESET DATABASE
# ════════════════════════════════════════════════════════════════════
print("=== SENTINEL CLINIC SEED ===")
print("Resetting database…")

# ── Self-heal: if the SQLite file is corrupted (e.g. a server was killed
# mid-write), delete it and rebuild from scratch. ──
from app.core.config import settings

DB_PATH = (
    settings.database_url.replace("sqlite:///./", "", 1) if settings.database_url.startswith("sqlite:///./") else None
)
if DB_PATH:
    try:
        with engine.connect() as conn:
            conn.execute(text("PRAGMA integrity_check"))
        print("  database file OK")
    except Exception as e:
        print(f"  ⚠ database file is corrupt ({type(e).__name__}) — rebuilding it…")
        engine.dispose()
        for suffix in ("", "-wal", "-shm"):
            p = Path(DB_PATH + suffix)
            if p.exists():
                p.unlink()
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        print("  ✓ removed corrupt file — creating a fresh database")


def _reset_database():
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    tables = insp.get_table_names()
    with engine.begin() as conn:
        for t in reversed(Base.metadata.sorted_tables):
            if t.name in tables:
                conn.execute(text(f'DELETE FROM "{t.name}"'))


try:
    _reset_database()
except Exception as e:
    # Corruption can also surface on the first real DELETE rather than the
    # integrity check — catch that too and rebuild from a clean file.
    print(f"  ⚠ reset failed ({type(e).__name__}: {e}) — rebuilding database file…")
    engine.dispose()
    if DB_PATH:
        for suffix in ("", "-wal", "-shm"):
            p = Path(DB_PATH + suffix)
            if p.exists():
                p.unlink()
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    _reset_database()

db = SessionLocal()

# ════════════════════════════════════════════════════════════════════
# 2. STAFF ACCOUNTS
# ════════════════════════════════════════════════════════════════════
admin = User(
    username="admin",
    password_hash=hash_password("password123"),
    name="Sam Okafor",
    role="admin",
    clinic_code="SENTINEL",
    onboarding_step=99,
    contact_info="admin@sentinel.demo",
    encryption_salt=os.urandom(16).hex(),
    created_at=days_ago(400, 9),
)
cel = User(
    username="cel",
    password_hash=hash_password("1234"),
    name="Dr. Celeste Raine",
    role="psychologist",
    clinic_code="SENTINEL",
    professional_code="PSY-19844",
    onboarding_step=99,
    contact_info="cel@sentinel.demo",
    psych_trusted_contact="clinical-director@sentinel.demo",
    occupation="Clinical Psychologist — CBT & adolescent anxiety",
    encryption_salt=os.urandom(16).hex(),
    created_at=days_ago(420, 9),
)
marcus = User(
    username="marcus",
    password_hash=hash_password("4321"),
    name="Dr. Marcus Vale",
    role="psychologist",
    clinic_code="SENTINEL",
    professional_code="PSY-21037",
    onboarding_step=99,
    contact_info="marcus@sentinel.demo",
    psych_trusted_contact="clinical-director@sentinel.demo",
    occupation="Clinical Psychologist — trauma, DBT skills, sport perf.",
    encryption_salt=os.urandom(16).hex(),
    created_at=days_ago(300, 9),
)
db.add_all([admin, cel, marcus])
db.commit()
print("  admin:      admin / password123")
print("  psych:      cel / 1234  ·  marcus / 4321")

# ════════════════════════════════════════════════════════════════════
# 3. THE TWENTY CLIENTS
# Each: username, name, age, gender, psych, presenting issue, personality,
# writing style, baseline vitals, trajectory (improving/stable/fluctuating),
# home situation, and a "spark" detail that makes them feel real.
# ════════════════════════════════════════════════════════════════════
CLIENTS = [
    dict(
        u="maya_k",
        name="Maya Kaplan",
        age=16,
        g="f",
        psych="cel",
        presenting="Generalized anxiety; panic attacks in exams",
        person="Perfectionist, quick-witted, keeps a color-coded planner, plays violin",
        voice="structured, self-deprecating humor, long sentences when anxious",
        traj="improving",
        home="lives with mom & older brother; parents divorced 2y ago",
        spark="studies best in the school stairwell at 7am",
        tc="mom.kaplan@example.com",
        occup="Year 11 student",
        meds="Fluoxetine 10mg since March",
    ),
    dict(
        u="dev_p",
        name="Dev Patel",
        age=17,
        g="m",
        psych="cel",
        presenting="Social anxiety; fear of presenting in class",
        person="Gentle, chess club captain, codes Discord bots, dry humor",
        voice="short, technical metaphors, minimizes then undercuts with detail",
        traj="improving",
        home="lives with both parents and grandmother",
        spark="calms down by refactoring code nobody asked him to fix",
        tc="dad.patel@example.com",
        occup="Year 12 student",
        meds="None",
    ),
    dict(
        u="luna_r",
        name="Luna Reyes",
        age=15,
        g="f",
        psych="marcus",
        presenting="Self-harm urges (historic); identity & belonging",
        person="Artistic, dyed hair changes with mood, writes slam poetry, fiercely loyal",
        voice="lyrical, fragment sentences, imagery-heavy",
        traj="fluctuating",
        home="foster care, stable placement 8 months",
        spark="sketches strangers on the bus and gives the drawings away",
        tc="foster.mama.joy@example.com",
        occup="Year 10 student",
        meds="None; PRN grounding approved",
    ),
    dict(
        u="theo_b",
        name="Theo Brandt",
        age=18,
        g="m",
        psych="cel",
        presenting="Depression; school refusal risk in final year",
        person="Skater, sardonic, secretly writes sci-fi, hates being pitied",
        voice="terse, sarcarm as armor, occasional raw honesty",
        traj="fluctuating",
        home="lives with father; mother overseas",
        spark="watches the same comfort movie every bad day (it's Paddington 2)",
        tc="dad.brandt@example.com",
        occup="Year 13 student",
        meds="Sertraline 50mg since May",
    ),
    dict(
        u="ava_s",
        name="Ava Sullivan",
        age=14,
        g="f",
        psych="marcus",
        presenting="OCD — contamination subtype + checking",
        person="Bright, anxious-organized, loves marine biology, apologizes often",
        voice="polite, hedging, lists things to feel safe",
        traj="improving",
        home="lives with both parents; twin brother",
        spark="knows every octopus fact; wants to be a marine researcher",
        tc="mom.sullivan@example.com",
        occup="Year 9 student",
        meds="None; ERP protocol week 11",
    ),
    dict(
        u="jayden_w",
        name="Jayden Wright",
        age=17,
        g="m",
        psych="marcus",
        presenting="Anger outbursts after loss of brother; grief",
        person="Guarded, football captain energy, loves his nephews, soft with kids",
        voice="clipped, deflects with 'I'm good', opens up in bursts",
        traj="stable",
        home="lives with mom; older sister has 2 toddlers",
        spark="coaches under-8s football on Saturdays",
        tc="mom.wright@example.com",
        occup="Year 12 student",
        meds="None",
    ),
    dict(
        u="zoe_m",
        name="Zoe Mbeki",
        age=16,
        g="f",
        psych="cel",
        presenting="Panic disorder; fear of vomiting (emetophobia)",
        person="Theatre kid, loud on stage quiet in crowds, big laugh, dramatic honesty",
        voice="expressive, CAPS for emphasis, theatrical metaphors",
        traj="improving",
        home="lives with mom & stepdad; new baby sister",
        spark="narrates her own life like a stage play when nervous",
        tc="mom.mbeki@example.com",
        occup="Year 11 student",
        meds="None; beta-blocker PRN for performances",
    ),
    dict(
        u="eli_n",
        name="Eli Nakamura",
        age=13,
        g="m",
        psych="cel",
        presenting="School anxiety + selective mutism history",
        person="Sweet, collects rocks, loves trains, talks a lot once comfortable",
        voice="young, earnest, run-on sentences, exclamation marks",
        traj="improving",
        home="lives with mom; sees dad alternate weekends",
        spark="rates days 1-10 by how many trains he saw",
        tc="mom.nakamura@example.com",
        occup="Year 8 student",
        meds="None",
    ),
    dict(
        u="sana_i",
        name="Sana Iqbal",
        age=18,
        g="f",
        psych="marcus",
        presenting="Acculturation stress; family conflict; insomnia",
        person="Responsible eldest daughter, debater, translating between two worlds",
        voice="formal then suddenly candid, weighed sentences",
        traj="stable",
        home="lives with parents & 3 younger siblings",
        spark="writes two diaries: one in English, one in Urdu",
        tc="sana.self@example.com",
        occup="Year 13 · Head Girl",
        meds="Sleep hygiene program; melatonin PRN",
    ),
    dict(
        u="kai_t",
        name="Kai Tanuvasa",
        age=16,
        g="m",
        psych="marcus",
        presenting="Sport performance anxiety (rugby); injury recovery",
        person="Physical, team-first, hides pain, gentle with younger players",
        voice="sport metaphors, short, 'we' not 'I'",
        traj="fluctuating",
        home="lives with aunt's family; 4 cousins",
        spark="replays games in his head to fall asleep",
        tc="aunt.lei@example.com",
        occup="Year 11 · 1st XV",
        meds="None",
    ),
    dict(
        u="ivy_c",
        name="Ivy Chen",
        age=17,
        g="f",
        psych="cel",
        presenting="Eating disorder (restricting); body image",
        person="High-achieving, ballet, people-pleaser, exhausted by her own standards",
        voice="precise, calorie-counts in passing, softens everything",
        traj="fluctuating",
        home="lives with both parents; high expectations",
        spark="feeds the ducks every Sunday 'so something gets enough'",
        tc="mom.chen@example.com",
        occup="Year 12 · ballet scholar",
        meds="None; meal plan supervised by nutritionist",
    ),
    dict(
        u="omar_h",
        name="Omar Haddad",
        age=15,
        g="m",
        psych="marcus",
        presenting="PTSD after house fire; nightmares; hypervigilance",
        person="Sweet-natured, checks exits, loves Minecraft builds, worried for others",
        voice="cautious, notices details of rooms, tender",
        traj="improving",
        home="rebuilding home; temporarily with cousins",
        spark="still has the fire-station sticker they gave him",
        tc="unc.yusuf@example.com",
        occup="Year 10 student",
        meds="None; trauma-focused CBT week 8",
    ),
    dict(
        u="rue_d",
        name="Rue Delgado",
        age=17,
        g="nb",
        psych="cel",
        presenting="Gender dysphoria; family acceptance; depression",
        person="Dry-funny, thrifted flannels, makes playlists for every feeling",
        voice="meme-fluent, tender beneath sarcasm",
        traj="fluctuating",
        home="lives with mom; dad estranged",
        spark="makes a playlist for every session theme",
        tc="mom.delgado@example.com",
        occup="Year 12 student",
        meds="None; exploring options with GP",
    ),
    dict(
        u="finn_o",
        name="Finn O'Carroll",
        age=14,
        g="m",
        psych="marcus",
        presenting="ADHD; emotional regulation; school detentions",
        person="Human golden retriever, impulsive, kind, zero volume control",
        voice="tangents, ALL-CAPS moments, instant honesty",
        traj="stable",
        home="lives with both parents & younger twins",
        spark="has 41 unfinished notebook 'inventions'",
        tc="dad.ocarroll@example.com",
        occup="Year 9 student",
        meds="Methylphenidate ER since January",
    ),
    dict(
        u="noor_a",
        name="Noor Al-Amin",
        age=16,
        g="f",
        psych="cel",
        presenting="Bullying victimization; withdrawal from friends",
        person="Observant, keeps the group chat running, wants to be an astronomer",
        voice="quiet, precise, notices social weather",
        traj="improving",
        home="lives with parents; youngest of 5",
        spark="names every star she learns after friends",
        tc="mom.alamin@example.com",
        occup="Year 11 student",
        meds="None",
    ),
    dict(
        u="jasper_l",
        name="Jasper Lindqvist",
        age=18,
        g="m",
        psych="cel",
        presenting="Alcohol misuse (weekend bingeing); school-pressure escape",
        person="Charming, class-clown armor, deeply tired underneath",
        voice="jokes first, real second, shrugs",
        traj="fluctuating",
        home="lives with mom; works Saturdays at a garage",
        spark="saves every £ he earns toward moving out",
        tc="mom.lindqvist@example.com",
        occup="Year 13 · part-time mechanic",
        meds="None",
    ),
    dict(
        u="amara_j",
        name="Amara Johnson",
        age=15,
        g="f",
        psych="marcus",
        presenting="Panic + fainting (vasovagal); medical anxiety",
        person="Brave-but-scared, science nerd, hates hospitals ironically",
        voice="clinical curiosity about her own symptoms, brave bravado",
        traj="improving",
        home="lives with mom & grandma",
        spark="wants to be a paramedic despite the fainting",
        tc="mom.johnson@example.com",
        occup="Year 10 student",
        meds="None; counter-pressure technique training",
    ),
    dict(
        u="leo_f",
        name="Leo Fischer",
        age=17,
        g="m",
        psych="cel",
        presenting="Perfectionism; burnout; teacher expectations",
        person="Straight-A machine, rowing crew, hasn't skipped homework since Year 7",
        voice="measured, achievement-framing, quietly cracking",
        traj="fluctuating",
        home="lives with both parents; legacy expectations",
        spark="rows at 5:30am and calls it 'the quiet hour'",
        tc="dad.fischer@example.com",
        occup="Year 12 · rowing captain",
        meds="None",
    ),
    dict(
        u="priya_g",
        name="Priya Gopalan",
        age=14,
        g="f",
        psych="marcus",
        presenting="Separation anxiety; school attendance dips",
        person="Attached to grandma, gentle, loves baking, worried eyes",
        voice="short, warm, checks in on others",
        traj="improving",
        home="multigenerational home; grandma is anchor",
        spark="bakes cardamom buns when home feels wobbly",
        tc="mom.gopalan@example.com",
        occup="Year 9 student",
        meds="None",
    ),
    dict(
        u="tyler_k",
        name="Tyler Kowalski",
        age=19,
        g="m",
        psych="marcus",
        presenting="Transition to adulthood; job loss; low mood",
        person="Handed-in-notice energy, gamer, delivery rider, big dreams stalled",
        voice="casual, meme references, guarded optimism",
        traj="stable",
        home="couch-surfing between dad's and mate's",
        spark="aims to save for a van to convert ('van Elvis')",
        tc="dad.kowalski@example.com",
        occup="Gap year · delivery rider",
        meds="None",
    ),
    dict(
        u="noa_b",
        name="Noa Bergström",
        age=15,
        g="f",
        psych="cel",
        presenting="Type 1 diabetes adjustment; burnout from self-management",
        person="Methodical, dark humour about pancreas jokes, bakes sugar-free, exhausted by numbers",
        voice="dry, data-fluent, tired-but-funny",
        traj="fluctuating",
        home="lives with mom; dad does night shifts at the plant",
        spark="rates insulin pump sites like film critics rate movies",
        tc="mom.bergstrom@example.com",
        occup="Year 10 student",
        meds="Insulin pump (T1D dx age 9); monitoring burnout",
    ),
    dict(
        u="dante_m",
        name="Dante Mercer",
        age=16,
        g="m",
        psych="marcus",
        presenting="Gaming disorder pattern; sleep reversal; social withdrawal",
        person="Sharp strategist, ranked grind, defensive about gaming, secretly bored of it",
        voice="gamer slang, stream-of-consciousness, honest in retrospect",
        traj="fluctuating",
        home="lives with dad; stepmom moved in last year",
        spark="holds the school speedrun record nobody knows about",
        tc="dad.mercer@example.com",
        occup="Year 11 student",
        meds="None; sleep restoration protocol",
    ),
    dict(
        u="wren_h",
        name="Wren Hollis",
        age=14,
        g="nb",
        psych="cel",
        presenting="Autism spectrum traits; school transition overload; sensory anxiety",
        person="Deep-focus artist, echolalia when happy, happiest in the library's back corner",
        voice="precise, literal-first, warms into metaphor",
        traj="improving",
        home="lives with mom & nana; two cats named after planets",
        spark="draws entire fantasy cities on one sheet of A3",
        tc="mom.hollis@example.com",
        occup="Year 9 student",
        meds="None; sensory profile updated termly",
    ),
    dict(
        u="gabe_d",
        name="Gabe Diaz",
        age=18,
        g="m",
        psych="marcus",
        presenting="New father; role strain; interrupted education",
        person="Tender and terrified, works evenings, quotes his abuela, loves loudly",
        voice="warm, weary, short sentences that land heavy",
        traj="improving",
        home="lives with girlfriend & baby girl; abuela next door",
        spark="sings bachata lullabies, badly, on purpose",
        tc="gabe.diaz.self@example.com",
        occup="Year 12 · part-time warehouse",
        meds="None",
    ),
    dict(
        u="mei_l",
        name="Mei Lau",
        age=17,
        g="f",
        psych="cel",
        presenting="Social comparison; body-image distress via social media; insomnia",
        person="Dancer, archive of other people's highlight reels, whip-smart, quietly self-critical",
        voice="clear-eyed, lists and comparisons, growing self-compassion",
        traj="improving",
        home="lives with parents; family restaurant downstairs",
        spark="choreographs in the restaurant after close when the floors shine",
        tc="mom.lau@example.com",
        occup="Year 12 · competition dancer",
        meds="None; sleep restriction trial week 3",
    ),
    dict(
        u="samir_b",
        name="Samir Boutros",
        age=16,
        g="m",
        psych="marcus",
        presenting="War displacement trauma; resettlement stress; survivor guilt",
        person="Polite and watchful, chess-with-cousins, draws maps from memory, dreams in two languages",
        voice="careful English, sudden Arabic words, vivid memory detail",
        traj="fluctuating",
        home="resettled with parents & younger sister; grandmother still abroad",
        spark="draws the old neighbourhood from memory — every balcony right",
        tc="dad.boutros@example.com",
        occup="Year 11 student",
        meds="None; trauma-informed care pathway",
    ),
    dict(
        u="poppy_a",
        name="Poppy Ashworth",
        age=13,
        g="f",
        psych="cel",
        presenting="Early-puberty anxiety; friendship-group fallout; first counselling",
        person="Bubbly then suddenly shy, horse-mad, collects keyrings, apologises for existing",
        voice="young, streamy, lots of 'like', brave endings",
        traj="improving",
        home="lives with mom & mom's partner; weekends at dad's",
        spark="can name every horse she's ever ridden and what it taught her",
        tc="mom.ashworth@example.com",
        occup="Year 8 student",
        meds="None",
    ),
    dict(
        u="caleb_j",
        name="Caleb Jones",
        age=19,
        g="m",
        psych="marcus",
        presenting="Leaving care; independent-living anxiety; identity after the system",
        person="Self-taught cook, keeps receipts in a shoebox, trust built slow, loyalty absolute",
        voice="plain, practical, feelings arrive sideways",
        traj="stable",
        home="supported lodgings; moving to own flat in spring",
        spark="cooks Sunday dinner for the whole lodging house",
        tc="keyworker.tanya@example.com",
        occup="Catering apprentice",
        meds="None",
    ),
    dict(
        u="tessa_w",
        name="Tessa Whitfield",
        age=15,
        g="f",
        psych="marcus",
        presenting="Chronic insomnia; nightmare disorder; daytime fog",
        person="Night-shift brain in a morning world, lucid-dreaming hobby, dry bedtime humour",
        voice="loopy at 3am, logical at noon, moon metaphors",
        traj="fluctuating",
        home="lives with both parents; blackout curtains everywhere",
        spark="keeps a dream atlas — maps of places that don't exist",
        tc="mom.whitfield@example.com",
        occup="Year 10 student",
        meds="None; CBT-I protocol week 6",
    ),
    dict(
        u="josh_o",
        name="Josh O'Neill",
        age=17,
        g="m",
        psych="cel",
        presenting="Cannabis misuse; exam-year motivation collapse; parental conflict",
        person="Charming slacker, works at the chippy, defended little brother once and never mentioned it",
        voice="deflecting jokes, sudden flat honesty",
        traj="fluctuating",
        home="lives with mom; little brother; dad left three years ago",
        spark="makes the best chips in a 3-mile radius and knows it",
        tc="mom.oneill@example.com",
        occup="Year 12 · part-time chippy",
        meds="None; weekly THC screens (client-agreed)",
    ),
]

print(f"\nCreating {len(CLIENTS)} client profiles…")

# ── 3a. CLIENT USER ACCOUNTS ──────────────────────────────────
DOB_YEAR = {13: 2013, 14: 2012, 15: 2011, 16: 2010, 17: 2009, 18: 2008, 19: 2007}
for c in CLIENTS:
    db.add(
        User(
            username=c["u"],
            password_hash=hash_password("sentinel123"),
            name=c["name"],
            role="patient",
            dob=f"{DOB_YEAR[c['age']]}-{RNG.randint(1, 12):02d}-{RNG.randint(1, 28):02d}",
            country=RNG.choice(["UK", "US", "NZ", "AU", "CA"]),
            timezone=RNG.choice(["Europe/London", "America/New_York", "Pacific/Auckland", "Australia/Sydney"]),
            occupation=c["occup"],
            clinic_code="SENTINEL",
            trusted_contact=c["tc"],
            assigned_psych=c["psych"],
            onboarding_step=99,
            contact_info=f"{c['u']}@sentinel.demo",
            encryption_salt=os.urandom(16).hex(),
            created_at=days_ago(RNG.randint(365, 400), 10),
        )
    )
db.commit()
print(f"  {len(CLIENTS)} client accounts created (password: sentinel123)")


def make_journal_body(c, day_idx, mood_state):
    """Compose a realistic journal entry from the client's voice + presenting issue."""
    b = c["_voice"]
    prefix = b["open"][day_idx % len(b["open"])]
    core = b["core"][day_idx % len(b["core"])]
    close = b["close"][day_idx % len(b["close"])]
    return f"{prefix} {core} {close}"


def journal_summary_pair(c, day_idx, mood_state, traj):
    """Returns (patient_summary, clinical_summary) tuned to trajectory."""
    name_first = c["name"].split()[0]
    traj_str = {
        "improving": "Improving trajectory; treatment gains noted.",
        "stable": "Stable presentation; maintenance phase.",
        "fluctuating": "Fluctuating presentation; monitor closely.",
    }[traj]
    openness = [
        "thanks for putting this into words today",
        "writing it down counts even when it doesn't feel like progress",
        "this is exactly the kind of honesty that moves things",
    ]
    encouragements = [
        "Small steps are still steps.",
        "You showed up for yourself today and that matters.",
        "Notice what helped today, and borrow it again tomorrow.",
    ]
    patient = f"Hey {name_first} — {RNG.choice(openness)}. {RNG.choice(encouragements)}"
    clinical = (
        f"{name_first} ({c['age']}, presenting: {c['presenting'].lower()}) — entry reflects {mood_state} affect "
        f"consistent with {traj} trajectory. {traj_str} No acute risk markers in text; compliance with assigned "
        f"exercises {'good' if RNG.random() < 0.7 else 'partial'}. Continue current plan."
    )
    return patient, clinical


EMOJI_BY_STATE = {
    "good": ("good", "😊"),
    "okay": ("okay", "😐"),
    "low": ("low", "😔"),
    "anxious": ("anxious", "😬"),
    "great": ("great", "🤩"),
}
VOICE_BANK = {
    "maya_k": {
        "open": [
            "Colour-coded today in the planner before I even got up.",
            "Exam countdown: 34 days. The planner knows.",
            "Woke up at 5:47 for no reason. Wrote this at 5:52.",
            "Stairwell at 7am again. Best study spot, no contest.",
        ],
        "core": [
            "Made flashcards for three subjects but keep re-reading the same line about enzymes like it might change.",
            "Had a panic buzz in my chest during the maths mock but did the breathing thing and it came down from a 9 to a 6.",
            "Mom asked if I'm okay and I said fine which is technically true like 60% of the time.",
            "Violin practice went long because the vibrato finally clicked and I didn't want to stop.",
        ],
        "close": [
            "Sleep goal tonight: before midnight. I know. I KNOW.",
            "Tomorrow: past papers, one break, no doom-scroll.",
            "Recording this here so future me knows 6/10 anxiety is survivable.",
            "Small win: I ate lunch in the hall instead of the toilets.",
        ],
    },
    "dev_p": {
        "open": [
            "Deployed the bot update at 2am. Worth it.",
            "Chess club ran long. I lost on time twice.",
            "School today.",
            "Woke up, checked messages, rehearsed saying things.",
        ],
        "core": [
            "Mrs. H announced presentations next week and my whole system blue-screened. Started writing the slides immediately — if I automate the prep maybe the fear can't find a process to attach to.",
            "Refactored the attendance script for the chess club. Nobody asked. It calms me down to fix things that can't disappoint me.",
            "Talked to one (1) new person at club. He liked my bot. I have decided we are allies now.",
            "Mom's been asking why I don't call people. It's not that I don't want to. Calls feel like exams that never end.",
        ],
        "close": [
            "Social battery: 12%. Recharging via headphones.",
            "The slides exist now. That's the win. Delivery is future-Dev's problem.",
            "Counting this as a green day on the spreadsheet I definitely don't keep.",
            "Tomorrow: say one thing in form period. One.",
        ],
    },
    "luna_r": {
        "open": [
            "New hair. The blue washed out but the feeling stayed.",
            "Bus sketches: three strangers, one dog.",
            "Placement feels safe tonight which is rare enough to write down.",
            "Wrote a poem on the 43 bus and lost it to the window.",
        ],
        "core": [
            "Missed the old street today. Not the people. The streetlight outside our old building — it blinked in a pattern like it was sending a code only I knew.",
            "Joy's kitchen smells like cinnamon always. She left the nightlight on without me asking. That's the kind of thing that saves a person quietly.",
            "Sharp feelings came at school. Didn't act on them. Drew them instead — they looked like static with teeth. Ms. Alvarez put it on the wall.",
            "Someone said my poem 'went hard'. I've been living off that sentence for four days.",
            "Caseworker visit went fine. She said 'stable placement' like it's a small thing. It's not a small thing.",
        ],
        "close": [
            "89 days clean tonight. Ink not scars. Counting anyway.",
            "Holding on. That's the whole entry tonight.",
            "Safe. Warm. Fed. Grateful beyond the words.",
            "Tomorrow I'll hand Ms. Alvarez the static-with-teeth one. Maybe.",
        ],
    },
    "theo_b": {
        "open": [
            "Skated the drainage ditch for an hour. Didn't land it.",
            "School: attended, technically.",
            "Dad's shift schedule changed again.",
            "Paddington 2 night. Yes, again.",
        ],
        "core": [
            "Got the uni talk at school and everyone acted like the future is a staircase and I'm the only one without legs. Skipped afternoon registration. Dad doesn't know.",
            "Wrote 400 words of the novel. Protagonist has my exact problem but gets a montage. Unfair, honestly.",
            "Sertraline day 41. Can't tell if it's working or if I've just gone quieter about it. Either way the walls aren't pressing in as much.",
            "Teacher said I 'have potential' which is what adults say when they mean 'disappointing but salvageable'.",
            "Skated until my hands shook. Better than the other thing my hands want to do when it gets loud in my head. Longer entry when I can.",
        ],
        "close": [
            "Attendance is a problem. I know it's a problem. Tomorrow I'll go to form at least.",
            "400 words. One scene. It counts. I'm deciding it counts.",
            "Talked to Dr Raine about the stairs at school. There's a plan. Plans are something.",
            "Paddington fixed nothing and also fixed everything. Standard.",
        ],
    },
    "ava_s": {
        "open": [
            "Hand-washed my jumper twice because the smell of the lab wouldn't leave.",
            "Day 11 of ERP. Reporting for duty.",
            "Octopus fact of the day: they have three hearts and I think that's why I love them.",
            "Checked the door four times before school. Down from seven.",
        ],
        "core": [
            "The canteen tray touched the table edge and my brain filed it under CONTAMINATED — DEPTH 3. Used the thought card Dr Vale gave me. It helped 40%, which is more than 0%.",
            "Twin made it a competition about who apologises less. He won by not apologising for winning. Infuriating and instructive.",
            "Did the exposure ladder rung 4: touched the door frame, no washing, watched the anxiety crest and fall like a tide chart. 22 minutes to baseline.",
            "Presented my marine bio project on octopus cognition. Hands shook the whole time but I did NOT re-check my notes 11 times. Only 3.",
        ],
        "close": [
            " apologises for the length of this entry. Working on that.",
            "Counting: 4 checks → 3. Trend: downward. Octopus patience: infinite.",
            "Telling Dr Vale I'm ready for rung 5. Telling her tonight so I can't take it back.",
            "The tide chart metaphor is mine. I'm keeping it.",
        ],
    },
    "jayden_w": {
        "open": [
            "Long day. I'm good.",
            "Nephews' bedtime was the best part.",
            "Gym at 6, pitch at 5.",
            "Coached the under-8s. Chaos. Loved it.",
        ],
        "core": [
            "Grieves me that Jordan's birthday's coming. He'd be 21. The lads want to do something at the pitch and I keep saying we'll see. We'll see means I'll stand there and it'll crack me open in front of everyone.",
            "Coach pulled me aside about leading warm-ups. Said I'm 'steady'. Steady. If he knew what steady costs some nights.",
            "Mom found me sorting Jordan's old boots. Didn't say anything. Just sat on the stairs next to me. That helped more than talking.",
            "Little man Tyreese asked me why I never smile in photos with him. I fixed it. We took eleven.",
        ],
        "close": [
            "I'm good. (Working on what that sentence hides.)",
            "11 days till the birthday. Plan: go. Stand there. Let it crack. Dr Vale says feelings are load-bearing, not explosive.",
            "Session Thursday. Bringing the boots thing up. Probably.",
            "The eleven photos are my phone background now. All of them.",
        ],
    },
    "zoe_m": {
        "open": [
            "THE GREEN ROOM SMELLED LIKE PAINT AND POSSIBLY MAGIC.",
            "Rehearsal. I died on stage (in character). Twice.",
            "Baby sister slept 4 hours straight. Hero.",
            "Warm-up scales in the shower. Neighbours thrilled.",
        ],
        "core": [
            "Dress rehearsal went FULL SHOW — audience of empty chairs and I still projected to the back row. BUT the after-party biscuits situation had me doing my 'exit quietly' move. Emetophobia's a terrible stage manager.",
            "Baby cried for three hours and my stomach did the flip it does and I did the breathing Dr Raine taught me — in for the curtain rise, out for the curtain fall — and I STAYED in the room.",
            "Mom says the baby has my lungs (loud). I choose to take it as a compliment about projection.",
            "Beta-blocker before the audition = hands steady, voice THERE. Asked Dr Raine if using it is cheating. She said asking for steadiness isn't cheating. Logging that quote forever.",
        ],
        "close": [
            "AUDITION SATURDAY. Curtains up, fear in the wings where it belongs.",
            "Curtain rise. Curtain fall. Repeat. That's the whole trick, folks.",
            "Narrator's note: our heroine survived the biscuit table. Standing ovation.",
            "Tally: panic attacks this week — one. Attendance at life — full.",
        ],
    },
    "eli_n": {
        "open": [
            "Saw 4 trains today!! The freight one had a really long line of tank cars!",
            "Rock of the day: the one with the stripe like a zebra crossing.",
            "Mom said I could sort my rocks tonight!!",
            "The 8:12 was cancelled so the 8:26 came instead and it was DOUBLE DECKER (the train not the bus)",
        ],
        "core": [
            "Had to read out loud in class and my throat went small. Mrs. Perry said I could point at the map instead and my heart came back down. She knows about my throat going small and she never makes it a big deal.",
            "Weekend is Dad's weekend. I packed Rocky (my best rock) and the timetable. Dad learned the freight schedule with me. He got it wrong on purpose so I could fix it. That was funny.",
            "A new kid sat alone at lunch so I showed him my rock collection photo album. He liked the zebra one best. I gave him the spare pebble from my pocket. Making a friend is like a slow train — you have to keep looking at it.",
            "Dr Celeste taught me 'square breathing' and I taught it to Rocky (he was nervous about the dentist field trip, we didn't end up going past the school gates, but still).",
        ],
        "close": [
            "Tomorrow's forecast: probably 3 trains, maybe 5 if the freight is late-late.",
            "Day rating: 7/10 (trains) + 2 (new friend) = 9!",
            "Mom says my throat is braver every week. I think she's right but don't tell her.",
            "Note to future Eli: the small voice is still yours, and it counts.",
        ],
    },
    "sana_i": {
        "open": [
            "Debate prep until 11. Head Girl duties until 12.",
            "Two diaries tonight. This one in English.",
            "Translate mode all day: teachers, then parents, then back.",
            "University application: submitted. Hands shaking slightly.",
        ],
        "core": [
            "Amir's parents' evening is Thursday and Dad expects me to attend as translator, but I have debate nationals the same evening. I am going to let someone down. The only variable is who.",
            "Mom found my English diary. Nothing incriminating in it — deliberately — but the violation sat in my chest all day like a swallowed stone. We had a civil conversation about locks. It changed nothing and I said so calmly, which is its own language.",
            "Got the offer from my first-choice university. Everyone cried. Then Dad asked what the accommodations are like for living at home, and I realized the celebration has a second act where I negotiate my own adulthood.",
            "Slept 4 hours. Woke at 3 to mentally re-translate an argument from 2019. Revisited the sleep protocol instead. Counted down in Urdu, then English. Slept at 4:15.",
        ],
        "close": [
            "Tomorrow: tell Dr Vale about the diaries. Both of them.",
            "The stone in my chest has a name now. Naming it shrinks it slightly.",
            "I can hold two worlds. I am allowed to also put one down sometimes.",
            "Nationals Thursday. Parents' evening resolved: Amir goes with a neighbour. I go with the team. First choice of my own, stated out loud.",
        ],
    },
    "kai_t": {
        "open": [
            "Gym before school. Legs are gone.",
            "Tape on, boots on, head not on yet.",
            "Cousins ate my recovery smoothie. All four.",
            "Aunt Lei's playing her country playlist again. Home sounds right.",
        ],
        "core": [
            "Selection trial in three weeks and my brain keeps replaying the intercept I missed in the semi — even though we WON. Coach says elite brains replay losses; I say mine needs better highlights settings.",
            "Contact training went full pace. Shoulder held. The physio's 'trust the repair' line is easier to say than feel. Tackled hard once anyway, on purpose, to test it. We don't tell the physio.",
            "Aunt asked if I miss my parents. Said 'we' a lot in the answer — 'we're good', 'we're training hard'. She gently said 'you, Kai. Are YOU good?' Scored a try in training the next day like the answer had to come out through my boots.",
            "Visualization drill Dr Vale gave me: replay the game in real-time, but rehearse the hard moments going WELL. Fell asleep mid-drill. First time sleep came easy in weeks.",
        ],
        "close": [
            "3 weeks. Trust the repair. Trust the brain too, I guess.",
            "We're good. I'm learning to be good, singular.",
            "Shoulder: 9/10. Trust: 6/10 and climbing.",
            "Sleep: arrived via rehearsal. Logging the drill as complete.",
        ],
    },
    "ivy_c": {
        "open": [
            "5:15 alarm. Studio by 6. Good.",
            "Meal plan day: exactly on protocol.",
            "Ballet Conditioning log: 90 min + 45 pointe.",
            "Sunday duck trip pending. Weather holding.",
        ],
        "core": [
            "Mistress said my épaulement is the best in the company and all I heard was 'so you can't afford an off day'. Ate exactly to plan but the numbers yelled the whole time. Wrote them here so they'd stop yelling in there.",
            "Mom made dumplings, my childhood favourite, and I calculated the whole plate before the first bite and tasted almost nothing. Logged it honestly with Dr Chen-wait, Dr Raine. She asked what nine-year-old Ivy would say about the dumplings. That question is still open.",
            "Performance of The Nutcracker in 5 weeks. Costume fitting. The mirror did its usual audit. I performed the 'what would I say to a friend' reframe out loud in the changing room like a weirdo. It helped 20%. Counting it anyway.",
            "Fed the ducks. They get enough. They never count. Note to self: keep feeding the ducks.",
        ],
        "close": [
            "Protocol: 100%. Smile: 80% genuine (up from 60).",
            "The numbers lost today, mostly.",
            "Ducks: 14. Regret: 0. Data point worth more than the mirror's.",
            "Asking Dr Raine to sit with the dumpling memory next session.",
        ],
    },
    "omar_h": {
        "open": [
            "Checked the smoke alarm in the hallway. Just once. Progress.",
            "Cousins' house again. It's loud in a good way.",
            "Minecraft: rebuilt our old kitchen block for block.",
            "Night was okay. One dream, no fire in it.",
        ],
        "core": [
            "Someone burned toast at school and the alarm went off and my whole body was back in that night for maybe ten seconds. Mr. Dixon let me stand by the open door. He didn't ask questions. Ten seconds is shorter than last month's twenty.",
            "The rebuild is at 80%. Same layout as home: kitchen door on the left, stairs with the creaky fourth step. Building it in the game is like telling my hands the house still exists somewhere.",
            "Visited the actual house site. Saw the new kitchen in boxes. Wrote this right after, hands a bit shaky, to prove to myself I could stay with the feeling instead of running from it. Dr Vale calls it 'touching the memory gently'. I call it heavy. Both are true.",
            "Yusuf uncle took us for kunafa. I knew where both exits were in the restaurant AND still enjoyed it. Both things can be true.",
        ],
        "close": [
            "Alarm: checked once. Sleep: 6.5 hours. No fires anywhere except toast-related.",
            "Rebuild continues. Block by block. So does me.",
            "Sticker still on my folder. Fire station 4, my favourites.",
            "Telling Dr Vale I want to visit the site weekly. Request, not avoidance.",
        ],
    },
    "rue_d": {
        "open": [
            "Made the session playlist: track 1 is literally called 'Acceptance Speech'.",
            "Thrifted a flannel so perfect it felt like a jump scare of joy.",
            "Mom used my name right twice today. Counting.",
            "Tired in the bones but the good tired.",
        ],
        "core": [
            "Dad texted 'how's my girl' and my chest did the thing where it's anger and grief in the same breath. Didn't reply. Drafted 14 replies. Sent none. Dr Raine says the non-reply is still communication, just at a frequency he hasn't tuned to yet.",
            "School form used my correct name in the register today. Small thing. Huge thing. Logged it as evidence for the part of my brain that keeps insisting nothing changes.",
            "Made a playlist for 'the talk with mom' — 23 tracks, none of which we'll listen to, but building it made the conversation feel survivable. We had tea. She got the pronouns right 80% of the time. 80% is a D+ but it's a D+ UP from last month's F.",
            "Dysphoria was loud getting dressed. Wore the flannel like armour anyway. Went out. Survived the mirror in the shop. Bought nothing. Still counting it a win.",
        ],
        "close": [
            "Playlist of the night: 'Evidence of Change'. Track 1: the register.",
            "14 drafts unsent. Draft 15 might be 'I'm your kid'. Saving it for when I'm ready, not when he's loud.",
            "80% today. A trending grade. Improving.",
            "Mom's tea, my name, correct. Some evenings that's the whole victory lap.",
        ],
    },
    "finn_o": {
        "open": [
            "OKAY SO TODAY WAS A LOT (good a lot?? mostly)",
            "Lost my pen. Found my pen. Lost my HOODIE though.",
            "Twin twins woke me at 6 with a trumpet. A TRUMPET.",
            "Detention: 0. Personal record possibly broken.",
        ],
        "core": [
            "Got moved seats in Science for 'excess enthusiasm' which is TEACHER for 'you asked 9 questions and answered 4 of them yourself'. Not sorry. Okay slightly sorry. The questions were GOOD though.",
            "Invention #42: a folder that buzzes when homework is due, built from an old watch. It works EXCEPT it buzzes for homework from 2019 too. Dad said that's called 'legacy debt'. I said it's called FEATURES.",
            "Got frustrated at maths and my brain went lightning-storm again, said something loud, had to do the walking-out thing. BUT I used the 5-count from Dr Vale's card and came back in 4 minutes instead of a whole lesson. That's a RECORD. Writing it down so it's real.",
            "The twins asked me to help build their block tower 'because you're good at falling things over'. I have never felt so seen or so insulted.",
        ],
        "close": [
            "Meds taken: yes. Water bottle drunk: 40%. Improving.",
            "Lightning-storm 1, Recovery 4 minutes, Detentions 0. THE NUMBERS ARE GOOD.",
            "Note for tomorrow: hoodies live on HOOKS. HOOKS, Finn.",
            "Telling Dr Vale about invention #42 AND the 4-minute comeback. Both wins.",
        ],
    },
    "noor_a": {
        "open": [
            "Sat at the back of the library again. Good spot. Invisible-adjacent.",
            "Jupiter was bright tonight. Named it after Hiba.",
            "Group chat: 214 messages. I read them all. Sent 2.",
            "Walked the long way home. The quiet route.",
        ],
        "core": [
            "They were doing the thing again by the science block — my name said like it's a punchline. I did the counting thing Dr Raine gave me and left through the far door. Far door = 40 seconds saved on my dignity but it worked.",
            "Hiba noticed I've been quiet. She didn't push. She just walked the long way home with me and pointed at Venus like it was normal to do that. It IS normal. We should all do it more.",
            "Told Mom about the science block. She wanted to storm the school with the fire of a thousand suns. I asked her to wait while I try the reporting route first. She's waiting. Loudly. In the house. But waiting.",
            "Reported it. Mr. Ellis took it seriously — actual notes, actual 'this has a name' (harassment). The word for it being official made something in my chest unclench.",
        ],
        "close": [
            "Stars logged: 3. Friends who show up: 1 (the good kind of enough).",
            "The far door is fine. But I'm practicing the main door too, one stride more each week.",
            "Mom waited. I reported. The adults did adult things. Noted for future me: asking works.",
            "Astronomy club Friday. Going. Sitting at the FRONT this time.",
        ],
    },
    "jasper_l": {
        "open": [
            "Garage shift 9-5. Smelled of petrol. Regeneration achieved.",
            "Saturday earnings: £84. Van fund: £1,290.",
            "Mom's new boyfriend cooked. It was... fine? Suspicious.",
            "Big night out planned. Already tired of it before it starts.",
        ],
        "core": [
            "The lads wanted to pre at Dev's — sorry, NOT Dev, other one — and I did my usual 'I'll catch up' which means drinks at 4pm then nothing remembered after 11. Woke up with the Fear and a mate saying I told the group chat I 'needed help pacing'. Drunk honesty is just honesty with the volume broken.",
            "Counted my Saturdays sober so far this month: one. ONE. Wrote the number down and stared at it. The number looked different in ink than in my head where it was 'barely any, it's social'.",
            "Ken at the garage (55, forearms like rope, quietly recovered 12 years) said 'you're too good at this to be doing it this young'. Didn't lecture. Just said it. It landed like a spanner in the chest. In a useful way.",
            "Told the lads I'm driving to the next one. Cover story: saving money. Real story: also saving money. Both true. Worked — zero drinks, still had a laugh, home by 1, no Fear.",
        ],
        "close": [
            "Van fund £1,290. Sobriety fund: rebuilding. Day count: 2.",
            "Ken's sentence lives in my chest rent-free. Good tenant.",
            "Driving to things now. Cheaper, funnier, rememberable.",
            "Session Wednesday. Telling Dr Raine the REAL number. She never flinches at numbers.",
        ],
    },
    "amara_j": {
        "open": [
            "Science today: circulatory system. Personally acquainted with mine.",
            "Grandma's soup protocol deployed. Status: restored.",
            "No faints this week. Streak: 12 days.",
            "Blood drive at school — I have THOUGHTS.",
        ],
        "core": [
            "We had to watch a first-aid video with an ACTUAL injection scene and my vision went sparkle-edged in class. Did the counter-pressure thing (hands gripped, arms tense, taught by Dr Vale) and stayed in my chair. My deskmate thought I was stretching. Best actor in Year 10, right here.",
            "Grandma, who fainted at her own wedding photos (family legend), told me her trick was 'sit with your head between your knees and your dignity between your teeth'. I love her so much.",
            "Paramedic open day at the hospital. Wanted to go so badly. Scared of going. Mom offered to come 'not as mom, as crew'. We went. I stood where they load the trolleys and my heart did 140 but my feet stayed. Two minutes. Then a paramedic named Kels showed us the radio codes and I was TOO fascinated to faint. Cure: curiosity, apparently.",
            "Logged my fainting triggers like field research: heat ✓, standing fast ✓, blood/injury talk ✓✓, injustice at the dinner table ✓ (who knew). Knowledge is armour.",
        ],
        "close": [
            "Streak: 12 days. Feet-stayed record: 2 minutes at ambulance HQ.",
            "Curiosity as anti-faint technology. Patent pending.",
            "Paramedic dream: still on. Stronger after the open day, actually.",
            "Telling Dr Vale about Kels and the radio codes. She'll love it.",
        ],
    },
    "leo_f": {
        "open": [
            "5:30 on the water. Mist. Quiet hour achieved.",
            "Mocks: 4 A*s, 1 A. The A is a wound I'm nursing privately.",
            "Crew list posted. Captaincy confirmed. Relief lasted 9 minutes.",
            "Erg session: 6k. Negative split. Still lost the argument in my head.",
        ],
        "core": [
            "Dad asked which unis are 'realistic' now that the A happened. Realistic. As if the A is a structural defect. I did the thought record Dr Raine taught me: evidence for 'one grade ruins everything' — none; evidence against — my entire transcript, my coach's face, physics itself.",
            "Haven't taken a full rest day in 41 days. Coach mandated one. I spent it writing the to-do list FOR the rest day, then rowing anyway at lunch, alone, which technically made it a rest day with extra steps and guilt.",
            "Harry (2-seat, chaos merchant, my best friend) ate a whole pizza in front of me while I ate my weighed rice and said 'you know this is mad, right?' and for the first time instead of explaining periodization I just said 'yeah'. Yeah. It's mad. Noted.",
            "Slept 5 hours because I was redoing the UCAS personal statement for the fourth draft. Fourth. The statement was already good. The statement was never the problem.",
        ],
        "close": [
            "Quiet hour tomorrow. Rest day: scheduled (skeptically).",
            "The A stands. So do I. Writing that sentence was harder than 6k.",
            "'Yeah' to Harry: breakthrough of the week.",
            "Bringing the thought record Thursday. Evidence-based, as is my custom.",
        ],
    },
    "priya_g": {
        "open": [
            "Baked cardamom buns before school. House smelled like safe.",
            "Grandma walked me to the gate today. Both of us pretending it's for her health.",
            "Attendance this week: full. Log it proudly.",
            "Amma's arthritis was better today. She danced a tiny bit at lunch.",
        ],
        "core": [
            "Mom's work trip got announced at dinner — two nights. My chest did the squeeze. Grandma saw my face do the thing and said 'we will make a project of it: her bed, your monopoly board, my snacks'. The squeeze went from 8/10 to 4/10 with a sentence.",
            "Missed the bus because I went back to hug grandma twice. Worth it. Also late. Also worth it. School understood (note went in advance — the pre-planning from Dr Marcus's card WORKS).",
            "Called mom after the first night. Voice shaky. She said 'you are braver than my wifi at grandma's'. I laughed and the shake went out of my voice. Laughing at her jokes is basically home-shaking-hands.",
            "Slept in grandma's room (permitted, official). The squeeze never fully left but it got small enough to sleep beside.",
        ],
        "close": [
            "Night two: monopoly + cardamom buns + grandma's radio. Survived, even smiled.",
            "Attendance: full. Hugs at gate: 2. Squeeze rating: 3/10 by evening.",
            "Thursday session: telling Dr Marcus the pre-planning note WORKED. He'll do his calm proud face.",
            "Home is people. The house is just where they keep the buns.",
        ],
    },
    "tyler_k": {
        "open": [
            "54 deliveries today. Legs: LEGAL SEPARATION pending.",
            "Couch at Dev's — sorry, different Dev — mine tonight, Dad's tomorrow.",
            "Applied to 6 jobs. Van fund: £410.",
            "Rain all shift. Sloshed but undefeated.",
        ],
        "core": [
            "Got the rejection email from the apprenticeship. Third one. Read it standing in the rain outside a kebab shop like a scene from a film about lads having a normal one. Let myself be gutted for exactly one kebab's worth of time, then applied to two more.",
            "Dad keeps 'joking' about rent. It's not a joke. It's a weather system. I keep my stuff in bags so I can leave without the conversation. Dr Marcus says 'bags are a plan, not a home'. Annoying. Correct.",
            "Played ranked till 3am again — not even enjoying it by then, just postponing the morning where I'm nothing in particular. Reframing for the week: I'm a rider with 54 deliveries and a van fund. The van has a name. Elvis. Van Elvis. The dream has a VIN number now.",
            "Met mates from school. Everyone's in different stages of the same limbo. Danny's got an apprenticeship, Shauna's at uni, I'm on the couch circuit. Sat with the feeling instead of dodging it. It passed. They always do. Dr Marcus is right and I hate it.",
        ],
        "close": [
            "Van fund: £410 → £447 (tips were good). Applications: 8 sent this week.",
            "Bags packed but not defeated. Plans beat panic.",
            "Tomorrow: shift at 9, gym with Danny after (he asked ME — noted, held onto).",
            "Telling Dr Marcus about Elvis. He'll pretend it's not a metaphor. It's absolutely a metaphor.",
        ],
    },
    "noa_b": {
        "open": [
            "Pump report: 2 lows overnight, none today. Small mercies.",
            "Counted carbs at breakfast like it's my actual GCSE subject.",
            "Site change day. The old one left a bruise shaped like Portugal.",
            "Nurse clinic went fine. I answered the questions like a professional, because I am one, apparently.",
        ],
        "core": [
            "Mom found me testing at 3am again. She does the worried face and I do the joke about my pancreas being a bad roommate. Neither of us means it.",
            "Slept through PE because the numbers were doing a rollercoaster all morning. Told the teacher it was a medical thing, which is true, and also a get-out-of-jail card I hate owning.",
            "Baked the lemon loaf for baking club with the sugar-free swap. Everyone said it tasted normal. I said thanks like that's a normal thing to be relieved about.",
            "The pump beeps at dinner, at homework, at 2am. It beeps like it's my job to be a pancreas. Some days I clock out of that job in my head and then feel guilty about it.",
            "New site in my arm. I rated it 6/10, would not recommend, staying for the plot. Dark humour keeps the burnout from becoming a fire.",
        ],
        "close": [
            "Numbers: stable-ish. Me: tired but here.",
            "Tomorrow I'll ask about the CGM upgrade. Asking counts.",
            "Diabetes didn't win today. Marking the score.",
            "Sleep before midnight. The pump and I have a truce.",
        ],
    },
    "dante_m": {
        "open": [
            "Ranked till 4am. No regrets (regrets pending).",
            "Slept through school. Dad noticed. Bad.",
            "New patch notes nerfed my main. Uninspired.",
            "Speedrun PB attempt tonight. Maybe.",
        ],
        "core": [
            "Dad said gaming is 'killing my future' and I said school is killing my present and nobody won. Sat in my room after and honestly couldn't tell you the last match I actually enjoyed.",
            "Stepmom made dinner I didn't eat. Not the food's fault. I just lose hours between the chair and the screen and come back to a cold plate and a colder room.",
            "Watched my own replay back for the analytics and saw myself not having fun for three straight hours. That's data I can't unsee.",
            "The crew's on at 10 now because of my schedule. Or what used to be my schedule. They're talking about meeting up IRL and I made an excuse before they finished the sentence.",
            "Slept 4 to noon again. The days feel like loading screens — technically part of the game but I'm not really playing them.",
        ],
        "close": [
            "Alarm set for 9. A real one. Typed it here so it's real.",
            "One match tonight. ONE. Then the controller goes on the shelf.",
            "Replied to the group chat about the meet-up. Didn't say no. That's the update.",
            "Log says I played 41 hours this week. Reading that number did more than any lecture.",
        ],
    },
    "wren_h": {
        "open": [
            "Library corner seat was free. Best possible start.",
            "The fire drill schedule changed without warning. Difficult.",
            "Drew 3 hours straight. The city now has a harbour.",
            "Nana made the toast the RIGHT way (diagonally cut). Good day signal.",
        ],
        "core": [
            "Science moved rooms today. Nobody thought to tell me the layout changes, so I spent the lesson mapping exits instead of atoms. Wrote it in the communication book so it's on record.",
            "The hand dryer in the east bathrooms is a personal enemy. Ms. Petrov lets me use the staff one now. Small accommodation, enormous difference, don't mind me while I cry about a hand dryer (I am not crying about a hand dryer).",
            "Alfie from maths asked why I repeat things when I'm happy. I told him it's called echolalia and it means the maths was GOOD. He said 'oh cool' and I think he meant it.",
            "The A3 city gained a tram system and a mayor. Her name is Professor Turnip. If school made sense like the city does, I'd attend twice.",
            "Mom and Nana attended the parents' evening together and read my sensory profile to the teacher like it was a legal document. My legal document. My case won.",
        ],
        "close": [
            "Tomorrow: normal fire drill time, normal hallway, prepared brain.",
            "The city has a library now. Meta.",
            "Wore the headphones all day and nobody made it weird. Logging that as a win.",
            "Nana's toast rating: 10/10 again. Consistency matters.",
        ],
    },
    "gabe_d": {
        "open": [
            "Sofia slept 4 hours straight. Personal best. Hers, mine, everyone's.",
            "Warehouse shift, then home, then the 2am feed. That's the whole diary.",
            "Abuela dropped off soup and judgement about my sleeping posture.",
            "Wrote my name on the form under 'parent'. Strange hands.",
        ],
        "core": [
            "Missed the UCAS deadline talk at college. Was at a health visitor appointment instead, holding Sofia while the nurse said 'dad' and meaning me. Plans change shape. Still working out if I mind.",
            "Girlfriend's college runs later than mine now, so evenings are mine and Sofia's. We do a tour of the flat, she points at everything with her whole arm, I narrate like a nature documentary. Best shift of the day.",
            "Told the lads at work I can't do Friday nights anymore. Nobody made it weird. Dr Vale says to log who shows up when you say the real thing. They showed. Everyone showed.",
            "Abuela watches Sofia on Wednesdays so I can finish coursework. She pretends it's nothing. It's the whole wall holding the roof up and we both know it.",
            "Money maths at midnight again: prams, nursery deposits, bus fares. Scary sums, then Sofia grabs my finger in her sleep and the sums get quieter. Doesn't fix them. Quiets them.",
        ],
        "close": [
            "One coursework section done after the feed. Counting it.",
            "Sofia's first word attempt tonight: 'ba' (ball? bottle? both?). Witnessed.",
            "Told Dr Vale the truth about being scared. He said scared dads are still dads. Keeping that.",
            "Sleep when she sleeps. That's the whole strategy. Execute the strategy, Gabe.",
        ],
    },
    "mei_l": {
        "open": [
            "Studio mirrors from 6 to 8. Compared myself to everyone. Twice.",
            "Deleted the dance hashtag off my phone. Reinstalled it. Delete count: 3 this week.",
            "Restaurant close-down with mom, mopping to old Cantopop. Good hours.",
            "Slept 5 hours. Not the plan. Logging honestly.",
        ],
        "core": [
            "Scrolling other people's competition clips at 1am like it's training. It's not training. It's collecting evidence for the case that I'm behind. Dr Raine asked what the evidence FOR me looks like. I had a list. It was longer. Why don't I believe it?",
            "The judgmental voice has my mom's accent and my ballet teacher's vocabulary. Noticed that in session and had to sit down inside my own head for a minute.",
            "Choreographed 32 counts after close tonight, alone, floors shining, nobody filming. No audience, no comparison, just music. That's what dancing actually is. Trying to remember that mid-scroll.",
            "Mom said 'you look tired' and I said 'busy' and we both let the lie stand because the restaurant was full. Writing the true version here: the phone is the busy thing.",
            "Body check ritual flagged: mirror, side profile, pinch, repeat. Down to once a day from five. The number is going the right direction, which is more than I could say a month ago.",
        ],
        "close": [
            "Phone charges in the kitchen now. Not the bedroom. New law.",
            "32 counts choreographed. Zero posts. Art survived without an audience — noteworthy.",
            "List of MY evidence: 6 items and growing. Homework: add one daily.",
            "Sleep: lights out 11:30. The insomnia plan says boring is the point.",
        ],
    },
    "samir_b": {
        "open": [
            "Called grandmother. Line was good today, voice better.",
            "Maths test. Wrote the date in Arabic first by accident.",
            "Rain here. Not like home's rain. Shorter stories.",
            "Cousins' chess night. Lost in 11 moves. Rematch Sunday.",
        ],
        "core": [
            "New boy at school asked where I'm from and for the first time I said the city name out loud without my chest tightening. He asked if the food is good. It is. I told him about the bread. Small thing. Big thing.",
            "Dreamed of the old street again — the balcony rail, the bakery smell, the sound of the generator. Drew it when I woke so the dream stays outside of me. Every balcony was right. My hands remember even when my head wants to forget.",
            "The visa paperwork for grandmother is 'processing'. Here, everything is processing. Waiting rooms with numbers. I am learning patience like it's a school subject I did not choose.",
            "Teacher played a news clip about the region without warning. My body left the room before I did. Told the counsellor, told Mr. Harris. They will tell me before next time. I wrote it in my own words so it counts.",
            "Father works two jobs now and still checks my homework. I want to make the sacrifice mean something but Dr Vale says meaning is not a debt. I am thinking about that sentence like a chess position.",
        ],
        "close": [
            "Grandmother's visa: week 6 of unknown. Hope with paperwork.",
            "English: 40 new words this month. Arabic: still the language of my dreams. Both mine.",
            "Sunday rematch plan: Sicilian defence. For the cousins, not the war.",
            "Safe tonight. Heat, bread, family under one roof. Counting it.",
        ],
    },
    "poppy_a": {
        "open": [
            "Rode Biscuit today and he was SO good (for Biscuit).",
            "New keyring: a tiny horseshoe. Adding it to the bag.",
            "Weekend at dad's soon. Stomach feels wobbly about it.",
            "Made the team joke in form and people LAUGHED (good laugh).",
        ],
        "core": [
            "Chloe and the group have a new group without me in it and everyone pretends it isn't happening. I told Dr Raine the truth which is that I keep being extra nice so they'll let me back in and it doesn't work and I feel sick at break times.",
            "Mom's partner made pancakes and asked about school in a normal voice and I ended up telling her about the group thing by accident. She didn't try to fix it. She just said 'that sounds really hard' and I cried a bit and it helped?? Confusing.",
            "Growth spurt means new bras and new feelings and everyone at school has opinions about both. Nobody teaches you what to DO with a body that's changing faster than the rules.",
            "Biscuit is the only one who doesn't care if I'm popular. You groom him, he stands there being large and honest. I told Dr Raine horses are therapy and she said 'formally, we call that equine-assisted' and I said 'I call it Biscuit'.",
            "Wrote the apology text to Mia about the party thing then deleted it then wrote it then deleted it. Dr Raine says maybe the apology isn't mine to write. Reading that sentence a lot.",
        ],
        "close": [
            "Stomach wobble about the weekend: 6/10. Breathing thing: helps 3 points.",
            "Keyring count: 24. No new ones needed (needed one).",
            "Told mom about the group thing properly. It's out of my body now.",
            "Biscuit day again Wednesday. That's the good thought to end on.",
        ],
    },
    "caleb_j": {
        "open": [
            "Cooked Sunday for eleven. Two trays of chicken, zero casualties.",
            "Flat viewing on Thursday. First one with MY name on the form.",
            "Receipts reconciled. Shoebox balanced to the pound.",
            "Apprentice shift: had the pastry section to myself. Nailed it.",
        ],
        "core": [
            "The flat viewing letter came and I read it four times because it has my name where adults' names usually go. Tanya says don't get attached until the reference clears. I'm attached already. Tanya knows I'm attached already.",
            "Someone at work asked what my folks do and I did the usual 'they're not around' shrug, and then later I thought about how many shrugs I do per week. Counted nine. The shoebox is where the receipts go; maybe I should put the shrugs somewhere too.",
            "Supported lodgings means a door that locks but isn't mine, a fridge with an arrangement, and a landlady who's kind in a professional way. I'm ready for a fridge that's just mine and an arrangement that's just mine. That's the dream, a whole boring dream, and I want it so bad.",
            "Cooked for the house and the youngest foster kid watched me chop onions the whole time and asked if I'd teach him. Taught him the claw grip. He burned nothing. Good night. The kind of night I used to watch other families have through windows.",
            "Interview at the restaurant went well except the part where they asked about five-year plans and my brain said 'survive Thursday'. Said it out loud actually, and the head chef laughed and said his was 'survive Saturday'. Hired.",
        ],
        "close": [
            "Flat: viewing Thursday 4pm. Suit for the landlord, apron for the dream.",
            "Sunday roasts: now a house institution. Unanimous.",
            "Called Tanya just to say thanks. She said 'that's the job' but I heard 'that's my boy'.",
            "Emergency fund: £310. Peace of mind is a number and mine is going up.",
        ],
    },
    "tessa_w": {
        "open": [
            "3am again. The moon and I are colleagues now.",
            "Dream atlas page 41: mapped the ferry city. Added fog.",
            "Slept 4.5 hours. Fog level: atmospheric.",
            "CBT-I sleep diary week 6, day 3. Data attached to my soul.",
        ],
        "core": [
            "The sleep restriction thing feels insane — get OUT of bed at 7:30 no matter what, no naps, build the pressure. Dr Marcus says my bed has become a place where I wrestle sleep instead of receiving it. Rude. Accurate.",
            "Nightmare at 2, lucid at 2:04, spun the dream into the ferry city and made the nightmare man buy a ticket. Took the teeth out of it. Woke up almost smug. Almost counts as rested.",
            "Mom keeps offering warm milk like it's 1953. I love her. The milk does nothing. The STATISTICS do something — my sleep efficiency went 62 to 74 percent in five weeks and I would marry a spreadsheet if legally allowed.",
            "Fog days at school are the worst part — teachers think you're lazy, you think you're lazy, the sleep diary says otherwise. I showed Mr. Dunne the chart. He adjusted my deadlines. Charts are tiny lawyers. Hire them.",
            "Woke at 3 and did the 20-minute rule (out of bed, boring book, dim light) instead of doom-rolling. Fell back asleep in 15. The protocol is slowly replacing the panic and I don't know when that happened.",
        ],
        "close": [
            "Sleep efficiency: 74% and climbing. The moon respects data.",
            "Ferry city gained a lighthouse. It's mine. Everything there is mine.",
            "Tomorrow's fog forecast: mild. Deadlines adjusted. No doom expected.",
            "No naps, lights out 11. If I break the rule I log it anyway. Data over shame.",
        ],
    },
    "josh_o": {
        "open": [
            "Chippy shift was slammed. Free scraps though.",
            "Skipped form again. It's just form, right? (writing it down anyway)",
            "Mom and I yelled about the same thing as always. Groundhog sequel.",
            "Half term countdown: 4 days. Motivation: also 4.",
        ],
        "core": [
            "Smoke sesh behind the rec turned into 3am and I woke up on Liam's floor with an exam in four hours. Did the exam. Probably scraped it. This is the part where I'd usually say 'it's fine' but writing it here it looks less fine.",
            "Mom found the grinder. Massive row, doors, the usual percussion section. But afterwards she said 'I'm not angry, I'm scared' which hit different than any grounding ever could. Sat with that for a while.",
            "Dr Raine asked what the smoke is FOR. Everyone asks about stopping, nobody asks what it's doing. Took me a full session to answer: it pauses the house. Just mutes it for a bit. Now I have to find a pause button that doesn't cost lungs.",
            "Little brother asked if I'd come to his match. I said yeah, then nearly bailed for a shift swap, then remembered I'm the one he looks for in the stands. Went. He scored. I yelled embarrassingly. Free, legal, better.",
            "Truce with mom: screens out of my room, I come home by 11, she stops the bedroom raids. Week one: kept. Nobody's made a banner but I'm quietly proud.",
        ],
        "close": [
            "Smoke count this week: 2 (was 5). No banner, but noted.",
            "Brother's next match Saturday. In the stands, non-negotiable.",
            "The pause alternative: chips + skate + one song at full volume. Tested. Works about 60%.",
            "Exam resit scheduled. It's just form. (It's not just form.)",
        ],
    },
}

print("  generating voice journals…")

j_count = 0
for c in CLIENTS:
    c["_voice"] = VOICE_BANK[c["u"]]
    traj = c["traj"]
    # 12 months of journals: 2-3 per week
    for week in range(52):
        for k in range(RNG.choice([2, 2, 3])):
            day_idx = week * 7 + RNG.randint(0, 6)
            if day_idx > 364:
                continue
            # mood state evolves by trajectory
            if traj == "improving":
                mood_state = RNG.choices(
                    ["good", "great", "okay", "anxious", "low"],
                    weights=[6, 2, 4, 2, 1] if week > 26 else [3, 1, 4, 4, 3],
                )[0]
            elif traj == "stable":
                mood_state = RNG.choices(["good", "okay", "anxious", "low", "great"], weights=[3, 4, 3, 2, 1])[0]
            else:
                mood_state = RNG.choices(["good", "okay", "anxious", "low", "great"], weights=[2, 3, 3, 3, 1])[0]
            body = make_journal_body(c, day_idx, mood_state)
            label, emoji = EMOJI_BY_STATE[mood_state]
            probs = {
                e: round(RNG.uniform(0.15, 0.95), 3)
                for e in [label, "neutral", RNG.choice(["curiosity", "gratitude", "fear", "joy"])]
            }
            ts = days_ago(364 - day_idx, RNG.randint(7, 22))
            db.add(
                JournalEntry(
                    patient_username=c["u"],
                    raw_content=body,
                    summary=journal_summary_pair(c, day_idx, mood_state, traj)[0],
                    clinical_summary=journal_summary_pair(c, day_idx, mood_state, traj)[1],
                    ai_source=RNG.choice(["ollama", "groq", "rule"]),
                    emotions=label,
                    emotion_probabilities=json.dumps(probs),
                    timestamp=ts,
                    created_at=ts,
                    version=1,
                )
            )
            j_count += 1
db.commit()
print(f"  {j_count} journal entries (each with warm + clinical summaries)")

# ── MOODS: daily logs for 400 days ──────────────────────────────────
m_count = 0
for c in CLIENTS:
    for d in range(400):
        traj = c["traj"]
        week = d // 7
        if traj == "improving":
            state = RNG.choices(
                ["good", "great", "okay", "anxious", "low"], weights=[6, 2, 4, 2, 1] if week > 26 else [3, 1, 4, 4, 3]
            )[0]
        elif traj == "stable":
            state = RNG.choices(["good", "okay", "anxious", "low", "great"], weights=[3, 4, 3, 2, 1])[0]
        else:
            state = RNG.choices(["good", "okay", "anxious", "low", "great"], weights=[2, 3, 3, 3, 1])[0]
        label, emoji = EMOJI_BY_STATE[state]
        ts = days_ago(d, RNG.randint(7, 21))
        db.add(MoodLog(patient_username=c["u"], date=ts[:10], emoji=emoji, label=label, timestamp=ts))
        m_count += 1
db.commit()
print(f"  {m_count} daily mood logs")

# ── RING VITALS: realistic per-client baselines ─────────────────────
BASELINES = {  # (bpm_mean, hrv_mean, stress_mean, sleep_mean)
    "maya_k": (78, 42, 48, 6.6),
    "dev_p": (72, 55, 35, 7.4),
    "luna_r": (80, 38, 55, 6.2),
    "theo_b": (76, 40, 50, 5.9),
    "ava_s": (82, 36, 58, 7.0),
    "jayden_w": (62, 62, 30, 7.8),
    "zoe_m": (80, 44, 46, 6.8),
    "eli_n": (84, 50, 40, 8.4),
    "sana_i": (74, 45, 52, 5.6),
    "kai_t": (58, 68, 28, 7.6),
    "ivy_c": (66, 34, 55, 6.0),
    "omar_h": (82, 39, 54, 6.1),
    "rue_d": (76, 43, 50, 6.4),
    "finn_o": (86, 46, 44, 7.2),
    "noor_a": (78, 47, 45, 6.9),
    "jasper_l": (72, 41, 49, 6.3),
    "amara_j": (80, 48, 47, 7.1),
    "leo_f": (56, 72, 42, 6.5),
    "priya_g": (84, 52, 42, 8.0),
    "tyler_k": (74, 42, 51, 6.0),
    "noa_b": (74, 44, 47, 6.3),
    "dante_m": (70, 48, 44, 5.2),
    "wren_h": (80, 41, 53, 6.7),
    "gabe_d": (72, 46, 45, 6.1),
    "mei_l": (68, 51, 49, 5.8),
    "samir_b": (78, 40, 56, 6.0),
    "poppy_a": (84, 49, 43, 8.2),
    "caleb_j": (76, 42, 52, 6.4),
    "tessa_w": (75, 38, 54, 4.9),
    "josh_o": (70, 44, 46, 6.9),
}
r_count = 0
for c in CLIENTS:
    bpm0, hrv0, st0, sl0 = BASELINES[c["u"]]
    improving = c["traj"] == "improving"
    for d in range(0, 364, 2):  # every 2 days, ~180 readings
        w = d / 364
        drift = (1 - w * 0.25) if improving else (1 + RNG.uniform(-0.1, 0.1))
        db.add(
            RingSensorLog(
                patient_username=c["u"],
                device_id=f"ring_{c['u']}",
                bpm=int(bpm0 * drift + RNG.uniform(-6, 6)),
                stress=int(min(95, max(5, st0 * drift + RNG.uniform(-8, 8)))),
                sleep_hours=round(max(3.5, sl0 * (1 + RNG.uniform(-0.15, 0.15))), 1),
                spo2=round(RNG.uniform(95, 99), 1),
                hrv=int(max(12, hrv0 * (2 - drift if improving else 1) + RNG.uniform(-8, 8))),
                logged_at=days_ago(d, RNG.randint(5, 9)),
            )
        )
        r_count += 1

    # Acute stress EPISODES: 3-6 short spikes per client (realistic physiology —
    # exams, conflicts, panic nights). Each episode = 2-4 clustered readings over
    # 1-3 hours with stress 25-40 above baseline, mostly afternoons/evenings.
    n_episodes = RNG.randint(3, 6)
    for _ in range(n_episodes):
        ep_days_ago = RNG.randint(1, 350)
        ep_hour = RNG.choice([9, 11, 13, 14, 15, 16, 17, 19, 20, 21, 22])
        ep_min = RNG.randint(0, 59)
        peak = min(97, st0 + RNG.randint(25, 40))
        dur_readings = RNG.randint(2, 4)
        for k in range(dur_readings):
            # rise to peak then fall back — a believable spike envelope
            frac = [0.55, 1.0, 0.8, 0.5][k]
            s = int(max(5, peak * frac if k else peak * 0.55))
            db.add(
                RingSensorLog(
                    patient_username=c["u"],
                    device_id=f"ring_{c['u']}",
                    bpm=int(bpm0 + (s - st0) * 0.6 + RNG.uniform(-4, 4)),
                    stress=min(98, s),
                    sleep_hours=round(max(3.5, sl0 * (1 + RNG.uniform(-0.15, 0.15))), 1),
                    spo2=round(RNG.uniform(95, 99), 1),
                    hrv=int(max(10, hrv0 * 0.55 + RNG.uniform(-5, 5))),  # HRV dips hard in spikes
                    logged_at=days_ago(
                        ep_days_ago, min(23, ep_hour + (k // 2)), (ep_min + (k % 2) * RNG.randint(10, 40)) % 60
                    ),
                )
            )
            r_count += 1
db.commit()
print(f"  {r_count} ring vitals readings (incl. acute spike episodes)")

# ── RING DEVICES ────────────────────────────────────────────────────
for c in CLIENTS:
    db.add(
        RingDevice(
            serial=f"RING-{c['u'].upper().replace('_', '-')}",
            patient_username=c["u"],
            device_token_hash="seeded-not-a-real-token-hash",
            vendor="simulated",
            status="paired",
            last_seen_at=days_ago(0, 6),
            created_at=days_ago(365, 9),
        )
    )
db.commit()
print(f"  {len(CLIENTS)} ring devices paired")

# ── BOOKINGS: past sessions + future pending ────────────────────────
SESSION_TYPES = ["Therapy", "Follow-up", "CBT Session", "Review", "Check-in"]
b_count = 0
for c in CLIENTS:
    n_past = RNG.randint(9, 16)
    for i in range(n_past):
        past = 350 - i * RNG.randint(18, 26)
        if past < 1:
            continue
        status = "Completed" if past > 6 else "Approved"
        db.add(
            Booking(
                patient_username=c["u"],
                psychologist_username=c["psych"],
                date=days_ago(past, None)[:10] if past > 0 else days_ahead(-past),
                time=RNG.choice(["09:00", "10:00", "11:00", "13:00", "15:30", "16:30"]),
                session_type=RNG.choice(SESSION_TYPES),
                status=status,
                contact=f"{c['name'].split()[0].lower()}@sentinel.demo",
                explanation=f"{RNG.choice(['Regular review', 'Skills practice review', 'Ongoing work on'])} {c['presenting'].lower()}",
                created_at=days_ago(past + 2, 10),
            )
        )
        b_count += 1
    # upcoming: one approved + one pending
    db.add(
        Booking(
            patient_username=c["u"],
            psychologist_username=c["psych"],
            date=days_ahead(RNG.randint(2, 9)),
            time=RNG.choice(["10:00", "15:30", "16:30"]),
            session_type=RNG.choice(SESSION_TYPES),
            status="Approved",
            contact=f"{c['name'].split()[0].lower()}@sentinel.demo",
            explanation="Scheduled follow-up session",
            created_at=days_ago(3, 10),
        )
    )
    db.add(
        Booking(
            patient_username=c["u"],
            psychologist_username=c["psych"],
            date=days_ahead(RNG.randint(10, 20)),
            time=RNG.choice(["11:00", "13:00"]),
            session_type=RNG.choice(SESSION_TYPES),
            status="Pending",
            contact=f"{c['name'].split()[0].lower()}@sentinel.demo",
            explanation="Client-requested check-in",
            created_at=days_ago(1, 12),
        )
    )
    b_count += 2
db.commit()
print(f"  {b_count} bookings (past completed + upcoming approved/pending)")

# ── FOLLOWUPS with grades & feedback ────────────────────────────────
FOLLOWUP_BANK = {
    "maya_k": [
        ("Exam-week coping plan", "Use box breathing before each past paper; 10-min worry window daily."),
        ("Worry-postponement log", "Write worries at 6pm only, not at 2am. Bring the log Thursday."),
    ],
    "dev_p": [
        ("Presentation exposure ladder", "Rung 3: present 2 slides to chess club only."),
        ("Conversation reps", "Initiate one low-stakes chat per day; log how it actually went vs predicted."),
    ],
    "luna_r": [
        ("Art instead of urges", "When sharp feelings come: draw them first, rate intensity after."),
        ("Safety plan refresh", "Update the plan with Joy; keep it in the sketchbook pocket."),
    ],
    "theo_b": [
        ("Attendance micro-goals", "Form period daily + 2 afternoon lessons minimum."),
        ("Novel scene", "400 words, any scene; mood after writing."),
    ],
    "ava_s": [
        ("ERP ladder rung 4-5", "Door-frame touch, no washing; log anxiety curve."),
        ("Reassurance fasting", "Ask mom to answer checking questions once only."),
    ],
    "jayden_w": [
        ("Birthday plan", "Decide by Thursday: attend pitch memorial or plan alternate ritual."),
        ("Feelings vocabulary", "Three entries using words beyond 'fine' and 'good'."),
    ],
    "zoe_m": [
        ("Performance exposure", "Sing one song to mom pre-audition; log anxiety before/during/after."),
        ("Emetophobia fact file", "List evidence for/against 'the flip means vomiting'."),
    ],
    "eli_n": [
        ("Throat-bravery ladder", "Read one line aloud at home, then to mom, then in form."),
        ("Train diary", "Keep logging day ratings; notice what makes 9/10 days."),
    ],
    "sana_i": [
        ("Boundary script", "One calm 'no' per week with a full sentence, not a paragraph."),
        ("Sleep protocol", "Lights out 23:00, no translation work in bed."),
    ],
    "kai_t": [
        ("Visualization rehearsal", "Nightly full-game replay with positive outcomes; log sleep."),
        ("Shoulder trust drills", "Full-contact rep in training; rate trust before/after."),
    ],
    "ivy_c": [
        ("Duck protocol", "Sunday ducks; journal what 'enough' feels like."),
        ("Dumpling memory", "Discuss with Dr Raine; write what 9-year-old Ivy would say."),
    ],
    "omar_h": [
        ("Site visits weekly", "One visit per week with uncle; log body response before/after."),
        ("Minecraft rebuild", "Continue rebuild; note which rooms are hardest."),
    ],
    "rue_d": [
        ("Draft 15", "When ready: send 'I'm your kid' or journal about not sending it."),
        ("Name evidence log", "Collect moments names/pronouns land right; review weekly."),
    ],
    "finn_o": [
        ("Lightning-storm card", "Use 5-count; log recovery times (target: under 10 min)."),
        ("Invention #42", "Fix the 2019-homework bug OR document why it's a feature."),
    ],
    "noor_a": [
        ("Main-door practice", "Once daily past the science block; log predictions vs reality."),
        ("Astronomy club", "Attend Friday; sit front; tell Hiba the plan."),
    ],
    "jasper_l": [
        ("Sober Saturday", "Two sober Saturdays this month; driving as strategy."),
        ("Fear log", "Note Sunday-morning Fear intensity; look for the trend."),
    ],
    "amara_j": [
        ("Counter-pressure practice", "Twice daily grips; log near-faint situations survived."),
        ("Curiosity exposure", "One medical video per week, hands gripped, staying seated."),
    ],
    "leo_f": [
        ("Rest day protocol", "One TRUE rest day weekly; no erg, no to-do list about the rest day."),
        ("'Yeah' practice", "Agree with Harry's observations without defending; log how it feels."),
    ],
    "priya_g": [
        ("Gate-hug rationing", "One hug at the gate; second hug becomes a wave."),
        ("Monopoly nights", "Two board nights when mom travels; log the squeeze rating."),
    ],
    "tyler_k": [
        ("Applications", "Two per week; keep the kebab-shop grieving window to one kebab."),
        ("Gym with Danny", "Accept invitations; log mood after (prediction vs actual)."),
    ],
    "noa_b": [
        ("Burnout dashboard", "Track pump tasks vs energy for one week; circle every task done on autopilot."),
        ("Carb-count holiday", "One meal a day with pre-set bolus; log how the break feels."),
    ],
    "dante_m": [
        ("Sleep anchor", "In bed by 11:30, alarm 9:00, phone outside room; log wake quality."),
        ("Joy check", "One gaming session rated for actual fun (not just hours); notice which one you'd repeat."),
    ],
    "wren_h": [
        ("City break", "Two 10-min sessions on the A3 city when school feels loud; note the effect."),
        ("Advance-warning card", "Give teachers the card before room changes; log what changed."),
    ],
    "gabe_d": [
        ("Coursework sprint", "Two 45-min blocks in Abuela's Wednesday window; log what got done."),
        ("Show-up list", "Write who showed up when you said the real thing; keep adding."),
    ],
    "mei_l": [
        ("Evidence-for-me log", "One item daily; review Friday before the studio."),
        ("Mirror audit", "One body check daily max; log the urge curve before/after."),
    ],
    "samir_b": [
        ("Balcony gallery", "One memory drawing per week with grandmother on the call; narrate in Arabic."),
        ("Warning-plan card", "Hand the news-clip card to form teacher; log that it worked."),
    ],
    "poppy_a": [
        ("Group-free lunch map", "Three lunch spots with different people; rate the break-times after."),
        ("Biscuit debrief", "After each ride, one sentence about what Biscuit taught you."),
    ],
    "caleb_j": [
        ("Flat folder", "Tenancy docs, references, budget in one folder; bring to session."),
        ("Recipe of mine", "Write the Sunday recipe like a restaurant menu card; keep a copy."),
    ],
    "tessa_w": [
        ("Diary honesty", "Log every wake, even the 3am ones; no rounding down."),
        ("Dream atlas entry", "One lucid mapping session; note nightmare-to-scene conversions."),
    ],
    "josh_o": [
        ("Pause menu", "Each urge: try chips + skate + one song first; log urge before/after."),
        ("Stand duty", "Brother's matches: non-negotiable attendance; log the vibe after."),
    ],
}
f_count = 0
for c in CLIENTS:
    tasks = FOLLOWUP_BANK[c["u"]]
    for i, (title, desc) in enumerate(tasks):
        status = "completed" if i == 0 else ("active" if RNG.random() < 0.7 else "completed")
        grade = RNG.choice(["Excellent", "Good", "Good", "Fair"]) if status == "completed" else ""
        feedback = {
            "Excellent": f"Outstanding work — the {title.lower()} was applied consistently and reflected on with real honesty. Keep this exact standard.",
            "Good": f"Solid effort on {title.lower()}. Minor gaps in logging, but the practice itself is clearly happening. Continue.",
            "Fair": f"Partial completion of {title.lower()}. We discussed barriers — worth breaking into smaller steps this week.",
            "": "",
        }[grade]
        assigned = days_ago(RNG.randint(20, 60), 10)
        db.add(
            FollowupTask(
                id=str(uuid.uuid4()),
                patient_username=c["u"],
                psychologist_username=c["psych"],
                title=title,
                description=desc,
                status=status,
                grade=grade,
                feedback=feedback,
                grade_updated_at=days_ago(RNG.randint(2, 15), 14) if status == "completed" else "",
                feedback_updated_at=days_ago(RNG.randint(2, 15), 14) if status == "completed" else "",
                assigned_at=assigned,
                completed_at=days_ago(RNG.randint(3, 18), 17) if status == "completed" else "",
            )
        )
        f_count += 1
db.commit()
print(f"  {f_count} follow-up tasks (grades + personalised feedback)")


# ── CLINICAL NOTES (per past session) ───────────────────────────────
def clinical_note(c, i):
    n = RNG.randint(0, 3)
    opens = [
        f"Session {i + 1}: {c['name'].split()[0]} presented {RNG.choice(['on time and settled', 'slightly withdrawn but engaged', 'bright and talkative today', 'tired but willing to work'])}. ",
        f"Session {i + 1}: Reviewed home practice and the week's journal themes. ",
        f"Session {i + 1}: {c['name'].split()[0]} arrived with {'clear agenda' if n > 1 else 'no explicit agenda; explored the week openly'}. ",
    ]
    body = {
        "maya_k": "Cognitive work on catastrophizing around exams; worry-postponement introduced. Breathing retraining reviewed. Panicked episode Monday downgraded from 9/10 to 6/10 using skills — significant. Continue CBT; consider exam accommodations letter.",
        "dev_p": "Graded exposure for presentations progressing (rung 2 of 5). Social anxiety maintains via avoidance + safety behaviours (scripting). Client insight good. Chess club as exposure arena — natural generalisation. Assign conversation reps.",
        "luna_r": "No self-harm incidents this week; urges peaked 6/10 Wednesday, managed with drawing displacement technique. Placement stable — reinforce. Identity work continues through poetry; strengths-based frame. Review safety plan.",
        "theo_b": "Attendance 61% this week — below target but improved. Low mood stable; anhedonia present but less total. Paddington ritual reframed as adaptive self-soothing. Father relationship: exploring. Monitor school-refusal risk; referral to college transition programme discussed.",
        "ava_s": "ERP rung 4 achieved with habituation in 22 min (was 45 at rung 1). Checking reduced 7→3 daily. Psychoeducation on OCD mechanism landing well. Twin dynamic leveraged therapeutically. Next: rung 5, reassurance fasting with mother.",
        "jayden_w": "Grief work: anniversary reaction anticipated (brother's birthday, 11 days). Avoidance of memorial discussed; alternate rituals co-created. Affect flattened at times; grief expressed physically (gym, coaching). Normalize. No risk indicators.",
        "zoe_m": "Panic frequency 1/week (down from 3). Emetophobia maintains some food avoidance post-show. Interoceptive exposure begun. Beta-blocker use reframed as sensible, not cheating. Audition Saturday = natural exposure; debrief planned.",
        "eli_n": "Selective mutism history: speaking volume in session notably increased. School: reads aloud 1:1 with trusted teacher. Slow-ladder approach validated. Rocks/trains as engagement anchors — working beautifully. Mother reinforcing bravely; reviewed at home strategies.",
        "sana_i": "Role-overload as eldest daughter + Head Girl + translator explored. Diary-privacy violation processed; anger expressed calmly but suppression noted. University offer = developmental push toward autonomy; family negotiation ahead. Sleep: protocol adherence ~60%.",
        "kai_t": "Performance anxiety pre-trial: visualization rehearsal assigned. Injury psychology — trust in repair building (6/10). Identity beyond rugby gently probed ('who are you without the boots?' — silence, then laughter, then material). Aunt's family: secure base affirmed.",
        "ivy_c": "Eating disorder voice strong under performance pressure. Meal plan adherence 100% but mechanistic — pleasure absent. Ballet identity entangled with self-worth. Duck ritual as embodied 'enoughness' practice — keep. Weight stable per nutritionist. Monitor closely; grade as fluctuating.",
        "omar_h": "Trauma-focused CBT wk 8. Nightmare frequency reduced (5→2/wk). Hypervigilance in new spaces improving via planned exits (healthy, currently). Site visit tolerated with shaking hands + staying = genuine exposure success. Fire-alarm incident: 10s flashbacks (was 20s+). Trajectory good.",
        "rue_d": "Gender dysphoria: family acceptance split (mother 80%, father estranged). School register = major validation event. Depression lighter this fortnight. Draft-15 text to father: ambivalence explored, no pressure applied. Playlist-making as affect regulation — effective, creative.",
        "finn_o": "ADHD: medicated mornings stable. Emotional regulation improving — recovery from lightning-storm episodes 45min→4min (client's own data, excellent). Detentions zero this fortnight. School liaison re: seating. Twin-brother dynamics warm. channel the chaos: invention project as executive-function scaffold.",
        "noor_a": "Bullying: formal report filed; school responding. Client's own coping (far door) validated while main-door exposure graded. Friendship with Hiba = protective factor, actively reinforced. Astronomy club = identity beyond 'victim' role. Confidence returning.",
        "jasper_l": "Alcohol: weekend pattern confirmed (binge, not dependence). Sober Saturdays target 2/month, currently 1. Ken (garage mentor) = natural recovery capital, leverage. Driving-to-events strategy client-generated — own it. The Fear tracked; trend line shown to client, landed well.",
        "amara_j": "Vasovagal syncope: counter-pressure technique mastered; faint-free 12 days. Medical-anxiety exposure via paramedic open day = 2 min tolerated, curiosity overcame arousal (breakthrough). Career dream reframed from avoidance-driver to exposure-currency. Grandma's humour = family resource.",
        "leo_f": "Perfectionism/burnout: 41 days without rest day (client data). Cognitive restructuring on 'one A ruins everything' — belief 90%→40%. Rest-day prescription resisted then accepted. Rowing identity examined; 'the quiet hour' reframed as genuine recovery not hidden training. Monitor for overtraining syndrome.",
        "priya_g": "Separation anxiety: mother's work trips as exposure events. Pre-planning card worked (client's words). Grandma as secure base — involve as co-regulator not rescuer. Cardamom buns = family co-regulation ritual, formalised in plan. Attendance full.",
        "tyler_k": "Transition-phase low mood. Rejections processed with time-boxed grieving (client's own framing — good instinct). Couch-surfing instability = background stressor; van project = agency + future orientation. Sleep hygiene vs ranked-until-3am: motivational interviewing applied. Mate contact protective.",
        "noa_b": "Diabetes distress is the presenting engine, not anxiety per se — reframed burnout as chronic unrecognised labour. Autopilot audit revealed 14 daily management tasks (client counted). CGM upgrade discussed with mother; client to raise with nurse. Humour adaptive, not deflective — do not pathologise. Monitor for rigid glycaemic perfectionism; trajectory watchful.",
        "dante_m": "Gaming framed as both refuge and schedule-destroyer. Client's own replay data ('watched myself not have fun for three hours') = genuine insight lever. Sleep anchor protocol agreed; phone outside room is the keystone. Social re-entry via one low-stakes IRL group invite. Father conflict de-escalation script rehearsed. Screen-time numbers presented without shaming; engagement good.",
        "wren_h": "Sensory profile updated with client's own language ('the hand dryer is a personal enemy'). Staff-bathroom accommodation generalising. Communication book use consistent — school responsive. Echolalia normalised with peer — positive identity moment. A3 city as regulation anchor working; formalise as home protocol. No distress escalation; trajectory improving.",
        "gabe_d": "Role strain mapped: worker/father/student with no unallocated hour. UCAS decision deferred deliberately, not avoided — distinction matters. Support audit strong (abuela, girlfriend, employer flexibility). Sleep debt is the moderator of everything; naps-before-coursework order agreed. Normalize 'scared dad' identity; no risk indicators. Trajectory improving with infrastructure.",
        "mei_l": "Comparison cycle made explicit: scroll → evidence-for-behind → restriction of joy. Client generated the 'evidence FOR' list unprompted — key cognitive shift. Body-check ritual reduced 5→1 daily. Phone-charging relocation agreed with mother. Insomnia: sleep restriction week 3, adherence moderate. Dance-as-art vs dance-as-content distinction landed; monitor competition season pressure.",
        "samir_b": "Displacement trauma presentation with strong protective factors (intact family, cousins' network, school engagement). Survivor guilt surfacing via grandmother's visa limbo — meaning-vs-debt reframe in progress. News-trigger protocol established with form teacher after unplanned clip. Memory drawings as containment — effective, culturally consonant. Heritage pride intact alongside integration. Trajectory fluctuating; monitor anniversary dates.",
        "poppy_a": "First counselling engagement excellent. Friendship fallout processed without adult rescue — client's own scripts trialled. Early-puberty psychoeducation delivered via body-changes card sort; mother enlisted for home side. Dad's weekends: anticipatory wobble 6/10, breathing tool effective (3-point drop). Horse as regulation anchor — formally noted, affectionately. No self-esteem collapse; trajectory improving.",
        "caleb_j": "Leaving-care transition: housing pathway live (viewing Thursday). Client's organisation (shoebox, reconciled receipts) reframed from survival skill to transferable competence — visibly landed. Identity work: from 'system kid' to 'house cook, apprentice, flatmate'. Support map: Tanya (keyworker) named as secure base. Independent-living anxiety normalised via concrete checklists. Employment secured; trajectory stable with upward trend.",
        "tessa_w": "CBT-I week 6: sleep efficiency 62→74%. Sleep restriction adherence moderate-high; client motivated by data. Nightmare disorder: lucid mapping conversion technique client-invented — formalised, working. School: deadline accommodations secured via chart presentation to teacher. 20-minute rule replacing doom-rolling. Monitor daytime fog impact on mood; trajectory fluctuating but improving.",
        "josh_o": "Cannabis use: functional analysis over confrontation. Client's own formulation — 'it pauses the house' — is the clinical hinge; alternative pause buttons trialled (60% efficacy). Use down 5→2/week, client-counted. Mother conflict: truce terms agreed and held week one; 'I'm scared not angry' moment processed as turning point. Brother's matches as protective ritual. Exam resit scheduled. Motivation fragile but trending; monitor peer network pull.",
    }[c["u"]]
    return opens[n % 3] + body


n_count = 0
for c in CLIENTS:
    n_sessions = RNG.randint(8, 14)
    for i in range(n_sessions):
        past = 340 - i * RNG.randint(20, 30)
        if past < 2:
            continue
        db.add(
            ClinicalNote(
                psychologist_username=c["psych"],
                patient_username=c["u"],
                raw_notes=clinical_note(c, i),
                ai_synthesis=clinical_note(c, i),
                timestamp=days_ago(past, RNG.randint(9, 17)),
            )
        )
        n_count += 1
db.commit()
print(f"  {n_count} clinical notes (OAP-style, per client)")

# ── PSYCH JOURNAL (reflections by both psychologists) ───────────────
REFLECTIONS = [
    (
        "cel",
        "Maya's breathing downgrade from 9 to 6 in the exam is the kind of data that makes this job. She still thinks CBT is 'a bit silly'. The evidence disagrees with her, politely.",
        "Session reflection: skill acquisition generalising to real stressor. Reinforce.",
    ),
    (
        "cel",
        "Ivy counted the dumplings again. The mirror audit metaphor she uses is precise and brutal. We're keeping the duck protocol — it's doing more work than she realises.",
        "Anorexic ideation latent but active. Weight stable. Continue dual approach.",
    ),
    (
        "cel",
        "Rue played me the 'Acceptance Speech' track. Sixteen and already knows music is medicine. The register moment needs to go in the evidence log we're building.",
        "Validation event logged. Depressive signs easing. Father contact: client-led only.",
    ),
    (
        "cel",
        "Eli brought Rocky (the rock). Rocky apparently also did square breathing. I have never been more professionally fulfilled.",
        "Rapport deepening. Exposure ladder next session with mother present.",
    ),
    (
        "cel",
        "Leo's belief in 'one grade ruins everything' dropped from 90 to 40 percent in a single thought record. He then apologised for the emotion in the room. We have work to do, delightfully.",
        "Perfectionism core belief accessible. Good prognosis if rest-day compliance holds.",
    ),
    (
        "cel",
        "Dev presented two slides to chess club. Two! The bot metaphor is doing heavy lifting: 'if I automate the prep the fear can't attach to a process'. Genuinely insightful framing.",
        "Exposure rung 3 complete. Confidence building. Assign rung 4.",
    ),
    (
        "cel",
        "Zoe narrated her own panic like a stage play and did the curtain-fall breath. Theatre kids are basically pre-trained for interoceptive work if you pitch it right.",
        "Panic frequency down. Audition planned as natural exposure. Debrief booked.",
    ),
    (
        "cel",
        "Sana told me about the two diaries. The fact that she told me is the intervention. English diary is for the world; Urdu diary is for her. Both true, both hers.",
        "Trust milestone. Boundary work proceeding. Sleep still fragile.",
    ),
    (
        "cel",
        "Noor named a star after Hiba and then told me the main-door plan like it was nothing. It is not nothing. It's a whole revolution at 16.",
        "Exposure progressing. Report route vindicated. Confidence returning.",
    ),
    (
        "marcus",
        "Jayden sorted his brother's boots and let his mom sit with him. Two months ago he'd have left the house. Grief is moving.",
        "Anniversary plan agreed. Alternate ritual: boots display + coaching dedication.",
    ),
    (
        "marcus",
        "Kai said 'we' for the whole session and then caught himself and laughed. Progress is often just grammar changing.",
        "Identity work opened. Visualization rehearsal assigned; sleep improving.",
    ),
    (
        "marcus",
        "Omar rebuilt the kitchen in Minecraft, block for block, including the creaky fourth stair. Digital exposure is still exposure. His hands were steady today.",
        "Nightmares halved. Site visits weekly approved. Trajectory strong.",
    ),
    (
        "marcus",
        "Finn's 4-minute comeback is genuinely elite self-regulation for ADHD. He wrote it down 'so it's real'. Data literacy as therapy, apparently.",
        "Reinforce card use. School liaison positive. Invention #42 = EF scaffold.",
    ),
    (
        "marcus",
        "Amara stood where they load the trolleys and stayed two minutes. Then interviewed a paramedic about radio codes. Curiosity beat the vasovagal response. I'm writing this one up for the journal club.",
        "Breakthrough session. Career-as-exposure framework formalised.",
    ),
    (
        "marcus",
        "Jasper drove to the party. Zero drinks. Laughed more than usual, noticed it, and told me the number straight: two sober days this month. Honesty like that is the whole ballgame.",
        "Binge pattern unchanged but insight sharp. Mentor leverage next.",
    ),
    (
        "marcus",
        "Tyler named the van Elvis. A man with a van fund and a name for it is not hopeless, whatever the rejection emails say.",
        "Agency building. Sleep vs gaming: MI ongoing. Applications scheduled.",
    ),
    (
        "marcus",
        "Priya's grandma danced a tiny bit at lunch. That's the secure base doing its work. The gate-hug rationing was Priya's idea — brave.",
        "Separation anxiety responding. Attendance full. Generalising well.",
    ),
    (
        "marcus",
        "Luna's 89 days. She counts in ink, not scars, she says. The static-with-teeth drawing is going on my office wall with permission.",
        "Urges managed via art displacement. Placement stable. Continue.",
    ),
    (
        "marcus",
        "Theo wrote 400 words and declared 'it counts because I'm deciding it counts'. That sentence is further than any metric.",
        "Engagement fragile but real. Attendance micro-goals holding. Monitor.",
    ),
    (
        "marcus",
        "Ava's checking went from seven to three and she apologised for taking session time. We did work on that too.",
        "ERP rung 4 with solid habituation. Reassurance fasting next. Twin ally engaged.",
    ),
    (
        "cel",
        "Noa brought her pump data to session like a tiny anxious accountant. Fourteen management tasks a day, counted. We turned burnout from a character flaw into a job description. Something unclenched.",
        "Diabetes distress reframed as labour overload. CGM upgrade pathway opened.",
    ),
    (
        "cel",
        "Mei's evidence-for-me list had nine items and she argued with every one. Then she did the mirror audit once instead of five and left early to choreograph. The room felt lighter.",
        "Body-check 5→1. Phone relocation agreed. Sleep trial adherence moderate.",
    ),
    (
        "cel",
        "Wren explained echolalia to a classmate like a lecture and he just said 'oh cool'. That's the whole inclusion agenda in eleven seconds.",
        "Peer acceptance event logged. Sensory accommodations generalising. Improving.",
    ),
    (
        "cel",
        "Poppy called her horse Biscuit 'the only one who doesn't care if I'm popular'. Equine-assisted, she says, or just Biscuit. Filed under both.",
        "Friendship scripts trialled. First-course engagement strong.",
    ),
    (
        "cel",
        "Josh answered the 'what is the smoke FOR' question after a full session of silence: 'it pauses the house'. Then he found his own alternative and it worked 60% of the time. That's how change actually looks.",
        "Use 5→2/week client-counted. Truce with mother held. Resit scheduled.",
    ),
    (
        "marcus",
        "Dante showed me his replay data unprompted. 'That's me not having fun for three hours.' Insight like that doesn't need my help, just my calendar.",
        "Own-data lever identified. Sleep anchor keystone agreed. Fluctuating, engaged.",
    ),
    (
        "marcus",
        "Samir drew the old street with every balcony correct, then apologised for the grammar in his journal. I told him the drawings have no grammar. He smiled with his whole face.",
        "Memory drawings as containment working. News-trigger protocol in place.",
    ),
    (
        "marcus",
        "Tessa's nightmare man bought a ferry ticket. She was smug about it. Smug is the best affect I've seen from her in weeks.",
        "Lucid conversion formalised. Sleep efficiency 74%. Improving within fluctuating.",
    ),
    (
        "marcus",
        "Caleb read his flat-viewing letter in session and his hands shook. Then he showed me the shoebox. Everything balanced to the pound. The system didn't make him soft; it made him exact.",
        "Housing pathway live. Identity shift visible. Stable, upward.",
    ),
    (
        "marcus",
        "Gabe said the nurse called him 'dad' and meant it, and he had to look at the floor for a second. Then he showed me a video of Sofia pointing at the whole flat with one arm.",
        "Role strain normalised. Coursework windows protected. Improving.",
    ),
]
for who, content, summary in REFLECTIONS:
    db.add(
        PsychJournalEntry(
            psychologist_username=who,
            raw_content=content,
            summary=summary,
            ai_source=RNG.choice(["ollama", "groq"]),
            emotions=RNG.choice(["reflective, encouraged", "thoughtful, moved", "tired but hopeful"]),
            timestamp=days_ago(RNG.randint(0, 30), RNG.randint(18, 22)),
        )
    )
db.commit()
print(f"  {len(REFLECTIONS)} psych journal reflections")

# ── NOTIFICATIONS ───────────────────────────────────────────────────
notif_count = 0
for c in CLIENTS:
    notifs = [
        (
            "Welcome to Sentinel",
            f"Hi {c['name'].split()[0]}, your care space is ready. Your clinician is Dr. {c['psych'].capitalize()}.",
            "system",
            360,
        ),
        ("Booking Approved", "Your upcoming session has been confirmed. Check Bookings for the time.", "info", 3),
        ("Follow-up Graded", "Dr. reviewed your completed task — feedback is waiting in Follow-Ups.", "info", 5),
        ("Mood Streak", "You've logged your mood 7 days straight. Consistency is quiet progress.", "system", 7),
        (
            "New coping tool",
            "The Skills Toolbox now has box breathing — try it before your next session.",
            "reminder",
            2,
        ),
    ]
    for title, msg, ntype, days in notifs:
        db.add(
            Notification(
                patient_username=c["u"],
                title=title,
                message=msg,
                notification_type=ntype,
                sent_at=days_ago(days, RNG.randint(8, 20)),
            )
        )
        notif_count += 1
    # psych notifications
for psych in ["cel", "marcus"]:
    psych_notifs = [
        ("Crisis drill complete", "Escalation chain tested end-to-end. All channels green.", "system", 12),
        ("New client note", "A client submitted a journal flagged for review — check Triage.", "info", 1),
        ("Clinic admin update", "Sam added new clinic reporting to the Admin Console.", "info", 4),
    ]
    for title, msg, ntype, days in psych_notifs:
        db.add(
            Notification(
                patient_username=psych,
                title=title,
                message=msg,
                notification_type=ntype,
                sent_at=days_ago(days, RNG.randint(9, 19)),
            )
        )
        notif_count += 1
db.commit()
print(f"  {notif_count} notifications")

# ── CRISIS HISTORY (resolved, realistic) ────────────────────────────
CRISIS_EVENTS = [
    (
        "maya_k",
        41,
        [("triggered", "self"), ("acknowledged", "cel"), ("resolved", "cel")],
        "Exam-week panic spiral; acknowledged in 2 min, resolved same evening.",
    ),
    (
        "luna_r",
        120,
        [
            ("triggered", "self"),
            ("trustee_notified", "system"),
            ("trustee_acknowledged", "trustee_portal"),
            ("resolved", "marcus"),
        ],
        "Urge surge after family contact; foster carer responded, video call de-escalated.",
    ),
    (
        "theo_b",
        200,
        [("triggered", "self"), ("acknowledged", "cel"), ("resolved", "cel")],
        "Bad night after uni talk; acknowledged quickly, safety plan reviewed.",
    ),
    (
        "omar_h",
        75,
        [("triggered", "self"), ("trustee_notified", "system"), ("resolved", "marcus")],
        "Fire alarm drill at school; escalated briefly, resolved with grounding call.",
    ),
    (
        "jasper_l",
        150,
        [("triggered", "self"), ("acknowledged", "marcus"), ("resolved", "marcus")],
        "Sunday Fear + alcohol regret spiral; phone session same morning.",
    ),
]
for patient, d, events, details in CRISIS_EVENTS:
    for ev, src in events:
        db.add(
            CrisisLog(
                event=ev, patient=patient, timestamp=days_ago(d, RNG.randint(14, 23)), source=src, details=details
            )
        )
# some patients have never had a crisis — that's realistic too
db.commit()
print(f"  crisis history: {len(CRISIS_EVENTS)} episodes (all resolved)")

# ── TRIAGE ENTRIES ──────────────────────────────────────────────────
t_count = 0
PRIORITY_MAP = {
    "fluctuating": ("high", RNG.randint(7, 9)),
    "stable": ("medium", RNG.randint(4, 6)),
    "improving": ("low", RNG.randint(2, 4)),
}
for c in CLIENTS:
    for k in range(3):
        pr, score = PRIORITY_MAP[c["traj"]]
        if k > 0:
            pr, score = RNG.choice(list(PRIORITY_MAP.values()))
            pr, score = pr, score if isinstance(score, int) else score
        db.add(
            TriageEntry(
                id=str(uuid.uuid4()),
                patient_username=c["u"],
                assessed_by=c["psych"],
                priority=pr,
                urgency_score=min(10, score + RNG.randint(-1, 1)),
                suggestion=f"{'Schedule within 48h' if pr == 'high' else 'Routine review' if pr == 'medium' else 'Monitor'} — {c['presenting'].lower()}",
                reasoning=f"Journal affect {RNG.choice(['low', 'anxious', 'mixed', 'improving'])}; mood trend {c['traj']}; ring stress index {RNG.randint(30, 70)}.",
                recent_mood=RNG.choice(["anxious", "low", "okay", "good"]),
                bpm=RNG.randint(58, 92),
                stress=RNG.randint(20, 70),
                status="closed" if k < 2 else "open",
                created_at=days_ago(RNG.randint(1, 40), 8),
                assessed_at=days_ago(RNG.randint(1, 40), 8),
            )
        )
        t_count += 1
db.commit()
print(f"  {t_count} triage assessments")

# ── SENSOR READINGS + PHYSIO SIGNALS (subset for tables) ────────────
s_count = 0
for c in CLIENTS:
    bpm0 = BASELINES[c["u"]][0]
    for d in range(0, 60, 3):
        bpm = int(bpm0 + RNG.uniform(-7, 7))
        db.add(
            SensorReading(
                patient_username=c["u"],
                device_id=f"ring_{c['u']}",
                heart_rate=bpm,
                rmssd=round(RNG.uniform(20, 70), 1),
                sdnn=round(RNG.uniform(30, 90), 1),
                temperature=round(RNG.uniform(36.1, 37.2), 1),
                logged_at=days_ago(d, RNG.randint(6, 8)),
            )
        )
        s_count += 1
db.commit()
print(f"  {s_count} sensor readings")

# ── AI ANALYSES (linked to recent journals) ─────────────────────────
a_count = 0
for c in CLIENTS:
    rows = (
        db.query(JournalEntry)
        .filter(JournalEntry.patient_username == c["u"])
        .order_by(JournalEntry.timestamp.desc())
        .limit(8)
        .all()
    )
    for jr in rows:
        pr = "high" if c["traj"] == "fluctuating" else ("medium" if c["traj"] == "stable" else "low")
        db.add(
            AIAnalysis(
                journal_id=jr.id,
                patient_username=c["u"],
                summary_patient=jr.summary,
                summary_clinical=jr.clinical_summary,
                priority=pr,
                confidence=round(RNG.uniform(0.62, 0.95), 2),
                explanation=f"Automated triage analysis — {pr} priority based on affect and risk markers.",
                provider=RNG.choice(["rule", "ollama", "groq"]),
                model_version="1.2.0",
                prompt_version="sentinel/v2.1",
                created_at=jr.timestamp,
            )
        )
        a_count += 1
db.commit()
print(f"  {a_count} AI analyses")

# ── EMOTION RESULTS (28 emotions for recent journals) ───────────────
EMOS = [
    "admiration",
    "amusement",
    "anger",
    "annoyance",
    "approval",
    "caring",
    "confusion",
    "curiosity",
    "desire",
    "disappointment",
    "disapproval",
    "disgust",
    "embarrassment",
    "excitement",
    "fear",
    "gratitude",
    "grief",
    "joy",
    "love",
    "nervousness",
    "optimism",
    "pride",
    "realization",
    "relief",
    "remorse",
    "sadness",
    "surprise",
    "neutral",
]
e_count = 0
for c in CLIENTS:
    rows = (
        db.query(JournalEntry)
        .filter(JournalEntry.patient_username == c["u"])
        .order_by(JournalEntry.timestamp.desc())
        .limit(10)
        .all()
    )
    for jr in rows:
        weights = {e: round(RNG.uniform(0.0, 0.15), 4) for e in EMOS}
        top = RNG.sample(EMOS, 4)
        for t in top:
            weights[t] = round(RNG.uniform(0.35, 0.9), 4)
        db.add(
            EmotionResult(
                journal_id=jr.id,
                patient_username=c["u"],
                model_version="distilbert-go-v2",
                created_at=jr.timestamp,
                **weights,
            )
        )
        e_count += 1
db.commit()
print(f"  {e_count} emotion analysis results")

# ── AUDIT LOG (hash-chained, realistic admin trail) ─────────────────
audit_actions = [
    ("admin", "admin", "user.login", "INFO"),
    ("admin", "admin", "directory.view", "INFO"),
    ("admin", "admin", "export.clinical_notes", "INFO"),
    ("cel", "psychologist", "triage.created", "INFO"),
    ("cel", "psychologist", "note.saved", "INFO"),
    ("marcus", "psychologist", "triage.created", "INFO"),
    ("marcus", "psychologist", "crisis.resolved", "HIGH"),
    ("admin", "admin", "user.login", "INFO"),
]
prev = ""
aud_count = 0
for i in range(60):
    user, role, action, sev = audit_actions[i % len(audit_actions)]
    ts = days_ago(RNG.randint(0, 30), RNG.randint(8, 20))
    details = RNG.choice(["routine access", "scheduled review", "weekly oversight", "automated chain entry"])
    raw = f"{prev}|{ts}|{user}|{action}|clinic|{RNG.randint(1, 99)}|success|{details}|{sev}"
    import hashlib

    cur = hashlib.sha256(raw.encode()).hexdigest()
    db.add(
        AuditLog(
            timestamp=ts,
            user=user,
            role=role,
            action=action,
            resource="clinic",
            resource_id=str(RNG.randint(1, 99)),
            severity=sev,
            status="success",
            ip="127.0.0.1",
            details=details,
            prev_hash=prev,
            curr_hash=cur,
        )
    )
    prev = cur
    aud_count += 1
db.commit()
print(f"  {aud_count} hash-chained audit entries")

# ── EVENT STORE ─────────────────────────────────────────────────────
EVENT_TYPES = [
    "journal.created",
    "mood.logged",
    "booking.approved",
    "followup.graded",
    "crisis.triggered",
    "note.saved",
    "user.login",
]
seq = 1
ev_count = 0
for i in range(120):
    c = RNG.choice(CLIENTS)
    et = RNG.choice(EVENT_TYPES)
    ts = days_ago(RNG.randint(0, 60), RNG.randint(6, 22))
    db.add(
        EventRecord(
            event_type=et,
            aggregate_type="patient",
            aggregate_id=c["u"],
            payload=json.dumps({"user": c["u"], "seed": True}),
            extra_metadata="{}",
            sequence=seq,
            created_at=ts,
        )
    )
    seq += 1
    ev_count += 1
db.commit()
print(f"  {ev_count} event-sourced records")

# ── CRISIS STATE RESET ──────────────────────────────────────────────
for cs in db.query(CrisisState).filter(CrisisState.active == 1).all():
    cs.active = 0
    cs.patient_username = ""
db.commit()

# ── CLEAR ALL LOGIN LOCKOUTS ──────────────────────────────
# A fresh demo should never start with accounts locked from earlier failed logins.
locked = 0
for u in db.query(User).all():
    if u.locked_until or (u.failed_attempts or 0) > 0:
        u.locked_until = ""
        u.failed_attempts = 0
        locked += 1
db.commit()
if locked:
    print(f"  cleared login lockouts on {locked} account(s)")

# ── SESSION REPORTS (structured one-page reports, 10-12 per client) ─
REPORT_TYPES = [
    "Intake",
    "Review",
    "Skills session",
    "Review",
    "Telehealth",
    "Review",
    "Skills session",
    "Review",
    "Crisis follow-up",
    "Review",
    "Planning",
]

REPORT_RISK = {
    "luna_r": "Moderate–low. No incidents this week; urges peaked 6/10 and were managed with the drawing displacement technique. Safety plan reviewed and current; foster placement stable.",
    "ivy_c": "Moderate. Eating-disorder voice active under performance pressure; weight stable per nutritionist, meal plan adhered to. Monitor closely; dietitian liaison in place.",
    "theo_b": "Moderate–low. Attendance below target but improved; no SI expressed. School-refusal risk monitored weekly with college transition plan in place.",
    "omar_h": "Moderate–low. Nightmare frequency down, flashbacks shortening. No current safety concerns; site-visit exposures supervised and graded.",
    "josh_o": "Low–moderate. Cannabis use functional pattern, not dependence. No risk indicators; motivation fragile, peer network monitored.",
    "rue_d": "Low. Dysphoria distress without self-harm ideation. Family acceptance split is the stressor; school register validation protective.",
}

REPORT_HOMEWORK = {
    "maya_k": [
        "One thought record daily",
        "Worry-postponement log each evening",
        "Box breathing before each exam paper",
        "Colour-code the revision plan, then follow it once",
    ],
    "dev_p": [
        "Two conversation reps at chess club",
        "Script one slide, then speak without it once",
        "Commit one 'unrequested refactor' to memory for next session",
        "Post once in the bot server voice chat",
    ],
    "luna_r": [
        "Sketch when urges rise — ink count, not scar count",
        "Write one slam poem stanza about belonging",
        "Use the grounding card before bed",
        "Bring one drawing to show me",
    ],
    "theo_b": [
        "One creative-writing block (400 words counts)",
        "Attend two lessons that aren't last period",
        "Paddington rewatch allowed — note the mood before and after",
        "Text dad one sentence about the week",
    ],
    "ava_s": [
        "ERP rung practice daily, log habituation time",
        "Checking tally — no apologising to the tally",
        "One octopus fact researched as reward",
        "Reassurance fast with mum, one hour",
    ],
    "jayden_w": [
        "Gym on the hard days, not just the good ones",
        "One coaching session with the under-8s — stay present",
        "Write the birthday letter, unsend-able is fine",
        "Say 'I'm good' once and then say the real thing",
    ],
    "zoe_m": [
        "Interoceptive exposure exercise daily",
        "Narrate one panic like a stage play — then curtain-fall breath",
        "Beta-blocker as prescribed, zero guilt",
        "Run one audition piece for me next week",
    ],
    "eli_n": [
        "Read aloud to mum 1:1, twice",
        "Add one rock to the collection and tell me its story",
        "Train-spotting log — days rated honestly",
        "Practise the brave-voice recording",
    ],
    "sana_i": [
        "Sleep protocol before midnight, 5 of 7 nights",
        "One diary entry in the Urdu diary, protected",
        "Draft the university email — send only when ready",
        "Delegate one household task, deliberately",
    ],
    "kai_t": [
        "Visualization rehearsal before each training",
        "Trust-the-repair leg work, logged",
        "One 'who am I without the boots' journal entry",
        "Sleep before midnight on school nights",
    ],
    "ivy_c": [
        "Duck protocol once daily — enoughness, not numbers",
        "One meal eaten for pleasure, not plan",
        "Mirror audit limited to once",
        "Note the ballet voice vs the real voice",
    ],
    "omar_h": [
        "Nightmare map on waking — brief, just words",
        "One planned exit rehearsed, one skipped on purpose",
        "Minecraft rebuild: the fourth stair",
        "Practice the fire-alarm story once, out loud",
    ],
    "rue_d": [
        "Playlist for the hard afternoons",
        "Draft-15 text — no send required",
        "One outfit chosen for the mirror, not the register",
        "Journal the father ambivalence, unedited",
    ],
    "finn_o": [
        "Emotion card used at the spark, not after",
        "Invention project: 30 minutes, timed",
        "Recovery-time self-measurement (the 4-minute stat)",
        "One homework started before 6pm",
    ],
    "noor_a": [
        "Far-door entry without apology",
        "One astronomy club session — stay the whole time",
        "Star journal: Hiba's star visible Thursday",
        "Practise the 'that's not okay' sentence",
    ],
    "jasper_l": [
        "Sober Saturday — one, this month, logged",
        "Drive to one event using the own-car strategy",
        "The Fear tracker: number, no story",
        "One garage hour with Ken",
    ],
    "amara_j": [
        "Counter-pressure technique on every needle-adjacent event",
        "One paramedic-radio question researched",
        "Faint-free streak calendar — keep it honest",
        "CV line about the ambulance open day",
    ],
    "leo_f": [
        "Rest day prescribed — non-negotiable, logged",
        "One thought record on 'one A ruins everything'",
        "The quiet hour: no clock, no split times",
        "One rowing-free social plan",
    ],
    "priya_g": [
        "Pre-planning card in the school bag",
        "One gate-hug saved for after school",
        "Cardamom bun ritual with grandma, twice",
        "Journal one 'I handled it' moment",
    ],
    "tyler_k": [
        "Applications: one per session, that's all",
        "Elvis the van: one hour of honest work",
        "Sleep by 1am, ranked games after — never before",
        "One mate contact, phone not text",
    ],
    "noa_b": [
        "Autopilot audit — recount the daily tasks",
        "CGM question written for the nurse",
        "One management task handed to mum",
        "Humour log — what actually helped",
    ],
    "dante_m": [
        "Phone outside room, every night — the keystone",
        "One replay with the fun-check question",
        "One IRL group invite, low stakes",
        "Father script rehearsed once",
    ],
    "wren_h": [
        "A3 city: add one street from memory",
        "Communication book entry daily",
        "One echolalia moment shared, if it comes",
        "Staff-bathroom route, no explanations owed",
    ],
    "gabe_d": [
        "Coursework window protected: 8–10pm",
        "One nap before coursework, not after midnight",
        "Sofia bedtime story — non-negotiable",
        "UCAS deferral email drafted",
    ],
    "mei_l": [
        "Mirror audit once daily, evidence list in hand",
        "Phone charges outside the bedroom",
        "Dance for art, once, camera off",
        "Sleep restriction log, honest numbers",
    ],
    "samir_b": [
        "Memory drawing: the balcony, correct count",
        "News-trigger: leave the room, one breath, return",
        "One heritage word used with pride, aloud",
        "Cousins' call on Sunday",
    ],
    "poppy_a": [
        "Biscuit time as regulation, formally scheduled",
        "One friendship script trialled for real",
        "Breathing tool at the wobble — note the drop",
        "Card sort with mum: the body-changes deck",
    ],
    "caleb_j": [
        "Flat checklist: Thursday viewing prep",
        "One receipt reconciled — competence, not survival",
        "Cook one house meal, own recipe choice",
        "Message Tanya once, just to say the week",
    ],
    "tessa_w": [
        "Sleep restriction protocol, adherence logged",
        "Nightmare conversion: ferry ticket technique",
        "20-minute rule — out of bed, no doom-rolling",
        "Chart for the teacher meeting",
    ],
    "josh_o": [
        "Pause-button alternative trialled, 60% target",
        "One brother's match attended, fully present",
        "Mother truce: hold the terms, note the wobble",
        "Resit revision: 25 minutes, timer visible",
    ],
}

REPORT_PLAN = {
    "improving": [
        "Continue current protocol; consolidate gains before adding load.",
        "Progress reviewed — next: raise the exposure rung; client in agreement.",
        "Generalisation check in two weeks; school accommodations letter if trend holds.",
        "Taper session frequency if the fortnight stays steady.",
    ],
    "fluctuating": [
        "Hold protocol; log the wobble triggers for pattern-mapping.",
        "Continue; monitor closely given the variable trajectory.",
        "Review coping-tool effectiveness; adjust the plan rather than the client.",
        "Keep fortnightly review; crisis plan remains current.",
    ],
    "stable": [
        "Maintain gains; protect the routine that is working.",
        "Steady — next review as scheduled; no protocol change.",
        "Reinforce supports; client to flag early warning signs.",
        "Consider graduation criteria discussion next block.",
    ],
}

report_count = 0
for c in CLIENTS:
    first = c["name"].split()[0]
    n_reports = RNG.randint(10, 12)
    risk_default = f"Low. No SI, no self-harm ideation expressed this session; protective factors solid ({c['spark'].split(';')[0].strip().lower()} remains a genuine anchor)."
    for i in range(n_reports):
        past = 330 - i * RNG.randint(24, 30)
        if past < 1:
            past = RNG.randint(1, 6)
        sdate = days_ago(past, RNG.randint(9, 17))[:10]
        stype = REPORT_TYPES[i % len(REPORT_TYPES)]
        dur = 80 if stype == "Intake" else (30 if stype == "Telehealth" else 50)
        phase = "early" if i < 3 else ("mid" if i < 7 else "late")
        hw_pool = REPORT_HOMEWORK[c["u"]]
        plan_pool = REPORT_PLAN[c["traj"]]
        presenting = c["presenting"]
        if phase == "early":
            concerns = f"{presenting}. {first} attended with {'clear goals from the first session' if i == 0 else 'growing clarity about what to work on'}; history taken collaboratively."
            mse = f"Presentation consistent with referral. Mood: {RNG.choice(['constricted but reachable', 'guarded, brightened with rapport', 'flat on arrival, lifted by end'])}. Affect: {RNG.choice(['restricted, congruent', 'reactive when engaged', 'wary, thawing'])}. Speech: {RNG.choice(['measured', 'quiet but fluent', 'halting, then flowing'])}. Cognition: alert and oriented; insight {'emerging' if i < 2 else 'developing well'}."
            interventions = clinical_note(c, i)
            progress = f"Baseline established. {'Engagement strong — therapy alliance forming faster than typical.' if i == 0 else 'First skills introduced; client willing to practise between sessions.'}"
        elif phase == "mid":
            concerns = f"{presenting} — frequency/intensity under active review this week."
            mse = f"Mood: {RNG.choice(['brighter than last block', 'variable but manageable', 'steadier week-on-week'])}. Affect: {RNG.choice(['fuller range emerging', 'congruent, warmer', 'lighter when discussing strengths'])}. Speech: {RNG.choice(['fluent, engaged', 'animated on progress topics'])}. Cognition: alert; insight {'good — links own patterns without prompting' if c['traj'] != 'fluctuating' else 'good on good days, thinner under stress'}"
            interventions = clinical_note(c, i)
            progress = RNG.choice(
                [
                    f"Measurable movement since session {i}: client-reported severity down; skills used in the wild, not just in here.",
                    f"Consistent fortnight. {first} brought own data/examples unprompted — a strong prognostic sign.",
                    "One setback processed without cascade — the skill is holding under load.",
                ]
            )
        else:
            concerns = f"{presenting} — consolidation phase; residual symptoms monitored."
            mse = f"Mood: {RNG.choice(['settled, optimistic about the plan', 'steady, future-focused', 'good humour, realistic'])}. Affect: congruent and flexible. Speech: fluent. Cognition: alert; insight {'strong — can articulate the maintenance cycle and their exit from it' if c['traj'] == 'improving' else 'solid, with support for the shaky weeks'}"
            interventions = clinical_note(c, i)
            progress = RNG.choice(
                [
                    f"Trend across the block is {'clearly upward' if c['traj'] == 'improving' else 'the right kind of uneven — dips are shallower, recovery faster' if c['traj'] == 'fluctuating' else 'steady — maintenance is the achievement'}. Client can name what works and why.",
                    "Relapse-signature drafted together — client knows their first three warning signs and the matched responses.",
                ]
            )
        homework = f"{hw_pool[i % len(hw_pool)]}; plus {hw_pool[(i + 1) % len(hw_pool)].lower()}."
        plan = plan_pool[i % len(plan_pool)]
        title = f"{'Initial assessment' if stype == 'Intake' else stype} — {'week ' + str((i + 1) * 4) if stype != 'Intake' else 'session 1'}"
        db.add(
            SessionReport(
                psychologist_username=c["psych"],
                patient_username=c["u"],
                session_date=sdate,
                session_type=stype,
                duration_min=dur,
                title=title,
                presenting_concerns=concerns,
                mental_state=mse,
                interventions=interventions,
                risk_assessment=REPORT_RISK.get(c["u"], risk_default),
                progress_note=progress,
                homework=homework,
                plan=plan,
                clinician_summary=f"{stype} · {'on track' if c['traj'] != 'fluctuating' else 'engaged, variable'} · homework set",
                created_at=days_ago(past, RNG.randint(17, 19)),
                updated_at=days_ago(past, RNG.randint(17, 19)),
            )
        )
        report_count += 1
db.commit()
print(f"  {report_count} one-page session reports ({len(CLIENTS)} clients)")

print("\n=== DONE ===")
print("  Login accounts:")
print("    admin / password123   (clinic oversight console)")
print("    cel   / 1234          (psychologist, 14 clients)")
print("    marcus / 4321         (psychologist, 16 clients)")
print(f"  Clients: {len(CLIENTS)} teens · 12 months of history each")
db.close()
