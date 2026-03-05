# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    """Extensión de res.company con configuración para reportes industriales."""

    _inherit = "res.company"

    # ========== LOGOS CORPORATIVOS ==========

    report_header_logo = fields.Binary(
        string="Logo Cabecera Reportes",
        attachment=True,
        help="Logo principal para reportes (recomendado: 200x80px PNG transparente)",
    )

    report_footer_logo = fields.Binary(
        string="Logo Pie de Página",
        attachment=True,
        help="Logo secundario para pie (opcional)",
    )

    # ========== DISCLAIMERS LEGALES ==========

    report_quotation_disclaimer = fields.Html(
        string="Aviso Legal Presupuestos",
        default="<p>Presupuesto válido por 30 días. Precios sujetos a disponibilidad.</p>",
        help="Texto legal a mostrar en pie de presupuestos",
    )

    report_delivery_disclaimer = fields.Html(
        string="Aviso Legal Albaranes",
        default="<p>Revisar mercancía en presencia del transportista.</p>",
        help="Instrucciones legales en albaranes (Fase 2)",
    )

    report_invoice_disclaimer = fields.Html(
        string="Aviso Legal Facturas",
        help="Condiciones legales facturas (Fase 2)",
    )

    # ========== CONFIGURACIÓN TÉCNICA PY3O ==========

    py3o_conversion_timeout = fields.Integer(
        string="Timeout Conversión Py3o (segundos)",
        default=30,
        help="Tiempo máximo de espera para conversión ODT→PDF",
    )

    py3o_enable_cache = fields.Boolean(
        string="Cachear Plantillas Py3o",
        default=True,
        help="Mantener plantillas en memoria para generación más rápida",
    )

    # ========== VALIDACIONES ==========

    @api.constrains("py3o_conversion_timeout")
    def _check_py3o_timeout(self):
        """Validar que el timeout sea razonable."""
        for company in self:
            if company.py3o_conversion_timeout < 5:
                raise ValidationError(
                    "El timeout de conversión Py3o debe ser al menos 5 segundos."
                )
            if company.py3o_conversion_timeout > 300:
                raise ValidationError(
                    "El timeout de conversión Py3o no debe exceder 300 segundos (5 minutos)."
                )
