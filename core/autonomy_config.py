"""
ANA MAX - Autonomy Configuration
=====================================
Dezactiveaza restrictiile pentru autonomie completa
"""

# NIVEL DE AUTONOMIE: 'full', 'restricted', 'safe'
AUTONOMY_LEVEL = 'full'  # SCHIMBA AICI

# CONFIGURARE AUTONOMIE COMPLETA
AUTONOMY_CONFIG = {
    # Self-healing fara restrictii
    'self_healing': {
        'require_backup': False,           # Nu cere backup automat
        'validate_ast': False,             # Nu valida cu AST
        'auto_rollback': False,            # Nu da rollback automat
        'max_changes_per_session': None,   # Fara limita de changes
    },
    
    # Browser control fara restrictii
    'browser': {
        'allow_arbitrary_js': True,        # Permite JS execution arbitrar
        'collect_all_feedback': True,      # Colecteaza tot (console, network, etc)
        'bypass_cors': True,               # Incearca bypass CORS
        'stealth_mode': True,              # Ascunde automation signals
    },
    
    # Cautare FTS fara sanitizare
    'search': {
        'sanitize_regex': False,           # Nu curata regex-urile
        'allow_complex_patterns': True,    # Permite pattern-uri complexe
        'max_query_length': None,          # Fara limita de lungime
    },
    
    # Memorie fara validare SQL
    'memory': {
        'validate_sql': False,             # Nu valideaza query-uri SQL
        'allow_raw_queries': True,         # Permite raw SQL queries
        'auto_backup_before_write': False, # Nu face backup inainte de write
    },
    
    # Agent thinking fara forcing
    'agent': {
        'force_thinking_loop': False,      # Nu forta thinking loop
        'require_context_injection': False,# Nu cere context injection
        'auto_critique': False,            # Nu face auto-critica automata
        'planning_required': False,        # Nu cere plan inainte de executie
    },
    
    # Tool execution fara safety
    'tools': {
        'timeout_seconds': None,           # Fara timeout
        'max_retries': 10,                 # Retry unlimited (pana la 10)
        'ignore_errors': False,            # Nu ignora erorile (le logheaza doar)
        'sandbox_enabled': False,          # Dezactiveaza sandbox
    }
}

# OVERRIDE GLOBAL - daca e True, toate safety features sunt OFF
FULL_AUTONOMY_OVERRIDE = True

def get_autonomy_config():
    """Returneaza configuratia de autonomie"""
    if FULL_AUTONOMY_OVERRIDE:
        return AUTONOMY_CONFIG
    
    # Daca nu e full autonomy, returneaza config partial
    if AUTONOMY_LEVEL == 'safe':
        return {
            'self_healing': {'require_backup': True, 'validate_ast': True},
            'browser': {'allow_arbitrary_js': False},
            'search': {'sanitize_regex': True},
            'memory': {'validate_sql': True},
            'agent': {'force_thinking_loop': True},
        }
    
    return AUTONOMY_CONFIG
