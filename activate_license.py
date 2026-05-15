#!/usr/bin/env python3
"""
ANA MAX - License Activator
============================
Script simplu pentru activarea unei licente Pro.

Utilizare:
    python activate_license.py --key YOUR_LICENSE_KEY
"""

import argparse
import sys
from core.license_manager import LicenseManager


def main():
    parser = argparse.ArgumentParser(
        description="ANA MAX License Activator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemple:
    python activate_license.py --key YOUR_LICENSE_KEY
    python activate_license.py -k YOUR_LICENSE_KEY
        """
    )
    
    parser.add_argument(
        "--key", "-k",
        required=True,
        help="Cheia de licenta primita"
    )
    
    parser.add_argument(
        "--secret", "-s",
        default="ana-max-secret-2026",
        help="Cheia secreta pentru validare (default: ana-max-secret-2026)"
    )
    
    args = parser.parse_args()
    
    print("\nANA MAX License Activator")
    print("=" * 40)
    
    manager = LicenseManager()
    success, message = manager.activate(args.key, secret_key=args.secret)
    
    if success:
        print(f"\n✅ SUCCESS: {message}")
        print("\nLicenta a fost activata cu succes!")
        print("Restartati serverul ANA MAX pentru a folosi tool-urile premium.")
    else:
        print(f"\n❌ FAILED: {message}")
        print("\nNu s-a putut activa licenta. Verificati:")
        print("  1. Cheia de licenta este corecta")
        print("  2. Licenta nu a expirat")
        print("  3. Nu ati mai activat pe acest calculator")
        sys.exit(1)


if __name__ == "__main__":
    main()