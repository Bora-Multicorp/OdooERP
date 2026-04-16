# -*- coding: utf-8 -*-
import math
import re
from odoo import models, api, _
from odoo.exceptions import ValidationError

# Hard ceiling on generated internal references (including hyphens).
MAX_REF_LENGTH = 24

# Keywords that identify the role of an attribute by its *name*.
_COLOUR_KEYWORDS = frozenset({'colour', 'color'})
_TYPE_KEYWORDS = frozenset({'type'})


def _abbreviate(text, max_len):
    """
    Auto-derive a short uppercase alphanumeric code from *text*.

    Strip every non-alphanumeric character (including spaces), uppercase,
    and take the first ``max_len`` characters.

        "Mobile Phone"  → MOBILEPHONE[:3]  = MOB
        "Toner & Inks"  → TONERINKS[:3]    = TON
        "Samsung"       → SAM
        "256 GB"        → 256GB[:5]        = 256GB
    """
    return re.sub(r'[^A-Z0-9]', '', text.upper())[:max_len]


def _build_variant_segment(variant_parts, max_len=5):
    """
    Combine multiple variant attribute codes into a single segment of
    ``max_len`` characters, ensuring each attribute contributes proportionally.

    Why this matters
    ----------------
    Naive ``''.join(parts)[:5]`` loses information when the first attribute
    value is already 5 chars.  E.g. Storage="256GB" + RAM="12GB" and
    Storage="256GB" + RAM="16GB" both collapse to "256GB" → collision.

    This function allocates ``ceil(max_len / n)`` characters to each part,
    so every attribute always contributes at least 1 character to the result.

    Examples (max_len=5)
    --------------------
    ["256GB"]                    → "256GB"   (1 part  → 5 chars each)
    ["12GB", "256GB"]  (sorted)  → "12G25"   (2 parts → 3 chars each, cap 5)
    ["16GB", "256GB"]  (sorted)  → "16G25"   ← different from above ✓
    ["12GB", "512GB"]  (sorted)  → "12G51"   ← different ✓
    ["12G", "256", "TI"]         → "12256T"  (3 parts → 2 chars each, cap 5)

    :param variant_parts: list of (attr_name, code_str) tuples, pre-sorted
                          by attribute name for consistent ordering.
    :param max_len: maximum characters in the output segment.
    :returns: str, length ≤ max_len
    """
    if not variant_parts:
        return ''

    n = len(variant_parts)
    per_part = math.ceil(max_len / n)          # chars allocated to each part
    combined = ''.join(seg[:per_part] for seg in variant_parts)
    return combined[:max_len]


