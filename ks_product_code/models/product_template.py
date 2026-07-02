# -*- coding: utf-8 -*-
import logging
import math
import re
import time
from odoo import models, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Hard ceiling on generated internal references (including hyphens).
MAX_REF_LENGTH = 24

# ── Attribute-name keywords ─────────────────────────────────────────────── #
# Matched against the *lowercase* attribute name.

# Colour: any attribute whose name contains one of these words is the
# COLOUR segment regardless of value.
_COLOUR_ATTR_KEYWORDS = frozenset({
    'colour', 'color', 'shade', 'finish', 'hue', 'tint', 'tone',
})

# Type: only meaningful for the Toner & Inks category path.
# "Box Type", "Print Type", "Printer Type" all contain "type" — but they must
# NOT be routed to the type segment for non-toner products (they would be
# silently dropped there).  The `is_toner` guard in _extract_attr_segments
# ensures this keyword is checked only for toner products.
_TYPE_ATTR_KEYWORDS = frozenset({'type'})

# ── Value-word colour fallback ───────────────────────────────────────────── #
# When the attribute NAME doesn't contain any colour keyword, check whether
# the attribute VALUE contains a known colour word.  This handles attribute
# names like "Style", "Appearance", "Variant", or unnamed spec fields where
# the value is obviously a colour ("Natural Titanium", "Phantom Black", etc.).
_KNOWN_COLOUR_WORDS = frozenset({
    # Neutrals / metals
    'BLACK', 'WHITE', 'SILVER', 'GOLD', 'GRAPHITE', 'TITANIUM',
    'BRONZE', 'COPPER', 'CHROME', 'PLATINUM',
    # Apple palette
    'MIDNIGHT', 'STARLIGHT', 'NATURAL', 'ALPINE', 'SIERRA',
    'PRODUCT',                          # "Product Red"
    # Samsung / Android palette
    'PHANTOM', 'MYSTIC', 'PRISM', 'AURORA', 'CLOUD', 'CREAM',
    'LAVENDER', 'MINT', 'BORA',         # "Bora Purple"
    # Common colours
    'BLUE', 'RED', 'GREEN', 'PINK', 'PURPLE', 'YELLOW', 'ORANGE',
    'GREY', 'GRAY', 'BROWN', 'BEIGE', 'IVORY', 'NUDE', 'BLUSH',
    'TEAL', 'CORAL', 'ROSE', 'NAVY', 'MAROON', 'VIOLET', 'MAGENTA',
    'CYAN', 'TURQUOISE', 'LIME', 'INDIGO', 'SAND', 'STONE', 'SLATE',
    'MIST', 'DUSK', 'DAWN', 'DESERT', 'MARINE', 'STORM', 'OLIVE',
    'SAGE', 'SPACE',
})

# ── Colour "not applicable" values ──────────────────────────────────────── #
# Colour attribute values that mean "no colour applies".  When matched, the
# colour segment is omitted from the generated reference rather than
# producing a misleading "NOT" or "NA" code component.
_COLOUR_NA_VALUES = frozenset({
    'NOTAPPLICABLE', 'NA', 'NONE', 'NIL', 'NULL', 'NO',
})

# ── Verbose-prefix pattern ───────────────────────────────────────────────── #
# Some attribute values begin with a meaningless filler phrase that obscures
# the numeric value (e.g. "Up to 100MB/s Read" → useful part is "100MB").
# These prefixes are stripped before abbreviation.
_VERBOSE_PREFIX = re.compile(
    r'^(UP\s*TO\s*|UP-TO\s*|AT\s+LEAST\s*|MAX\s*\.?\s*|MIN\s*\.?\s*)',
    re.IGNORECASE,
)


# ── Abbreviation helpers ─────────────────────────────────────────────────── #

