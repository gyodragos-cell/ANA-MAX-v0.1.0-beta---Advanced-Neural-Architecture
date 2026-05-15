#!/usr/bin/env python3
"""
ANA MAX - License Key Generator
================================
Script utilitar pentru generarea licentelor Pro.
Folositi acest script doar pentru a genera licente pentru distributie.

Utilizare:
    python generate_license.py --email user@example.com --days 30
    python generate_license.py --email user@example.com --days 7 --trial
"""

import argparse
import sys
from datetime import datetime

# Importa LicenseManager
from core.license_manager import LicenseManager


def generate_license(email: str, days: int, secret_key: str = "ana-max-secret-2026") -> str:
    """
    Genereaza o cheie de licenta.
    
    Args:
        email: Email-ul utilizatorului
        days: Durata in zile
        secret_key: Cheia secreta (default: ana-max-secret-2026)
    
    Returns:
        Cheia de licenta
    """
    manager = LicenseManager()
    return manager.generate_license_key(email=email, duration_days=days, secret_key=secret_key)


def main():
    parser = argparse.ArgumentParser(
        description="ANA MAX License Key Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemple:
    python generate_license.py --email user@example.com --days 30
    python generate_license.py --email user@example.com --days 7 --trial
    python generate_license.py --email user@example.com --days 365 --key custom-secret-key
        """
    )
    
    parser.add_argument(
        "--email", "-e",
        required=True,
        help="Email-ul utilizatorului pentru licenta"
    )
    
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=30,
        help="Durata licentei in zile (default: 30)"
    )
    
    parser.add_argument(
        "--trial", "-t",
        action="store_true",
        help="Genereaza licenta de trial (maxim 7 zile)"
    )
    
    parser.add_argument(
        "--key", "-k",
        default="ana-max-secret-2026",
        help="Cheia secreta pentru generare (default: ana-max-secret-2026)"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Afiseaza doar cheia de licenta (fara alte mesaje)"
    )
    
    args = parser.parse_args()
    
    # Valideaza days pentru trial
    if args.trial and args.days > 7:
        print("Eroare: Licenta de trial nu poate depasi 7 zile.", file=sys.stderr)
        sys.exit(1)
    
    # Genereaza licenta
    days = min(args.days, 7) if args.trial else args.days
    license_key = generate_license(args.email, days, args.key)
    
    if args.quiet:
        print(license_key)
    else:
        print("\n" + "=" * 60)
        print("ANA MAX License Key Generator")
        print("=" * 60)
        print(f"Email:          {args.email}")
        print(f"Durata:         {days} zile")
        print(f"Tip:            {'Trial' if args.trial or days <= 7 else 'Pro'}")
        print(f"Data expirare:  {(datetime.now() + __import__('datetime').timedelta(days=days)).strftime('%Y-%m-%d')}")
        print("-" * 60)
        print(f"LICENTA KEY:")
        print(f"  {license_key}")
        print("-" * 60)
        print("\nInstructiuni activare:")
        print("  1. Trimite aceasta cheie utilizatorului")
        print("  2. Utilizatorul ruleaza: python -c \"from core.license_manager import LicenseManager; m = LicenseManager(); m.activate('CHEIA_AICI')\"")
        print("  3. Sau plaseaza cheia in fisierul .license")
        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()