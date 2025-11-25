"""
message_queue.py - Système de file d'attente pour les messages
Évite les traitements simultanés et les conflits
Nouveau module pour le dossier thalamus
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from collections import deque
import time
import hashlib
from pathlib import Path
import sys

# Import logger
sys.path.append(str(Path(__file__).parent.parent))
from hypothalamus.logger import log


class MessageQueue:
    """
    File d'attente intelligente pour éviter les traitements simultanés
    et les doublons de messages
    """
    
    def __init__(self, max_size: int = 100, dedup_window: float = 2.0):
        """
        Initialise la queue
        
        Args:
            max_size: Taille maximale de la queue
            dedup_window: Fenêtre de temps (secondes) pour la déduplication
        """
        self.queue = deque(maxlen=max_size)
        self.processing = False
        self.current_task: Optional[asyncio.Task] = None
        self.processing_lock = asyncio.Lock()
        
        # Système anti-duplication
        self.recent_hashes = {}  # hash -> timestamp
        self.dedup_window = dedup_window
        
        # Statistiques
        self.stats = {
            'processed': 0,
            'dropped': 0,
            'duplicates': 0,
            'errors': 0,
            'total_time': 0.0,
            'avg_processing_time': 0.0
        }
        
        log.info("MessageQueue initialisée (Thalamus)")
    
    def _compute_hash(self, message: Dict[str, Any]) -> str:
        """Calcule un hash unique pour un message"""
        # Créer une représentation stable du message
        content = message.get('content', '')
        msg_type = message.get('type', '')
        
        # Ignorer le timestamp pour le hash
        hash_str = f"{msg_type}:{content}"
        return hashlib.md5(hash_str.encode()).hexdigest()
    
    def _is_duplicate(self, message: Dict[str, Any]) -> bool:
        """Vérifie si un message est un doublon"""
        msg_hash = self._compute_hash(message)
        current_time = time.time()
        
        # Nettoyer les vieux hashes
        self.recent_hashes = {
            h: t for h, t in self.recent_hashes.items()
            if current_time - t < self.dedup_window * 2
        }
        
        # Vérifier si c'est un doublon
        if msg_hash in self.recent_hashes:
            time_diff = current_time - self.recent_hashes[msg_hash]
            if time_diff < self.dedup_window:
                self.stats['duplicates'] += 1
                log.debug(f"Message dupliqué ignoré (Δt={time_diff:.2f}s)")
                return True
        
        # Enregistrer le hash
        self.recent_hashes[msg_hash] = current_time
        return False
    
    async def add_message(self, message: Dict[str, Any]) -> bool:
        """
        Ajoute un message à la queue
        
        Args:
            message: Message à ajouter
            
        Returns:
            bool: True si ajouté, False sinon
        """
        # Vérifier les doublons
        if self._is_duplicate(message):
            return False
        
        # Vérifier la capacité
        if len(self.queue) >= self.queue.maxlen:
            self.stats['dropped'] += 1
            log.warning(f"Queue pleine ({self.queue.maxlen}), message ignoré: {message.get('type')}")
            return False
        
        # Ajouter timestamp si absent
        if 'timestamp' not in message:
            message['timestamp'] = time.time()
        
        # Ajouter le message
        self.queue.append(message)
        
        log.debug(f"Message ajouté: {message.get('type')} (position {len(self.queue)})")
        return True
    
    async def process_next(self, handler_func: Callable) -> bool:
        """
        Traite le prochain message de la queue
        
        Args:
            handler_func: Fonction pour traiter le message
            
        Returns:
            bool: True si un message a été traité
        """
        if not self.queue:
            return False
        
        async with self.processing_lock:
            if not self.queue:  # Double vérification après le lock
                return False
            
            message = self.queue.popleft()
            
            # Vérifier l'expiration (messages > 30s)
            age = time.time() - message.get('timestamp', 0)
            if age > 30:
                log.debug(f"Message expiré ignoré ({age:.1f}s): {message.get('type')}")
                return False
            
            # Traiter le message
            start_time = time.time()
            
            try:
                await handler_func(message)
                
                # Mettre à jour les stats
                processing_time = time.time() - start_time
                self.stats['processed'] += 1
                self.stats['total_time'] += processing_time
                
                if self.stats['processed'] > 0:
                    self.stats['avg_processing_time'] = (
                        self.stats['total_time'] / self.stats['processed']
                    )
                
                log.debug(f"Message traité en {processing_time:.2f}s: {message.get('type')}")
                return True
                
            except Exception as e:
                self.stats['errors'] += 1
                log.error(f"Erreur traitement message: {e}")
                return False
    
    async def process_queue(
        self, 
        handler_func: Callable,
        max_batch: int = 10,
        delay_between: float = 0.1
    ):
        """
        Traite la queue de messages par batch
        
        Args:
            handler_func: Fonction pour traiter chaque message
            max_batch: Nombre maximum de messages à traiter
            delay_between: Délai entre chaque message (secondes)
        """
        if self.processing:
            log.warning("Traitement déjà en cours")
            return
        
        self.processing = True
        processed_count = 0
        
        try:
            while self.queue and processed_count < max_batch:
                success = await self.process_next(handler_func)
                
                if success:
                    processed_count += 1
                    
                    # Pause entre messages pour éviter la surcharge
                    if delay_between > 0 and self.queue:
                        await asyncio.sleep(delay_between)
            
            if processed_count > 0:
                log.info(f"Batch traité: {processed_count} messages")
                
        finally:
            self.processing = False
    
    def clear(self, keep_stats: bool = False):
        """
        Vide la queue
        
        Args:
            keep_stats: Si True, conserve les statistiques
        """
        count = len(self.queue)
        self.queue.clear()
        self.recent_hashes.clear()
        
        if not keep_stats:
            self.stats = {
                'processed': 0,
                'dropped': 0,
                'duplicates': 0,
                'errors': 0,
                'total_time': 0.0,
                'avg_processing_time': 0.0
            }
        
        log.info(f"Queue vidée ({count} messages supprimés)")
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut détaillé de la queue"""
        return {
            'size': len(self.queue),
            'capacity': self.queue.maxlen,
            'utilization': len(self.queue) / self.queue.maxlen * 100,
            'processing': self.processing,
            'stats': self.stats.copy(),
            'dedup_cache_size': len(self.recent_hashes)
        }
    
    def peek(self, n: int = 5) -> list:
        """
        Aperçu des prochains messages sans les retirer
        
        Args:
            n: Nombre de messages à voir
            
        Returns:
            Liste des n prochains messages
        """
        preview = []
        for i, msg in enumerate(self.queue):
            if i >= n:
                break
            preview.append({
                'position': i + 1,
                'type': msg.get('type'),
                'age': time.time() - msg.get('timestamp', 0),
                'preview': str(msg.get('content', ''))[:50]
            })
        return preview
    
    async def wait_for_empty(self, timeout: float = 30.0) -> bool:
        """
        Attend que la queue soit vide
        
        Args:
            timeout: Temps maximum d'attente
            
        Returns:
            bool: True si la queue est vide, False si timeout
        """
        start_time = time.time()
        
        while self.queue or self.processing:
            if time.time() - start_time > timeout:
                return False
            await asyncio.sleep(0.1)
        
        return True