def _normalize_value(text):
    """
    Strip verbose English prefixes that obscure the numeric content of a
    value before abbreviation.

        "Up to 100MB/s Read"  →  "100MBS READ"  →  _abbreviate → "100MB"
        "Up to 120MB/s Read"  →  "120MBS READ"  →  _abbreviate → "120MB"
        "At least 16 GB"      →  "16 GB"         →  _abbreviate → "16GB"
        "256 GB"              →  "256 GB"         (unchanged)
        "Master Carton"       →  "MASTER CARTON"  (unchanged)
    """
    cleaned = re.sub(r'[^A-Z0-9 ]', '', text.upper()).strip()
    return _VERBOSE_PREFIX.sub('', cleaned).strip()


def _abbreviate(text, max_len):
    """
    Strip non-alphanumeric characters, uppercase, take first ``max_len`` chars.

        "Mobile Phone"  → MOB     (MOBILEPHONE[:3])
        "Toner & Inks"  → TON
        "Samsung"       → SAM
        "256 GB"        → 256GB   (256GB[:5])
        "Master Carton" → MAS     (MASTERCARTON[:3])
        "Ink Bottle"    → INK
        "Laser"         → LAS
    """
    return re.sub(r'[^A-Z0-9]', '', text.upper())[:max_len]


def _colour_abbreviate(text, max_len=4):
    """
    Produce a ≤``max_len`` (default 4) colour code that differentiates
    multi-word colour names better than plain truncation.

    Algorithm
    ---------
    Single word  →  first ``max_len`` chars.
                    "BLACK" → "BLAC",  "BLUE" → "BLUE",  "GOLD" → "GOLD"

    Multi-word   →  first 3 chars of FIRST word  +  first 1 char of LAST word.
                    This handles the most common collision classes in the
                    product catalogue:

                    Modifer-colour names (first word is the base):
                        "PHANTOM BLACK"  → PHA+B = "PHAB"
                        "PHANTOM GREY"   → PHA+G = "PHAG"  ✓
                        "PHANTOM PURPLE" → PHA+P = "PHAP"  ✓
                        "PRISM BLACK"    → PRI+B = "PRIB"
                        "PRISM GOLD"     → PRI+G = "PRIG"  ✓
                        "PRISM SILVER"   → PRI+S = "PRIS"  ✓

                    Colour-modifier names (last word is the base):
                        "BLACK TITANIUM"   → BLA+T = "BLAT"
                        "BLUE TITANIUM"    → BLU+T = "BLUT"  ✓
                        "NATURAL TITANIUM" → NAT+T = "NATT"  ✓
                        "WHITE TITANIUM"   → WHI+T = "WHIT"  ✓
                        "DESERT TITANIUM"  → DES+T = "DEST"  ✓

    Note: "PRISM BLACK" and "PRISM BLUE" both resolve to PRI+B = "PRIB".
    3-char last-word initials cannot distinguish them.  If a product has
    both variants the intra-template check raises a ValidationError — use
    ``part_code`` to override in that case.
    """
    words = [re.sub(r'[^A-Z0-9]', '', w) for w in text.upper().split()]
    words = [w for w in words if w]
    if not words:
        return ''
    if len(words) == 1:
        return words[0][:max_len]
    first = words[0]
    last = words[-1]
    # 3 chars from first word + 1 from last word, capped at max_len
    return (first[:3] + last[:1])[:max_len]


# ── Variant segment builder ──────────────────────────────────────────────── #

def _build_variant_segment(variant_parts, max_len=4):
    """
    Combine multiple variant-attribute codes into a single ≤``max_len`` segment,
    allocating chars proportionally so every attribute contributes.

    Naive join+truncate loses information when the first attribute fills the
    slot (e.g. Storage="256GB" + RAM="12GB" both collapse to "256GB").
    This function allocates ceil(max_len / n) chars per attribute.

    Examples (max_len=4, parts already sorted by attribute name)
    -----------------------------------------------------------
    ["256G"]                        → "256G"    (1 part  → 4 each)
    ["12GB",  "256G"]  RAM+Storage  → "1225"    (2 parts → 2 each, cap 4)
    ["16GB",  "256G"]               → "1625"    ← different ✓
    ["MAS",   "256G"]  Box+Storage  → "MA25"    ← Master Carton + 256 GB
    ["LOO",   "256G"]               → "LO25"    ← Loose + 256 GB ✓ different
    ["LAS",   "256G",  "BLK"]       → "L2B"     (3 parts → 2 each, cap 4)
    """
    if not variant_parts:
        return ''
    n = len(variant_parts)
    per_part = math.ceil(max_len / n)
    return ''.join(seg[:per_part] for seg in variant_parts)[:max_len]


