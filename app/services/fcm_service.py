import firebase_admin
from firebase_admin import credentials, messaging
import os
import logging

logger = logging.getLogger(__name__)

# Chemin vers la clé de service au niveau de la racine backend
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
cred_path = os.path.join(base_dir, "monitoring-637eb-firebase-adminsdk-fbsvc-2f15674456.json")

def init_firebase():
    """Initialise le SDK Admin Firebase si nécessaire."""
    try:
        if not firebase_admin._apps:
            # Priorité 1 : Variable d'environnement (Production - Render)
            firebase_config = os.getenv("FIREBASE_CONFIG")
            if firebase_config:
                import json
                config_dict = json.loads(firebase_config)
                cred = credentials.Certificate(config_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialisé via variable d'environnement.")
                return

            # Priorité 2 : Fichier local (Développement)
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialisé via fichier JSON.")
            else:
                logger.warning(f"Configuration Firebase introuvable (ni ENV ni fichier à {cred_path})")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de Firebase : {e}")

async def send_push_notification(token: str, title: str, body: str, data: dict = None):
    """Envoie une notification push à un token spécifique."""
    if not firebase_admin._apps:
        init_firebase()
        
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=token,
        )
        response = messaging.send(message)
        return response
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi FCM : {e}")
        return None

async def send_topic_notification(topic: str, title: str, body: str, data: dict = None):
    """Envoie une notification push à un topic (groupe d'appareils)."""
    if not firebase_admin._apps:
        init_firebase()
        
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            topic=topic,
        )
        response = messaging.send(message)
        return response
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi au topic {topic} : {e}")
        return None
