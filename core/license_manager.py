#!/usr/bin/env python3
"""
ANA MAX - License Manager
=========================
Sistem de licensing pentru functionalitatile Premium.
"""

import base64
import hashlib
import hmac
import json
import os
import platform
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class LicenseError(Exception):
    """Exception pentru erori de licensing."""
    pass


class LicenseManager:
    """Manager pentru licentele ANA MAX."""
    
    # Premium tools care necesita licenta
    PREMIUM_TOOLS = [
        "live_desktop_viewer", 
        "desktop_control",
        "desktop_control_tool",
        "windows_insight",
        "windows_insight_tool",
        "windows_deep_sight",
    ]
    
    def __init__(self, license_file: Optional[str] = None):
        """
        Initializeaza LicenseManager.
        
        Args:
            license_file: Path catre fisierul de licenta (default: .license)
        """
        self.license_file = Path(license_file or ".license")
        self._license_data: Optional[Dict] = None
        self._machine_id = self._get_machine_id()
        
    def _get_machine_id(self) -> str:
        """Genereaza un ID unic pentru masina curenta."""
        # Combina mai multe identificatori de sistem
        components = [
            platform.node(),  # Nume calculator
            platform.machine(),  # Arhitectura
            str(uuid.getnode()),  # MAC/node id fallback stabil
        ]
        raw_id = "|".join(components)
        return hashlib.sha256(raw_id.encode()).hexdigest()[:32]
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Deriveaza o cheie de criptare din parola."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def generate_license_key(self, email: str, duration_days: int = 30, 
                            secret_key: str = "ana-max-secret-2026") -> str:
        """
        Genereaza o cheie de licenta (doar pentru serverul de licensing).
        
        Args:
            email: Email-ul utilizatorului
            duration_days: Durata licentei in zile
            secret_key: Cheia secreta pentru generare
            
        Returns:
            Cheia de licenta generata
        """
        issue_date = datetime.now()
        expiry_date = issue_date + timedelta(days=duration_days)
        
        license_data = {
            "email": email,
            "issued": issue_date.isoformat(),
            "expires": expiry_date.isoformat(),
            "type": "pro" if duration_days > 7 else "trial",
            "version": "1.0",
        }
        
        # Serializeaza si semneaza
        data_json = json.dumps(license_data, sort_keys=True)
        signature = hmac.new(
            secret_key.encode(),
            data_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Cripteaza datele
        salt = os.urandom(16)
        key = self._derive_key(secret_key, salt)
        fernet = Fernet(key)
        
        encrypted_data = fernet.encrypt(data_json.encode())
        
        # Combina totul intr-o cheie
        license_key = base64.urlsafe_b64encode(
            salt + encrypted_data + signature.encode()
        ).decode()
        
        return license_key
    
    def activate(self, license_key: str, secret_key: str = "ana-max-secret-2026") -> Tuple[bool, str]:
        """
        Activeaza o licenta.
        
        Args:
            license_key: Cheia de licenta
            secret_key: Cheia secreta pentru validare
            
        Returns:
            (success, message)
        """
        try:
            # Decodifica cheia
            raw_data = base64.urlsafe_b64decode(license_key.encode())
            
            # Extrage sarea, datele criptate si semnatura
            salt = raw_data[:16]
            encrypted_data = raw_data[16:-64]  # SHA256 = 64 caractere hex
            signature_hex = raw_data[-64:].decode()
            
            # Deriveaza cheia si decripteaza
            key = self._derive_key(secret_key, salt)
            fernet = Fernet(key)
            decrypted_json = fernet.decrypt(encrypted_data).decode()
            
            # Verifica semnatura
            signature_valid = hmac.compare_digest(
                hmac.new(secret_key.encode(), decrypted_json.encode(), hashlib.sha256).hexdigest(),
                signature_hex
            )
            
            if not signature_valid:
                return False, "Licenta invalida: semnatura nu corespunde"
            
            # Parseaza datele
            license_data = json.loads(decrypted_json)
            
            # Verifica expirarea
            expiry_date = datetime.fromisoformat(license_data["expires"])
            if datetime.now() > expiry_date:
                return False, f"Licenta expirata la {expiry_date.strftime('%Y-%m-%d')}"
            
            # Salveaza licenta
            license_data["activated"] = datetime.now().isoformat()
            license_data["machine_id"] = self._machine_id
            
            self._save_license(license_data)
            
            return True, f"Licenta {license_data['type']} activata pana la {expiry_date.strftime('%Y-%m-%d')}"
            
        except InvalidToken:
            return False, "Licenta invalida: cheia secreta nu poate decripta licenta"
        except Exception as e:
            return False, f"Eroare la activare: {str(e)}"
    
    def _save_license(self, license_data: Dict) -> None:
        """Salveaza datele licentei in fisier."""
        self.license_file.write_text(json.dumps(license_data, indent=2))
        self._license_data = license_data
    
    def load_license(self) -> bool:
        """Incarca licenta din fisier."""
        if not self.license_file.exists():
            return False
        
        try:
            self._license_data = json.loads(self.license_file.read_text())
            
            # Verifica daca licenta este inca valida
            if "expires" in self._license_data:
                expiry_date = datetime.fromisoformat(self._license_data["expires"])
                if datetime.now() > expiry_date:
                    self._license_data = None
                    return False
            
            return True
        except (json.JSONDecodeError, KeyError):
            self._license_data = None
            return False
    
    def is_pro(self) -> bool:
        """Verifica daca utilizatorul are licenta Pro."""
        if self._license_data is None:
            self.load_license()
        
        if self._license_data is None:
            return False
        
        # Verifica expirarea
        expiry_date = datetime.fromisoformat(self._license_data["expires"])
        if datetime.now() > expiry_date:
            return False
        
        return self._license_data.get("type") in ("pro", "trial")
    
    def get_license_info(self) -> Optional[Dict]:
        """Returneaza informatii despre licenta."""
        if self._license_data is None:
            self.load_license()
        
        if self._license_data is None:
            return None
        
        return {
            "type": self._license_data.get("type", "free"),
            "email": self._license_data.get("email", "unknown"),
            "expires": self._license_data.get("expires"),
            "is_valid": self.is_pro(),
            "days_remaining": (datetime.fromisoformat(self._license_data["expires"]) - datetime.now()).days
                if self._license_data.get("expires") else None,
        }
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Verifica daca un tool este permis in functie de licenta.
        
        Args:
            tool_name: Numele tool-ului
            
        Returns:
            True daca tool-ul este permis
        """
        if tool_name not in self.PREMIUM_TOOLS:
            return True  # Tool gratuit
        
        return self.is_pro()
    
    def deactivate(self) -> bool:
        """Dezactiveaza licenta curenta."""
        if self.license_file.exists():
            self.license_file.unlink()
            self._license_data = None
            return True
        return False


# Singleton global
_license_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """Returneaza instanta globala LicenseManager."""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


def check_premium_access(tool_name: str) -> Tuple[bool, str]:
    """
    Verifica accesul la un tool premium.
    
    Args:
        tool_name: Numele tool-ului
        
    Returns:
        (allowed, message)
    """
    manager = get_license_manager()
    
    if manager.is_tool_allowed(tool_name):
        return True, "Access granted"
    
    license_info = manager.get_license_info()
    if license_info:
        return False, (
            f"Tool-ul '{tool_name}' este premium. "
            f"Licenta ta {license_info['type']} este expirata sau nu acopera acest tool. "
            f"Zile ramase: {license_info['days_remaining']}. "
            "Te rog sa iti reinnoiesti licenta."
        )
    
    return False, (
        f"Tool-ul '{tool_name}' este premium. "
        "Ai nevoie de o licenta Pro pentru a-l folosi. "
        "Visit https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture for more information."
    )