# ── Main model class ─────────────────────────────────────────────────────── #

class ProductTemplateInternalRef(models.Model):
    """
    Category-aware internal reference generator for product variants.

    Pattern
    -------
    Toner & Inks:   BRAND - TYPE  - MODEL  - COLOUR
    All others:     BRAND - CAT - (GRP) - MODEL - VARIANT - COLOUR

    Attribute classification (per-variant, fully automatic)
    -------------------------------------------------------
    Every product.template.attribute.value on a variant is classified into
    one of the roles below.  Classification is tried IN ORDER; the first
    matching rule wins.

    ┌──────────────┬───────────────────────────────────────────────────────┐
    │ Role         │ Rule                                                  │
    ├──────────────┼───────────────────────────────────────────────────────┤
    │ COLOUR (3)   │ 1. Attr name ∋ colour/color/shade/finish/hue/tint/tone│
    │              │ 2. Value words ∩ _KNOWN_COLOUR_WORDS ≠ ∅              │
    │              │    → handles "Natural Titanium", "Phantom Black", etc.│
    ├──────────────┼───────────────────────────────────────────────────────┤
    │ TYPE   (3)   │ Attr name ∋ "type"  AND  product is Toner & Inks only │
    │              │ For other categories this rule is SKIPPED — the value │
    │              │ falls into VARIANT instead (see note below).          │
    ├──────────────┼───────────────────────────────────────────────────────┤
    │ VARIANT (≤5) │ Everything else: Storage, RAM, Connectivity (4G/5G/  │
    │              │ WiFi/LTE), Processor/Chip, Print Type, Printer Type,  │
    │              │ Box Type (Master Carton/Loose), Display, SIM, etc.    │
    │              │ Parts are sorted by attribute name and combined with  │
    │              │ proportional char allocation.                         │
    └──────────────┴───────────────────────────────────────────────────────┘

    NOTE — why TYPE is NOT a special segment outside Toner & Inks
    ─────────────────────────────────────────────────────────────
    "Box Type" (Master Carton / Loose), "Print Type" (Laser / Inkjet), and
    "Printer Type" all contain the word "type".  Treating them as a TYPE
    segment for non-toner products would silently discard the value (the
    TYPE slot is only present in the Toner pattern).  Instead, they go to
    VARIANT where they correctly differentiate variants.

    Uniqueness guarantee
    --------------------
    All codes are generated before any write.  Writes use context flag
    ``skip_sku_duplicate_check=True`` to suppress per-row constraint.
    A final cross-check validates intra-template and cross-product uniqueness.
    """
    _inherit = 'product.template'

    # ------------------------------------------------------------------ #
    #  Main entry-point                                                   #
    # ------------------------------------------------------------------ #

    def _generate_and_assign_sku(self):
        self.ensure_one()
        t0 = time.monotonic()

        variants = self.env['product.product'].with_context(active_test=False).search(
            [('product_tmpl_id', '=', self.id)]
        )

        if not variants:
            code = self._generate_sku(self.id)
            code = self._resolve_cross_product_conflict(code, set(), self.name)
            self.with_context(skip_sku_duplicate_check=True).default_code = code
            _logger.info(
                "[SKU-PERF] tmpl=%s '%s' single-code path took %.2fs",
                self.id, self.name, time.monotonic() - t0,
            )
            return

        # Step 1 — generate all codes first (no writes)
        t1 = time.monotonic()
        new_codes = {v.id: self._generate_sku(v.id) for v in variants}
        _logger.info(
            "[SKU-PERF] tmpl=%s '%s' step1 generate (%d variants) took %.2fs",
            self.id, self.name, len(variants), time.monotonic() - t1,
        )

        # Step 2 — intra-template collision resolution (auto-disambiguate)
        t2 = time.monotonic()
        seen = {}   # code → vid of first variant that claimed it
        for vid in list(new_codes.keys()):
            code = new_codes[vid]
            if not code:
                continue
            if code in seen:
                va = self.env['product.product'].browse(seen[code])
                vb = self.env['product.product'].browse(vid)
                if self._variants_have_same_attributes(va, vb):
                    raise ValidationError(
                        _("Variants '%(a)s' and '%(b)s' of '%(product)s' have "
                          "identical attribute values — they are duplicates. "
                          "Please remove one of them.")
                        % {'product': self.name,
                           'a': va.display_name, 'b': vb.display_name}
                    )
                new_codes[vid] = self._disambiguate_intra(
                    code, vb, set(new_codes.values())
                )
            seen[new_codes[vid]] = vid
        _logger.info(
            "[SKU-PERF] tmpl=%s '%s' step2 intra-collision took %.2fs",
            self.id, self.name, time.monotonic() - t2,
        )

        # Step 3 — cross-product collision resolution
        t3 = time.monotonic()
        taken_globally = set()
        name_words = (self.name or '').split()
        for vid in sorted(new_codes.keys()):
            code = new_codes[vid]
            if not code:
                continue
            tv = time.monotonic()
            resolved = self._resolve_cross_product_conflict(
                code, taken_globally, self.name, own_ids=list(new_codes.keys())
            )
            dtv = time.monotonic() - tv
            if dtv > 0.5:
                _logger.warning(
                    "[SKU-PERF] tmpl=%s variant=%s code=%s conflict resolution "
                    "took %.2fs -> resolved=%s",
                    self.id, vid, code, dtv, resolved,
                )
            new_codes[vid] = resolved
            taken_globally.add(resolved)
        _logger.info(
            "[SKU-PERF] tmpl=%s '%s' step3 cross-product (%d variants) took %.2fs",
            self.id, self.name, len(variants), time.monotonic() - t3,
        )

        # Step 4 — write all codes, per-row constraint suppressed
        t4 = time.monotonic()
        ctx = dict(self.env.context, skip_sku_duplicate_check=True)
        for variant in variants:
            variant.with_context(**ctx).default_code = new_codes[variant.id]
        _logger.info(
            "[SKU-PERF] tmpl=%s '%s' step4 write took %.2fs, total %.2fs",
            self.id, self.name, time.monotonic() - t4, time.monotonic() - t0,
        )

    def _disambiguate_intra(self, base_code, variant, all_codes):
        """
        Make base_code unique within all_codes by appending more attribute chars.
        Tries progressively wider prefixes of combined attribute values, then
        falls back to a numeric suffix. Raises only if tens of thousands of
        suffixes are all taken (should never happen in practice).
        """
        taken = set(all_codes) - {base_code}

        # Collect all non-colour attribute values concatenated
        frags = []
        for ptav in variant.product_template_attribute_value_ids:
            attr_name = ptav.attribute_id.name.lower().strip()
            if not self._is_colour_ptav(ptav, attr_name):
                clean = re.sub(r'[^A-Z0-9]', '', ptav.name.upper())
                if clean:
                    frags.append(clean)
        combined = ''.join(frags)

        for suffix_len in range(2, max(len(combined) + 1, 3)):
            suffix = combined[:suffix_len]
            candidate = (base_code + suffix)[:MAX_REF_LENGTH].rstrip('-')
            if candidate not in taken and candidate != base_code:
                return candidate

        # Numeric fallback. Reserve room for the suffix instead of appending
        # then truncating — if base_code is already MAX_REF_LENGTH chars,
        # truncation would silently drop the suffix and candidate would
        # never change, looping forever.
        n = 2
        while n <= 99999:
            suffix = str(n)
            candidate = (base_code[:MAX_REF_LENGTH - len(suffix)] + suffix).rstrip('-')
            if candidate not in taken:
                return candidate
            n += 1

        raise ValidationError(
            _("Could not disambiguate internal reference '%(code)s' within "
              "its own product after %(n)d attempts.") % {'code': base_code, 'n': n}
        )

    @staticmethod
    def _variants_have_same_attributes(va, vb):
        """Return True if both variants carry exactly the same attribute value ids."""
        a_vals = set(va.product_template_attribute_value_ids.mapped('product_attribute_value_id').ids)
        b_vals = set(vb.product_template_attribute_value_ids.mapped('product_attribute_value_id').ids)
        return a_vals == b_vals

    def _resolve_cross_product_conflict(self, code, taken_locally, product_name, own_ids=None):
        """
        Ensure code doesn't clash with any other product's default_code.
        Tries word fragments from product_name first, then numeric suffixes.
        Raises only if the code namespace around this prefix is saturated
        after tens of thousands of attempts (should never happen in practice).

        Every candidate we could ever try (code, code+frag, code+N) starts
        with ``code`` — so one prefix search up front fetches every
        colliding default_code that exists, and the retry loop below checks
        candidates against that in-memory set instead of issuing one DB
        round-trip per candidate. With heavy collisions (e.g. generic codes
        from products missing brand_id) the old per-candidate search could
        take hundreds of sequential round-trips per variant.
        """
        own_ids = own_ids or []
        if not code:
            return code

        t0 = time.monotonic()
        existing = self.env['product.product'].with_context(active_test=False).search(
            [('default_code', '=like', code + '%'), ('id', 'not in', own_ids)]
        ).mapped('default_code')
        taken = set(existing) | set(taken_locally)

        def _is_taken(c):
            return c in taken

        if not _is_taken(code):
            return code

        # Try word fragments from product name
        words = re.sub(r'[^A-Z0-9 ]', '', (product_name or '').upper()).split()
        for word in words:
            frag = word[:3]
            if frag and frag.upper() not in code.upper():
                candidate = (code + frag)[:MAX_REF_LENGTH].rstrip('-')
                if not _is_taken(candidate):
                    return candidate

        # Numeric fallback.
        # The suffix must always survive the MAX_REF_LENGTH truncation, or
        # the candidate never changes between iterations — reserve room for
        # it up front instead of truncating (code + suffix).
        n = 2
        while n <= 99999:
            suffix = str(n)
            candidate = (code[:MAX_REF_LENGTH - len(suffix)] + suffix).rstrip('-')
            if not _is_taken(candidate):
                if n > 20 or time.monotonic() - t0 > 0.5:
                    _logger.warning(
                        "[SKU-PERF] code=%s needed %d numeric-suffix retries "
                        "(%.2fs total, 1 batched DB search) to find a free code",
                        code, n, time.monotonic() - t0,
                    )
                return candidate
            n += 1

        # Exhausted a generous search space — surface this instead of
        # looping forever or silently returning a colliding code.
        raise ValidationError(
            _("Could not generate a unique internal reference for base code "
              "'%(code)s' after %(n)d attempts — the code namespace around "
              "this prefix is saturated.") % {'code': code, 'n': n}
        )

    def _check_cross_product_unique(self, code_map):
        # Kept for backward compatibility — no longer raises, just a no-op stub.
        pass

    # ------------------------------------------------------------------ #
    #  Per-variant SKU builder                                            #
    # ------------------------------------------------------------------ #

    def _generate_sku(self, variant_id):
        self.ensure_one()

        # Manual override
        if self.part_code:
            code = self._sanitize_ref(self.part_code)
            self._validate_ref(code)
            return code

        # Detect category BEFORE attribute extraction so the is_toner flag
        # can gate whether "type" attributes route to type_code or variant_parts.
        toner_categ = self.env.ref(
            'ks_product_master.product_category_type_toner_inks',
            raise_if_not_found=False,
        )
        is_toner = bool(
            toner_categ and self._is_category_match(self.categ_id, toner_categ)
        )

        variant = self._resolve_variant(variant_id)
        colour_code, type_code, variant_parts = self._extract_attr_segments(
            variant, is_toner=is_toner
        )

        brand = self._brand_segment()
        model = self._model_segment()

        if is_toner:
            # BRAND-TYPE-MODEL-COLOUR
            parts = [brand, type_code, model, colour_code]
        else:
            # BRAND-CAT-(GRP)-MODEL-VARIANT-COLOUR
            cat = self._cat_segment()
            grp = self._group_segment()
            variant_seg = _build_variant_segment(variant_parts, max_len=4)
            parts = [brand, cat, grp, model, variant_seg, colour_code]

        code = '-'.join(p for p in parts if p)
        self._validate_ref(code)
        return code

    # ------------------------------------------------------------------ #
    #  Attribute segment extractor                                        #
    # ------------------------------------------------------------------ #

    def _extract_attr_segments(self, variant, is_toner=False):
        """
        Classify each attribute value of *variant* into colour, type, or variant.

        Classification order (first match wins)
        ----------------------------------------
        1. COLOUR  — attr name ∋ colour keyword  OR  value ∈ known colour words
        2. TYPE    — attr name ∋ "type"  AND  is_toner=True
                     (skipped for non-toner; value goes to VARIANT instead)
        3. VARIANT — everything else

        Variant parts are sorted by attribute name for consistent ordering.

        Real-world attribute examples and their routing
        -----------------------------------------------
        Attribute name          Value            is_toner  → Route
        ─────────────────────── ──────────────── ────────  ─────────
        Color / Colour          Blue Titanium    any       COLOUR
        Shade / Finish          Midnight         any       COLOUR
        (any name)              Natural Titanium any       COLOUR  ← value fallback
        Type                    Ink Bottle       True      TYPE
        Type                    Laser            False     VARIANT
        Print Type              Inkjet           False     VARIANT
        Printer Type            Laser Colour     False     VARIANT
        Box Type                Master Carton    False     VARIANT
        Box Type                Loose            False     VARIANT
        Storage                 256 GB           any       VARIANT
        RAM                     12 GB            any       VARIANT
        Connectivity            5G / WiFi        any       VARIANT
        Network                 4G LTE           any       VARIANT
        Processor               M3 / SD8Gen2     any       VARIANT
        SIM                     Dual SIM         any       VARIANT
        Display                 6.1 inch         any       VARIANT
        """
        colour_code = ''
        type_code = ''
        raw_parts = []   # [(attr_name_str, seg_str), ...]

        if not (variant and variant.exists()):
            return colour_code, type_code, []

        for ptav in variant.product_template_attribute_value_ids:
            attr_name = ptav.attribute_id.name.lower().strip()
            # Strip verbose prefixes ("Up to", "At least" …) before abbreviating
            # so numeric values are not buried behind filler words.
            norm = _normalize_value(ptav.name)
            seg = _abbreviate(norm, 5)

            if self._is_colour_ptav(ptav, attr_name):
                # Skip N/A values so they don't inject "NOT"/"NA" into the code.
                clean_val = re.sub(r'[^A-Z0-9]', '', ptav.name.upper())
                if clean_val in _COLOUR_NA_VALUES:
                    continue
                # 4-char smarter multi-word abbreviation (last colour wins)
                colour_code = _colour_abbreviate(norm, max_len=4)

            elif is_toner and any(kw in attr_name for kw in _TYPE_ATTR_KEYWORDS):
                # TYPE segment: toner products only
                type_code = seg[:3]

            else:
                # VARIANT: storage, RAM, connectivity, box type,
                #          print type, printer type, processor, SIM, etc.
                # Use 4-char seg so _build_variant_segment stays within budget.
                raw_parts.append((attr_name, seg[:4]))

        # Sort by attribute name → identical combination always → identical code
        raw_parts.sort(key=lambda x: x[0])
        return colour_code, type_code, [seg for _, seg in raw_parts]

    # ------------------------------------------------------------------ #
    #  Colour classifier                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_colour_ptav(ptav, attr_name):
        """
        Stage 1: attribute NAME contains a colour keyword.
        Stage 2: attribute VALUE contains a known colour word.

        Stage 2 exists so that colour is detected even when the attribute is
        named "Style", "Appearance", "Variant", or any non-standard name.
        """
        if any(kw in attr_name for kw in _COLOUR_ATTR_KEYWORDS):
            return True
        value_words = set(re.sub(r'[^A-Z ]', '', ptav.name.upper()).split())
        return bool(value_words & _KNOWN_COLOUR_WORDS)

    # ------------------------------------------------------------------ #
    #  Segment builders                                                   #
    # ------------------------------------------------------------------ #

    def _brand_segment(self):
        if not self.brand_id:
            return ''
        return _abbreviate(self.brand_id.name, 3)

    def _cat_segment(self):
        if not self.categ_id:
            return ''
        return _abbreviate(self.categ_id.name, 3)

    def _model_segment(self):
        """
        Extract a ≤6-char model slug from the product name.

        Strategy 1 – mixed token (letters + digits in same token)
            Best for model codes embedded in the name.
            "Tab S6 Lite LTE SM-P615 4/64 GB"  → P615
            "Tab S6 Lite LTE SM-P619 4/64 GB"  → P619  ✓ different
            "Galaxy S24 Ultra"                  → S24
            "Canon GI490"                       → GI490
            "MacBook Air M3"                    → M3

        Strategy 2 – word immediately followed by standalone version number
            Handles "iPhone 15", "iPad 10", "Xperia 5" etc.
            Allocates 4 chars to the word + 2 to the number (total ≤ 6).
            "iPhone 15 Pro 128 GB …"  → IPHO + 15 = IPHO15
            "iPhone 14 Pro …"         → IPHO + 14 = IPHO14  ✓ different
            "iPad 10"                 → IPAD + 10 = IPAD10

        Strategy 3 – fallback: first 6 alnum chars of the full name.
        """
        name = (self.name or '').upper()
        tokens = [
            re.sub(r'[^A-Z0-9]', '', p)
            for p in re.split(r'[\s\-]+', name)
        ]
        tokens = [t for t in tokens if t]

        # Strategy 1
        for token in reversed(tokens):
            if re.search(r'[A-Z]', token) and re.search(r'[0-9]', token):
                return token[:6]

        # Strategy 2
        for i in range(len(tokens) - 1):
            alpha, nxt = tokens[i], tokens[i + 1]
            if re.fullmatch(r'[A-Z]+', alpha) and re.fullmatch(r'[0-9]+', nxt):
                num_part = nxt[:2]
                return alpha[:6 - len(num_part)] + num_part

        # Strategy 3
        return re.sub(r'[^A-Z0-9]', '', name)[:6]

    def _group_segment(self):
        grp = getattr(self, 'accessory_group', False)
        if not grp:
            return ''
        return _abbreviate(grp.name, 3)

    # ------------------------------------------------------------------ #
    #  Validation                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _sanitize_ref(raw):
        return re.sub(r'[^A-Z0-9\-]', '', raw.strip().upper()).strip('-')

    def _validate_ref(self, code):
        if not code:
            return
        if len(code) > MAX_REF_LENGTH:
            raise ValidationError(
                _("Internal reference '%(code)s' is %(len)d chars "
                  "(max %(max)d). Shorten the product name or attribute values.")
                % {'code': code, 'len': len(code), 'max': MAX_REF_LENGTH}
            )
        if '--' in code:
            raise ValidationError(
                _("Internal reference '%(code)s' has consecutive hyphens. "
                  "Check that brand, category, and attributes are all set.")
                % {'code': code}
            )
        if not re.fullmatch(r'[A-Z0-9]([A-Z0-9\-]*[A-Z0-9])?', code):
            raise ValidationError(
                _("Internal reference '%(code)s' contains invalid characters. "
                  "Only A-Z, 0-9, and hyphens are allowed.")
                % {'code': code}
            )

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_category_match(categ, target):
        current = categ
        while current:
            if current.id == target.id:
                return True
            current = current.parent_id
        return False

    def _resolve_variant(self, variant_id):
        if not variant_id:
            return self.env['product.product']
        variant = self.env['product.product'].browse(variant_id)
        if not variant.exists() or variant.product_tmpl_id.id != self.id:
            return self.env['product.product']
        return variant

    def write(self, vals):
        res = super().write(vals)
        extra_triggers = {'brand_id', 'categ_id', 'part_code', 'accessory_group'}
        if any(f in vals for f in extra_triggers):
            for rec in self:
                rec._generate_and_assign_sku()
        return res
