# Primero los modelos fundamentales
from . import document_ocr
from . import document_extraction
from . import document_type  # Modelo base sin dependencias
from . import res_config_settings  # Configuración general

# Luego modelos principales
from . import document_automation  # Modelo principal

from . import document_template
from . import document_rule

# Finalmente extensiones y funcionalidades adicionales
#from . import mail_thread  # Extensión de mail.thread