class ProductTemplateInternalRef(models.Model):
    """
    Replaces the generic SKU builder in ``ks_product_master`` with a
    structured, category-aware internal reference generator.

    No manual code configuration is required — every segment is derived
    automatically from existing product data.

    Generation priority
    -------------------
    1. ``part_code`` filled in → use it directly (sanitised, validated).
    2. **Toner & Inks** category → ``BRAND-TYPE-MODEL-COLOUR``
    3. **All other** categories → ``BRAND-CAT-(GRP)-MODEL-VARIANT-COLOUR``

    Segment derivation  (all auto-calculated — no user input)
    ----------------------------------------------------------
    Rule: strip non-alnum characters, uppercase, take first N chars.
    Variant segment distributes chars proportionally across ALL non-colour /
    non-type attributes so that no single attribute swamps the others.

    Segment  | Length | Source → Example
    ---------|--------|--------------------------------------------------
    BRAND    | ≤ 3    | brand_id.name         "Samsung"      → SAM
    CAT      | ≤ 3    | categ_id.name         "Mobile Phone" → MOB
    GRP      | ≤ 3    | accessory_group.name  (optional)
    MODEL    | ≤ 6    | product name          "Galaxy S24U"  → GALAXY
    TYPE     | ≤ 3    | "Type" attr value     "Ink Bottle"   → INK
    VARIANT  | ≤ 5    | other attr values     proportional split per attr
    COLOUR   | ≤ 3    | "Colour/Color" value  "Titanium"     → TIT

    Uniqueness guarantee
    --------------------
    All codes for a template's variants are generated first, then written
    in one pass with the per-row constraint suppressed.  A single
    post-generation check then validates:
      (a) no two variants of the same template share a code, and
      (b) no variant's code collides with any other product.product record.
    """
    _inherit = 'product.template'

    # ------------------------------------------------------------------ #
    #  Main entry-point – overrides ks_product_master                    #
    # ------------------------------------------------------------------ #

    def _generate_and_assign_sku(self):
        """
        Generate and write internal references for every variant of ``self``.

        This overrides the ks_product_master implementation to fix two issues:

        1. **Proportional variant segment** – each attribute value gets a fair
           share of the 5-char variant slot (see :func:`_build_variant_segment`).

        2. **Race-condition-free writes** – all new codes are computed first,
           then written in one pass with the per-row duplicate constraint
           suppressed (context key ``skip_sku_duplicate_check=True``).
           A single post-write validation checks both intra-template and
           cross-product uniqueness.
        """
        self.ensure_one()

        variants = self.env['product.product'].with_context(active_test=False).search(
            [('product_tmpl_id', '=', self.id)]
        )

        if not variants:
            # Single-variant template (no attribute lines yet)
            code = self._generate_sku(self.id)
            self.with_context(skip_sku_duplicate_check=True).default_code = code
            self._check_cross_product_unique({self.id: code})
            return

        # ── Step 1: generate all codes without writing anything ───────── #
        new_codes = {}        # {variant.id: code_str}
        for variant in variants:
            new_codes[variant.id] = self._generate_sku(variant.id)

        # ── Step 2: validate intra-template uniqueness ────────────────── #
        # Two variants of the same product genuinely having identical codes
        # means their differentiating attributes produce the same abbreviation.
        seen = {}
        for vid, code in new_codes.items():
            if not code:
                continue
            if code in seen:
                variant_a = self.env['product.product'].browse(seen[code])
                variant_b = self.env['product.product'].browse(vid)
                raise ValidationError(
                    _("Cannot generate a unique Internal Reference for all "
                      "variants of '%(product)s'.\n\n"
                      "Variants '%(a)s' and '%(b)s' both produce the code "
                      "'%(code)s'.\n\n"
                      "This means their attribute values abbreviate to the same "
                      "string.  Rename one of the attribute values so the first "
                      "few characters are different (e.g. '256GB' vs '512GB' "
                      "rather than '256GBv1' vs '256GBv2').")
                    % {
                        'product': self.name,
                        'a': variant_a.display_name,
                        'b': variant_b.display_name,
                        'code': code,
                    }
                )
            seen[code] = vid

        # ── Step 3: write all codes – suppress per-row constraint ─────── #
        ctx = dict(self.env.context, skip_sku_duplicate_check=True)
        for variant in variants:
            variant.with_context(**ctx).default_code = new_codes[variant.id]

        # ── Step 4: validate cross-product uniqueness ─────────────────── #
        self._check_cross_product_unique(new_codes)

    def _check_cross_product_unique(self, code_map):
        """
        Raise ValidationError if any generated code already exists on a
        product.product record that does NOT belong to this template.

        :param code_map: dict {variant_id: code_str}
        """
        own_ids = list(code_map.keys())
        for vid, code in code_map.items():
            if not code:
                continue
            duplicate = self.env['product.product'].with_context(
                active_test=False
            ).search(
                [
                    ('default_code', '=', code),
                    ('id', 'not in', own_ids),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("Internal Reference '%(code)s' is already assigned to "
                      "'%(other)s'.\n\n"
                      "It conflicts with a variant of '%(this)s'.  "
                      "Change the product name, brand, category, or attribute "
                      "values so the generated reference is unique.")
                    % {
                        'code': code,
                        'other': duplicate.display_name,
                        'this': self.name,
                    }
                )

    # ------------------------------------------------------------------ #
    #  Per-variant code builder (called by _generate_and_assign_sku)     #
    # ------------------------------------------------------------------ #

    def _generate_sku(self, variant_id):
        """
        Return the structured internal reference string for one variant.

        :param variant_id: int – ID of a product.product record, or the
                           template's own ID when no variants exist yet.
        :returns: str – validated reference, may be '' if data is missing.
        """
        self.ensure_one()

        # 1. Manual override
        if self.part_code:
            code = self._sanitize_ref(self.part_code)
            self._validate_ref(code)
            return code

        # 2. Resolve variant
        variant = self._resolve_variant(variant_id)

        # 3. Extract attribute segments
        colour_code, type_code, variant_parts = self._extract_attr_segments(variant)

        # 4. Detect Toner & Inks
        toner_categ = self.env.ref(
            'ks_product_master.product_category_type_toner_inks',
            raise_if_not_found=False,
        )
        is_toner = bool(
            toner_categ and self._is_category_match(self.categ_id, toner_categ)
        )

        # 5. Build segment list
        brand = self._brand_segment()
        model = self._model_segment()

        if is_toner:
            parts = [brand, type_code, model, colour_code]
        else:
            cat = self._cat_segment()
            grp = self._group_segment()
            # Proportional split: every attribute contributes to the variant seg
            variant_seg = _build_variant_segment(variant_parts, max_len=5)
            parts = [brand, cat, grp, model, variant_seg, colour_code]

        code = '-'.join(p for p in parts if p)

        # 6. Validate format and length
        self._validate_ref(code)
        return code

    # ------------------------------------------------------------------ #
    #  Attribute segment extractor                                        #
    # ------------------------------------------------------------------ #

    def _extract_attr_segments(self, variant):
        """
        Walk the variant's attribute values and classify each into:
          - colour_code   (attribute name contains "colour" / "color")
          - type_code     (attribute name contains "type")
          - variant_parts (everything else: storage, RAM, chip, etc.)

        variant_parts is returned **sorted by attribute name** so that the
        same combination always produces the same segment regardless of the
        order attributes happen to be stored.

        :returns: tuple(colour_code: str, type_code: str, variant_parts: list[str])
        """
        colour_code = ''
        type_code = ''
        raw_variant_parts = []   # list of (attr_name, seg) for sorting

        if not (variant and variant.exists()):
            return colour_code, type_code, []

        for ptav in variant.product_template_attribute_value_ids:
            attr_name = ptav.attribute_id.name.lower().strip()
            seg = _abbreviate(
                re.sub(r'[^A-Z0-9 ]', '', ptav.name.upper()),
                5,
            )

            if any(kw in attr_name for kw in _COLOUR_KEYWORDS):
                colour_code = seg[:3]
            elif any(kw in attr_name for kw in _TYPE_KEYWORDS):
                type_code = seg[:3]
            else:
                raw_variant_parts.append((attr_name, seg))

        # Sort by attribute name → consistent ordering across all variants
        raw_variant_parts.sort(key=lambda x: x[0])
        variant_parts = [seg for _, seg in raw_variant_parts]

        return colour_code, type_code, variant_parts

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

        Strategy
        --------
        Split the name on spaces and hyphens, then scan **right-to-left**
        for the last token that contains BOTH at least one letter and at
        least one digit — this is almost always the unique model identifier
        (e.g. P615, S24, V15G4, MBA13).

        Examples
        --------
        "Tab S6 Lite LTE SM-P615 4/64 GB" → tokens include S6, P615
                                             last mixed = P615  → "P615"
        "Tab S6 Lite LTE SM-P619 4/64 GB" → last mixed = P619  → "P619"  ✓ different
        "Samsung Galaxy S24 Ultra"         → last mixed = S24   → "S24"
        "iPhone 15 Pro Max"                → no mixed token     → "IPHONE" (fallback)
        "GI490"  (toner model)             → last mixed = GI490 → "GI490"

        Fallback: first 6 alnum chars of the full cleaned name when no
        mixed-case token is found.
        """
        name = (self.name or '').upper()

        # Tokenise on spaces and hyphens, strip each token to alnum only
        tokens = [
            re.sub(r'[^A-Z0-9]', '', part)
            for part in re.split(r'[\s\-]+', name)
        ]
        tokens = [t for t in tokens if t]   # drop empties

        # Last token with BOTH a letter and a digit = the model identifier
        for token in reversed(tokens):
            if re.search(r'[A-Z]', token) and re.search(r'[0-9]', token):
                return token[:6]

        # Fallback: first 6 alnum chars of the full name
        return re.sub(r'[^A-Z0-9]', '', name)[:6]

    def _group_segment(self):
        grp = getattr(self, 'accessory_group', False)
        if not grp:
            return ''
        return _abbreviate(grp.name, 3)

    # ------------------------------------------------------------------ #
    #  Validation helpers                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _sanitize_ref(raw):
        return re.sub(r'[^A-Z0-9\-]', '', raw.strip().upper()).strip('-')

    def _validate_ref(self, code):
        if not code:
            return

        if len(code) > MAX_REF_LENGTH:
            raise ValidationError(
                _("Internal reference '%(code)s' is %(len)d characters long "
                  "(maximum is %(max)d). Shorten the product name or attribute "
                  "values so the generated reference fits within %(max)d characters.")
                % {'code': code, 'len': len(code), 'max': MAX_REF_LENGTH}
            )

        if '--' in code:
            raise ValidationError(
                _("Internal reference '%(code)s' contains consecutive hyphens. "
                  "One or more segments could not be derived — check that the "
                  "product has a brand, category, and properly named attributes.")
                % {'code': code}
            )

        if not re.fullmatch(r'[A-Z0-9]([A-Z0-9\-]*[A-Z0-9])?', code):
            raise ValidationError(
                _("Internal reference '%(code)s' contains invalid characters. "
                  "Only uppercase letters (A-Z), digits (0-9), and hyphens are "
                  "allowed. The reference must not start or end with a hyphen.")
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
        if not variant.exists():
            return self.env['product.product']
        if variant.product_tmpl_id.id != self.id:
            return self.env['product.product']
        return variant

    # ------------------------------------------------------------------ #
    #  write() – extend trigger fields                                    #
    # ------------------------------------------------------------------ #

    def write(self, vals):
        res = super().write(vals)
        extra_triggers = {'brand_id', 'categ_id', 'part_code', 'accessory_group'}
        if any(field in vals for field in extra_triggers):
            for rec in self:
                rec._generate_and_assign_sku()
        return res
