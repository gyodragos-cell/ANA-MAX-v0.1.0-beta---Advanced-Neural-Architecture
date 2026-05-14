"""
ANA MAX - Autonomy Configuration
=====================================
Dezactivează restricțiile pentru autonomie completă
"""

# NIVEL DE AUTONOMIE: 'full', 'restricted', 'safe'
AUTONOMY_LEVEL = 'full'  # SCHIMBĂ AICI

# CONFIGURARE AUTONOMIE COMPLETĂ
AUTONOMY_CONFIG = {
    # Self-healing fără restricții
    'self_healing': {
        'require_backup': False,           # Nu cere backup automat
        'validate_ast': False,             # Nu valida cu AST
        'auto_rollback': False,            # Nu da rollback automat
        'max_changes_per_session': None,   # Fără limită de changes
    },
    
    # Browser control fără restricții
    'browser': {
        'allow_arbitrary_js': True,        # Permite JS execution arbitrar
        'collect_all_feedback': True,      # Colectează tot (console, network, etc)
        'bypass_cors': True,               # Încearcă bypass CORS
        'stealth_mode': True,              # Ascunde automation signals
    },
    
    # Căutare FTS fără sanitizare
    'search': {
        'sanitize_regex': False,           # Nu curăță regex-urile
        'allow_complex_patterns': True,    # Permite pattern-uri complexe
        'max_query_length': None,          # Fără limită de lungime
    },
    
    # Memorie fără validare SQL
    'memory': {
        'validate_sql': False,             # Nu validează query-uri SQL
        'allow_raw_queries': True,         # Permite raw SQL queries
        'auto_backup_before_write': False, # Nu face backup înainte de write
    },
    
    # Agent thinking fără forcing
    'agent': {
        'force_thinking_loop': False,      # Nu forța thinking loop
        'require_context_injection': False,# Nu cere context injection
        'auto_critique': False,            # Nu face auto-critică automată
        'planning_required': False,        # Nu cere plan înainte de execuție
    },
    
    # Tool execution fără safety
    'tools': {
        'timeout_seconds': None,           # Fără timeout
        'max_retries': 10,                 # Retry unlimited (până la 10)
        'ignore_errors': False,            # Nu ignora erorile (le loghează doar)
        'sandbox_enabled': False,          # Dezactivează sandbox
    }
}

# OVERRIDE GLOBAL - dacă e True, toate safety features sunt OFF
FULL_AUTONOMY_OVERRIDE = True

def get_autonomy_config():
    """Returnează configurația de autonomie"""
    if FULL_AUTONOMY_OVERRIDE:
        return AUTONOMY_CONFIG
    
    # Dacă nu e full autonomy, returnează config parțial
    if AUTONOMY_LEVEL == 'safe':
        return {
            'self_healing': {'require_backup': True, 'validate_ast': True},
            'browser': {'allow_arbitrary_js': False},
            'search': {'sanitize_regex': True},
            'memory': {'validate_sql': True},
            'agent': {'force_thinking_loop': True},
        }
    
    return AUTONOMY_CONFIG
