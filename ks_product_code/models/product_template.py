# -*- coding: utf-8 -*-
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

    Algorithm
    ---------
    Strip every non-alphanumeric character (including spaces), uppercase,
    and take the first ``max_len`` characters.

    This is intentionally simple so that multi-word names read left-to-right
    in a natural way:

        "Mobile Phone"  → MOBILEPHONE[:3]  = MOB
        "Toner & Inks"  → TONERINKS[:3]    = TON
        "Samsung"       → SAM
        "Canon"         → CAN
        "Ink Bottle"    → INKBOTTLE[:3]    = INK
        "256 GB"        → 256GB[:5]        = 256GB
        "Black"         → BLA
        "Silver"        → SIL

    :param text: raw name string (any case, may contain spaces/special chars)
    :param max_len: desired output length
    :returns: uppercase alphanumeric string, length ≤ max_len
    """
    return re.sub(r'[^A-Z0-9]', '', text.upper())[:max_len]


class ProductTemplateInternalRef(models.Model):
    """
    Replaces the generic SKU builder in ``ks_product_master`` with a
    structured, category-aware internal reference generator.

    No manual code configuration is required.  Every segment is derived
    automatically from existing product data.

    Generation priority
    -------------------
    1. ``part_code`` filled in → use it directly (sanitised, validated).
    2. **Toner & Inks** category → ``BRAND-TYPE-MODEL-COLOUR``
    3. **All other** categories → ``BRAND-CAT-(GRP)-MODEL-VARIANT-COLOUR``

    Segment derivation  (all auto-calculated — no user input)
    ----------------------------------------------------------
    Rule: strip non-alnum characters, uppercase, take first N chars.

    Segment  | Length | Source → Example
    ---------|--------|--------------------------------------------------
    BRAND    | ≤ 3    | brand_id.name       "Samsung"     → SAM
    CAT      | ≤ 3    | categ_id.name       "Mobile Phone"→ MOB
    GRP      | ≤ 3    | accessory_group.name (optional)
    MODEL    | ≤ 6    | product name        "Galaxy S24 Ultra" → GALAXY
    TYPE     | ≤ 3    | "Type" attr value   "Ink Bottle"  → INK
    VARIANT  | ≤ 5    | other attr values   "256 GB"      → 256GB
    COLOUR   | ≤ 3    | "Colour/Color" val  "Titanium"    → TIT

    Validation
    ----------
    • Total length ≤ 24 characters (hyphens counted)
    • Uppercase alphanumeric + single hyphens only
    • No leading / trailing hyphens; no consecutive hyphens
    • Duplicate ``default_code`` check at variant level (product.product)
    """
    _inherit = 'product.template'

    # ------------------------------------------------------------------ #
    #  Public entry-point (replaces ks_product_master._generate_sku)     #
    # ------------------------------------------------------------------ #

    def _generate_sku(self, variant_id):
        """
        Return a structured internal reference string for *variant_id*.

        Called by ``ks_product_master._generate_and_assign_sku()`` for every
        variant belonging to ``self`` (a ``product.template`` singleton).

        :param variant_id: int  – ID of a ``product.product`` record, OR the
                           template's own ID when no variants exist yet.
        :returns: str – validated internal reference (may be empty string if
                  all segments are missing, which is silently allowed)
        """
        self.ensure_one()

        # ── 1. Manual override: honour part_code ────────────────────── #
        if self.part_code:
            code = self._sanitize_ref(self.part_code)
            self._validate_ref(code)
            return code

        # ── 2. Resolve the variant safely ───────────────────────────── #
        variant = self._resolve_variant(variant_id)

        # ── 3. Extract attribute segments ───────────────────────────── #
        colour_code, type_code, variant_parts = self._extract_attr_segments(variant)

        # ── 4. Detect Toner & Inks (walks hierarchy) ────────────────── #
        toner_categ = self.env.ref(
            'ks_product_master.product_category_type_toner_inks',
            raise_if_not_found=False,
        )
        is_toner = bool(
            toner_categ and self._is_category_match(self.categ_id, toner_categ)
        )

        # ── 5. Build ordered segment list ───────────────────────────── #
        brand = self._brand_segment()
        model = self._model_segment()

        if is_toner:
            # Pattern: BRAND-TYPE-MODEL-COLOUR
            parts = [brand, type_code, model, colour_code]
        else:
            # Pattern: BRAND-CAT-(GRP)-MODEL-VARIANT-COLOUR
            cat = self._cat_segment()
            grp = self._group_segment()
            variant_seg = ''.join(variant_parts)[:5]   # cap at 5 chars
            parts = [brand, cat, grp, model, variant_seg, colour_code]

        # Join non-empty segments
        code = '-'.join(p for p in parts if p)

        # ── 6. Validate ─────────────────────────────────────────────── #
        self._validate_ref(code)
        return code

    # ------------------------------------------------------------------ #
    #  Attribute segment extractor                                        #
    # ------------------------------------------------------------------ #

    def _extract_attr_segments(self, variant):
        """
        Classify each attribute value of *variant* into one of:
          - ``colour_code`` – value whose attribute name contains "colour"/"color"
          - ``type_code``   – value whose attribute name contains "type"
          - ``variant_parts`` – everything else (storage, RAM, chip …)

        All codes are auto-derived via :func:`_abbreviate`; no manual input.

        :returns: tuple(colour_code: str, type_code: str, variant_parts: list[str])
        """
        colour_code = ''
        type_code = ''
        variant_parts = []

        if not (variant and variant.exists()):
            return colour_code, type_code, variant_parts

        for ptav in variant.product_template_attribute_value_ids:
            attr_name = ptav.attribute_id.name.lower().strip()
            seg = _abbreviate(
                re.sub(r'[^A-Z0-9 ]', '', ptav.name.upper()),
                5,       # derive up to 5 chars; callers trim further as needed
            )

            if any(kw in attr_name for kw in _COLOUR_KEYWORDS):
                colour_code = seg[:3]            # colour fixed at 3 chars
            elif any(kw in attr_name for kw in _TYPE_KEYWORDS):
                type_code = seg[:3]              # type fixed at 3 chars
            else:
                variant_parts.append(seg)        # up to 5 chars per part

        return colour_code, type_code, variant_parts

    # ------------------------------------------------------------------ #
    #  Segment builders  (all purely auto-derived)                       #
    # ------------------------------------------------------------------ #

    def _brand_segment(self):
        """3-char code from brand name.  Returns '' when no brand is set."""
        if not self.brand_id:
            return ''
        return _abbreviate(self.brand_id.name, 3)

    def _cat_segment(self):
        """3-char code from category name.  Returns '' when no category is set."""
        if not self.categ_id:
            return ''
        return _abbreviate(self.categ_id.name, 3)

    def _model_segment(self):
        """Up-to-6-char slug from the product name (first 6 alnum chars)."""
        return re.sub(r'[^A-Z0-9]', '', (self.name or '').upper())[:6]

    def _group_segment(self):
        """3-char code from accessory group name.  Returns '' when not set."""
        grp = getattr(self, 'accessory_group', False)
        if not grp:
            return ''
        return _abbreviate(grp.name, 3)

    # ------------------------------------------------------------------ #
    #  Validation helpers                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _sanitize_ref(raw):
        """
        Sanitise a manually entered ``part_code``:
          • Uppercase
          • Keep only A-Z, 0-9, and hyphens
          • Strip surrounding hyphens
        """
        return re.sub(r'[^A-Z0-9\-]', '', raw.strip().upper()).strip('-')

    def _validate_ref(self, code):
        """
        Raise ``ValidationError`` when *code* violates any constraint:

        1. ≤ ``MAX_REF_LENGTH`` (24) characters including hyphens
        2. No consecutive hyphens ``--``
        3. Starts and ends with an alphanumeric character
        4. Contains only A-Z, 0-9, and single hyphens
        """
        if not code:
            return   # empty code is silently accepted (missing data)

        if len(code) > MAX_REF_LENGTH:
            raise ValidationError(
                _("Internal reference '%(code)s' is %(len)d characters long "
                  "(maximum is %(max)d).  "
                  "The product name or attribute values are too long — shorten "
                  "them so the generated reference fits within %(max)d characters.")
                % {'code': code, 'len': len(code), 'max': MAX_REF_LENGTH}
            )

        if '--' in code:
            raise ValidationError(
                _("Internal reference '%(code)s' contains consecutive hyphens.  "
                  "One or more segments could not be derived — check that the "
                  "product has a brand, category, and properly named attributes.")
                % {'code': code}
            )

        if not re.fullmatch(r'[A-Z0-9]([A-Z0-9\-]*[A-Z0-9])?', code):
            raise ValidationError(
                _("Internal reference '%(code)s' contains invalid characters.  "
                  "Only uppercase letters (A-Z), digits (0-9), and hyphens are "
                  "allowed.  The reference must not start or end with a hyphen.")
                % {'code': code}
            )

    # ------------------------------------------------------------------ #
    #  Category hierarchy helper                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_category_match(categ, target):
        """
        Return ``True`` if *categ* equals *target* or is any descendant of it.
        Walks up the parent chain so sub-categories of "Toner & Inks" are
        identified correctly.
        """
        current = categ
        while current:
            if current.id == target.id:
                return True
            current = current.parent_id
        return False

    # ------------------------------------------------------------------ #
    #  Variant resolver                                                   #
    # ------------------------------------------------------------------ #

    def _resolve_variant(self, variant_id):
        """
        Safely return the ``product.product`` record for *variant_id*.

        Returns an empty recordset when:
          • *variant_id* is falsy
          • No ``product.product`` with that ID exists
          • The record does not belong to this template (guard against the
            legacy code path in ``_generate_and_assign_sku`` that passes the
            template's own ID when no variants exist yet)
        """
        if not variant_id:
            return self.env['product.product']
        variant = self.env['product.product'].browse(variant_id)
        if not variant.exists():
            return self.env['product.product']
        if variant.product_tmpl_id.id != self.id:
            return self.env['product.product']
        return variant

    # ------------------------------------------------------------------ #
    #  write() – extend the fields that trigger regeneration             #
    # ------------------------------------------------------------------ #

    def write(self, vals):
        """
        Regenerate internal references when any code-influencing field changes.

        ``ks_product_master`` already triggers regeneration on ``name`` and
        ``attribute_line_ids``.  We extend that set with the other fields that
        feed into the structured reference formula.
        """
        res = super().write(vals)

        extra_triggers = {'brand_id', 'categ_id', 'part_code', 'accessory_group'}
        if any(field in vals for field in extra_triggers):
            for rec in self:
                rec._generate_and_assign_sku()

        return res
