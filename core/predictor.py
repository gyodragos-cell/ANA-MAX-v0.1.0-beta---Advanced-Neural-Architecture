"""
🔮 Ana Behavior Predictor
Anticipeaza nevoile utilizatorului bazat pe pattern-uri invatate
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import json


class BehaviorPredictor:
    """Prezice comportamentul si nevoile utilizatorului"""
    
    def __init__(self, db_path: str = "memory/learning.db"):
        self.db_path = db_path
    
    def predict_next_action(self) -> Optional[Dict[str, Any]]:
        """Prezice urmatoarea actiune probabila a utilizatorului"""
        now = datetime.now()
        current_hour = now.hour
        current_day = now.weekday()
        
        predictions = []
        
        # Predictie bazata pe ora zilei
        time_prediction = self._predict_by_time(current_hour, current_day)
        if time_prediction:
            predictions.append(time_prediction)
        
        # Predictie bazata pe pattern-uri recente
        recent_prediction = self._predict_by_recent_activity()
        if recent_prediction:
            predictions.append(recent_prediction)
        
        # Predictie bazata pe secvente
        sequence_prediction = self._predict_by_sequence()
        if sequence_prediction:
            predictions.append(sequence_prediction)
        
        if not predictions:
            return None
        
        # Returneaza predictia cu cea mai mare incredere
        return max(predictions, key=lambda x: x['confidence'])
    
    def _predict_by_time(self, hour: int, day: int) -> Optional[Dict[str, Any]]:
        """Prezice bazat pe ora si ziua"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Ce fisiere creeaza de obicei la aceasta ora?
        cursor.execute("""
            SELECT file_extension, COUNT(*) as count
            FROM file_events
            WHERE hour_of_day = ? AND day_of_week = ?
            AND event_type = 'created'
            AND timestamp > datetime('now', '-30 days')
            GROUP BY file_extension
            ORDER BY count DESC
            LIMIT 1
        """, (hour, day))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[1] >= 3:  # Minim 3 ocurente
            return {
                'type': 'time_based',
                'action': 'create_file',
                'details': {
                    'file_type': result[0],
                    'reason': f'De obicei creezi fisiere {result[0]} la aceasta ora'
                },
                'confidence': min(0.9, result[1] / 10)
            }
        
        return None
    
    def _predict_by_recent_activity(self) -> Optional[Dict[str, Any]]:
        """Prezice bazat pe activitatea recenta"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Ultimele 5 fisiere create
        cursor.execute("""
            SELECT file_extension, file_path
            FROM file_events
            WHERE event_type = 'created'
            AND timestamp > datetime('now', '-1 hour')
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        
        recent_files = cursor.fetchall()
        conn.close()
        
        if len(recent_files) >= 3:
            # Detecteaza daca lucreaza la un proiect
            extensions = [f[0] for f in recent_files]
            
            if extensions.count('.py') >= 2:
                return {
                    'type': 'recent_activity',
                    'action': 'python_project',
                    'details': {
                        'suggestion': 'Pare ca lucrezi la un proiect Python. Ai nevoie de ajutor?'
                    },
                    'confidence': 0.75
                }
            
            if extensions.count('.js') >= 2 or extensions.count('.ts') >= 2:
                return {
                    'type': 'recent_activity',
                    'action': 'javascript_project',
                    'details': {
                        'suggestion': 'Lucrezi la JavaScript/TypeScript. Pot ajuta cu debugging?'
                    },
                    'confidence': 0.75
                }
        
        return None
    
    def _predict_by_sequence(self) -> Optional[Dict[str, Any]]:
        """Prezice bazat pe secvente de actiuni"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Detecteaza secvente comune
        cursor.execute("""
            SELECT file_path, event_type, timestamp
            FROM file_events
            WHERE timestamp > datetime('now', '-10 minutes')
            ORDER BY timestamp ASC
        """)
        
        events = cursor.fetchall()
        conn.close()
        
        if len(events) >= 3:
            # Detecteaza pattern: creare folder → creare README → creare main file
            paths = [e[0] for e in events]
            
            # Verifica daca a creat un folder nou
            folders_created = [p for p in paths if '\\' in p or '/' in p]
            readme_created = any('README' in p.upper() for p in paths)
            
            if folders_created and readme_created:
                return {
                    'type': 'sequence',
                    'action': 'new_project_setup',
                    'details': {
                        'suggestion': 'Creezi un proiect nou? Pot genera structura completa!'
                    },
                    'confidence': 0.85
                }
        
        return None
    
    def get_contextual_suggestions(self) -> List[Dict[str, Any]]:
        """Ofera sugestii contextuale bazate pe invatare"""
        suggestions = []
        
        # Sugestii bazate pe pattern-uri
        patterns = self._analyze_repetitive_tasks()
        for pattern in patterns:
            suggestions.append({
                'type': 'automation',
                'title': f"Automatizeaza: {pattern['task']}",
                'description': pattern['description'],
                'confidence': pattern['confidence']
            })
        
        # Sugestii bazate pe timp
        time_suggestions = self._get_time_based_suggestions()
        suggestions.extend(time_suggestions)
        
        return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)
    
    def _analyze_repetitive_tasks(self) -> List[Dict[str, Any]]:
        """Detecteaza task-uri repetitive care pot fi automatizate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        patterns = []
        
        # Detecteaza crearea repetitiva de foldere cu acelasi pattern
        cursor.execute("""
            SELECT file_path, COUNT(*) as count
            FROM file_events
            WHERE event_type = 'created'
            AND timestamp > datetime('now', '-30 days')
            GROUP BY file_path
            HAVING count >= 3
        """)
        
        repetitive = cursor.fetchall()
        
        for path, count in repetitive:
            patterns.append({
                'task': f'Creare {path}',
                'description': f'Ai creat acest fisier de {count} ori. Pot crea un template!',
                'confidence': min(0.9, count / 10)
            })
        
        conn.close()
        return patterns
    
    def _get_time_based_suggestions(self) -> List[Dict[str, Any]]:
        """Sugestii bazate pe ora curenta"""
        now = datetime.now()
        suggestions = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Ce aplicatii foloseste de obicei la aceasta ora?
        cursor.execute("""
            SELECT process_name, COUNT(*) as count
            FROM process_events
            WHERE hour_of_day = ?
            AND timestamp > datetime('now', '-30 days')
            GROUP BY process_name
            ORDER BY count DESC
            LIMIT 3
        """, (now.hour,))
        
        apps = cursor.fetchall()
        
        for app, count in apps:
            if count >= 5:
                suggestions.append({
                    'type': 'time_based',
                    'title': f'Porneste {app}',
                    'description': f'De obicei folosesti {app} la aceasta ora',
                    'confidence': min(0.8, count / 15)
                })
        
        conn.close()
        return suggestions
    
    def learn_from_feedback(self, prediction_id: int, feedback: str):
        """Invata din feedback-ul utilizatorului"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE predictions
            SET user_feedback = ?
            WHERE id = ?
        """, (feedback, prediction_id))
        
        conn.commit()
        conn.close()
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """Genereaza un rezumat al zilei"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        # Fisiere create azi
        cursor.execute("""
            SELECT COUNT(*) FROM file_events
            WHERE DATE(timestamp) = DATE('now')
            AND event_type = 'created'
        """)
        files_created = cursor.fetchone()[0]
        
        # Aplicatii folosite azi
        cursor.execute("""
            SELECT process_name, SUM(duration_seconds) as total_time
            FROM process_events
            WHERE DATE(timestamp) = DATE('now')
            GROUP BY process_name
            ORDER BY total_time DESC
            LIMIT 5
        """)
        apps_used = dict(cursor.fetchall())
        
        # Ore active
        cursor.execute("""
            SELECT MIN(hour_of_day), MAX(hour_of_day)
            FROM file_events
            WHERE DATE(timestamp) = DATE('now')
        """)
        hours = cursor.fetchone()
        
        conn.close()
        
        return {
            'date': today.isoformat(),
            'files_created': files_created,
            'apps_used': apps_used,
            'active_hours': {
                'start': hours[0] if hours[0] else 0,
                'end': hours[1] if hours[1] else 0
            },
            'productivity_score': self._calculate_productivity_score(files_created, apps_used)
        }
    
    def _calculate_productivity_score(self, files_created: int, apps_used: Dict) -> float:
        """Calculeaza un scor de productivitate (0-100)"""
        score = 0
        
        # Puncte pentru fisiere create
        score += min(30, files_created * 3)
        
        # Puncte pentru aplicatii productive
        productive_apps = {'VS Code', 'Python', 'Git', 'Sublime Text', 'Notepad++'}
        for app, time in apps_used.items():
            if any(prod_app.lower() in app.lower() for prod_app in productive_apps):
                score += min(20, time / 360)  # Max 20 puncte pentru 2 ore
        
        return min(100, score)


if __name__ == "__main__":
    # Test
    predictor = BehaviorPredictor()
    
    print("🔮 Predictie urmatoare actiune:")
    prediction = predictor.predict_next_action()
    if prediction:
        print(json.dumps(prediction, indent=2))
    else:
        print("Nu exista suficiente date pentru predictie")
    
    print("\n💡 Sugestii contextuale:")
    suggestions = predictor.get_contextual_suggestions()
    for sug in suggestions[:3]:
        print(f"- {sug['title']} (confidence: {sug['confidence']:.2f})")
    
    print("\n📊 Rezumat zilnic:")
    summary = predictor.get_daily_summary()
    print(json.dumps(summary, indent=2))
