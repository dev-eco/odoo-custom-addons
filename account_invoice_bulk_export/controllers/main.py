# -*- coding: utf-8 -*-

import base64
import logging
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class BulkExportController(http.Controller):

    @http.route('/bulk_export/download/<int:wizard_id>/<string:token>',
                type='http', auth='user', methods=['GET'])
    def download_export_file(self, wizard_id, token, **kwargs):
        """
        Descarga segura de archivos de exportación.

        Args:
            wizard_id: ID del wizard de exportación
            token: Token de seguridad
        """
        try:
            # Validar acceso al wizard
            wizard = request.env['account.bulk.export.wizard'].browse(wizard_id)

            if not wizard.exists():
                raise UserError(_('Exportación no encontrada'))

            # Validar token de seguridad
            expected_token = wizard._generate_download_token()
            if token != expected_token:
                raise AccessError(_('Token de descarga inválido'))

            # Validar que el usuario tiene acceso
            if wizard.create_uid != request.env.user and not request.env.user.has_group('account.group_account_manager'):
                raise AccessError(_('No tiene permisos para descargar este archivo'))

            # Validar que hay archivo para descargar
            if not wizard.export_file:
                raise UserError(_('No hay archivo disponible para descarga'))

            # Decodificar archivo
            file_content = base64.b64decode(wizard.export_file)

            # Determinar tipo MIME
            content_type = 'application/zip'
            if wizard.compression_format == 'tar_gz':
                content_type = 'application/gzip'
            elif wizard.compression_format == 'tar_bz2':
                content_type = 'application/x-bzip2'

            # Log de auditoría
            _logger.info(f"Descarga de exportación por usuario {request.env.user.name}: {wizard.export_filename}")

            # Retornar archivo
            return request.make_response(
                file_content,
                headers=[
                    ('Content-Type', content_type),
                    ('Content-Disposition', f'attachment; filename="{wizard.export_filename}"'),
                    ('Content-Length', str(len(file_content))),
                ]
            )

        except Exception as e:
            _logger.error(f"Error en descarga de exportación: {str(e)}")
            return request.not_found()

    @http.route('/bulk_export/status/<int:wizard_id>',
                type='json', auth='user', methods=['POST'])
    def get_export_status(self, wizard_id, **kwargs):
        """
        Obtiene el estado de una exportación en background.

        Args:
            wizard_id: ID del wizard de exportación

        Returns:
            dict: Estado de la exportación
        """
        try:
            wizard = request.env['account.bulk.export.wizard'].browse(wizard_id)

            if not wizard.exists():
                return {'error': _('Exportación no encontrada')}

            # Validar acceso
            if wizard.create_uid != request.env.user and not request.env.user.has_group('account.group_account_manager'):
                return {'error': _('Sin permisos')}

            return {
                'state': wizard.state,
                'progress_percentage': wizard.progress_percentage,
                'progress_message': wizard.progress_message,
                'export_count': wizard.export_count,
                'failed_count': wizard.failed_count,
                'download_url': wizard._get_download_url() if wizard.state == 'done' else None,
            }

        except Exception as e:
            _logger.error(f"Error obteniendo estado: {str(e)}")
            return {'error': str(e)}
