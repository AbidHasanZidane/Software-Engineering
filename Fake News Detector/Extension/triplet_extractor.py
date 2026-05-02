import spacy
import json
import os
import re

nlp = spacy.load("en_core_web_sm")

KB_FILE = "general_knowledge_base.json"

# ---------------------------------------------------
# BAD WORD FILTERS
# ---------------------------------------------------
BAD_SUBJECTS = {
    "he", "she", "it", "they",
    "his", "her", "their",
    "them", "him", "its",
    "this", "that", "these",
    "those", "which", "who",
    "whom", "whose"
}

BAD_OBJECTS = BAD_SUBJECTS.copy()

BAD_PATTERNS = {
    "related articles",
    "click here",
    "read more",
    "follow us",
    "copyright",
    "advertisement"
}


# ---------------------------------------------------
# LOAD / SAVE KB
# ---------------------------------------------------
def load_kb():

    if os.path.exists(KB_FILE):

        with open(KB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return {"triplets": []}


def save_kb(kb):

    with open(KB_FILE, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2)


kb = load_kb()


# ---------------------------------------------------
# CLEANING HELPERS
# ---------------------------------------------------
def normalize_text(text):

    text = re.sub(r"\s+", " ", text)

    return text.strip()

def normalize_predicate(pred):
    pred = pred.lower().strip()

    NORMALIZATION = {
        "is": "be",
        "are": "be",
        "was": "be",
        "were": "be",

        "has": "have",
        "had": "have",

    }

    return NORMALIZATION.get(pred, pred)

def get_full_span(token):

    # reject pronouns immediately
    if token.pos_ == "PRON":
        return None

    parts = []

    for t in token.subtree:

        # stop runaway subtree growth
        if t.dep_ in ["relcl", "acl", "advcl"]:
            break

        # remove junk
        if t.dep_ in [
            "punct",
            "cc",
            "mark",
            "det"
        ]:
            continue

        # reject pronouns inside subtree
        if t.pos_ == "PRON":
            continue

        parts.append(t.text)

    phrase = " ".join(parts)

    phrase = normalize_text(phrase)

    if len(phrase) < 2:
        return None

    # reject huge nonsense chunks
    if len(phrase.split()) > 10:
        return None

    return phrase


def is_negated(token):

    if token.dep_ == "neg":
        return True

    for child in token.children:
        if child.dep_ == "neg":
            return True

    return False


def clean_triplet(triplet):

    s = normalize_text(triplet["subject"].lower())
    p = normalize_text(triplet["predicate"].lower())
    o = normalize_text(triplet["object"].lower())

    # empty check
    if not s or not p or not o:
        return None

    # pronoun rejection
    if s in BAD_SUBJECTS:
        return None

    if o in BAD_OBJECTS:
        return None

    # possessive junk
    if s.endswith("'s"):
        return None

    if o.endswith("'s"):
        return None

    # absurd lengths
    if len(s.split()) > 8:
        return None

    if len(o.split()) > 12:
        return None

    # reject noisy text
    for bp in BAD_PATTERNS:

        if bp in s:
            return None

        if bp in o:
            return None

    return {
        "subject": s,
        "predicate": p,
        "object": o
    }


# ---------------------------------------------------
# MAIN EXTRACTION
# ---------------------------------------------------
def extract_triplets_general(text):

    doc = nlp(text)

    triplets = []
    negated_triplets = []

    # ---------------------------------------------------
    # VERB RELATIONS
    # ---------------------------------------------------
    for token in doc:

        if token.pos_ != "VERB" and not (
            token.pos_ == "AUX" and token.dep_ == "ROOT"
        ):
            continue

        subj = None
        obj = None

        # -----------------------------
        # SUBJECT
        # -----------------------------
        for child in token.children:

            if child.dep_ in ["nsubj", "nsubjpass"]:

                subj = get_full_span(child)

                if subj:
                    break

        # -----------------------------
        # OBJECT
        # -----------------------------
        for child in token.children:

            if child.dep_ in ["dobj", "attr"]:

                obj = get_full_span(child)

                if obj:
                    break

            # prepositional objects
            if child.dep_ == "prep":

                prep = child.lemma_

                for grand in child.children:

                    if grand.dep_ == "pobj":

                        pobj = get_full_span(grand)

                        if pobj:

                            obj = f"{prep} {pobj}"

                            break

                if obj:
                    break

        # -----------------------------
        # BUILD TRIPLET
        # -----------------------------
        if subj and obj:

            triplet = {
                "subject": subj,
                "predicate": token.lemma_,
                "object": obj
            }

            cleaned = clean_triplet(triplet)

            if cleaned:

                if is_negated(token):
                    negated_triplets.append(cleaned)
                else:
                    triplets.append(cleaned)

    # ---------------------------------------------------
    # COPULA RELATIONS
    # ---------------------------------------------------
    for token in doc:

        if token.lemma_ not in [
            "be",
            "become",
            "seem",
            "appear"
        ]:
            continue

        subj = None
        obj = None

        for child in token.children:

            if child.dep_ in ["nsubj", "nsubjpass"]:
                subj = get_full_span(child)

            if child.dep_ in ["attr", "acomp"]:
                obj = get_full_span(child)

        if subj and obj:

            triplet = {
                "subject": subj,
                "predicate": token.lemma_,
                "object": obj
            }

            cleaned = clean_triplet(triplet)

            if cleaned:

                if is_negated(token):
                    negated_triplets.append(cleaned)
                else:
                    triplets.append(cleaned)


    for token in doc:

        if token.dep_ != "poss":
            continue

        # reject pronouns
        if token.pos_ == "PRON":
            continue

        if token.text.lower() in BAD_SUBJECTS:
            continue

        if token.head.pos_ != "NOUN":
            continue

        owner = get_full_span(token)
        possessed = get_full_span(token.head)

        if not owner or not possessed:
            continue

        triplet = {
            "subject": owner,
            "predicate": "has",
            "object": possessed
        }

        cleaned = clean_triplet(triplet)

        if cleaned:
            triplets.append(cleaned)

    unique = []
    seen = set()

    for t in triplets:

        key = (
            t["subject"],
            t["predicate"],
            t["object"]
        )

        if key not in seen:
            seen.add(key)
            unique.append(t)

    triplets = unique


    if not triplets and not negated_triplets:
        triplets = extract_with_patterns(text)

    return triplets, negated_triplets



def extract_with_patterns(text):

    triplets = []

    matches = re.findall(
        r'(\b[\w\s]+\b)\s+'
        r'(is|are|was|were|becomes|seems)\s+'
        r'(\b[\w\s]+\b)',
        text,
        re.IGNORECASE
    )

    for m in matches:

        triplet = {
            "subject": m[0].strip().lower(),
            "predicate": m[1].lower(),
            "object": m[2].strip().lower()
        }

        cleaned = clean_triplet(triplet)

        if cleaned:
            triplets.append(cleaned)

    return triplets



def compare_with_kb(triplets, negated_triplets):

    results = {
        "matches": [],
        "contradictions": [],
        "unknown": []
    }

    for t in triplets:

        exact = any(
            t["subject"] == kt["subject"] and
            t["predicate"] == kt["predicate"] and
            t["object"] == kt["object"]
            for kt in kb["triplets"]
        )

        if exact:
            results["matches"].append(t)
            continue

        contra = None

        for kt in kb["triplets"]:

            if (
                t["subject"] == kt["subject"] and
                t["predicate"] == kt["predicate"] and
                t["object"] != kt["object"]
            ):
                contra = {
                    "claimed": t,
                    "known": kt
                }
                break

        if contra:
            results["contradictions"].append(contra)
        else:
            results["unknown"].append(t)

    # negation contradiction
    for nt in negated_triplets:

        for kt in kb["triplets"]:

            if (
                nt["subject"] == kt["subject"] and
                nt["predicate"] == kt["predicate"] and
                nt["object"] == kt["object"]
            ):
                results["contradictions"].append({
                    "claimed_negated": nt,
                    "known": kt
                })

                break

    return results


def add_triplet_to_kb(triplet):

    subject = triplet["subject"]
    predicate = normalize_predicate(triplet["predicate"])
    triplet["predicate"] = predicate
    obj = triplet["object"]

    found_index = None

    for i, existing in enumerate(kb["triplets"]):

        if (
            existing["subject"] == subject and
            existing["predicate"] == predicate
        ):
            found_index = i
            break

    # update existing
    if found_index is not None:

        if kb["triplets"][found_index]["object"] != obj:

            kb["triplets"][found_index] = triplet

            save_kb(kb)

            return True

        return False

    # add new
    if triplet not in kb["triplets"]:

        kb["triplets"].append(triplet)

        save_kb(kb)

        return True

    return False


def add_text_to_kb(text):

    triplets, neg = extract_triplets_general(text)

    added_or_updated = []

    for t in triplets:

        if add_triplet_to_kb(t):
            added_or_updated.append(t)

    return added_or_updated

def get_kb():
    return kb
