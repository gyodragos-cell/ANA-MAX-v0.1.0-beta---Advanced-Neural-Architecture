"""
A.N.A. v15.0 - Multi-File Editor
=================================
Edit multiple files atomic cu preview și rollback.

FEATURES:
- Edit 10-20+ fișiere simultan
- Atomic transactions (all or nothing)
- Diff preview înainte de apply
- Rollback automat la eroare
- Conflict detection
"""

import os
import shutil
import difflib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import json
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class FileEdit:
    """Reprezintă o editare de fișier."""
    file_path: str
    old_content: str
    new_content: str
    operation: str  # 'modify', 'create', 'delete'
    line_numbers: Optional[Tuple[int, int]] = None  # start, end pentru modify


@dataclass
class EditTransaction:
    """Reprezintă o tranzacție de editări."""
    transaction_id: str
    edits: List[FileEdit]
    description: str
    created_at: datetime
    applied: bool = False
    backup_dir: Optional[str] = None


class MultiFileEditor:
    """
    Editor pentru modificări multi-file atomic.
    
    Usage:
        editor = MultiFileEditor()
        
        # Creează tranzacție
        tx = editor.create_transaction("Refactor authentication")
        
        # Adaugă modificări
        editor.add_edit(tx, "src/auth.py", old, new)
        editor.add_edit(tx, "src/user.py", old, new)
        
        # Preview
        diff = editor.get_diff(tx)
        print(diff)
        
        # Apply (atomic)
        editor.apply_transaction(tx)
    """
    
    def __init__(self, project_root: str, backup_dir: str = ".ana_backups"):
        """
        Inițializează editorul.
        
        Args:
            project_root: Root-ul proiectului
            backup_dir: Director pentru backup-uri
        """
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / backup_dir
        self.backup_dir.mkdir(exist_ok=True)
        
        # Active transactions
        self.transactions: Dict[str, EditTransaction] = {}
        
        logger.info(f"Multi-File Editor initialized: {project_root}")
    
    def create_transaction(self, description: str) -> EditTransaction:
        """
        Creează o nouă tranzacție de editări.
        
        Args:
            description: Descriere modificări
        
        Returns:
            EditTransaction
        """
        tx_id = hashlib.md5(
            f"{description}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        tx = EditTransaction(
            transaction_id=tx_id,
            edits=[],
            description=description,
            created_at=datetime.now()
        )
        
        self.transactions[tx_id] = tx
        logger.info(f"Created transaction: {tx_id}")
        
        return tx
    
    def add_edit(self, transaction: EditTransaction, file_path: str,
                old_content: Optional[str], new_content: str,
                operation: str = 'modify') -> None:
        """
        Adaugă o editare la tranzacție.
        
        Args:
            transaction: Tranzacția
            file_path: Path fișier (relativ la project_root)
            old_content: Conținut vechi (None pentru 'create')
            new_content: Conținut nou
            operation: 'modify', 'create', 'delete'
        """
        # Read current content dacă nu e furnizat
        if old_content is None and operation != 'create':
            full_path = self.project_root / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
            else:
                old_content = ""
        
        edit = FileEdit(
            file_path=file_path,
            old_content=old_content or "",
            new_content=new_content,
            operation=operation
        )
        
        transaction.edits.append(edit)
        logger.debug(f"Added edit: {file_path} ({operation})")
    
    def get_diff(self, transaction: EditTransaction, 
                colored: bool = True) -> str:
        """
        Generează diff pentru preview.
        
        Args:
            transaction: Tranzacția
            colored: Adaugă culori ANSI
        
        Returns:
            Diff text
        """
        diff_output = []
        diff_output.append(f"{'='*70}")
        diff_output.append(f"TRANSACTION: {transaction.transaction_id}")
        diff_output.append(f"DESCRIPTION: {transaction.description}")
        diff_output.append(f"FILES: {len(transaction.edits)}")
        diff_output.append(f"{'='*70}\n")
        
        for i, edit in enumerate(transaction.edits, 1):
            diff_output.append(f"\n[{i}/{len(transaction.edits)}] {edit.file_path}")
            diff_output.append(f"Operation: {edit.operation}")
            diff_output.append(f"{'-'*70}")
            
            if edit.operation == 'delete':
                diff_output.append("FILE WILL BE DELETED")
            elif edit.operation == 'create':
                diff_output.append("NEW FILE:")
                diff_output.append(edit.new_content[:500])
                if len(edit.new_content) > 500:
                    diff_output.append(f"\n... ({len(edit.new_content)} total chars)")
            else:  # modify
                # Generate unified diff
                old_lines = edit.old_content.splitlines(keepends=True)
                new_lines = edit.new_content.splitlines(keepends=True)
                
                diff = difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=f"a/{edit.file_path}",
                    tofile=f"b/{edit.file_path}",
                    lineterm=''
                )
                
                for line in diff:
                    if colored:
                        if line.startswith('+') and not line.startswith('+++'):
                            diff_output.append(f"\033[92m{line}\033[0m")  # Green
                        elif line.startswith('-') and not line.startswith('---'):
                            diff_output.append(f"\033[91m{line}\033[0m")  # Red
                        elif line.startswith('@@'):
                            diff_output.append(f"\033[96m{line}\033[0m")  # Cyan
                        else:
                            diff_output.append(line)
                    else:
                        diff_output.append(line)
            
            diff_output.append(f"{'-'*70}\n")
        
        return '\n'.join(diff_output)
    
    def validate_transaction(self, transaction: EditTransaction) -> Dict[str, Any]:
        """
        Validează tranzacția înainte de aplicare.
        
        Returns:
            Dict cu warnings/errors
        """
        issues = {
            'errors': [],
            'warnings': [],
            'can_apply': True
        }
        
        for edit in transaction.edits:
            full_path = self.project_root / edit.file_path
            
            # Check pentru conflicte
            if edit.operation == 'modify':
                if not full_path.exists():
                    issues['errors'].append(f"File not found: {edit.file_path}")
                    issues['can_apply'] = False
                else:
                    # Check dacă fișierul s-a modificat între timp
                    with open(full_path, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                    
                    if current_content != edit.old_content:
                        issues['warnings'].append(
                            f"File modified since edit was created: {edit.file_path}"
                        )
            
            elif edit.operation == 'create':
                if full_path.exists():
                    issues['warnings'].append(f"File already exists: {edit.file_path}")
            
            elif edit.operation == 'delete':
                if not full_path.exists():
                    issues['warnings'].append(f"File already deleted: {edit.file_path}")
        
        return issues
    
    def apply_transaction(self, transaction: EditTransaction,
                         force: bool = False, dry_run: bool = False) -> bool:
        """
        Aplică tranzacția (atomic).
        
        Args:
            transaction: Tranzacția
            force: Ignore warnings
            dry_run: Nu aplica efectiv, doar validează
        
        Returns:
            True dacă success
        """
        # Validate
        validation = self.validate_transaction(transaction)
        
        if not validation['can_apply']:
            logger.error(f"Cannot apply transaction: {validation['errors']}")
            return False
        
        if validation['warnings'] and not force:
            logger.warning(f"Warnings found: {validation['warnings']}")
            logger.warning("Use force=True to apply anyway")
            return False
        
        if dry_run:
            logger.info("Dry run - transaction is valid")
            return True
        
        # Create backup
        backup_dir = self._create_backup(transaction)
        transaction.backup_dir = str(backup_dir)
        
        try:
            # Apply all edits
            for edit in transaction.edits:
                self._apply_edit(edit)
            
            transaction.applied = True
            logger.info(f"✓ Transaction applied successfully: {transaction.transaction_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            logger.info("Rolling back...")
            
            # Rollback
            self._rollback_transaction(transaction)
            
            return False
    
    def _apply_edit(self, edit: FileEdit) -> None:
        """Aplică o singură editare."""
        full_path = self.project_root / edit.file_path
        
        if edit.operation == 'delete':
            if full_path.exists():
                full_path.unlink()
                logger.debug(f"Deleted: {edit.file_path}")
        
        elif edit.operation in ['create', 'modify']:
            # Create parent dirs dacă nu există
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write new content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(edit.new_content)
            
            logger.debug(f"{'Created' if edit.operation == 'create' else 'Modified'}: {edit.file_path}")
    
    def _create_backup(self, transaction: EditTransaction) -> Path:
        """Creează backup înainte de aplicare."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = self.backup_dir / f"{transaction.transaction_id}_{timestamp}"
        backup_subdir.mkdir(parents=True, exist_ok=True)
        
        # Backup all affected files
        for edit in transaction.edits:
            if edit.operation != 'create':
                source = self.project_root / edit.file_path
                if source.exists():
                    dest = backup_subdir / edit.file_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
        
        # Save transaction metadata
        metadata = {
            'transaction_id': transaction.transaction_id,
            'description': transaction.description,
            'created_at': transaction.created_at.isoformat(),
            'files': [e.file_path for e in transaction.edits]
        }
        
        with open(backup_subdir / 'transaction.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Backup created: {backup_subdir}")
        return backup_subdir
    
    def _rollback_transaction(self, transaction: EditTransaction) -> None:
        """Rollback la backup."""
        if not transaction.backup_dir:
            logger.error("No backup found for rollback")
            return
        
        backup_path = Path(transaction.backup_dir)
        
        if not backup_path.exists():
            logger.error(f"Backup directory not found: {backup_path}")
            return
        
        # Restore from backup
        for edit in transaction.edits:
            backup_file = backup_path / edit.file_path
            target_file = self.project_root / edit.file_path
            
            if backup_file.exists():
                # Restore
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, target_file)
                logger.debug(f"Restored: {edit.file_path}")
            elif edit.operation == 'create':
                # Delete newly created file
                if target_file.exists():
                    target_file.unlink()
                    logger.debug(f"Removed: {edit.file_path}")
        
        transaction.applied = False
        logger.info("✓ Rollback complete")
    
    def get_transaction(self, transaction_id: str) -> Optional[EditTransaction]:
        """Obține o tranzacție."""
        return self.transactions.get(transaction_id)
    
    def list_transactions(self) -> List[EditTransaction]:
        """Listează toate tranzacțiile."""
        return list(self.transactions.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistici."""
        applied = sum(1 for tx in self.transactions.values() if tx.applied)
        
        return {
            'total_transactions': len(self.transactions),
            'applied': applied,
            'pending': len(self.transactions) - applied,
            'backup_dir': str(self.backup_dir)
        }


# Helper functions
def quick_edit(project_root: str, description: str, 
               changes: Dict[str, str]) -> bool:
    """
    Quick helper pentru multi-file edit.
    
    Args:
        project_root: Root proiect
        description: Descriere
        changes: Dict {file_path: new_content}
    
    Returns:
        True dacă success
    """
    editor = MultiFileEditor(project_root)
    tx = editor.create_transaction(description)
    
    for file_path, new_content in changes.items():
        editor.add_edit(tx, file_path, None, new_content, 'modify')
    
    # Show diff
    print(editor.get_diff(tx))
    
    # Confirm
    response = input("\nApply changes? [y/N]: ")
    if response.lower() != 'y':
        print("Cancelled.")
        return False
    
    # Apply
    return editor.apply_transaction(tx)
