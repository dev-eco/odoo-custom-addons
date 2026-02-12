# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Extensión de contacto para funcionalidades B2B de distribuidores."""

    _inherit = 'res.partner'

    # ========== CAMPO UNIFICADO ==========
    # USAR SOLO is_distributor (NO is_b2b_distributor)
    
    is_distributor = fields.Boolean(
        string='Es Distribuidor B2B',
        compute='_compute_is_distributor',
        store=True,
        help='Se marca automáticamente si el contacto tiene un usuario con acceso al Portal B2B'
    )

    credit_limit = fields.Monetary(
        string='Límite de Crédito',
        currency_field='currency_id',
        default=0.0,
        help='Límite máximo de crédito permitido para este distribuidor'
    )

    available_credit = fields.Monetary(
        string='Crédito Disponible',
        currency_field='currency_id',
        compute='_compute_available_credit',
        store=False,
        help='Crédito disponible = Límite - Deuda pendiente'
    )

    distributor_pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Tarifa Distribuidor',
        help='Tarifa de precios específica para este distribuidor'
    )

    total_invoiced_year = fields.Monetary(
        string='Facturado Año Actual',
        currency_field='currency_id',
        compute='_compute_total_invoiced_year',
        store=False,
        help='Total facturado en el año en curso'
    )

    @api.depends('user_ids', 'user_ids.groups_id')
    def _compute_is_distributor(self) -> None:
        """
        Determina si el partner es distribuidor basado en sus usuarios.

        Un partner es distribuidor si alguno de sus usuarios tiene el grupo Portal B2B.
        Se actualiza automáticamente cuando se asignan/desasignan usuarios o grupos.
        """
        try:
            portal_b2b_group = self.env.ref(
                'portal_b2b_base.group_portal_b2b',
                raise_if_not_found=False
            )
        except Exception as e:
            _logger.warning(f"No se pudo obtener grupo Portal B2B: {str(e)}")
            portal_b2b_group = None

        for partner in self:
            if portal_b2b_group and partner.user_ids:
                # Verificar si algún usuario del partner tiene el grupo Portal B2B
                has_portal_b2b_access = any(
                    portal_b2b_group in user.groups_id
                    for user in partner.user_ids
                )
                partner.is_distributor = has_portal_b2b_access

                if has_portal_b2b_access:
                    _logger.debug(
                        f"Partner {partner.name} marcado como distribuidor "
                        f"(usuarios con acceso Portal B2B: {len([u for u in partner.user_ids if portal_b2b_group in u.groups_id])})"
                    )
            else:
                partner.is_distributor = False

    @api.depends('credit', 'credit_limit')
    def _compute_available_credit(self) -> None:
        """
        Calcula el crédito disponible para el distribuidor.

        Crédito disponible = Límite de crédito - Deuda pendiente (credit)
        Si no hay límite configurado, el crédito disponible es 0.
        """
        for partner in self:
            if partner.credit_limit > 0:
                partner.available_credit = partner.credit_limit - partner.credit
            else:
                partner.available_credit = 0.0

            _logger.debug(
                f"Partner {partner.name} - Límite: {partner.credit_limit}, "
                f"Deuda: {partner.credit}, Disponible: {partner.available_credit}"
            )

    @api.depends('invoice_ids', 'invoice_ids.amount_total', 'invoice_ids.state')
    def _compute_total_invoiced_year(self) -> None:
        """
        Calcula el total facturado en el año actual.

        Solo cuenta facturas de cliente (out_invoice) en estado posted.
        """
        current_year = fields.Date.today().year

        for partner in self:
            domain = [
                ('partner_id', 'child_of', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', f'{current_year}-01-01'),
                ('invoice_date', '<=', f'{current_year}-12-31'),
            ]

            invoices = self.env['account.move'].search(domain)
            partner.total_invoiced_year = sum(invoices.mapped('amount_total'))

    def validar_credito_disponible(self, monto: float) -> bool:
        """
        Valida si el distribuidor tiene crédito suficiente para un monto dado.

        Args:
            monto: Monto a validar

        Returns:
            True si hay crédito suficiente, False en caso contrario

        Raises:
            ValidationError: Si el distribuidor no tiene límite de crédito configurado
        """
        self.ensure_one()

        if not self.is_distributor:
            _logger.warning(f"Validación de crédito llamada en partner no distribuidor: {self.name}")
            return True

        if self.credit_limit <= 0:
            raise ValidationError(
                _('El distribuidor %s no tiene límite de crédito configurado.') % self.name
            )

        credito_despues = self.available_credit - monto

        if credito_despues < 0:
            _logger.warning(
                f"Crédito insuficiente para {self.name}. "
                f"Disponible: {self.available_credit}, Requerido: {monto}"
            )
            return False

        return True

    def obtener_tarifa_aplicable(self):
        """
        Obtiene la tarifa de precios aplicable al distribuidor.

        Returns:
            product.pricelist: Tarifa del distribuidor o tarifa por defecto
        """
        self.ensure_one()

        if self.distributor_pricelist_id:
            return self.distributor_pricelist_id

        if self.property_product_pricelist:
            return self.property_product_pricelist

        # Tarifa por defecto de la compañía
        return self.env['product.pricelist'].search([
            ('company_id', 'in', [self.env.company.id, False])
        ], limit=1)

    @api.constrains('credit_limit')
    def _check_credit_limit(self) -> None:
        """Valida que el límite de crédito sea positivo o cero."""
        for partner in self:
            if partner.credit_limit < 0:
                raise ValidationError(
                    _('El límite de crédito no puede ser negativo.')
                )

    def action_grant_portal_access(self):
        """
        Acción para otorgar acceso al portal B2B.
        
        Crea un usuario PORTAL (no interno) y lo asigna al grupo Portal B2B.
        El usuario SOLO tiene acceso al portal, NO al backend.
        """
        self.ensure_one()

        # Verificar si ya tiene usuario
        if self.user_ids:
            existing_user = self.user_ids[0]
            
            # Si ya es usuario portal, solo agregar grupo B2B
            if existing_user.has_group('base.group_portal'):
                b2b_group = self.env.ref('portal_b2b_base.group_portal_b2b')
                
                if b2b_group not in existing_user.groups_id:
                    existing_user.sudo().write({
                        'groups_id': [(4, b2b_group.id)]
                    })
                    
                    _logger.info(f"Grupo Portal B2B añadido a usuario existente {existing_user.login}")
                    
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Grupo Asignado'),
                            'message': _('Se ha asignado el grupo Portal B2B al usuario existente.'),
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Ya Configurado'),
                            'message': _('Este usuario ya tiene acceso al Portal B2B.'),
                            'type': 'info',
                            'sticky': False,
                        }
                    }
            else:
                # Es usuario interno, no podemos convertirlo
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Usuario Interno Detectado'),
                        'message': _('Este contacto tiene un usuario interno. No se puede convertir en usuario portal. Cree un nuevo contacto para el portal B2B.'),
                        'type': 'warning',
                        'sticky': True,
                    }
                }

        # Validar email
        if not self.email:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Email Requerido'),
                    'message': _('El contacto debe tener un email para crear el usuario portal.'),
                    'type': 'danger',
                    'sticky': False,
                }
            }

        # Verificar si el email ya está en uso
        existing_user = self.env['res.users'].sudo().search([('login', '=', self.email)], limit=1)
        if existing_user:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Email en Uso'),
                    'message': _('Ya existe un usuario con este email: %s') % self.email,
                    'type': 'danger',
                    'sticky': False,
                }
            }

        # Crear usuario PORTAL (no interno)
        try:
            portal_group = self.env.ref('base.group_portal')
            b2b_group = self.env.ref('portal_b2b_base.group_portal_b2b')

            # IMPORTANTE: Solo grupos de portal, NO grupos internos
            user = self.env['res.users'].sudo().create({
                'name': self.name,
                'login': self.email,
                'email': self.email,
                'partner_id': self.id,
                'groups_id': [(6, 0, [portal_group.id, b2b_group.id])],
                'active': True,
            })

            # Enviar email de invitación
            try:
                user.action_reset_password()
                _logger.info(f"Usuario portal B2B creado y email enviado: {user.login}")
            except Exception as e:
                _logger.warning(f"Usuario creado pero error al enviar email: {str(e)}")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Usuario Portal Creado'),
                    'message': _('Se ha creado el usuario portal B2B. Se ha enviado un email con las instrucciones de acceso.'),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error(f"Error al crear usuario portal: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error al crear el usuario portal: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