# Test standalone
if __name__ == "__main__":
    import asyncio
    
    async def test_handler(message: Dict[str, Any]):
        """Handler de test"""
        print(f"  Traitement: {message.get('type')} - {message.get('content')}")
        await asyncio.sleep(0.5)  # Simuler traitement
    
    async def test_queue():
        print("🧪 Test MessageQueue")
        
        queue = MessageQueue(max_size=10)
        
        # Test 1: Ajout de messages
        print("\n1️⃣ Ajout de messages...")
        messages = [
            {'type': 'text_message', 'content': 'Bonjour'},
            {'type': 'text_message', 'content': 'Bonjour'},  # Doublon
            {'type': 'voice_input', 'content': 'Test vocal'},
            {'type': 'text_message', 'content': 'Comment vas-tu?'},
        ]
        
        for msg in messages:
            added = await queue.add_message(msg)
            print(f"  {'✅' if added else '❌'} {msg}")
            await asyncio.sleep(0.1)
        
        # Test 2: Aperçu
        print("\n2️⃣ Aperçu de la queue:")
        preview = queue.peek(3)
        for item in preview:
            print(f"  {item}")
        
        # Test 3: Traitement
        print("\n3️⃣ Traitement par batch...")
        await queue.process_queue(test_handler, max_batch=5)
        
        # Test 4: Statistiques
        print("\n4️⃣ Statistiques:")
        status = queue.get_status()
        print(f"  Taille: {status['size']}/{status['capacity']}")
        print(f"  Traités: {status['stats']['processed']}")
        print(f"  Doublons: {status['stats']['duplicates']}")
        print(f"  Temps moyen: {status['stats']['avg_processing_time']:.2f}s")
        
        print("\n✅ Test terminé")
    
    asyncio.run(test_queue())
