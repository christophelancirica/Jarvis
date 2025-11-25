"""
system_monitor.py - Surveillance système (Hypothalamus)
Responsabilité : Monitoring santé, métriques, état du système
Nouveau module pour l'hypothalamus étendu
"""

import time
import psutil
import threading
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# Import logger depuis hypothalamus
sys.path.append(str(Path(__file__).parent.parent))
from hypothalamus.logger import log

class SystemMonitor:
    """Moniteur système centralisé (Hypothalamus)"""
    
    def __init__(self, monitoring_interval: float = 5.0):
        self.monitoring_interval = monitoring_interval
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Métriques système
        self.metrics = {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'memory_available_gb': 0.0,
            'disk_percent': 0.0,
            'temperature': None,
            'last_update': 0
        }
        
        # Seuils d'alerte
        self.thresholds = {
            'cpu_warning': 80.0,
            'cpu_critical': 95.0,
            'memory_warning': 85.0,
            'memory_critical': 95.0,
            'disk_warning': 90.0,
            'disk_critical': 95.0
        }
        
        # Historique pour tendances
        self.history = {
            'cpu': [],
            'memory': [],
            'timestamps': []
        }
        self.history_max_size = 100
        
        log.info("SystemMonitor initialisé (Hypothalamus)")
    
    def start_monitoring(self):
        """Démarre le monitoring en arrière-plan"""
        if self.is_monitoring:
            log.warning("Monitoring déjà actif")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        log.success("Monitoring système démarré")
    
    def stop_monitoring(self):
        """Arrête le monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        log.info("Monitoring système arrêté")
    
    def _monitoring_loop(self):
        """Boucle principale de monitoring"""
        while self.is_monitoring:
            try:
                self._update_metrics()
                self._check_thresholds()
                self._update_history()
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                log.error(f"Erreur monitoring: {e}")
                time.sleep(self.monitoring_interval * 2)  # Pause plus longue en cas d'erreur
    
    def _update_metrics(self):
        """Met à jour les métriques système"""
        try:
            # CPU
            self.metrics['cpu_percent'] = psutil.cpu_percent(interval=1)
            
            # Mémoire
            memory = psutil.virtual_memory()
            self.metrics['memory_percent'] = memory.percent
            self.metrics['memory_available_gb'] = memory.available / (1024**3)
            
            # Disque (partition racine)
            disk = psutil.disk_usage('/')
            self.metrics['disk_percent'] = disk.percent
            
            # Température (si disponible)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Prendre la première température disponible
                    first_sensor = list(temps.values())[0]
                    if first_sensor:
                        self.metrics['temperature'] = first_sensor[0].current
            except:
                self.metrics['temperature'] = None
            
            self.metrics['last_update'] = time.time()
            
        except Exception as e:
            log.error(f"Erreur mise à jour métriques: {e}")
    
    def _check_thresholds(self):
        """Vérifie les seuils et génère des alertes"""
        current_time = time.time()
        
        # CPU
        cpu = self.metrics['cpu_percent']
        if cpu > self.thresholds['cpu_critical']:
            log.warning(f"🚨 CPU critique: {cpu:.1f}%")
        elif cpu > self.thresholds['cpu_warning']:
            log.warning(f"⚠️  CPU élevé: {cpu:.1f}%")
        
        # Mémoire
        memory = self.metrics['memory_percent']
        if memory > self.thresholds['memory_critical']:
            log.warning(f"🚨 Mémoire critique: {memory:.1f}%")
        elif memory > self.thresholds['memory_warning']:
            log.warning(f"⚠️  Mémoire élevée: {memory:.1f}%")
        
        # Disque
        disk = self.metrics['disk_percent']
        if disk > self.thresholds['disk_critical']:
            log.warning(f"🚨 Disque critique: {disk:.1f}%")
        elif disk > self.thresholds['disk_warning']:
            log.warning(f"⚠️  Disque élevé: {disk:.1f}%")
    
    def _update_history(self):
        """Met à jour l'historique des métriques"""
        current_time = time.time()
        
        self.history['cpu'].append(self.metrics['cpu_percent'])
        self.history['memory'].append(self.metrics['memory_percent'])
        self.history['timestamps'].append(current_time)
        
        # Limiter la taille de l'historique
        if len(self.history['cpu']) > self.history_max_size:
            self.history['cpu'].pop(0)
            self.history['memory'].pop(0)
            self.history['timestamps'].pop(0)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques actuelles"""
        return {
            'success': True,
            'metrics': self.metrics.copy(),
            'thresholds': self.thresholds.copy(),
            'monitoring_active': self.is_monitoring
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Retourne les informations système détaillées"""
        try:
            import platform
            
            # Informations de base
            uname = platform.uname()
            
            # Processeur
            cpu_info = {
                'physical_cores': psutil.cpu_count(logical=False),
                'logical_cores': psutil.cpu_count(logical=True),
                'max_frequency': f"{psutil.cpu_freq().max:.2f}Mhz" if psutil.cpu_freq() else "N/A",
                'current_frequency': f"{psutil.cpu_freq().current:.2f}Mhz" if psutil.cpu_freq() else "N/A"
            }
            
            # Mémoire
            memory = psutil.virtual_memory()
            memory_info = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'percentage': memory.percent
            }
            
            # Disque
            disk = psutil.disk_usage('/')
            disk_info = {
                'total_gb': round(disk.total / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'percentage': disk.percent
            }
            
            return {
                'success': True,
                'system': {
                    'platform': uname.system,
                    'platform_release': uname.release,
                    'platform_version': uname.version,
                    'architecture': uname.machine,
                    'hostname': uname.node,
                    'processor': uname.processor,
                    'python_version': platform.python_version()
                },
                'cpu': cpu_info,
                'memory': memory_info,
                'disk': disk_info,
                'boot_time': psutil.boot_time()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_process_info(self, process_name: str = "python") -> Dict[str, Any]:
        """Retourne les informations sur les processus Jarvis/Python"""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
                try:
                    if process_name.lower() in proc.info['name'].lower():
                        # Vérifier si c'est un processus Jarvis
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'jarvis' in cmdline.lower():
                            processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'cpu_percent': proc.info['cpu_percent'],
                                'memory_percent': proc.info['memory_percent'],
                                'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'success': True,
                'processes': processes,
                'count': len(processes)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Retourne le statut de santé global"""
        metrics = self.metrics
        
        # Calculer le score de santé (0-100)
        health_score = 100
        
        # Pénalités selon les métriques
        if metrics['cpu_percent'] > self.thresholds['cpu_warning']:
            health_score -= 20
        if metrics['memory_percent'] > self.thresholds['memory_warning']:
            health_score -= 20
        if metrics['disk_percent'] > self.thresholds['disk_warning']:
            health_score -= 10
        
        # Statut global
        if health_score >= 80:
            status = "Excellent"
            color = "green"
        elif health_score >= 60:
            status = "Bon"
            color = "yellow"
        elif health_score >= 40:
            status = "Moyen"
            color = "orange"
        else:
            status = "Problème"
            color = "red"
        
        return {
            'success': True,
            'health_score': health_score,
            'status': status,
            'color': color,
            'metrics': metrics,
            'last_update': metrics['last_update']
        }

# Test standalone
if __name__ == "__main__":
    print("🧪 Test SystemMonitor (Hypothalamus)")
    
    monitor = SystemMonitor(monitoring_interval=2.0)
    
    try:
        # Test des métriques
        monitor._update_metrics()
        print(f"✅ Métriques: {monitor.get_current_metrics()}")
        
        # Test info système
        system_info = monitor.get_system_info()
        if system_info['success']:
            print(f"✅ Système: {system_info['system']['platform']} {system_info['system']['architecture']}")
            print(f"✅ CPU: {system_info['cpu']['logical_cores']} cores")
            print(f"✅ RAM: {system_info['memory']['total_gb']}GB")
        
        # Test health
        health = monitor.get_health_status()
        print(f"✅ Santé: {health['status']} ({health['health_score']}/100)")
        
        # Test monitoring (court)
        print("🔄 Test monitoring 5s...")
        monitor.start_monitoring()
        time.sleep(5)
        monitor.stop_monitoring()
        
        print("✅ Test SystemMonitor terminé")
        
    except Exception as e:
        print(f"❌ Erreur test: {e}")