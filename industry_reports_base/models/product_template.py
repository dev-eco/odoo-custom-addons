# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    """Extensión de product.template con campos técnicos para reportes industriales."""

    _inherit = "product.template"

    # ========== MATERIAL Y ACABADO ==========

    product_material = fields.Char(
        string="Material",
        help="Material principal del producto (ej: Acero inoxidable, PVC, Aluminio)",
    )

    product_finish = fields.Selection(
        [
            ("natural", "Natural"),
            ("painted", "Pintado"),
            ("galvanized", "Galvanizado"),
            ("anodized", "Anodizado"),
            ("polished", "Pulido"),
            ("other", "Otro"),
        ],
        string="Acabado",
        help="Tipo de acabado superficial",
    )

    # ========== DIMENSIONES DETALLADAS ==========

    dimension_length = fields.Float(
        string="Largo (mm)", digits=(8, 2), help="Longitud en milímetros"
    )

    dimension_width = fields.Float(
        string="Ancho (mm)", digits=(8, 2), help="Ancho en milímetros"
    )

    dimension_height = fields.Float(
        string="Alto (mm)", digits=(8, 2), help="Altura en milímetros"
    )

    dimension_diameter = fields.Float(
        string="Diámetro (mm)",
        digits=(8, 2),
        help="Diámetro para productos cilíndricos",
    )

    dimension_display = fields.Char(
        string="Dimensiones",
        compute="_compute_dimension_display",
        store=False,
        help="Formato legible: 100 x 50 x 30 mm o Ø 50 mm",
    )

    # ========== INFORMACIÓN TÉCNICA ADICIONAL ==========

    technical_datasheet = fields.Binary(
        string="Ficha Técnica PDF",
        attachment=True,
        help="Documento técnico del producto",
    )

    technical_datasheet_filename = fields.Char(string="Nombre Ficha Técnica")

    # ========== PACKAGING (para futura implementación albaranes Fase 2) ==========

    package_units_per_box = fields.Integer(
        string="Unidades por Caja",
        default=1,
        help="Cantidad de unidades en empaque estándar",
    )

    package_box_weight = fields.Float(
        string="Peso Caja Completa (kg)",
        digits=(8, 2),
        help="Peso bruto de la caja con producto",
    )

    # ========== MÉTODOS COMPUTED ==========

    @api.depends(
        "dimension_length", "dimension_width", "dimension_height", "dimension_diameter"
    )
    def _compute_dimension_display(self):
        """
        Calcula el formato legible de las dimensiones.

        Formatos:
        - Rectangular: "100 x 50 x 30 mm" (largo x ancho x alto)
        - Cilíndrico: "Ø 75 mm" (diámetro)
        - Vacío: '' (sin dimensiones)
        """
        for product in self:
            dims = []

            # Recopilar dimensiones rectangulares (convertir a enteros)
            if product.dimension_length:
                dims.append(str(int(product.dimension_length)))
            if product.dimension_width:
                dims.append(str(int(product.dimension_width)))
            if product.dimension_height:
                dims.append(str(int(product.dimension_height)))

            # Formato rectangular: "100 x 50 x 30 mm"
            if dims:
                product.dimension_display = " x ".join(dims) + " mm"
            # Formato cilíndrico: "Ø 75 mm"
            elif product.dimension_diameter:
                product.dimension_display = f"Ø {int(product.dimension_diameter)} mm"
            # Sin dimensiones
            else:
                product.dimension_display = ""
