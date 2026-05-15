#!/usr/bin/env python3
"""
Teste pentru LicenseManager.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest import TestCase, main

from core.license_manager import LicenseManager, check_premium_access, get_license_manager


class TestLicenseManager(TestCase):
    """Teste pentru clasa LicenseManager."""
    
    def setUp(self):
        """Seteaza un fisier temporar pentru licente."""
        self.temp_dir = tempfile.mkdtemp()
        self.license_file = Path(self.temp_dir) / ".license"
        self.manager = LicenseManager(str(self.license_file))
    
    def tearDown(self):
        """Curata fisierul temporar."""
        if self.license_file.exists():
            self.license_file.unlink()
        os.rmdir(self.temp_dir)
    
    def test_machine_id_generation(self):
        """Testeaza generarea machine_id."""
        machine_id = self.manager._machine_id
        self.assertIsNotNone(machine_id)
        self.assertEqual(len(machine_id), 32)  # SHA256 hex[:32]
    
    def test_license_generation(self):
        """Testeaza generarea unei chei de licenta."""
        license_key = self.manager.generate_license_key(
            email="test@example.com",
            duration_days=30,
            secret_key="test-secret"
        )
        self.assertIsNotNone(license_key)
        self.assertTrue(len(license_key) > 50)  # Cheia ar trebui sa fie lunga
    
    def test_license_activation_success(self):
        """Testeaza activarea unei licente valide."""
        # Genereaza licenta
        license_key = self.manager.generate_license_key(
            email="test@example.com",
            duration_days=30,
            secret_key="test-secret"
        )
        
        # Activeaza licenta
        success, message = self.manager.activate(license_key, secret_key="test-secret")
        
        self.assertTrue(success)
        self.assertIn("activata", message)
        self.assertTrue(self.license_file.exists())
    
    def test_license_activation_invalid_signature(self):
        """Testeaza activarea cu semnatura invalida."""
        license_key = self.manager.generate_license_key(
            email="test@example.com",
            duration_days=30,
            secret_key="correct-secret"
        )
        
        # Incearca sa activeze cu secret gresit
        success, message = self.manager.activate(license_key, secret_key="wrong-secret")
        
        self.assertFalse(success)
        self.assertIn("invalida", message.lower())
    
    def test_license_expiration(self):
        """Testeaza detectarea licentei expirate."""
        # Genereaza licenta expirata (in trecut)
        from cryptography.fernet import Fernet
        import base64
        import hashlib
        import hmac
        import os as _os
        
        secret_key = "test-secret"
        issue_date = datetime.now() - timedelta(days=60)
        expiry_date = datetime.now() - timedelta(days=30)
        
        license_data = {
            "email": "expired@example.com",
            "issued": issue_date.isoformat(),
            "expires": expiry_date.isoformat(),
            "type": "pro",
            "version": "1.0",
        }
        
        # Serializeaza si semneaza
        data_json = json.dumps(license_data, sort_keys=True)
        signature = hmac.new(
            secret_key.encode(),
            data_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Cripteaza
        salt = _os.urandom(16)
        kdf = self.manager._derive_key(secret_key, salt)
        fernet = Fernet(kdf)
        encrypted_data = fernet.encrypt(data_json.encode())
        
        license_key = base64.urlsafe_b64encode(
            salt + encrypted_data + signature.encode()
        ).decode()
        
        # Incearca activarea
        success, message = self.manager.activate(license_key, secret_key=secret_key)
        
        self.assertFalse(success)
        self.assertIn("expirata", message.lower())
    
    def test_is_pro_without_license(self):
        """Testeaza is_pro() fara licenta."""
        self.assertFalse(self.manager.is_pro())
    
    def test_is_pro_with_valid_license(self):
        """Testeaza is_pro() cu licenta valida."""
        license_key = self.manager.generate_license_key(
            email="test@example.com",
            duration_days=30,
            secret_key="test-secret"
        )
        self.manager.activate(license_key, secret_key="test-secret")
        
        # Reincarca managerul
        new_manager = LicenseManager(str(self.license_file))
        self.assertTrue(new_manager.is_pro())
    
    def test_is_tool_allowed_free_tool(self):
        """Testeaza accesul la tool gratuit."""
        self.assertTrue(self.manager.is_tool_allowed("code"))
        self.assertTrue(self.manager.is_tool_allowed("files"))
        self.assertTrue(self.manager.is_tool_allowed("web"))
    
    def test_is_tool_allowed_premium_without_license(self):
        """Testeaza accesul la tool premium fara licenta."""
        self.assertFalse(self.manager.is_tool_allowed("desktop_capture"))
        self.assertFalse(self.manager.is_tool_allowed("windows_deep_sight"))
    
    def test_is_tool_allowed_premium_with_license(self):
        """Testeaza accesul la tool premium cu licenta."""
        license_key = self.manager.generate_license_key(
            email="test@example.com",
            duration_days=30,
            secret_key="test-secret"
        )
        self.manager.activate(license_key, secret_key="test-secret")
        
        # Reincarca managerul
        new_manager = LicenseManager(str(self.license_file))
        self.assertTrue(new_manager.is_tool_allowed("desktop_capture"))
        self.assertTrue(new_manager.is_tool_allowed("windows_deep_sight"))
    
    def test_get_license_info(self):
        """Testeaza obtinerea informatiilor despre licenta."""
        # Fara licenta
        info = self.manager.get_license_info()
        self.assertIsNone(info)
        
        # Cu licenta
        license_key = self.manager.generate_license_key(
            email="test@example.com",
            duration_days=30,
            secret_key="test-secret"
        )
        self.manager.activate(license_key, secret_key="test-secret")
        
        new_manager = LicenseManager(str(self.license_file))
        info = new_manager.get_license_info()
        
        self.assertIsNotNone(info)
        self.assertEqual(info["email"], "test@example.com")
        self.assertEqual(info["type"], "pro")
        self.assertTrue(info["is_valid"])
        self.assertIsNotNone(info["days_remaining"])
    
    def test_deactivate(self):
        """Testeaza dezactivarea licentei."""
        license_key = self.manager.generate_license_key(
            email="test@example.com",
            duration_days=30,
            secret_key="test-secret"
        )
        self.manager.activate(license_key, secret_key="test-secret")
        
        self.assertTrue(self.license_file.exists())
        
        success = self.manager.deactivate()
        self.assertTrue(success)
        self.assertFalse(self.license_file.exists())
        self.assertFalse(self.manager.is_pro())


class TestCheckPremiumAccess(TestCase):
    """Teste pentru functia check_premium_access."""
    
    def setUp(self):
        """Reset the global license manager."""
        import core.license_manager as lm
        lm._license_manager = None
    
    def test_free_tool_access(self):
        """Testeaza accesul la tool gratuit."""
        allowed, message = check_premium_access("code")
        self.assertTrue(allowed)
        self.assertEqual(message, "Access granted")
    
    def test_premium_tool_without_license(self):
        """Testeaza accesul la tool premium fara licenta."""
        allowed, message = check_premium_access("desktop_capture")
        self.assertFalse(allowed)
        self.assertIn("premium", message.lower())
    
    def test_premium_tool_with_license(self):
        """Testeaza accesul la tool premium cu licenta."""
        import tempfile
        from pathlib import Path
        
        temp_dir = tempfile.mkdtemp()
        license_file = Path(temp_dir) / ".license"
        
        # Seteaza license manager global
        import core.license_manager as lm
        lm._license_manager = lm.LicenseManager(str(license_file))
        
        # Genereaza si activeaza licenta
        license_key = lm._license_manager.generate_license_key(
            email="test@example.com",
            duration_days=30,
            secret_key="ana-max-secret-2026"
        )
        lm._license_manager.activate(license_key)
        
        allowed, message = check_premium_access("desktop_capture")
        self.assertTrue(allowed)
        
        # Curata
        if license_file.exists():
            license_file.unlink()
        os.rmdir(temp_dir)
        lm._license_manager = None


if __name__ == "__main__":
    main()