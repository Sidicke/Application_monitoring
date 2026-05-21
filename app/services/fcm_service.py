import firebase_admin
from firebase_admin import credentials, messaging
import os
import logging

logger = logging.getLogger(__name__)

# Chemin vers la clé de service au niveau de la racine backend
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
cred_path = os.path.join(base_dir, "monitoring-637eb-firebase-adminsdk-fbsvc-2f15674456.json")

def init_firebase():
    """Initialise le SDK Admin Firebase."""
    try:
        if not firebase_admin._apps:
            # On garde le reste en dur, mais on sort la clé privée pour éviter le blocage GitHub
            private_key = os.getenv("FIREBASE_PRIVATE_KEY")
            
            if not private_key:
                # Fallback sur fichier local pour le dev (si présent)
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase initialisé via fichier JSON local.")
                    return
                else:
                    logger.warning("Clé privée FIREBASE_PRIVATE_KEY manquante et pas de fichier JSON.")
                    return

            firebase_config = {
                "type": "service_account",
                "project_id": "monitoring-637eb",
                "private_key_id": "2f15674456d2822bee6067148027a8577d169ae2",
                "private_key": private_key.replace("\\n", "\n"),
                "client_email": "firebase-adminsdk-fbsvc@monitoring-637eb.iam.gserviceaccount.com",
                "client_id": "108505626044135363165",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40monitoring-637eb.iam.gserviceaccount.com",
                "universe_domain": "googleapis.com"
            }
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialisé avec succès (via ENV Private Key).")
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
